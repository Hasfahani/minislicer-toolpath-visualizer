@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
if errorlevel 1 (
  echo.
  echo App run failed.
  exit /b %errorlevel%
)
