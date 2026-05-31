"""Top setup and sidebar orchestration for MiniSlicer."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.profiles import QUALITY_PROFILES
from ui.process_controls import (
    render_placement_controls,
    render_preview_controls,
    render_print_controls,
    render_toolpath_controls,
)
from ui.shape_controls import render_shape_controls
from ui.stl_workflow import render_import_controls


def render_quick_setup() -> dict[str, Any]:
    with st.expander("Quick Setup", expanded=True):
        qs1, qs2, qs3, qs4, qs5 = st.columns([1.4, 1.3, 1.1, 1.1, 0.8])
        profile = qs1.selectbox(
            "Quality profile", ["Custom", *QUALITY_PROFILES.keys()], index=3,
            help="Sets perimeters, layer height, and speed as a starting point.",
        )
        quick_plate = qs2.segmented_control(
            "Build plate", ["None", "220 x 220", "300 x 300"], default="220 x 220",
        )
        control_mode = qs3.segmented_control(
            "Controls", ["Basic", "Advanced"], default="Basic",
            help="Advanced unlocks fine-grained overrides.",
        )
        process_mode = qs4.segmented_control("Process", ["FDM", "DED / Metal"], default="FDM")
        if qs5.button("Reset", help="Reset all settings to defaults", width="stretch"):
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
    advanced: bool,
    shapes: list[str],
    patterns: list[str],
    shape_icons: dict[str, str],
    pattern_icons: dict[str, str],
) -> dict[str, Any]:
    with st.sidebar:
        st.markdown("## Settings")

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
        values.update(render_placement_controls(quick_plate, advanced))
        values.update(render_preview_controls(advanced))

        st.divider()
        configured = sum([
            values["uploaded_stl"] is not None or values["uploaded_svg"] is not None,
            profile != "Custom" or values["printer_profile_name"] != values["available_profiles"][0],
            quick_plate != "None",
            advanced,
        ])
        labels = ["Import", "Profile", "Plate", "Advanced"]
        progress_text = "  |  ".join(
            f"OK {labels[i]}" if i < configured else f"-- {labels[i]}"
            for i in range(4)
        )
        st.progress(configured / 4, text=f"Setup  {configured}/4")
        st.caption(progress_text)

    return values
