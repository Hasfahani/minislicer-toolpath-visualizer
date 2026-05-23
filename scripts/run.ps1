$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    Write-Error "Virtual environment not found. Run .\\scripts\\setup.ps1 first."
}

& .\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
