@echo off
REM Double-click to start the whole pipeline (Docker Desktop must be running).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
REM BUG-007: keep the window open whatever happens, so errors stay visible.
echo.
echo Finished. Full log saved in start.log in this folder.
pause
