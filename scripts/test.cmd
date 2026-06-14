REM Purpose: Windows shortcut that runs the PowerShell test script.
REM Reason: Gives Command Prompt users the same lint-and-test workflow.
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0test.ps1"
if errorlevel 1 (
  echo.
  echo Tests failed.
  exit /b %errorlevel%
)
echo.
echo Tests passed.
