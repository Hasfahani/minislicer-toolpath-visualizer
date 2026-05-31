"""Process, placement, and preview controls for MiniSlicer."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.metrics import MATERIAL_DENSITY
from src.profiles import PRINTER_PROFILES, profile_names


def render_toolpath_controls(
    default: dict[str, float | int],
    patterns: list[str],
    pattern_icons: dict[str, str],
    advanced: bool,
) -> dict[str, Any]:
    with st.expander("Toolpath", expanded=True):
        tc1, tc2 = st.columns(2)
        perimeter_count = tc1.slider("Perimeters", 1, 10, int(default["perimeters"]))
        perimeter_spacing = tc2.number_input("Perim. spacing (mm)", 0.1, value=1.0, step=0.1)

        infill_pattern = st.selectbox(
            "Infill pattern", patterns, index=0,
            format_func=lambda p: f"{pattern_icons.get(p, '')} {p}",
        )

        ic1, ic2 = st.columns([1, 2])
        infill_mode = ic1.radio("Fill by", ["Spacing", "Density"], horizontal=False)
        if infill_mode == "Density":
            infill_density = ic2.slider("Density (%)", 5, 100, 25, 5)
            infill_spacing = 3.0
        else:
            infill_spacing = ic2.number_input(
                "Spacing (mm)", 0.1, value=float(default["spacing"]), step=0.1,
            )
            infill_density = 25

        if advanced:
            st.markdown("**Advanced Toolpath**")
            infill_angle = st.slider("Infill angle (deg)", -90, 90, 45, 5)
            alternate_angle = st.checkbox("Alternate angle each layer", value=False)
            a1, a2 = st.columns(2)
            infill_clearance = a1.number_input("Wall clearance (mm)", 0.0, value=0.0, step=0.1)
            infill_overlap = a2.number_input("Infill overlap (mm)", 0.0, value=0.0, step=0.05)
            perimeter_speed_mult = st.slider(
                "Perimeter speed mult.", 0.2, 1.5, 0.8, 0.05,
                help="Multiplier applied to print speed for perimeters.",
            )
        else:
            infill_angle = 45
            alternate_angle = False
            infill_clearance = 0.0
            infill_overlap = 0.0
            perimeter_speed_mult = 0.8

    return locals()


def render_print_controls(default: dict[str, float | int], advanced: bool, stl_info: Any) -> dict[str, Any]:
    with st.expander("Print Settings", expanded=False):
        available_profiles = profile_names()
        custom_profile_name = available_profiles[0]
        printer_profile_name = st.selectbox("Printer profile", available_profiles, index=0)
        printer_profile = PRINTER_PROFILES[printer_profile_name]
        if printer_profile_name != custom_profile_name:
            st.caption(f"_{printer_profile.description}_")

        use_profile = printer_profile_name != custom_profile_name
        prof_speed = printer_profile.scan_speed_mm_s if use_profile else float(default["speed"])
        prof_lh = printer_profile.layer_thickness_mm if use_profile else float(default["layer_height"])
        prof_mat = printer_profile.material if use_profile else "PLA"

        default_model_height = float(stl_info.height) if stl_info is not None and stl_info.height > 0 else 5.0
        ps1, ps2 = st.columns(2)
        layer_number = ps1.number_input("Layer #", min_value=1, value=1, step=1)
        model_height = ps2.number_input("Model height (mm)", 0.05, value=default_model_height, step=0.5)

        material_choice = st.selectbox(
            "Material", list(MATERIAL_DENSITY.keys()),
            index=list(MATERIAL_DENSITY.keys()).index(prof_mat)
            if prof_mat in MATERIAL_DENSITY else 0,
        )
        material_cost = st.number_input("Material cost ($/kg)", 0.0, value=24.0, step=1.0)

        if advanced:
            st.markdown("**Advanced Print**")
            av1, av2 = st.columns(2)
            layer_height = av1.number_input("Layer height (mm)", 0.05, value=prof_lh, step=0.01)
            nozzle_diameter = av2.number_input(
                "Nozzle diameter (mm)", 0.1,
                value=printer_profile.hatch_spacing_mm if use_profile else 0.4,
                step=0.05,
            )
            sv1, sv2 = st.columns(2)
            print_speed = sv1.number_input("Print speed (mm/s)", 0.1, value=prof_speed, step=1.0)
            travel_speed = sv2.number_input(
                "Travel speed (mm/s)", 0.1, value=max(100.0, prof_speed * 2), step=5.0,
            )
            fd1, fd2 = st.columns(2)
            filament_diameter = fd1.selectbox("Filament diameter (mm)", [1.75, 2.85])
            acceleration_mm_s2 = fd2.number_input("Accel (mm/s^2)", 10.0, value=500.0, step=50.0)
        else:
            layer_height = prof_lh
            nozzle_diameter = printer_profile.hatch_spacing_mm if use_profile else 0.4
            print_speed = prof_speed
            travel_speed = max(100.0, prof_speed * 2)
            filament_diameter = 1.75
            acceleration_mm_s2 = 500.0

    return locals()


def render_placement_controls(quick_plate: str, advanced: bool) -> dict[str, Any]:
    with st.expander("Placement", expanded=False):
        show_plate = st.checkbox("Show build plate", value=quick_plate != "None")
        plate_default = 300.0 if "300" in quick_plate else 220.0

        pl1, pl2 = st.columns(2)
        scale_pct = pl1.slider("Scale (%)", 10, 300, 100, 5)
        rotate_deg = pl2.slider("Rotate (deg)", -180, 180, 0, 5)
        center_on_plate = st.checkbox("Center on plate", value=show_plate)

        if advanced:
            fit_to_plate = st.checkbox("Fit inside plate", value=False, disabled=not show_plate)
            plate_margin = st.number_input("Plate margin (mm)", 0.0, value=5.0, step=1.0)
            ap1, ap2 = st.columns(2)
            plate_w = ap1.number_input("Plate width (mm)", 10.0, value=plate_default, step=10.0)
            plate_d = ap2.number_input("Plate depth (mm)", 10.0, value=plate_default, step=10.0)
            mc1, mc2 = st.columns(2)
            mirror_x = mc1.checkbox("Mirror X", value=False)
            mirror_y = mc2.checkbox("Mirror Y", value=False)
            tx1, tx2 = st.columns(2)
            translate_x = tx1.number_input("Translate X (mm)", value=0.0, step=1.0)
            translate_y = tx2.number_input("Translate Y (mm)", value=0.0, step=1.0)
        else:
            fit_to_plate = False
            plate_margin = 5.0
            plate_w = plate_default
            plate_d = plate_default
            mirror_x = False
            mirror_y = False
            translate_x = 0.0
            translate_y = 0.0

    return locals()


def render_preview_controls(advanced: bool) -> dict[str, Any]:
    with st.expander("Preview Appearance", expanded=False):
        scheme_options = ["Classic", "Colorblind", "Dark", "Neon", "High Contrast"]
        color_scheme = st.selectbox("Color scheme", scheme_options, index=0)
        line_width_scale = st.slider("Line thickness", 0.5, 3.0, 1.0, 0.25)

        pv1, pv2 = st.columns(2)
        show_boundary = pv1.checkbox("Outline", value=True)
        show_perimeters = pv1.checkbox("Perimeters", value=True)
        show_infill = pv1.checkbox("Infill", value=True)
        show_dimensions = pv1.checkbox("Dimensions", value=True)
        show_travel = pv2.checkbox("Travel moves", value=False)
        show_seams = pv2.checkbox("Seam markers", value=False)
        show_start_end = pv2.checkbox("Start/end points", value=False)
        show_arrows = pv2.checkbox("Direction arrows", value=False)
        show_extrusion = pv2.checkbox("Extrusion width", value=False)

    if advanced:
        with st.expander("Quality / Export", expanded=False):
            optimize_perimeters = st.checkbox("Optimize perimeter order", value=False)
            optimize_infill = st.checkbox("Optimize infill order", value=True)
            reverse_lines = st.checkbox(
                "Allow line reversal", value=True, disabled=not optimize_infill,
            )
            q1, q2 = st.columns(2)
            simplify_tolerance = q1.number_input("Simplify tol. (mm)", 0.0, value=0.0, step=0.01)
            min_segment_length = q2.number_input("Min seg. len (mm)", 0.0, value=0.0, step=0.05)
            ex1, ex2 = st.columns(2)
            z_hop = ex1.number_input("Z-hop (mm)", 0.0, value=0.0, step=0.05)
            extrusion_per_mm = ex2.number_input("E/mm", 0.0, value=0.04, step=0.005)
            include_e = st.checkbox("Include E values in G-code", value=False)
    else:
        optimize_perimeters = False
        optimize_infill = True
        reverse_lines = True
        simplify_tolerance = 0.0
        min_segment_length = 0.0
        z_hop = 0.0
        include_e = False
        extrusion_per_mm = 0.04

    return locals()
