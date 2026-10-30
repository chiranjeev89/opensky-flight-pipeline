@echo off
REM Stops all containers. Your data (Azurite, lake, Airflow DB) is kept.
cd /d "%~dp0"
docker compose down
echo Stopped. Run start.bat to continue collecting.
pause
