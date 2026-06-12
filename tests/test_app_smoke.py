"""Smoke tests for the Streamlit application shell.

These tests render the real app with streamlit.testing and exercise the
three top-level setting modes (default, Advanced controls, Metal process).
They lock the settings contract between the sidebar control modules and
app.py: a control key that goes missing fails here instead of at demo time.
"""

from streamlit.testing.v1 import AppTest


def _run_app() -> AppTest:
    app = AppTest.from_file("app.py")
    app.run(timeout=60)
    assert not app.exception
    return app


def _set_segmented_control(app: AppTest, label: str, value: str) -> None:
    # Segmented controls surface as button_group elements in AppTest.
    for control in app.get("button_group"):
        if control.label == label:
            control.set_value(value)
            app.run(timeout=60)
            return
    raise AssertionError(f"No segmented control labeled {label!r} found")


def test_streamlit_app_loads_default_dashboard() -> None:
    app = _run_app()

    assert [tab.label for tab in app.tabs] == ["Design", "Plan", "Release"]


def test_streamlit_app_runs_with_advanced_controls() -> None:
    app = _run_app()

    _set_segmented_control(app, "Controls", "Advanced")

    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Design", "Plan", "Release"]


def test_streamlit_app_runs_in_metal_mode_with_advanced_controls() -> None:
    app = _run_app()

    _set_segmented_control(app, "Process", "Metal (LPBF/DED)")
    _set_segmented_control(app, "Controls", "Advanced")

    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Design", "Plan", "Release"]
