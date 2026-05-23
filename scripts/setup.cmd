@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 (
  echo.
  echo Setup failed.
  exit /b %errorlevel%
)
echo.
echo Setup completed successfully.
