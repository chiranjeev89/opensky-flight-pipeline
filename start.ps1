# One-click start for Windows: checks Docker, creates .env, builds and starts the stack,
# runs the pipeline once end to end, opens Airflow + dashboard. Safe to run again any time.
# Usage: double-click start.bat   (or: powershell -ExecutionPolicy Bypass -File start.ps1)

# BUG-007: NOT "Stop". Windows PowerShell 5.1 turns any stderr line from a native
# command (docker prints progress to stderr) into a terminating error, which killed
# the script silently. We check $LASTEXITCODE after each docker call instead.
$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot
# Everything shown on screen is also saved to start.log, so errors can be read later.
try { Start-Transcript -Path "$PSScriptRoot\start.log" -Force | Out-Null } catch {}
trap { Write-Host "`nUNEXPECTED ERROR: $_" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

function Say($msg, $color = "Cyan") { Write-Host "`n==> $msg" -ForegroundColor $color }
function Fail($msg) { Write-Host "`nSTOPPED: $msg" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

# ---------- 1. Docker installed? ----------
Say "Checking Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Desktop is not installed."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $ans = Read-Host "Install it now with winget? (y/n)"
        if ($ans -eq "y") {
            winget install -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements
            Fail "Docker Desktop installed. RESTART your PC, open Docker Desktop once (accept terms), then run start.bat again."
        }
    }
    Fail "Install Docker Desktop from https://www.docker.com/products/docker-desktop/ then run start.bat again."
}

# ---------- 2. Docker engine running? ----------
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Say "Starting Docker Desktop (can take 1-3 minutes)" "Yellow"
    $exe = "$Env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $exe) { Start-Process $exe }
    $ok = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 5
        docker info *> $null
        if ($LASTEXITCODE -eq 0) { $ok = $true; break }
        Write-Host -NoNewline "."
    }
    if (-not $ok) { Fail "Docker engine did not start. Open Docker Desktop, wait for 'Engine running', run start.bat again. If it complains about WSL, run 'wsl --install' in an Administrator terminal and restart." }
}
Write-Host "Docker engine is running."

# ---------- 3. .env ----------
if (-not (Test-Path ".env")) {
    Say "Creating .env (your secrets stay on this PC, .env is git-ignored)"
    $content = Get-Content ".env.example" -Raw
    $id = Read-Host "OpenSky client_id (press Enter to skip = anonymous, 400 credits/day is still enough)"
    $secret = ""
    if ($id) {
        $sec = Read-Host "OpenSky client_secret" -AsSecureString
        $secret = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
    }
    $jwt = -join ((48..57) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
    $content = $content -replace "(?m)^OPENSKY_CLIENT_ID=.*$", "OPENSKY_CLIENT_ID=$id"
    $content = $content -replace "(?m)^OPENSKY_CLIENT_SECRET=.*$", "OPENSKY_CLIENT_SECRET=$secret"
    $content = $content -replace "(?m)^AIRFLOW_JWT_SECRET=.*$", "AIRFLOW_JWT_SECRET=$jwt"
    # Write without BOM and with LF endings so Docker reads it cleanly
    [IO.File]::WriteAllText("$PSScriptRoot\.env", ($content -replace "`r`n", "`n"), (New-Object Text.UTF8Encoding $false))
    Write-Host ".env created."
} else { Write-Host ".env already exists, keeping it." }

# ---------- 4. Build + start ----------
Say "Building images and starting containers (first time: 5-15 minutes)"
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Fail "docker compose up failed. Read the red error text above; see docs/OPERATIONS.md." }

# ---------- 5. Wait for Airflow ----------
Say "Waiting for Airflow API server on http://localhost:8080"
$up = $false
for ($i = 0; $i -lt 120; $i++) {
    try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://localhost:8080/api/v2/version"; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {}
    Start-Sleep -Seconds 5; Write-Host -NoNewline "."
}
if (-not $up) { docker compose ps; Fail "Airflow did not become healthy in 10 min. Run: docker compose logs airflow-apiserver --tail 80  to see why." }
Write-Host "Airflow is up."

function AF([string[]]$cliArgs) { docker compose exec -T airflow-scheduler airflow @cliArgs 2>$null }

function Wait-Run($dag, $minutes) {
    for ($i = 0; $i -lt ($minutes * 6); $i++) {
        Start-Sleep -Seconds 10
        $json = (AF @("dags", "list-runs", $dag, "-o", "json")) -join ""
        try { $runs = $json | ConvertFrom-Json } catch { continue }
        $last = $runs | Select-Object -First 1
        if ($last.state -eq "success") { return "success" }
        if ($last.state -eq "failed")  { return "failed" }
        Write-Host -NoNewline "."
    }
    return "timeout"
}

# ---------- 6. Run the pipeline once now (instead of waiting for the schedule) ----------
Say "Waiting for the DAGs to be parsed"
for ($i = 0; $i -lt 30; $i++) { if ((AF @("dags", "list")) -match "opensky_ingest") { break }; Start-Sleep -Seconds 5 }
AF @("dags", "unpause", "opensky_ingest") | Out-Null
AF @("dags", "unpause", "flight_transform") | Out-Null

Say "Run 1/2: opensky_ingest (OpenSky -> Azure Blob)"
AF @("dags", "trigger", "opensky_ingest") | Out-Null
$s1 = Wait-Run "opensky_ingest" 5
Write-Host " $s1"
if ($s1 -ne "success") { Fail "Ingest did not succeed. Open http://localhost:8080 -> opensky_ingest -> the red task -> Logs." }

Say "Run 2/2: flight_transform (sync -> dbt build + tests -> publish)"
AF @("dags", "trigger", "flight_transform") | Out-Null
$s2 = Wait-Run "flight_transform" 10
Write-Host " $s2"
if ($s2 -ne "success") { Fail "Transform did not succeed. Open http://localhost:8080 -> flight_transform -> the red task -> Logs." }

# ---------- 7. Done ----------
Say "ALL GREEN. The pipeline now runs by itself: ingest every 10 min, transform hourly at :05." "Green"
docker compose ps --format "table {{.Service}}\t{{.State}}\t{{.Status}}"
Start-Process "http://localhost:8080"
Start-Process "http://localhost:8501"
Write-Host "`nAirflow:   http://localhost:8080"
Write-Host "Dashboard: http://localhost:8501"
Write-Host "Stop with stop.bat (data is kept). Keep the PC on and Docker running to collect data."
Read-Host "`nPress Enter to close"
