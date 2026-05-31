"""Export buttons and previews for MiniSlicer."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.exporters import (
    ProductionExportError,
    export_gcode_like,
    export_production_gcode,
    export_segments_csv,
    export_segments_json,
    export_svg,
)
from src.profiles import FDM_MACHINE_PROFILES


def render_export_panel(
    segments: list[Any],
    production_segments: list[Any],
    boundary: Any,
    perimeters: list[Any],
    infill_lines: list[Any],
    params: dict[str, Any],
    print_speed: float,
    layer_height: float,
    travel_speed: float,
    z_hop: float,
    include_e: bool,
    extrusion_per_mm: float,
    report: str,
    layer_number: int,
) -> None:
    csv_text = export_segments_csv(segments)
    json_text = export_segments_json(segments, params)
    svg_text = export_svg(boundary, perimeters, infill_lines)
    gcode_text = export_gcode_like(
        segments, print_speed_mm_s=float(print_speed), layer_height_mm=float(layer_height),
        travel_speed_mm_s=float(travel_speed), z_hop_mm=float(z_hop),
        include_e_values=bool(include_e), extrusion_per_mm=float(extrusion_per_mm),
    )
    readiness = params.get("readiness", {}) if isinstance(params, dict) else {}
    readiness_status = readiness.get("status", "Review") if isinstance(readiness, dict) else "Review"
    process_mode = params.get("process_mode", "") if isinstance(params, dict) else ""
    production_meta = params.get("production_export", {}) if isinstance(params, dict) else {}
    production_allowed = readiness_status != "Blocked" and str(process_mode).startswith("FDM")
    if isinstance(production_meta, dict) and not production_meta.get("full_build_enabled", True):
        production_allowed = False

    st.markdown("### Download Files")
    st.markdown(
        "CSV, SVG, JSON, and report exports are always available for review. "
        "Production G-code is gated by readiness checks and an FDM machine profile."
    )

    d1, d2, d3, d4, d5, d6 = st.columns(6)
    fname = f"layer_{int(layer_number)}"
    d1.download_button(
        "CSV", csv_text, f"toolpaths_{fname}.csv", "text/csv",
        width="stretch", help="Segment data as a spreadsheet-ready CSV.",
    )
    d2.download_button(
        "Preview G-code", gcode_text, f"toolpaths_{fname}_preview.gcode.txt", "text/plain",
        width="stretch", help="Simplified educational G-code preview.",
    )
    d3.download_button(
        "SVG", svg_text, f"toolpaths_{fname}.svg", "image/svg+xml",
        width="stretch", help="Scalable vector export of boundary + toolpaths.",
    )
    d4.download_button(
        "JSON", json_text, f"toolpaths_{fname}.json", "application/json",
        width="stretch", help="Full segment data with parameters as JSON.",
    )
    d5.download_button(
        "Report", report, f"toolpaths_{fname}_report.txt", "text/plain",
        width="stretch", help="Human-readable summary report.",
    )
    machine_name = d6.selectbox("Machine", sorted(FDM_MACHINE_PROFILES), label_visibility="collapsed")

    try:
        production_gcode = export_production_gcode(
            segments=production_segments,
            machine=FDM_MACHINE_PROFILES[machine_name],
            print_speed_mm_s=float(print_speed),
            layer_height_mm=float(layer_height),
            travel_speed_mm_s=float(travel_speed),
            extrusion_per_mm=float(extrusion_per_mm),
            z_hop_mm=float(z_hop),
            job_name=str(params.get("shape_type", "MiniSlicer job")),
        )
        production_error = ""
    except ProductionExportError as exc:
        production_gcode = ""
        production_error = str(exc)

    if production_error:
        production_allowed = False
        st.error(f"Production G-code blocked: {production_error}")
    elif isinstance(production_meta, dict) and not production_meta.get("full_build_enabled", True):
        st.error(
            "Production G-code blocked: full-build export exceeds "
            f"{production_meta.get('layer_limit', 'the configured')} layer limit."
        )
    elif not production_allowed:
        st.warning("Production G-code is blocked until readiness is unblocked and process mode is FDM.")
    else:
        st.success(
            f"Production G-code is ready for {machine_name}: "
            f"{production_meta.get('layer_count', '?')} layers, "
            f"{production_meta.get('segment_count', len(production_segments)):,} moves."
        )

    st.download_button(
        "Production G-code",
        production_gcode,
        f"toolpaths_full_build_production.gcode",
        "text/plain",
        width="stretch",
        disabled=not production_allowed,
        help="Machine-profiled FDM G-code with start/end sequence, temperatures, fan, extrusion, and bounds checks.",
    )

    st.markdown("---")
    col_gc, col_prod, col_js = st.columns(3)
    with col_gc:
        with st.expander("Preview G-code"):
            st.code(gcode_text[:6000], language="text")
    with col_prod:
        with st.expander("Production G-code"):
            st.code((production_gcode or production_error)[:6000], language="text")
    with col_js:
        with st.expander("JSON preview"):
            st.code(json_text[:4000], language="json")
