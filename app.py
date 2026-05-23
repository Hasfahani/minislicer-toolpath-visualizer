"""Streamlit app for MiniSlicer toolpath visualization."""

from __future__ import annotations

import json
import math
from typing import Any

import streamlit as st
from shapely import affinity
from shapely.geometry import Polygon

from src.animation import create_animated_figure
from src.exporters import (
    export_gcode_like,
    export_segments_csv,
    export_segments_json,
    export_svg,
    segments_to_dataframe,
)
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
from src.metrics import MATERIAL_DENSITY, summarize_metrics
from src.plotting import (
    create_3d_figure,
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
from src.toolpaths import (
    build_ordered_segments,
    filter_short_lines,
    generate_infill,
    generate_inward_perimeters,
    optimize_path_order,
    simplify_lines,
    total_travel_distance,
)


PROFILES: dict[str, dict[str, float | int]] = {
    "Fast Preview": {"layer_height": 0.32, "speed": 90.0, "perimeters": 1, "spacing": 6.0},
    "Draft": {"layer_height": 0.28, "speed": 70.0, "perimeters": 2, "spacing": 4.0},
    "Balanced": {"layer_height": 0.20, "speed": 50.0, "perimeters": 3, "spacing": 3.0},
    "Strong": {"layer_height": 0.20, "speed": 45.0, "perimeters": 5, "spacing": 2.2},
    "Fine": {"layer_height": 0.12, "speed": 35.0, "perimeters": 4, "spacing": 2.0},
}

SHAPES = [
    "Rectangle",
    "Rounded Rectangle",
    "Circle",
    "Ellipse",
    "Triangle",
    "Regular Polygon",
    "Star",
    "Cross",
    "Capsule",
    "Arrow",
    "Custom Polygon",
]
PATTERNS = ["Parallel Lines", "Zigzag", "Grid", "Triangles", "Honeycomb", "Concentric"]


def fmt_time(seconds: float) -> str:
    if math.isinf(seconds):
        return "inf"
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    if seconds >= 60:
        return f"{int(seconds // 60)}m {seconds % 60:.0f}s"
    return f"{seconds:.1f}s"


def read_number(config: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(config.get(key, default))
    except (TypeError, ValueError):
        return default


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
        c = shape.centroid
        scale = settings["scale_pct"] / 100.0
        shape = affinity.scale(shape, xfact=scale, yfact=scale, origin=(c.x, c.y))

    if settings["mirror_x"] or settings["mirror_y"]:
        c = shape.centroid
        shape = affinity.scale(
            shape,
            xfact=-1.0 if settings["mirror_x"] else 1.0,
            yfact=-1.0 if settings["mirror_y"] else 1.0,
            origin=(c.x, c.y),
        )

    if settings["rotate_deg"]:
        c = shape.centroid
        shape = affinity.rotate(shape, settings["rotate_deg"], origin=(c.x, c.y))

    if settings["translate_x"] or settings["translate_y"]:
        shape = affinity.translate(shape, xoff=settings["translate_x"], yoff=settings["translate_y"])

    if settings["fit_to_plate"] and settings["show_plate"]:
        min_x, min_y, max_x, max_y = shape.bounds
        target_w = max(settings["plate_w"] - 2 * settings["plate_margin"], 1.0)
        target_h = max(settings["plate_d"] - 2 * settings["plate_margin"], 1.0)
        scale = min(1.0, target_w / max(max_x - min_x, 1e-9), target_h / max(max_y - min_y, 1e-9))
        if scale < 1.0:
            c = shape.centroid
            shape = affinity.scale(shape, xfact=scale, yfact=scale, origin=(c.x, c.y))

    if settings["center_on_plate"] and settings["show_plate"]:
        c = shape.centroid
        shape = affinity.translate(shape, xoff=settings["plate_w"] / 2 - c.x, yoff=settings["plate_d"] / 2 - c.y)

    return shape


def app_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1500px; }
        [data-testid="stSidebar"] { border-right: 1px solid rgba(148, 163, 184, 0.24); }
        [data-testid="stMetric"] {
            background: rgba(248,250,252,.78);
            border: 1px solid rgba(148,163,184,.26);
            border-radius: 8px;
            padding: .75rem .9rem;
        }
        [data-testid="stMetricLabel"] { color: #475569; }
        .stTabs [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid rgba(148,163,184,.28); }
        .stTabs [data-baseweb="tab"] { height: 2.6rem; border-radius: 6px 6px 0 0; padding: 0 .85rem; }
        div[data-testid="stPlotlyChart"] { border: 1px solid rgba(148,163,184,.22); border-radius: 8px; overflow: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="MiniSlicer - Toolpath Planner", layout="wide", page_icon=":material/build:")
app_css()

st.title("MiniSlicer - Toolpath Planner")
st.caption(
    "Interactive FDM/DED toolpath visualizer for planning concepts, previews, metrics, and educational exports."
)

with st.expander("Quick Setup", expanded=True):
    q1, q2, q3, q4 = st.columns([1.4, 1.4, 1.2, 1.2])
    profile = q1.selectbox("Profile", ["Custom", *PROFILES.keys()], index=3)
    process_mode = q2.segmented_control("Process", ["FDM", "DED / Metal"], default="FDM")
    default = PROFILES.get(profile, PROFILES["Balanced"])
    quick_plate = q3.segmented_control("Plate", ["None", "220 x 220", "300 x 300"], default="220 x 220")
    q4.info("Use the sidebar for detailed controls.", icon=":material/tune:")

with st.sidebar:
    st.header("Controls")

    with st.expander("Import", expanded=False):
        uploaded_config = st.file_uploader("Load JSON config", type=["json"])
        imported_config: dict[str, Any] = {}
        if uploaded_config is not None:
            try:
                imported = json.loads(uploaded_config.read().decode("utf-8"))
                imported_config = imported.get("parameters", {}) if isinstance(imported, dict) else {}
                st.success("Config loaded.")
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Could not load config: {exc}")

        uploaded_svg = st.file_uploader("Import SVG shape", type=["svg"])
        svg_target_width = st.number_input("SVG target width (mm)", 5.0, value=80.0, step=5.0)

    with st.expander("Shape", expanded=True):
        shape_type = st.selectbox("Shape", SHAPES, index=0, disabled=uploaded_svg is not None)
        width = st.number_input("Width / base (mm)", 1.0, value=50.0, step=1.0)
        height = st.number_input("Height (mm)", 1.0, value=30.0, step=1.0)
        radius = st.number_input("Radius (mm)", 1.0, value=22.0, step=1.0)
        corner_radius = st.number_input("Corner radius (mm)", 0.0, value=5.0, step=0.5)
        sides = st.slider("Polygon sides", 3, 16, 6)
        points = st.slider("Star points", 3, 12, 5)
        inner_radius = st.number_input("Star inner radius (mm)", 0.5, value=10.0, step=0.5)
        size = st.number_input("Cross size (mm)", 1.0, value=42.0, step=1.0)
        arm_width = st.number_input("Cross arm width (mm)", 0.5, value=14.0, step=0.5)
        length = st.number_input("Arrow length (mm)", 1.0, value=54.0, step=1.0)
        head_width = st.number_input("Arrow head width (mm)", 1.0, value=24.0, step=1.0)
        shaft_width = st.number_input("Arrow shaft width (mm)", 0.5, value=10.0, step=0.5)
        coords_text = st.text_area("Custom polygon", value="0,0; 50,0; 40,25; 10,35")

    with st.expander("Toolpath", expanded=True):
        perimeter_count = st.slider("Perimeters", 1, 10, int(default["perimeters"]))
        perimeter_spacing = st.number_input("Perimeter spacing (mm)", 0.1, value=1.0, step=0.1)
        perimeter_speed_mult = st.slider("Perimeter speed multiplier", 0.2, 1.5, 0.8, 0.05)
        infill_pattern = st.selectbox("Infill pattern", PATTERNS, index=0)
        infill_mode = st.radio("Infill control", ["Spacing", "Density"], horizontal=True)
        infill_spacing = st.number_input("Infill spacing (mm)", 0.1, value=float(default["spacing"]), step=0.1)
        infill_density = st.slider("Infill density (%)", 5, 100, 25, 5)
        infill_angle = st.slider("Infill angle (deg)", -90, 90, 45, 5)
        alternate_angle = st.checkbox("Alternate angle by layer", value=False)
        infill_clearance = st.number_input("Wall clearance (mm)", 0.0, value=0.0, step=0.1)
        infill_overlap = st.number_input("Infill overlap (mm)", 0.0, value=0.0, step=0.05)

    with st.expander("Process", expanded=True):
        layer_number = st.number_input("Layer", min_value=1, value=1, step=1)
        layer_height = st.number_input("Layer height (mm)", 0.05, value=float(default["layer_height"]), step=0.01)
        model_height = st.number_input("Model height estimate (mm)", 0.05, value=5.0, step=0.5)
        print_speed = st.number_input("Print speed (mm/s)", 0.1, value=float(default["speed"]), step=1.0)
        travel_speed = st.number_input("Travel speed (mm/s)", 0.1, value=max(100.0, float(default["speed"]) * 2), step=5.0)
        material_choice = st.selectbox("Material", list(MATERIAL_DENSITY.keys()))
        nozzle_diameter = st.number_input("Nozzle diameter (mm)", 0.1, value=0.4, step=0.1)
        filament_diameter = st.selectbox("Filament diameter (mm)", [1.75, 2.85])
        material_cost = st.number_input("Material cost ($/kg)", 0.0, value=24.0, step=1.0)

    with st.expander("Placement", expanded=False):
        show_plate = st.checkbox("Show build plate", value=quick_plate != "None")
        plate_default = 300.0 if quick_plate == "300 x 300" else 220.0
        plate_w = st.number_input("Plate width (mm)", 10.0, value=plate_default, step=10.0)
        plate_d = st.number_input("Plate depth (mm)", 10.0, value=plate_default, step=10.0)
        center_on_plate = st.checkbox("Center on plate", value=show_plate)
        fit_to_plate = st.checkbox("Fit inside plate", value=False, disabled=not show_plate)
        plate_margin = st.number_input("Plate margin (mm)", 0.0, value=5.0, step=1.0)
        scale_pct = st.slider("Scale (%)", 10, 300, 100, 5)
        rotate_deg = st.slider("Rotate (deg)", -180, 180, 0, 5)
        mirror_x = st.checkbox("Mirror X", value=False)
        mirror_y = st.checkbox("Mirror Y", value=False)
        translate_x = st.number_input("Translate X (mm)", value=0.0, step=1.0)
        translate_y = st.number_input("Translate Y (mm)", value=0.0, step=1.0)

    with st.expander("Preview", expanded=False):
        color_scheme = st.selectbox("Color scheme", ["Classic", "Colorblind", "Dark", "Neon"], index=0)
        line_width_scale = st.slider("Line thickness", 0.5, 3.0, 1.0, 0.25)
        show_boundary = st.checkbox("Outline", value=True)
        show_perimeters = st.checkbox("Perimeters", value=True)
        show_infill = st.checkbox("Infill", value=True)
        show_travel = st.checkbox("Travel moves", value=False)
        show_seams = st.checkbox("Seam markers", value=False)
        show_start_end = st.checkbox("Start/end points", value=False)
        show_arrows = st.checkbox("Direction arrows", value=False)
        show_dimensions = st.checkbox("Dimensions", value=True)
        show_extrusion = st.checkbox("Extrusion width", value=False)

    with st.expander("Quality / Export", expanded=False):
        optimize_perimeters = st.checkbox("Optimize perimeter order", value=False)
        optimize_infill = st.checkbox("Optimize infill order", value=True)
        reverse_lines = st.checkbox("Allow line reversal", value=True, disabled=not optimize_infill)
        simplify_tolerance = st.number_input("Simplify tolerance (mm)", 0.0, value=0.0, step=0.01)
        min_segment_length = st.number_input("Minimum segment length (mm)", 0.0, value=0.0, step=0.05)
        z_hop = st.number_input("Z-hop in G-code (mm)", 0.0, value=0.0, step=0.05)
        include_e = st.checkbox("Include E values", value=False)
        extrusion_per_mm = st.number_input("Extrusion per mm (E/mm)", 0.0, value=0.04, step=0.005)

shape_settings = {
    "width": width,
    "height": height,
    "radius": radius,
    "corner_radius": corner_radius,
    "sides": sides,
    "points": points,
    "inner_radius": min(inner_radius, radius - 0.01),
    "size": size,
    "arm_width": arm_width,
    "length": length,
    "head_width": head_width,
    "shaft_width": min(shaft_width, head_width - 0.1),
    "coords_text": coords_text,
}

if uploaded_svg is not None:
    shape, svg_error = parse_svg_to_polygon(uploaded_svg.read(), target_width_mm=svg_target_width)
    if shape is None:
        st.error(f"SVG import failed: {svg_error}")
        st.stop()
else:
    shape = build_shape(shape_type, shape_settings)

shape = validate_polygon(shape) if shape is not None else None
if shape is None:
    st.error("The selected shape is invalid. Adjust the dimensions or custom polygon points.")
    st.stop()

placement = {
    "scale_pct": scale_pct,
    "mirror_x": mirror_x,
    "mirror_y": mirror_y,
    "rotate_deg": rotate_deg,
    "translate_x": translate_x,
    "translate_y": translate_y,
    "fit_to_plate": fit_to_plate,
    "center_on_plate": center_on_plate,
    "show_plate": show_plate,
    "plate_w": plate_w,
    "plate_d": plate_d,
    "plate_margin": plate_margin,
}
shape = apply_placement(shape, placement)

effective_spacing = (
    max(0.1, float(nozzle_diameter) * 100.0 / float(infill_density))
    if infill_mode == "Density"
    else float(infill_spacing)
)
effective_angle = 45.0 if alternate_angle and int(layer_number) % 2 == 1 else -45.0 if alternate_angle else float(infill_angle)

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
    shape,
    segments,
    perimeters,
    infill_lines,
    print_speed_mm_s=float(print_speed),
    travel_speed_mm_s=float(travel_speed),
    layer_height_mm=float(layer_height),
    nozzle_diameter_mm=float(nozzle_diameter),
    filament_diameter_mm=float(filament_diameter),
    material=material_choice,
)

layer_count = max(1, math.ceil(float(model_height) / float(layer_height)))
full_time_s = metrics["estimated_motion_time_s"] * layer_count
full_weight_g = metrics["weight_g"] * layer_count
full_cost = full_weight_g / 1000.0 * float(material_cost)
min_x, min_y, max_x, max_y = shape.bounds
fits_plate = not show_plate or (min_x >= 0 and min_y >= 0 and max_x <= plate_w and max_y <= plate_d)
travel_ratio = 100 * metrics["travel_length_mm"] / metrics["total_motion_length_mm"] if metrics["total_motion_length_mm"] else 0.0
plate_size = (float(plate_w), float(plate_d)) if show_plate else None
extrusion_width = float(nozzle_diameter) if show_extrusion else 0.0

top1, top2, top3, top4, top5 = st.columns(5)
top1.metric("Path", f"{metrics['total_path_length_mm']:.1f} mm")
top2.metric("Segments", f"{metrics['segment_count']}")
top3.metric("Layer Time", fmt_time(metrics["estimated_motion_time_s"]))
top4.metric("Full Estimate", fmt_time(full_time_s))
top5.metric("Plate Fit", "Yes" if fits_plate else "No")

tab_preview, tab_compare, tab_anim, tab_3d, tab_metrics, tab_advisor, tab_data, tab_export = st.tabs(
    ["Preview", "Compare", "Animation", "3D", "Metrics", "Advisor", "Data", "Export"]
)

with tab_preview:
    c1, c2 = st.columns([3, 1])
    preview_layer = c1.slider("Layer preview", 1, min(layer_count, 50), min(int(layer_number), min(layer_count, 50)))
    mode = c2.selectbox(
        "Mode",
        ["Toolpath", "Extrusion", "Perimeters only", "Infill only", "Travel only", "Speed map", "Time map", "Density"],
    )
    layer_angle = 45.0 if alternate_angle and preview_layer % 2 == 1 else -45.0 if alternate_angle else effective_angle
    preview_infill = infill_lines
    if layer_angle != effective_angle:
        preview_infill = generate_infill(infill_shape, infill_pattern, effective_spacing, layer_angle)
        if optimize_infill:
            preview_infill = optimize_path_order(preview_infill, allow_reverse=reverse_lines)

    st.caption(
        f"Layer {preview_layer}/{layer_count} | {infill_pattern} | spacing {effective_spacing:.2f} mm | angle {layer_angle:+.0f} deg"
    )
    common = dict(
        line_width_scale=float(line_width_scale),
        color_scheme=color_scheme,
        build_plate_size=plate_size,
        show_direction_arrows=show_arrows,
        show_dimensions=show_dimensions,
    )
    if mode == "Speed map":
        fig = create_speed_map_figure(boundary, perimeters, preview_infill, print_speed, travel_speed, line_width_scale, plate_size, perimeter_speed_mult)
    elif mode == "Time map":
        fig = create_time_map_figure(boundary, perimeters, preview_infill, print_speed, line_width_scale, plate_size)
    elif mode == "Density":
        fig = create_path_density_figure(perimeters, preview_infill, boundary, build_plate_size=plate_size)
    else:
        fig = create_toolpath_figure(
            boundary,
            perimeters if mode != "Infill only" else [],
            preview_infill if mode != "Perimeters only" else [],
            show_travel_moves=show_travel or mode == "Travel only",
            show_seam_markers=show_seams,
            show_boundary=show_boundary,
            show_perimeters=show_perimeters and mode != "Infill only" and mode != "Travel only",
            show_infill=show_infill and mode != "Perimeters only" and mode != "Travel only",
            show_start_end_points=show_start_end,
            extrusion_width_mm=float(nozzle_diameter) if mode == "Extrusion" else extrusion_width,
            print_speed_mm_s=float(print_speed),
            **common,
        )
    st.plotly_chart(fig, width="stretch")

with tab_compare:
    a, b, run_col = st.columns([2, 2, 1])
    pattern_a = a.selectbox("Pattern A", PATTERNS, index=PATTERNS.index(infill_pattern))
    pattern_b = b.selectbox("Pattern B", PATTERNS, index=2)
    run_compare = run_col.button("Compare", type="primary", width="stretch")
    if run_compare:
        infill_a = generate_infill(infill_shape, pattern_a, effective_spacing, effective_angle)
        infill_b = generate_infill(infill_shape, pattern_b, effective_spacing, effective_angle)
        fig_cmp = create_comparison_figure(boundary, perimeters, infill_a, infill_b, pattern_a, pattern_b, line_width_scale, color_scheme)
        st.plotly_chart(fig_cmp, width="stretch")
        ca, cb, cc, cd = st.columns(4)
        ca.metric("A lines", len(infill_a))
        cb.metric("B lines", len(infill_b), delta=len(infill_b) - len(infill_a))
        cc.metric("A infill", f"{sum(l.length for l in infill_a):.1f} mm")
        cd.metric("B infill", f"{sum(l.length for l in infill_b):.1f} mm")
    else:
        st.info("Pick two patterns and click Compare.")

with tab_anim:
    if segments:
        st.plotly_chart(create_animated_figure(boundary, segments), width="stretch")
    else:
        st.info("No segments to animate.")

with tab_3d:
    layer_count_3d = st.slider("Layers to stack", 1, 30, min(layer_count, 8))
    if st.button("Generate 3D view", type="primary"):
        fig_3d = create_3d_figure(shape, layer_count_3d, perimeter_count, perimeter_spacing, effective_spacing, layer_height, infill_pattern)
        st.plotly_chart(fig_3d, width="stretch")
    else:
        st.info("Click Generate 3D view to render the layer stack.")

with tab_metrics:
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Area", f"{metrics['area_mm2']:.2f} mm2")
    g2.metric("Bounds", f"{metrics['bbox_width_mm']:.1f} x {metrics['bbox_height_mm']:.1f} mm")
    g3.metric("Material", f"{full_weight_g:.2f} g")
    g4.metric("Cost", f"${full_cost:.2f}")
    st.plotly_chart(create_metrics_figure(metrics, print_speed, travel_speed), width="stretch")
    if infill_lines:
        st.plotly_chart(create_infill_length_histogram(infill_lines, print_speed), width="stretch")

with tab_advisor:
    if fits_plate:
        st.success("Shape fits inside the selected build plate.")
    else:
        st.error("Shape is outside the selected build plate. Enable Center on plate or Fit inside plate.")
    tips: list[str] = []
    if not perimeters:
        tips.append("No perimeters were generated. Reduce perimeter count or spacing.")
    if not infill_lines:
        tips.append("No infill was generated. Reduce spacing or wall clearance.")
    if travel_ratio > 25:
        tips.append("Travel share is high. Try Zigzag, enable optimization, or allow line reversal.")
    if layer_height > nozzle_diameter * 0.8:
        tips.append("Layer height is high relative to nozzle diameter.")
    if not tips:
        tips.append("This setup looks coherent for preview and comparison.")
    for tip in tips:
        st.write(f"- {tip}")
    s1, s2, s3 = st.columns(3)
    s1.metric("Travel Share", f"{travel_ratio:.1f}%")
    s2.metric("Path Efficiency", f"{metrics['path_efficiency_pct']:.1f}%")
    s3.metric("Full Layers", layer_count)

with tab_data:
    st.dataframe(segments_to_dataframe(segments), width="stretch")

with tab_export:
    params = {
        "shape_type": "SVG" if uploaded_svg is not None else shape_type,
        "process_mode": process_mode,
        "profile": profile,
        "perimeter_count": int(perimeter_count),
        "perimeter_spacing_mm": float(perimeter_spacing),
        "infill_pattern": infill_pattern,
        "infill_spacing_mm": float(effective_spacing),
        "infill_angle_deg": float(effective_angle),
        "layer_height_mm": float(layer_height),
        "model_height_mm": float(model_height),
        "print_speed_mm_s": float(print_speed),
        "travel_speed_mm_s": float(travel_speed),
        "material": material_choice,
        "plate": {"enabled": bool(show_plate), "width_mm": float(plate_w), "depth_mm": float(plate_d)},
        "placement": placement,
    }
    csv_text = export_segments_csv(segments)
    json_text = export_segments_json(segments, params)
    svg_text = export_svg(boundary, perimeters, infill_lines)
    gcode_text = export_gcode_like(
        segments,
        print_speed_mm_s=float(print_speed),
        layer_height_mm=float(layer_height),
        travel_speed_mm_s=float(travel_speed),
        z_hop_mm=float(z_hop),
        include_e_values=bool(include_e),
        extrusion_per_mm=float(extrusion_per_mm),
    )
    report = "\n".join(
        [
            "MiniSlicer Toolpath Report",
            "",
            f"Profile: {profile}",
            f"Process: {process_mode}",
            f"Shape: {'SVG' if uploaded_svg else shape_type}",
            f"Infill: {infill_pattern}, {effective_spacing:.2f} mm, {effective_angle:+.0f} deg",
            f"Path length: {metrics['total_path_length_mm']:.2f} mm",
            f"Travel length: {metrics['travel_length_mm']:.2f} mm",
            f"Path efficiency: {metrics['path_efficiency_pct']:.1f}%",
            f"Full estimate: {layer_count} layers, {fmt_time(full_time_s)}, {full_weight_g:.2f} g, ${full_cost:.2f}",
            f"Build plate fit: {'yes' if fits_plate else 'no'}",
            "",
            "Educational preview only; not machine-ready slicer output.",
        ]
    )
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.download_button("CSV", csv_text, f"toolpaths_layer_{int(layer_number)}.csv", "text/csv", width="stretch")
    d2.download_button("G-code", gcode_text, f"toolpaths_layer_{int(layer_number)}.gcode.txt", "text/plain", width="stretch")
    d3.download_button("SVG", svg_text, f"toolpaths_layer_{int(layer_number)}.svg", "image/svg+xml", width="stretch")
    d4.download_button("JSON", json_text, f"toolpaths_layer_{int(layer_number)}.json", "application/json", width="stretch")
    d5.download_button("Report", report, f"toolpaths_layer_{int(layer_number)}_report.txt", "text/plain", width="stretch")
    with st.expander("JSON preview"):
        st.code(json_text[:4000], language="json")
