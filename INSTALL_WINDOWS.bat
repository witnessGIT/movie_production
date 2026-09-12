@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\setup_windows.ps1"
if errorlevel 1 (
  echo.
  echo Installation failed. Please read the error above.
  pause
  exit /b 1
)
echo.
echo Installation completed.
pause
