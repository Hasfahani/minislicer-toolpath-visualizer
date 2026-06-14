# Purpose: Renders toolpath, print, business, DED, placement, and preview controls.
# Reason: Process controls are grouped here to keep sidebar logic organized and reusable.
"""Process, placement, and preview controls for MiniSlicer."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.metrics import MATERIAL_DENSITY
from src.profiles import PRINTER_PROFILES, profile_names
from src.scenarios import as_float, as_int, option_index


def _overrides() -> dict[str, Any]:
    """Active control overrides set by a loaded scenario or re-applied config."""
    return st.session_state.get("_overrides", {})


def render_toolpath_controls(
    default: dict[str, float | int],
    patterns: list[str],
    pattern_icons: dict[str, str],
    advanced: bool,
) -> dict[str, Any]:
    ov = _overrides()
    fill_modes = ["Spacing", "Density"]
    with st.expander("2 - Toolpath", expanded=True, icon=":material/route:"):
        tc1, tc2 = st.columns(2)
        perimeter_count = tc1.slider(
            "Perimeters", 1, 10,
            max(1, min(10, as_int(ov.get("perimeter_count"), int(default["perimeters"])))),
            help="Number of outline walls around the part.",
        )
        perimeter_spacing = tc2.number_input(
            "Perim. spacing (mm)", 0.1, value=1.0, step=0.1,
            help="Distance between adjacent perimeter walls.",
        )

        infill_pattern = st.selectbox(
            "Infill pattern", patterns,
            index=option_index(patterns, ov.get("infill_pattern"), 0),
            format_func=lambda p: f"{pattern_icons.get(p, '')} {p}",
            help="Interior fill style. Compare options in the Plan tab.",
        )

        ic1, ic2 = st.columns([1, 2])
        infill_mode = ic1.radio(
            "Fill by", fill_modes, index=option_index(fill_modes, ov.get("infill_mode"), 0),
            horizontal=False,
            help="Spacing sets line gap directly; Density derives it from a percentage.",
        )
        if infill_mode == "Density":
            infill_density = ic2.slider(
                "Density (%)", 5, 100, max(5, min(100, as_int(ov.get("infill_density"), 25))), 5,
            )
            infill_spacing = 3.0
        else:
            infill_spacing = ic2.number_input(
                "Spacing (mm)", 0.1,
                value=as_float(ov.get("infill_spacing"), float(default["spacing"])), step=0.1,
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

    return {
        "perimeter_count": perimeter_count,
        "perimeter_spacing": perimeter_spacing,
        "infill_pattern": infill_pattern,
        "infill_mode": infill_mode,
        "infill_density": infill_density,
        "infill_spacing": infill_spacing,
        "infill_angle": infill_angle,
        "alternate_angle": alternate_angle,
        "infill_clearance": infill_clearance,
        "infill_overlap": infill_overlap,
        "perimeter_speed_mult": perimeter_speed_mult,
    }


def render_print_controls(default: dict[str, float | int], advanced: bool, stl_info: Any) -> dict[str, Any]:
    with st.expander("3 - Print settings", expanded=False, icon=":material/print:"):
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

        ov = _overrides()
        default_model_height = float(stl_info.height) if stl_info is not None and stl_info.height > 0 else 5.0
        ps1, ps2 = st.columns(2)
        layer_number = ps1.number_input(
            "Layer #", min_value=1, value=max(1, as_int(ov.get("layer_number"), 1)), step=1,
        )
        model_height = ps2.number_input(
            "Model height (mm)", 0.05,
            value=as_float(ov.get("model_height"), default_model_height), step=0.5,
        )

        material_keys = list(MATERIAL_DENSITY.keys())
        default_material_index = material_keys.index(prof_mat) if prof_mat in material_keys else 0
        material_choice = st.selectbox(
            "Material", material_keys,
            index=option_index(material_keys, ov.get("material_choice"), default_material_index),
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

    return {
        "available_profiles": available_profiles,
        "printer_profile_name": printer_profile_name,
        "layer_number": layer_number,
        "model_height": model_height,
        "material_choice": material_choice,
        "material_cost": material_cost,
        "layer_height": layer_height,
        "nozzle_diameter": nozzle_diameter,
        "print_speed": print_speed,
        "travel_speed": travel_speed,
        "filament_diameter": filament_diameter,
        "acceleration_mm_s2": acceleration_mm_s2,
    }


def render_business_controls(advanced: bool) -> dict[str, Any]:
    """Render launch, quoting, and customer-facing planning controls."""
    ov = _overrides()
    with st.expander("6 - Business / Launch", expanded=False, icon=":material/payments:"):
        job_name = st.text_input("Job name", value=str(ov.get("job_name", "MiniSlicer planning run")))
        c1, c2 = st.columns(2)
        customer_name = c1.text_input("Customer", value=str(ov.get("customer_name", "Internal")))
        owner_name = c2.text_input("Owner", value="Engineering")
        job_id = st.text_input("Job ID", value="MS-PLN-001")

        q1, q2 = st.columns(2)
        batch_quantity = q1.number_input(
            "Batch qty", min_value=1, value=max(1, as_int(ov.get("batch_quantity"), 1)), step=1,
        )
        target_unit_price = q2.number_input(
            "Target $/part", min_value=0.0,
            value=max(0.0, as_float(ov.get("target_unit_price"), 0.0)), step=5.0,
        )

        application_type = st.selectbox(
            "Application",
            [
                "General machine component",
                "Wear part / crusher component",
                "Aerospace tooling",
                "Repair / cladding",
                "Bridge production / spare part",
            ],
        )
        route_col, urgency_col = st.columns(2)
        conventional_route = route_col.selectbox(
            "Conventional route",
            ["Casting", "Forging", "Machining from billet", "Weld fabrication"],
        )
        urgency = urgency_col.selectbox(
            "Delivery driver",
            ["Normal procurement", "Expedite", "Line-down / launch critical"],
        )
        qualification_level = st.selectbox(
            "Qualification level",
            ["Prototype", "Industrial", "Aerospace / safety critical"],
        )
        material_strategy = st.selectbox(
            "Material strategy",
            ["Single material", "Wear-facing / gradient", "Repair overlay"],
        )

        quote_profile = st.segmented_control(
            "Quote profile",
            ["Startup", "Service Bureau", "Enterprise Pilot"],
            default="Service Bureau",
            help="Sets default costing assumptions; Advanced mode lets you override them.",
        ) or "Service Bureau"
        preset_rates = {
            "Startup": {
                "machine_rate_per_h": 12.0,
                "labor_rate_per_h": 35.0,
                "setup_time_min": 10.0,
                "postprocess_time_min": 6.0,
                "scrap_allowance_pct": 6.0,
                "margin_pct": 25.0,
                "max_lead_time_h": 36.0,
            },
            "Service Bureau": {
                "machine_rate_per_h": 18.0,
                "labor_rate_per_h": 45.0,
                "setup_time_min": 12.0,
                "postprocess_time_min": 8.0,
                "scrap_allowance_pct": 8.0,
                "margin_pct": 35.0,
                "max_lead_time_h": 24.0,
            },
            "Enterprise Pilot": {
                "machine_rate_per_h": 35.0,
                "labor_rate_per_h": 65.0,
                "setup_time_min": 20.0,
                "postprocess_time_min": 12.0,
                "scrap_allowance_pct": 12.0,
                "margin_pct": 45.0,
                "max_lead_time_h": 16.0,
            },
        }
        rates = preset_rates[str(quote_profile)]

        if advanced:
            st.markdown("**Cost and Capacity**")
            r1, r2 = st.columns(2)
            machine_rate_per_h = r1.number_input(
                "Machine $/h", min_value=0.0, value=float(rates["machine_rate_per_h"]), step=1.0,
            )
            labor_rate_per_h = r2.number_input(
                "Labor $/h", min_value=0.0, value=float(rates["labor_rate_per_h"]), step=1.0,
            )
            t1, t2 = st.columns(2)
            setup_time_min = t1.number_input(
                "Setup min", min_value=0.0, value=float(rates["setup_time_min"]), step=1.0,
            )
            postprocess_time_min = t2.number_input(
                "Postprocess min/part", min_value=0.0, value=float(rates["postprocess_time_min"]), step=1.0,
            )
            m1, m2 = st.columns(2)
            scrap_allowance_pct = m1.number_input(
                "Scrap allowance (%)", min_value=0.0, value=float(rates["scrap_allowance_pct"]), step=1.0,
            )
            margin_pct = m2.number_input(
                "Margin (%)", min_value=0.0, value=float(rates["margin_pct"]), step=1.0,
            )
            max_lead_time_h = st.number_input(
                "Max machine time (h)", min_value=0.0, value=float(rates["max_lead_time_h"]), step=1.0,
            )
            st.markdown("**Customer Intake**")
            intake1, intake2 = st.columns(2)
            finish_tolerance_mm = intake1.number_input("Finish tolerance (mm)", 0.01, value=0.5, step=0.05)
            annual_quantity = intake2.number_input("Annual demand", min_value=1, value=1, step=1)
            ndt_required = st.checkbox("NDT / inspection package required", value=True)
            redesign_required = st.checkbox("Redesign for additive required", value=True)
        else:
            machine_rate_per_h = rates["machine_rate_per_h"]
            labor_rate_per_h = rates["labor_rate_per_h"]
            setup_time_min = rates["setup_time_min"]
            postprocess_time_min = rates["postprocess_time_min"]
            scrap_allowance_pct = rates["scrap_allowance_pct"]
            margin_pct = rates["margin_pct"]
            max_lead_time_h = rates["max_lead_time_h"]
            finish_tolerance_mm = 0.5
            annual_quantity = int(batch_quantity)
            ndt_required = True
            redesign_required = True

    return {
        "job_name": job_name,
        "customer_name": customer_name,
        "owner_name": owner_name,
        "job_id": job_id,
        "batch_quantity": batch_quantity,
        "target_unit_price": target_unit_price,
        "application_type": application_type,
        "conventional_route": conventional_route,
        "urgency": urgency,
        "qualification_level": qualification_level,
        "material_strategy": material_strategy,
        "quote_profile": quote_profile,
        "machine_rate_per_h": machine_rate_per_h,
        "labor_rate_per_h": labor_rate_per_h,
        "setup_time_min": setup_time_min,
        "postprocess_time_min": postprocess_time_min,
        "scrap_allowance_pct": scrap_allowance_pct,
        "margin_pct": margin_pct,
        "max_lead_time_h": max_lead_time_h,
        "finish_tolerance_mm": finish_tolerance_mm,
        "annual_quantity": annual_quantity,
        "ndt_required": ndt_required,
        "redesign_required": redesign_required,
    }


def render_ded_controls(process_mode: str, advanced: bool) -> dict[str, Any]:
    """Render neutral wire-arc DED process assumptions."""
    ded_enabled = str(process_mode).startswith("Metal")

    ded_profile = "Generic large-format wire DED"
    ded_envelope_x_mm = 500.0
    ded_envelope_y_mm = 500.0
    ded_envelope_z_mm = 1500.0
    ded_wire_diameter_mm = 1.2
    ded_wire_feed_m_min = 6.0
    ded_arc_current_a = 180.0
    ded_arc_voltage_v = 24.0
    ded_arc_efficiency_pct = 80.0
    ded_deposition_efficiency_pct = 88.0
    ded_robot_utilization_pct = 72.0
    ded_machining_allowance_pct = 12.0
    ded_billet_buy_to_fly = 3.5
    ded_conventional_lead_time_weeks = 20.0
    ded_machine_capacity_h_week = 80.0
    ded_preheat_temp_c = 80.0
    ded_interpass_limit_c = 250.0
    ded_cooling_rate_c_min = 12.0
    ded_heat_retention_pct = 22.0
    ded_robot_reach_mm = 1800.0
    ded_positioner_payload_kg = 500.0
    ded_fixture_mass_kg = 75.0
    ded_torch_clearance_mm = 120.0
    ded_program_point_limit = 25000

    if ded_enabled:
        with st.expander("Metal / DED process", expanded=True, icon=":material/bolt:"):
            ded_profile = st.segmented_control(
                "Process preset",
                [
                    "Generic large-format wire DED",
                    "High-deposition steel build",
                    "Fine-bead repair / cladding",
                ],
                default="Generic large-format wire DED",
            ) or "Generic large-format wire DED"
            presets = {
                "Generic large-format wire DED": {
                    "feed": 6.0,
                    "wire": 1.2,
                    "current": 180.0,
                    "voltage": 24.0,
                    "efficiency": 88.0,
                },
                "High-deposition steel build": {
                    "feed": 9.0,
                    "wire": 1.6,
                    "current": 260.0,
                    "voltage": 28.0,
                    "efficiency": 90.0,
                },
                "Fine-bead repair / cladding": {
                    "feed": 3.5,
                    "wire": 1.0,
                    "current": 120.0,
                    "voltage": 20.0,
                    "efficiency": 84.0,
                },
            }
            preset = presets[str(ded_profile)]

            env1, env2, env3 = st.columns(3)
            ded_envelope_x_mm = env1.number_input("Envelope X (mm)", 50.0, value=500.0, step=50.0)
            ded_envelope_y_mm = env2.number_input("Envelope Y (mm)", 50.0, value=500.0, step=50.0)
            ded_envelope_z_mm = env3.number_input("Envelope Z (mm)", 50.0, value=1500.0, step=50.0)

            p1, p2 = st.columns(2)
            ded_wire_diameter_mm = p1.number_input(
                "Wire diameter (mm)", 0.4, value=float(preset["wire"]), step=0.1,
            )
            ded_wire_feed_m_min = p2.number_input(
                "Wire feed (m/min)", 0.1, value=float(preset["feed"]), step=0.25,
            )

            if advanced:
                st.markdown("**Arc, Yield, and Lead Time**")
                a1, a2 = st.columns(2)
                ded_arc_current_a = a1.number_input(
                    "Arc current (A)", 1.0, value=float(preset["current"]), step=10.0,
                )
                ded_arc_voltage_v = a2.number_input(
                    "Arc voltage (V)", 1.0, value=float(preset["voltage"]), step=1.0,
                )
                e1, e2 = st.columns(2)
                ded_arc_efficiency_pct = e1.number_input("Arc efficiency (%)", 1.0, 100.0, 80.0, 1.0)
                ded_deposition_efficiency_pct = e2.number_input(
                    "Deposition efficiency (%)", 1.0, 100.0,
                    float(preset["efficiency"]), 1.0,
                )
                u1, u2 = st.columns(2)
                ded_robot_utilization_pct = u1.number_input("Robot utilization (%)", 1.0, 100.0, 72.0, 1.0)
                ded_machining_allowance_pct = u2.number_input("Machining allowance (%)", 0.0, 100.0, 12.0, 1.0)
                c1, c2 = st.columns(2)
                ded_billet_buy_to_fly = c1.number_input("Billet buy-to-fly", 1.0, value=3.5, step=0.25)
                ded_conventional_lead_time_weeks = c2.number_input(
                    "Conventional lead time (weeks)", 0.0, value=20.0, step=1.0,
                )
                ded_machine_capacity_h_week = st.number_input(
                    "Available machine hours / week", 1.0, value=80.0, step=5.0,
                )
                st.markdown("**Thermal and Robot Handoff**")
                th1, th2 = st.columns(2)
                ded_preheat_temp_c = th1.number_input("Preheat temp (C)", 0.0, value=80.0, step=10.0)
                ded_interpass_limit_c = th2.number_input("Interpass limit (C)", 1.0, value=250.0, step=10.0)
                th3, th4 = st.columns(2)
                ded_cooling_rate_c_min = th3.number_input("Cooling rate (C/min)", 0.1, value=12.0, step=1.0)
                ded_heat_retention_pct = th4.number_input("Heat retention (%)", 0.0, 100.0, 22.0, 1.0)
                rb1, rb2 = st.columns(2)
                ded_robot_reach_mm = rb1.number_input("Robot reach (mm)", 100.0, value=1800.0, step=100.0)
                ded_positioner_payload_kg = rb2.number_input("Positioner payload (kg)", 1.0, value=500.0, step=25.0)
                rb3, rb4 = st.columns(2)
                ded_fixture_mass_kg = rb3.number_input("Fixture mass (kg)", 0.0, value=75.0, step=5.0)
                ded_torch_clearance_mm = rb4.number_input("Torch clearance (mm)", 0.0, value=120.0, step=10.0)
                ded_program_point_limit = st.number_input(
                    "Robot program point limit", min_value=1000, value=25000, step=1000,
                )

    return {
        "ded_enabled": ded_enabled,
        "ded_profile": ded_profile,
        "ded_envelope_x_mm": ded_envelope_x_mm,
        "ded_envelope_y_mm": ded_envelope_y_mm,
        "ded_envelope_z_mm": ded_envelope_z_mm,
        "ded_wire_diameter_mm": ded_wire_diameter_mm,
        "ded_wire_feed_m_min": ded_wire_feed_m_min,
        "ded_arc_current_a": ded_arc_current_a,
        "ded_arc_voltage_v": ded_arc_voltage_v,
        "ded_arc_efficiency_pct": ded_arc_efficiency_pct,
        "ded_deposition_efficiency_pct": ded_deposition_efficiency_pct,
        "ded_robot_utilization_pct": ded_robot_utilization_pct,
        "ded_machining_allowance_pct": ded_machining_allowance_pct,
        "ded_billet_buy_to_fly": ded_billet_buy_to_fly,
        "ded_conventional_lead_time_weeks": ded_conventional_lead_time_weeks,
        "ded_machine_capacity_h_week": ded_machine_capacity_h_week,
        "ded_preheat_temp_c": ded_preheat_temp_c,
        "ded_interpass_limit_c": ded_interpass_limit_c,
        "ded_cooling_rate_c_min": ded_cooling_rate_c_min,
        "ded_heat_retention_pct": ded_heat_retention_pct,
        "ded_robot_reach_mm": ded_robot_reach_mm,
        "ded_positioner_payload_kg": ded_positioner_payload_kg,
        "ded_fixture_mass_kg": ded_fixture_mass_kg,
        "ded_torch_clearance_mm": ded_torch_clearance_mm,
        "ded_program_point_limit": ded_program_point_limit,
    }


def render_placement_controls(quick_plate: str, advanced: bool) -> dict[str, Any]:
    with st.expander("4 - Placement", expanded=False, icon=":material/open_with:"):
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

    return {
        "show_plate": show_plate,
        "scale_pct": scale_pct,
        "rotate_deg": rotate_deg,
        "center_on_plate": center_on_plate,
        "fit_to_plate": fit_to_plate,
        "plate_margin": plate_margin,
        "plate_w": plate_w,
        "plate_d": plate_d,
        "mirror_x": mirror_x,
        "mirror_y": mirror_y,
        "translate_x": translate_x,
        "translate_y": translate_y,
    }


def render_preview_controls(advanced: bool) -> dict[str, Any]:
    with st.expander("5 - Appearance & overlays", expanded=False, icon=":material/palette:"):
        scheme_options = ["Classic", "Colorblind", "Dark", "Neon", "High Contrast"]
        color_scheme = st.selectbox(
            "Color scheme", scheme_options, index=0,
            help="Palette for the toolpath preview.",
        )
        line_width_scale = st.slider("Line thickness", 0.5, 3.0, 1.0, 0.25)

        st.caption("Toggle overlays drawn on the preview:")
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
        with st.expander("Quality / Export", expanded=False, icon=":material/tune:"):
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

    return {
        "color_scheme": color_scheme,
        "line_width_scale": line_width_scale,
        "show_boundary": show_boundary,
        "show_perimeters": show_perimeters,
        "show_infill": show_infill,
        "show_dimensions": show_dimensions,
        "show_travel": show_travel,
        "show_seams": show_seams,
        "show_start_end": show_start_end,
        "show_arrows": show_arrows,
        "show_extrusion": show_extrusion,
        "optimize_perimeters": optimize_perimeters,
        "optimize_infill": optimize_infill,
        "reverse_lines": reverse_lines,
        "simplify_tolerance": simplify_tolerance,
        "min_segment_length": min_segment_length,
        "z_hop": z_hop,
        "extrusion_per_mm": extrusion_per_mm,
        "include_e": include_e,
    }
