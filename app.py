"""Streamlit app for MiniSlicer toolpath visualization."""

from __future__ import annotations

import math
from html import escape
from typing import Any

import streamlit as st
from shapely import affinity
from shapely.geometry import Polygon

from src.animation import create_animated_figure
from src.exporters import segments_to_dataframe
from src.geometry import (
    create_arrow_shape,
    create_capsule,
    create_circle,
    create_cross,
    create_ellipse,
    create_regular_polygon,
    create_rectangle,
    create_rounded_rectangle,
    create_star,
    create_triangle,
    parse_custom_polygon,
    validate_polygon,
)
from src.job_analysis import (
    classify_program_risk,
    estimate_job_economics,
    generate_job_dossier_html,
    generate_job_dossier_markdown,
)
from src.metrics import summarize_metrics
from src.plotting import (
    create_comparison_figure,
    create_infill_length_histogram,
    create_metrics_figure,
    create_path_density_figure,
    create_speed_map_figure,
    create_time_map_figure,
    create_toolpath_figure,
    shape_boundary,
)
from src.svg_import import parse_svg_to_polygon
from src.stl_import import slice_stl_to_polygon
from src.toolpaths import (
    build_ordered_segments,
    filter_short_lines,
    generate_infill,
    generate_inward_perimeters,
    optimize_path_order,
    simplify_lines,
    total_travel_distance,
)
from src.validation import assess_job_readiness, readiness_to_dict
from ui.export_panel import render_export_panel
from ui.sidebar import render_quick_setup, render_sidebar
from ui.stl_workflow import render_stl_multilayer_view


SHAPES = [
    "Rectangle", "Rounded Rectangle", "Circle", "Ellipse", "Triangle",
    "Regular Polygon", "Star", "Cross", "Capsule", "Arrow", "Custom Polygon",
]
PATTERNS = ["Parallel Lines", "Zigzag", "Grid", "Triangles", "Honeycomb", "Concentric"]

SHAPE_ICONS = {
    "Rectangle": "[]", "Rounded Rectangle": "()", "Circle": "o", "Ellipse": "0",
    "Triangle": "^", "Regular Polygon": "hex", "Star": "*", "Cross": "+",
    "Capsule": "cap", "Arrow": "->", "Custom Polygon": "pen",
}

PATTERN_ICONS = {
    "Parallel Lines": "|||", "Zigzag": "zig", "Grid": "#",
    "Triangles": "tri", "Honeycomb": "hex", "Concentric": "O",
}


def fmt_time(seconds: float) -> str:
    if math.isinf(seconds):
        return "inf"
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    if seconds >= 60:
        return f"{int(seconds // 60)}m {seconds % 60:.0f}s"
    return f"{seconds:.1f}s"


def largest_polygon(geometry: object) -> Polygon | None:
    if isinstance(geometry, Polygon) and not geometry.is_empty:
        return geometry
    geoms = getattr(geometry, "geoms", None)
    if geoms is None:
        return None
    polys = [geom for geom in geoms if isinstance(geom, Polygon) and not geom.is_empty]
    return max(polys, key=lambda poly: poly.area) if polys else None


def build_shape(shape_type: str, settings: dict[str, Any]) -> Polygon | None:
    if shape_type == "Rectangle":
        return create_rectangle(settings["width"], settings["height"])
    if shape_type == "Rounded Rectangle":
        return create_rounded_rectangle(settings["width"], settings["height"], settings["corner_radius"])
    if shape_type == "Circle":
        return create_circle(settings["radius"])
    if shape_type == "Ellipse":
        return create_ellipse(settings["width"], settings["height"])
    if shape_type == "Triangle":
        return create_triangle(settings["width"], settings["height"])
    if shape_type == "Regular Polygon":
        return create_regular_polygon(settings["radius"], settings["sides"])
    if shape_type == "Star":
        return create_star(settings["radius"], settings["inner_radius"], settings["points"])
    if shape_type == "Cross":
        return create_cross(settings["size"], settings["arm_width"])
    if shape_type == "Capsule":
        return create_capsule(settings["width"], settings["height"])
    if shape_type == "Arrow":
        return create_arrow_shape(settings["length"], settings["head_width"], settings["shaft_width"])
    return parse_custom_polygon(settings["coords_text"])


def apply_placement(shape: Polygon, settings: dict[str, Any]) -> Polygon:
    if settings["scale_pct"] != 100:
        centroid = shape.centroid
        scale = settings["scale_pct"] / 100.0
        shape = affinity.scale(shape, xfact=scale, yfact=scale, origin=(centroid.x, centroid.y))

    if settings["mirror_x"] or settings["mirror_y"]:
        centroid = shape.centroid
        shape = affinity.scale(
            shape,
            xfact=-1.0 if settings["mirror_x"] else 1.0,
            yfact=-1.0 if settings["mirror_y"] else 1.0,
            origin=(centroid.x, centroid.y),
        )

    if settings["rotate_deg"]:
        centroid = shape.centroid
        shape = affinity.rotate(shape, settings["rotate_deg"], origin=(centroid.x, centroid.y))

    if settings["translate_x"] or settings["translate_y"]:
        shape = affinity.translate(shape, xoff=settings["translate_x"], yoff=settings["translate_y"])

    if settings["fit_to_plate"] and settings["show_plate"]:
        min_x, min_y, max_x, max_y = shape.bounds
        target_w = max(settings["plate_w"] - 2 * settings["plate_margin"], 1.0)
        target_h = max(settings["plate_d"] - 2 * settings["plate_margin"], 1.0)
        scale = min(1.0, target_w / max(max_x - min_x, 1e-9), target_h / max(max_y - min_y, 1e-9))
        if scale < 1.0:
            centroid = shape.centroid
            shape = affinity.scale(shape, xfact=scale, yfact=scale, origin=(centroid.x, centroid.y))

    if settings["center_on_plate"] and settings["show_plate"]:
        centroid = shape.centroid
        shape = affinity.translate(
            shape,
            xoff=settings["plate_w"] / 2 - centroid.x,
            yoff=settings["plate_d"] / 2 - centroid.y,
        )

    return shape


def app_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ms-ink: #172033;
            --ms-muted: #667085;
            --ms-line: #d7dde8;
            --ms-panel: #ffffff;
            --ms-surface: #f5f7fb;
            --ms-blue: #1d4ed8;
            --ms-teal: #0f766e;
            --ms-amber: #b45309;
            --ms-green: #15803d;
        }
        .stApp { background: linear-gradient(180deg, #f7f9fc 0%, #ffffff 34rem); }
        .block-container { padding-top: 0.65rem; padding-bottom: 2rem; max-width: 1600px; }
        .ms-header {
            background: #172033; border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px; padding: 0.95rem 1.2rem 0.9rem; margin-bottom: 0.85rem;
            display: flex; align-items: center; gap: 0.85rem;
            box-shadow: 0 12px 30px rgba(23, 32, 51, 0.12);
        }
        .ms-header-icon {
            width: 2.25rem; height: 2.25rem; border-radius: 8px; display: grid;
            place-items: center; background: #e0f2fe; color: #075985; font-weight: 700;
        }
        .ms-header-title { font-size: 1.42rem; font-weight: 700; color: #f8fafc; margin: 0; }
        .ms-header-sub { font-size: 0.82rem; color: #cbd5e1; margin: 0; }
        .ms-header-badge {
            margin-left: auto; background: rgba(20,184,166,0.14);
            border: 1px solid rgba(94,234,212,0.28); border-radius: 6px;
            padding: 0.25rem 0.75rem; font-size: 0.75rem; color: #ccfbf1; white-space: nowrap;
        }
        .exec-strip {
            display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.75rem;
            margin: 0.2rem 0 0.9rem;
        }
        .exec-card {
            background: #ffffff; border: 1px solid var(--ms-line); border-radius: 8px;
            padding: 0.85rem 0.95rem; min-height: 5.4rem;
        }
        .exec-label { color: var(--ms-muted); font-size: 0.76rem; font-weight: 650; margin-bottom: 0.25rem; }
        .exec-value { color: var(--ms-ink); font-size: 1.35rem; font-weight: 760; line-height: 1.2; }
        .exec-note { color: var(--ms-muted); font-size: 0.78rem; margin-top: 0.25rem; }
        @media (max-width: 980px) { .exec-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @media (max-width: 640px) { .exec-strip { grid-template-columns: 1fr; } }
        [data-testid="stSidebar"] { border-right: 1px solid var(--ms-line); background: var(--ms-surface); }
        [data-testid="stMetric"] {
            background: var(--ms-panel); border: 1px solid var(--ms-line); border-radius: 8px;
            padding: 0.72rem 0.9rem;
        }
        .metric-blue [data-testid="stMetric"] { border-left: 3px solid var(--ms-blue); }
        .metric-green [data-testid="stMetric"] { border-left: 3px solid var(--ms-green); }
        .metric-orange [data-testid="stMetric"] { border-left: 3px solid var(--ms-amber); }
        .metric-purple [data-testid="stMetric"] { border-left: 3px solid #6d28d9; }
        .metric-teal [data-testid="stMetric"] { border-left: 3px solid var(--ms-teal); }
        .setup-summary { display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 0.4rem 0 0.75rem; }
        .setup-chip {
            display: inline-flex; gap: 0.35rem; min-height: 1.8rem; border: 1px solid var(--ms-line);
            border-radius: 6px; padding: 0.2rem 0.72rem; background: rgba(255,255,255,0.86);
            color: var(--ms-ink); font-size: 0.8rem; font-weight: 600;
        }
        .setup-chip span { color: var(--ms-muted); font-weight: 500; }
        .setup-chip.fit-ok { border-color: #bbf7d0; background: #f0fdf4; color: #166534; }
        .setup-chip.fit-warn { border-color: #fecaca; background: #fef2f2; color: #991b1b; }
        div[data-testid="stPlotlyChart"] {
            border: 1px solid var(--ms-line); border-radius: 8px; overflow: hidden;
            box-shadow: 0 10px 26px rgba(23, 32, 51, 0.06);
        }
        [data-testid="stAlert"], div[data-testid="stExpander"], [data-testid="stDataFrame"] {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="ms-header">
            <div class="ms-header-icon">MS</div>
            <div>
                <p class="ms-header-title">MiniSlicer Toolpath Planner</p>
                <p class="ms-header-sub">Interactive FDM/DED previews, metrics, comparisons, and educational exports</p>
            </div>
            <div class="ms-header-badge">Job Planning Workbench</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="MiniSlicer - Toolpath Planner",
    layout="wide",
    page_icon=":material/build:",
    initial_sidebar_state="expanded",
)
app_css()
render_header()

quick = render_quick_setup()
profile = quick["profile"]
quick_plate = quick["quick_plate"]
control_mode = quick["control_mode"]
process_mode = quick["process_mode"]
advanced = quick["advanced"]
default = quick["default"]

controls = render_sidebar(
    default,
    profile,
    quick_plate,
    advanced,
    SHAPES,
    PATTERNS,
    SHAPE_ICONS,
    PATTERN_ICONS,
)
locals().update(controls)

shape_settings = {
    "width": width, "height": height, "radius": radius,
    "corner_radius": corner_radius, "sides": sides, "points": points,
    "inner_radius": min(inner_radius, radius - 0.01),
    "size": size, "arm_width": arm_width,
    "length": length, "head_width": head_width,
    "shaft_width": min(shaft_width, head_width - 0.1),
    "coords_text": coords_text,
}

source_label = shape_type
if uploaded_stl is not None and stl_bytes is not None:
    shape = slice_stl_to_polygon(stl_bytes, z_height=stl_slice_z, target_width_mm=stl_target_width)
    source_label = f"STL slice Z={stl_slice_z:.2f}"
    if shape is None:
        st.error(
            "The STL could not be sliced at this Z height. "
            "Try sliding the **Slice at Z** control to a height inside the solid part of the mesh."
        )
        st.stop()
elif uploaded_svg is not None:
    shape, svg_error = parse_svg_to_polygon(uploaded_svg.read(), target_width_mm=svg_target_width)
    source_label = "SVG"
    if shape is None:
        st.error(f"SVG import failed: {svg_error}")
        st.stop()
else:
    shape = build_shape(shape_type, shape_settings)

shape = validate_polygon(shape) if shape is not None else None
if shape is None:
    st.error(
        "The selected shape is invalid - adjust the dimensions or custom polygon points.  \n"
        "For a Custom Polygon, ensure at least 3 non-collinear points are provided."
    )
    st.stop()

placement = {
    "scale_pct": scale_pct, "mirror_x": mirror_x, "mirror_y": mirror_y,
    "rotate_deg": rotate_deg, "translate_x": translate_x, "translate_y": translate_y,
    "fit_to_plate": fit_to_plate, "center_on_plate": center_on_plate,
    "show_plate": show_plate, "plate_w": plate_w, "plate_d": plate_d, "plate_margin": plate_margin,
}
shape = apply_placement(shape, placement)

effective_spacing = (
    max(0.1, float(nozzle_diameter) * 100.0 / float(infill_density))
    if infill_mode == "Density"
    else float(infill_spacing)
)
effective_angle = (
    45.0 if alternate_angle and int(layer_number) % 2 == 1
    else -45.0 if alternate_angle
    else float(infill_angle)
)

boundary = shape_boundary(shape)
perimeters = generate_inward_perimeters(shape, int(perimeter_count), float(perimeter_spacing))

infill_shape = shape
net_clearance = max(0.0, float(infill_clearance) - float(infill_overlap))
if net_clearance > 0:
    inset = largest_polygon(shape.buffer(-net_clearance))
    if inset is None:
        st.warning("Wall clearance is too large for this shape; infill uses the full shape.")
    else:
        infill_shape = inset

infill_lines = generate_infill(infill_shape, infill_pattern, effective_spacing, effective_angle)

if optimize_perimeters:
    perimeters = optimize_path_order(perimeters, allow_reverse=False)
if optimize_infill:
    infill_lines = optimize_path_order(infill_lines, allow_reverse=reverse_lines)
if simplify_tolerance > 0:
    perimeters = simplify_lines(perimeters, simplify_tolerance)
    infill_lines = simplify_lines(infill_lines, simplify_tolerance)
if min_segment_length > 0:
    perimeters = filter_short_lines(perimeters, min_segment_length)
    infill_lines = filter_short_lines(infill_lines, min_segment_length)

segments = build_ordered_segments(None, perimeters, infill_lines, int(layer_number))
metrics = summarize_metrics(
    shape, segments, perimeters, infill_lines,
    print_speed_mm_s=float(print_speed),
    travel_speed_mm_s=float(travel_speed),
    layer_height_mm=float(layer_height),
    nozzle_diameter_mm=float(nozzle_diameter),
    filament_diameter_mm=float(filament_diameter),
    material=material_choice,
    acceleration_mm_s2=float(acceleration_mm_s2),
    perimeter_speed_mult=float(perimeter_speed_mult),
)

layer_count = max(1, math.ceil(float(model_height) / float(layer_height)))
production_segments = segments
production_layer_limit = 600
if layer_count <= production_layer_limit:
    production_segments = []
    for prod_layer in range(1, layer_count + 1):
        prod_angle = (
            45.0 if alternate_angle and prod_layer % 2 == 1
            else -45.0 if alternate_angle
            else float(effective_angle)
        )
        prod_infill = infill_lines
        if prod_angle != effective_angle:
            prod_infill = generate_infill(infill_shape, infill_pattern, effective_spacing, prod_angle)
            if optimize_infill:
                prod_infill = optimize_path_order(prod_infill, allow_reverse=reverse_lines)
            if simplify_tolerance > 0:
                prod_infill = simplify_lines(prod_infill, simplify_tolerance)
            if min_segment_length > 0:
                prod_infill = filter_short_lines(prod_infill, min_segment_length)
        production_segments.extend(
            build_ordered_segments(None, perimeters, prod_infill, prod_layer)
        )
full_time_s = metrics["estimated_motion_time_s"] * layer_count
full_weight_g = metrics["weight_g"] * layer_count
full_cost = full_weight_g / 1000.0 * float(material_cost)
economics = estimate_job_economics(
    metrics=metrics,
    layer_count=layer_count,
    layer_height_mm=float(layer_height),
    nozzle_diameter_mm=float(nozzle_diameter),
    print_speed_mm_s=float(print_speed),
    full_time_s=full_time_s,
    full_weight_g=full_weight_g,
    material_cost_per_kg=float(material_cost),
)
min_x, min_y, max_x, max_y = shape.bounds
fits_plate = not show_plate or (min_x >= 0 and min_y >= 0 and max_x <= plate_w and max_y <= plate_d)
travel_ratio = (
    100 * metrics["travel_length_mm"] / metrics["total_motion_length_mm"]
    if metrics["total_motion_length_mm"] else 0.0
)
plate_size = (float(plate_w), float(plate_d)) if show_plate else None
extrusion_width = float(nozzle_diameter) if show_extrusion else 0.0
readiness = assess_job_readiness(
    fits_plate=fits_plate,
    metrics=metrics,
    perimeter_count=int(perimeter_count),
    infill_line_count=len(infill_lines),
    layer_height_mm=float(layer_height),
    nozzle_diameter_mm=float(nozzle_diameter),
    effective_spacing_mm=float(effective_spacing),
    perimeter_spacing_mm=float(perimeter_spacing),
    segment_count=int(metrics["segment_count"]),
    travel_ratio_pct=float(travel_ratio),
    process_mode=str(process_mode),
    imported_stl=uploaded_stl is not None,
    imported_svg=uploaded_svg is not None,
    volumetric_flow_mm3_s=economics["volumetric_flow_mm3_s"],
    model_height_mm=float(model_height),
    layer_count=layer_count,
)
program_risk = classify_program_risk(readiness, economics)

m1, m2, m3, m4, m5, m6 = st.columns(6)
metric_specs = [
    (m1, "metric-blue", "Path length", f"{metrics['total_path_length_mm']:.1f} mm", None, None),
    (m2, "metric-purple", "Segments", f"{metrics['segment_count']:,}", None, None),
    (m3, "metric-teal", "Layer time", fmt_time(metrics["estimated_motion_time_s"]), None, None),
    (
        m4, "metric-orange", "Full build", fmt_time(full_time_s),
        None, f"{layer_count} layers x {fmt_time(metrics['estimated_motion_time_s'])}/layer",
    ),
    (m5, "metric-green", "Material", f"{full_weight_g:.2f} g", None, f"${full_cost:.2f} at ${material_cost:.0f}/kg"),
    (
        m6, "metric-blue", "Readiness", f"{readiness['score']}/100",
        readiness["status"], "Computed from fit, paths, material, and motion checks.",
    ),
]
for column, css_class, label, value, delta, help_text in metric_specs:
    with column:
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        st.metric(label, value, delta=delta, help=help_text, delta_color="inverse" if delta else "normal")
        st.markdown("</div>", unsafe_allow_html=True)

if metrics["segment_count"] > 5000:
    st.warning(
        "Segment count exceeds 5,000. Increase spacing or reduce perimeters to avoid slow renders."
    )

fit_class = "fit-ok" if fits_plate else "fit-warn"
fit_label = "Fits plate" if fits_plate else "Outside plate"
summary_items = [
    ("Shape", source_label),
    ("Infill", f"{infill_pattern} - {effective_spacing:.2f} mm"),
    ("Layer", f"{float(layer_height):.2f} mm - {layer_count} layers"),
    ("Material", material_choice),
    ("Mode", f"{process_mode} - {control_mode} controls"),
]
summary_html = "".join(
    f'<div class="setup-chip"><span>{escape(label)}</span>{escape(str(value))}</div>'
    for label, value in summary_items
)
st.markdown(
    f'<div class="setup-summary">{summary_html}'
    f'<div class="setup-chip {fit_class}">{escape(fit_label)}</div></div>',
    unsafe_allow_html=True,
)

if readiness["status"] == "Blocked":
    st.error(
        f"Job readiness: {readiness['score']}/100 - blocked by "
        f"{readiness['blockers']} critical issue(s). Open Advisor for the fix list."
    )
elif readiness["warnings"]:
    st.warning(
        f"Job readiness: {readiness['score']}/100 - review "
        f"{readiness['warnings']} warning(s) before exporting."
    )
else:
    st.success(f"Job readiness: {readiness['score']}/100 - setup is ready for planning review.")

tab_exec, tab_preview, tab_compare, tab_anim, tab_3d, tab_metrics, tab_advisor, tab_data, tab_export = st.tabs([
    "Executive", "Preview", "Compare", "Animation", "3D", "Metrics", "Advisor", "Data", "Export",
])

with tab_exec:
    risk_color = {"Low": "#15803d", "Medium": "#b45309", "High": "#b91c1c", "Blocked": "#991b1b"}.get(
        program_risk, "#172033"
    )
    st.markdown(
        f"""
        <div class="exec-strip">
            <div class="exec-card">
                <div class="exec-label">Release State</div>
                <div class="exec-value">{escape(readiness["status"])} - {readiness["score"]}/100</div>
                <div class="exec-note">{readiness["blockers"]} blockers, {readiness["warnings"]} warnings</div>
            </div>
            <div class="exec-card">
                <div class="exec-label">Quoted Part Cost</div>
                <div class="exec-value">${economics["quoted_price"]:.2f}</div>
                <div class="exec-note">${economics["cost_per_cm3"]:.2f}/cm3 including scrap and margin</div>
            </div>
            <div class="exec-card">
                <div class="exec-label">Build Productivity</div>
                <div class="exec-value">{economics["build_rate_cm3_h"]:.2f} cm3/h</div>
                <div class="exec-note">{fmt_time(full_time_s)} machine time</div>
            </div>
            <div class="exec-card">
                <div class="exec-label">Program Risk</div>
                <div class="exec-value" style="color:{risk_color}">{escape(program_risk)}</div>
                <div class="exec-note">{economics["volumetric_flow_mm3_s"]:.2f} mm3/s requested flow</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ex1, ex2 = st.columns([1.2, 1])
    with ex1:
        st.markdown("### Production Decision")
        decision_rows = {
            "Geometry": source_label,
            "Process": process_mode,
            "Material": material_choice,
            "Layers": layer_count,
            "Path efficiency": f"{metrics['path_efficiency_pct']:.1f}%",
            "Travel share": f"{travel_ratio:.1f}%",
            "Material volume": f"{economics['volume_cm3']:.2f} cm3",
            "Full segment export": f"{len(production_segments):,} moves",
        }
        st.dataframe(
            [{"signal": key, "value": value} for key, value in decision_rows.items()],
            hide_index=True,
            width="stretch",
        )
    with ex2:
        st.markdown("### Cost Stack")
        st.bar_chart({
            "USD": {
                "Material": economics["material_cost"],
                "Machine": economics["machine_cost"],
                "Labor": economics["labor_cost"],
                "Scrap + margin": max(
                    0.0,
                    economics["quoted_price"]
                    - economics["material_cost"]
                    - economics["machine_cost"]
                    - economics["labor_cost"],
                ),
            }
        })

    st.markdown("### Top Actions")
    if readiness["issues"]:
        for issue in readiness["issues"][:4]:
            if issue.severity == "blocker":
                st.error(f"{issue.title}: {issue.action}")
            elif issue.severity == "warning":
                st.warning(f"{issue.title}: {issue.action}")
            else:
                st.info(f"{issue.title}: {issue.action}")
    else:
        st.success("This setup is clear for planning review. Export the job dossier for sign-off.")

with tab_preview:
    ctrl_row = st.columns([2, 1, 1])
    preview_layer = ctrl_row[0].slider(
        "Layer preview", 1, min(layer_count, 50), min(int(layer_number), min(layer_count, 50)),
        help="Preview any layer up to layer 50.",
    )
    mode = ctrl_row[1].selectbox(
        "View mode",
        ["Toolpath", "Extrusion", "Perimeters only", "Infill only", "Travel only", "Speed map", "Time map", "Density"],
    )
    auto_fit_axes = ctrl_row[2].checkbox("Auto-fit axes", value=True)

    layer_angle = (
        45.0 if alternate_angle and preview_layer % 2 == 1
        else -45.0 if alternate_angle
        else effective_angle
    )
    preview_infill = infill_lines
    if layer_angle != effective_angle:
        preview_infill = generate_infill(infill_shape, infill_pattern, effective_spacing, layer_angle)
        if optimize_infill:
            preview_infill = optimize_path_order(preview_infill, allow_reverse=reverse_lines)

    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
    info_col1.caption(f"**Layer** {preview_layer} / {layer_count}")
    info_col2.caption(f"**Pattern** {PATTERN_ICONS.get(infill_pattern, '')} {infill_pattern}")
    info_col3.caption(f"**Spacing** {effective_spacing:.2f} mm")
    info_col4.caption(f"**Angle** {layer_angle:+.0f} deg")

    common = dict(
        line_width_scale=float(line_width_scale),
        color_scheme=color_scheme,
        build_plate_size=plate_size,
        show_direction_arrows=show_arrows,
        show_dimensions=show_dimensions,
    )
    if mode == "Speed map":
        fig = create_speed_map_figure(
            boundary, perimeters, preview_infill, print_speed,
            travel_speed, line_width_scale, plate_size, perimeter_speed_mult,
        )
    elif mode == "Time map":
        fig = create_time_map_figure(
            boundary, perimeters, preview_infill, print_speed, line_width_scale, plate_size,
        )
    elif mode == "Density":
        fig = create_path_density_figure(
            perimeters, preview_infill, boundary, build_plate_size=plate_size,
        )
    else:
        fig = create_toolpath_figure(
            boundary,
            perimeters if mode != "Infill only" else [],
            preview_infill if mode != "Perimeters only" else [],
            show_travel_moves=show_travel or mode == "Travel only",
            show_seam_markers=show_seams,
            show_boundary=show_boundary,
            show_perimeters=show_perimeters and mode not in ("Infill only", "Travel only"),
            show_infill=show_infill and mode not in ("Perimeters only", "Travel only"),
            show_start_end_points=show_start_end,
            extrusion_width_mm=float(nozzle_diameter) if mode == "Extrusion" else extrusion_width,
            print_speed_mm_s=float(print_speed),
            **common,
        )
    if not auto_fit_axes:
        fig.update_layout(uirevision="preserve-preview-zoom")
    st.plotly_chart(fig, width="stretch")

with tab_compare:
    st.markdown("Compare two infill patterns side-by-side with the same shape and spacing settings.")
    ca, cb = st.columns(2)
    pattern_a = ca.selectbox(
        "Pattern A", PATTERNS, index=PATTERNS.index(infill_pattern),
        format_func=lambda p: f"{PATTERN_ICONS.get(p, '')} {p}",
    )
    pattern_b = cb.selectbox(
        "Pattern B", PATTERNS, index=2,
        format_func=lambda p: f"{PATTERN_ICONS.get(p, '')} {p}",
    )

    auto_compare = st.checkbox("Auto-compare on change", value=True)
    run_compare = st.button("Compare now", type="primary") or auto_compare

    if run_compare:
        infill_a = generate_infill(infill_shape, pattern_a, effective_spacing, effective_angle)
        infill_b = generate_infill(infill_shape, pattern_b, effective_spacing, effective_angle)
        fig_cmp = create_comparison_figure(
            boundary, perimeters, infill_a, infill_b,
            pattern_a, pattern_b, line_width_scale, color_scheme,
        )
        st.plotly_chart(fig_cmp, width="stretch")
        cm1, cm2, cm3, cm4, cm5 = st.columns(5)
        cm1.metric("A - Lines", len(infill_a))
        cm2.metric("B - Lines", len(infill_b), delta=len(infill_b) - len(infill_a))
        a_len = sum(line.length for line in infill_a)
        b_len = sum(line.length for line in infill_b)
        cm3.metric("A - Infill", f"{a_len:.1f} mm")
        cm4.metric("B - Infill", f"{b_len:.1f} mm", delta=f"{b_len - a_len:+.1f} mm")
        cm5.metric("Shorter by", f"{abs(b_len - a_len):.1f} mm")
    else:
        st.info("Pick two patterns. Comparison updates automatically when **Auto-compare** is on.")

with tab_anim:
    if segments:
        st.plotly_chart(create_animated_figure(boundary, segments), width="stretch")
    else:
        st.info("No segments to animate - try adjusting perimeter count or infill spacing.")

with tab_3d:
    render_stl_multilayer_view(
        stl_bytes,
        stl_info,
        stl_target_width,
        float(layer_height),
        int(perimeter_count),
        float(perimeter_spacing),
        infill_pattern,
        float(effective_spacing),
        float(effective_angle),
        bool(optimize_infill),
        bool(reverse_lines),
        color_scheme,
        shape,
        layer_count,
    )

with tab_metrics:
    mg1, mg2, mg3, mg4, mg5 = st.columns(5)
    mg1.metric("Shape area", f"{metrics['area_mm2']:.2f} mm^2")
    mg2.metric("Bounding box", f"{metrics['bbox_width_mm']:.1f} x {metrics['bbox_height_mm']:.1f} mm")
    mg3.metric("Material", f"{full_weight_g:.2f} g")
    mg4.metric("Total cost", f"${full_cost:.2f}")
    mg5.metric("Filament", f"{metrics['filament_length_m'] * layer_count:.2f} m")

    if optimize_infill or optimize_perimeters:
        raw_pt = total_travel_distance(
            generate_inward_perimeters(shape, int(perimeter_count), float(perimeter_spacing))
        )
        raw_it = total_travel_distance(
            generate_infill(infill_shape, infill_pattern, effective_spacing, effective_angle)
        )
        opt_pt = total_travel_distance(perimeters) if optimize_perimeters else raw_pt
        opt_it = total_travel_distance(infill_lines) if optimize_infill else raw_it
        raw_total = raw_pt + raw_it
        opt_total = opt_pt + opt_it
        saving_mm = max(0.0, raw_total - opt_total)
        saving_pct = 100.0 * saving_mm / raw_total if raw_total > 0 else 0.0
        with st.expander("Path Optimization Results", expanded=True):
            oc1, oc2, oc3 = st.columns(3)
            oc1.metric("Travel before NN", f"{raw_total:.1f} mm")
            oc2.metric(
                "Travel after NN", f"{opt_total:.1f} mm",
                delta=f"-{saving_mm:.1f} mm" if saving_mm > 0 else "no change",
                delta_color="inverse",
            )
            oc3.metric("Travel saved", f"{saving_pct:.1f}%")

    mc1, mc2 = st.columns(2)
    with mc1:
        st.plotly_chart(create_metrics_figure(metrics, print_speed, travel_speed), width="stretch")
    with mc2:
        if infill_lines:
            st.plotly_chart(create_infill_length_histogram(infill_lines, print_speed), width="stretch")
        else:
            st.info("No infill lines to show histogram for.")

    with st.expander("Raw metrics", expanded=False):
        st.json({
            "total_path_mm": f"{metrics['total_path_length_mm']:.2f}",
            "perimeter_mm": f"{metrics['perimeter_length_mm']:.2f}",
            "infill_mm": f"{metrics['infill_length_mm']:.2f}",
            "travel_mm": f"{metrics['travel_length_mm']:.2f}",
            "path_efficiency_%": f"{metrics['path_efficiency_pct']:.1f}",
            "layer_time_s": f"{metrics['estimated_motion_time_s']:.2f}",
            "full_build_s": f"{full_time_s:.2f}",
            "weight_g/layer": f"{metrics['weight_g']:.4f}",
            "weight_g/total": f"{full_weight_g:.2f}",
            "filament_m/layer": f"{metrics['filament_length_m']:.3f}",
            "material_vol_mm3": f"{metrics['material_volume_mm3']:.2f}",
        })

with tab_advisor:
    adv_col1, adv_col2 = st.columns([2, 1])

    with adv_col1:
        st.markdown("### Job Readiness")
        st.progress(readiness["score"] / 100.0, text=f"{readiness['status']} - {readiness['score']}/100")
        if not readiness["issues"]:
            st.success("All automated checks passed for planning review.")
        else:
            for issue in readiness["issues"]:
                message = f"**{issue.title}**  \n{issue.detail}  \nAction: {issue.action}"
                if issue.severity == "blocker":
                    st.error(message)
                elif issue.severity == "warning":
                    st.warning(message)
                else:
                    st.info(message)

    with adv_col2:
        st.markdown("### Release Snapshot")
        ad1, ad2 = st.columns(2)
        ad1.metric("Travel share", f"{travel_ratio:.1f}%", delta_color="inverse")
        ad2.metric("Path efficiency", f"{metrics['path_efficiency_pct']:.1f}%")
        st.metric("Blockers", readiness["blockers"])
        st.metric("Warnings", readiness["warnings"])
        st.metric("Full layers", layer_count)
        density_actual = (
            100 * float(nozzle_diameter) / max(effective_spacing, 0.01)
            if effective_spacing > 0 else 0
        )
        st.metric("Actual density", f"{min(density_actual, 100):.0f}%")

with tab_data:
    df = segments_to_dataframe(segments)
    st.markdown(f"**{len(df)} segments** - columns: `type`, `x0`, `y0`, `x1`, `y1`, `length_mm`, `layer`")
    st.dataframe(df, width="stretch")

with tab_export:
    params = {
        "shape_type": source_label, "process_mode": process_mode, "profile": profile,
        "perimeter_count": int(perimeter_count), "perimeter_spacing_mm": float(perimeter_spacing),
        "infill_pattern": infill_pattern, "infill_spacing_mm": float(effective_spacing),
        "infill_angle_deg": float(effective_angle), "layer_height_mm": float(layer_height),
        "model_height_mm": float(model_height), "print_speed_mm_s": float(print_speed),
        "travel_speed_mm_s": float(travel_speed), "material": material_choice,
        "plate": {"enabled": bool(show_plate), "width_mm": float(plate_w), "depth_mm": float(plate_d)},
        "placement": placement,
        "readiness": readiness_to_dict(readiness),
        "economics": economics,
        "program_risk": program_risk,
        "production_export": {
            "layer_count": int(layer_count),
            "segment_count": len(production_segments),
            "full_build_enabled": bool(layer_count <= production_layer_limit),
            "layer_limit": int(production_layer_limit),
        },
    }
    readiness_lines = [
        f"- {issue.severity.upper()}: {issue.title} | {issue.detail} | Action: {issue.action}"
        for issue in readiness["issues"]
    ] or ["- PASS: All automated checks passed."]
    report = "\n".join([
        "MiniSlicer Toolpath Report",
        "=" * 40,
        f"Readiness:      {readiness['status']} ({readiness['score']}/100)",
        f"Generated:      layer {int(layer_number)} of {layer_count}",
        f"Profile:        {profile}",
        f"Process:        {process_mode}",
        f"Shape:          {source_label}",
        f"Printer:        {printer_profile_name}",
        f"Material:       {material_choice}",
        "",
        "Toolpath",
        f"Infill:         {infill_pattern}, {effective_spacing:.2f} mm, {effective_angle:+.0f} deg",
        f"Perimeters:     {perimeter_count} x {perimeter_spacing:.2f} mm spacing",
        f"Path length:    {metrics['total_path_length_mm']:.2f} mm",
        f"Travel length:  {metrics['travel_length_mm']:.2f} mm",
        f"Path efficiency:{metrics['path_efficiency_pct']:.1f}%",
        "",
        "Full Build",
        f"Layers:         {layer_count}",
        f"Time estimate:  {fmt_time(full_time_s)}",
        f"Material:       {full_weight_g:.2f} g ({metrics['filament_length_m'] * layer_count:.2f} m filament)",
        f"Cost estimate:  ${full_cost:.2f}",
        f"Build plate fit:{' yes' if fits_plate else ' NO - shape outside plate'}",
        "",
        "Readiness Findings",
        *readiness_lines,
        "",
        "Planning output only - validate machine-specific start/end code and process limits before production.",
    ])
    dossier_md = generate_job_dossier_markdown(
        job_name=source_label,
        params=params,
        metrics=metrics,
        readiness=readiness,
        economics=economics,
        full_time_text=fmt_time(full_time_s),
        full_weight_g=full_weight_g,
        layer_count=layer_count,
        risk=program_risk,
    )
    dossier_html = generate_job_dossier_html(dossier_md)
    render_export_panel(
        segments,
        production_segments,
        boundary,
        perimeters,
        infill_lines,
        params,
        float(print_speed),
        float(layer_height),
        float(travel_speed),
        float(z_hop),
        bool(include_e),
        float(extrusion_per_mm),
        report,
        dossier_md,
        dossier_html,
        int(layer_number),
    )
