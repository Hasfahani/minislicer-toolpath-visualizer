# Purpose: Coordinates quick setup, sample loading, sidebar sections, and setup progress.
# Reason: Central sidebar orchestration keeps app.py from knowing every widget detail.
"""Top setup and sidebar orchestration for MiniSlicer."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.profiles import QUALITY_PROFILES
from src.scenarios import option_index, scenario_names, scenario_overrides
from ui.process_controls import (
    render_business_controls,
    render_ded_controls,
    render_placement_controls,
    render_preview_controls,
    render_print_controls,
    render_toolpath_controls,
)
from ui.shape_controls import render_shape_controls
from ui.stl_workflow import render_import_controls


def render_quick_setup() -> dict[str, Any]:
    overrides = st.session_state.get("_overrides", {})
    plate_options = ["None", "220 x 220", "300 x 300"]
    profile_options = ["Custom", *QUALITY_PROFILES.keys()]
    process_options = ["FDM", "Metal (LPBF/DED)"]

    def _plate_default() -> str:
        value = overrides.get("quick_plate", "220 x 220")
        return value if value in plate_options else "220 x 220"

    def _process_default() -> str:
        value = overrides.get("process_mode", "FDM")
        return value if value in process_options else "FDM"

    with st.expander("Quick Setup", expanded=True, icon=":material/tune:"):
        st.caption(
            "Start here: set the job mode, then refine the details in the left sidebar. "
            "Switch Controls to Advanced to unlock fine-grained overrides everywhere."
        )

        sc1, sc2 = st.columns([3, 1])
        scenario = sc1.selectbox(
            "Load a sample job", ["Manual setup", *scenario_names()],
            help="One-click demo configurations that populate the controls below.",
        )
        sc2.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        if sc2.button(
            "Load", width="stretch", icon=":material/download:",
            disabled=scenario == "Manual setup",
            help="Apply the selected sample job to every control.",
        ):
            st.session_state["_overrides"] = scenario_overrides(scenario)
            st.rerun()

        if overrides:
            st.caption(
                f"Loaded preset applied to {len(overrides)} controls. "
                "Tweak anything, or press Reset to clear."
            )

        qs1, qs2, qs3, qs4, qs5 = st.columns([1.5, 1.4, 1.1, 1.3, 0.7])
        profile = qs1.selectbox(
            "Quality profile", profile_options,
            index=option_index(profile_options, overrides.get("profile"), 3),
            help="One-click starting point for perimeters, layer height, and speed.",
        )
        quick_plate = qs2.segmented_control(
            "Build plate", plate_options, default=_plate_default(),
            help="Reference build area drawn behind the part.",
        )
        control_mode = qs3.segmented_control(
            "Controls", ["Basic", "Advanced"], default="Basic",
            help="Advanced unlocks fine-grained overrides in every sidebar section.",
        )
        process_mode = qs4.segmented_control(
            "Process", process_options, default=_process_default(),
            help="FDM polymer printing, or metal LPBF / wire-arc DED planning.",
        )
        qs5.markdown("<div style='height:1.55rem'></div>", unsafe_allow_html=True)
        if qs5.button(
            "Reset", help="Clear all settings and start fresh",
            width="stretch", icon=":material/restart_alt:",
        ):
            st.session_state.clear()
            st.rerun()

    default = QUALITY_PROFILES.get(profile, QUALITY_PROFILES["Balanced"])
    return {
        "profile": profile,
        "quick_plate": quick_plate,
        "control_mode": control_mode,
        "process_mode": process_mode,
        "advanced": control_mode == "Advanced",
        "default": default,
    }


def render_sidebar(
    default: dict[str, float | int],
    profile: str,
    quick_plate: str,
    process_mode: str,
    advanced: bool,
    shapes: list[str],
    patterns: list[str],
    shape_icons: dict[str, str],
    pattern_icons: dict[str, str],
) -> dict[str, Any]:
    with st.sidebar:
        st.markdown("## Job controls")
        st.caption("Work top to bottom. Each numbered section expands; Advanced mode adds overrides.")

        # Workflow order: source -> geometry -> toolpath -> process -> layout -> look -> commercial.
        values: dict[str, Any] = {}
        values.update(render_import_controls())
        values.update(
            render_shape_controls(
                shapes,
                shape_icons,
                values["uploaded_svg"] is not None or values["uploaded_stl"] is not None,
            )
        )
        values.update(render_toolpath_controls(default, patterns, pattern_icons, advanced))
        values.update(render_print_controls(default, advanced, values["stl_info"]))
        values.update(render_ded_controls(process_mode, advanced))
        values.update(render_placement_controls(quick_plate, advanced))
        values.update(render_preview_controls(advanced))
        values.update(render_business_controls(advanced))

        st.divider()
        checks = [
            ("Import", values["uploaded_stl"] is not None or values["uploaded_svg"] is not None),
            ("Profile", profile != "Custom"
                or values["printer_profile_name"] != values["available_profiles"][0]),
            ("Plate", quick_plate != "None"),
            ("Advanced", advanced),
        ]
        done = sum(1 for _, ok in checks if ok)
        progress_text = "  |  ".join(
            f"OK {name}" if ok else f"-- {name}" for name, ok in checks
        )
        st.progress(done / len(checks), text=f"Setup  {done}/{len(checks)}")
        st.caption(progress_text)

    return values
