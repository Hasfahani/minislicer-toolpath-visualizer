# Purpose: Smoke-tests first-run company workspace initialization.
# Reason: A fresh deployment must render a secure administrator bootstrap flow.
"""Smoke test for the authenticated Company Operations page."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_process_intelligence_page_renders_admin_bootstrap(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINISLICER_DB_PATH", str(tmp_path / "company.db"))
    app = AppTest.from_file("pages/process_intelligence.py")
    app.run(timeout=60)

    assert not app.exception
    assert any("Create the first administrator" in item.value for item in app.info)
