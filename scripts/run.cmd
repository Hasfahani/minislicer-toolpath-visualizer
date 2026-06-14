REM Purpose: Windows shortcut that runs the PowerShell app launcher.
REM Reason: Makes starting the Streamlit app easier for non-PowerShell workflows.
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
if errorlevel 1 (
  echo.
  echo App run failed.
  exit /b %errorlevel%
)
