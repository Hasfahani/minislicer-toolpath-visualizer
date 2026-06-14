# Purpose: Creates the virtual environment and installs runtime plus development dependencies.
# Reason: A repeatable setup script makes onboarding, demos, and testing easier on Windows.
param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "[MiniSlicer] Setting up virtual environment..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    & $PythonExe -m venv .venv
}

Write-Host "[MiniSlicer] Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

Write-Host "[MiniSlicer] Installing dependencies (runtime + dev tools)..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

Write-Host "[MiniSlicer] Setup complete." -ForegroundColor Green
Write-Host "Run .\\scripts\\run.ps1 to start the app." -ForegroundColor Green
