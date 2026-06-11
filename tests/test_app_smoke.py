"""Smoke tests for the Streamlit application shell."""

from streamlit.testing.v1 import AppTest


def test_streamlit_app_loads_default_dashboard() -> None:
    app = AppTest.from_file("app.py")

    app.run(timeout=30)

    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Design", "Plan", "Release"]
