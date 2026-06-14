# Purpose: Smoke-tests the tutorial/guide page and its goal selector.
# Reason: The guide is part of the interview demo, so it should not silently break.
"""Smoke test for the advanced guide page so it cannot silently break."""

from streamlit.testing.v1 import AppTest


def test_tutorial_page_renders_without_exception() -> None:
    app = AppTest.from_file("pages/tutorial.py")
    app.run(timeout=60)
    assert not app.exception


def test_tutorial_goal_selector_switches_without_error() -> None:
    app = AppTest.from_file("pages/tutorial.py")
    app.run(timeout=60)
    assert not app.exception

    selectors = app.get("selectbox")
    assert selectors, "expected at least one selectbox on the tutorial page"
    selectors[0].set_value("Production G-code readiness")
    app.run(timeout=60)
    assert not app.exception
