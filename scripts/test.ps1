# Purpose: Runs ruff linting and pytest from the local virtual environment.
# Reason: One test command gives a reliable pre-demo and pre-commit quality check.
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    Write-Error "Virtual environment not found. Run .\\scripts\\setup.ps1 first."
}

& .\.venv\Scripts\Activate.ps1

Write-Host "[MiniSlicer] Linting (ruff)..." -ForegroundColor Cyan
python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Lint failed."
}

Write-Host "[MiniSlicer] Running tests (pytest)..." -ForegroundColor Cyan
python -m pytest -q
