# BUG-007: start.bat window closed right after the OpenSky prompt
Symptom (first real run on Windows, 2026-10-30): pressing Enter at the client_id prompt closed the window; no error visible.
Root cause: `$ErrorActionPreference = "Stop"` in start.ps1. In Windows PowerShell 5.1, stderr output from a native command (`docker compose` writes build progress to stderr) is wrapped as an error record, which "Stop" makes terminating. The script died at `docker compose up` and the window closed.
Fix: `$ErrorActionPreference = "Continue"` (exit codes are already checked with `$LASTEXITCODE`), a `trap` that prints any unexpected error and waits, `Start-Transcript` to start.log, and `pause` at the end of start.bat.
Verification: pending second run on Windows.
Lesson: on Windows PowerShell 5.1 never combine EAP=Stop with native CLI tools.
