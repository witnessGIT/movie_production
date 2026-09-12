@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\dev.ps1"
if errorlevel 1 (
  echo.
  echo Start failed. If this is the first run, double-click INSTALL_WINDOWS.bat first.
  pause
  exit /b 1
)
