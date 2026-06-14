REM Purpose: Windows shortcut that runs the PowerShell setup script.
REM Reason: Lets users double-click or call setup from Command Prompt without typing PowerShell flags.
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
