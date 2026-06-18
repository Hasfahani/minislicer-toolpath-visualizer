# Purpose: Smoke-tests the process-intelligence workspace without a dataset.
# Reason: The company-data workflow must render safely before evidence is available.
"""Smoke test for the Process Intelligence page."""

from streamlit.testing.v1 import AppTest


def test_process_intelligence_page_renders_in_collection_mode() -> None:
    app = AppTest.from_file("pages/process_intelligence.py")
    app.run(timeout=60)

    assert not app.exception
    assert any("No qualified dataset loaded" in item.value for item in app.info)
