"""Streamlit app for MiniSlicer toolpath visualization."""

from __future__ import annotations

from dataclasses import replace
from html import escape
from math import ceil

import streamlit as st

from src.animation import create_animated_figure
from src.catalog import PATTERN_ICONS, PATTERNS, SHAPE_ICONS, SHAPES
from src.exporters import segments_to_dataframe
from src.geometry import validate_polygon
from src.job_analysis import (
    assess_commercial_fit,
    assess_manufacturing_partner_fit,
    build_batch_scenarios,
    build_ded_recommendations,
    build_launch_recommendations,
    build_optimization_playbook,
    build_production_handoff_recommendations,
    build_qualification_plan,
    build_quality_scorecard,
    build_release_checklist,
    classify_program_risk,
    compute_launch_score,
    estimate_ded_process,
    estimate_job_economics,
    estimate_robot_cell_handoff,
    estimate_thermal_management,
    generate_job_dossier_html,
    generate_job_dossier_markdown,
)
from src.metrics import MATERIAL_DENSITY, summarize_metrics
from src.planner import (
    ToolpathSettings,
    build_plan_fingerprint,
    build_production_segments,
    plan_layer,
    rank_infill_patterns,
)
from src.plotting import (
    create_comparison_figure,
    create_infill_length_histogram,
    create_metrics_figure,
    create_path_density_figure,
    create_speed_map_figure,
    create_time_map_figure,
    create_toolpath_figure,
)
from src.stl_import import slice_stl_to_polygon
from src.svg_import import parse_svg_to_polygon
from src.toolpaths import (
    generate_infill,
    generate_inward_perimeters,
    total_travel_distance,
)
from src.validation import assess_job_readiness, readiness_to_dict
from src.workflow import apply_placement, build_shape, fmt_time, largest_polygon
from ui.dashboard import (
    render_ded_process_panel,
    render_executive_dashboard,
    render_launch_optimizer,
    render_launch_ribbon,
    render_next_action,
    render_partner_fit_panel,
    render_pattern_ranking,
    render_production_handoff_panel,
    render_quality_scorecard,
    render_release_gate_matrix,
)
from ui.export_panel import render_export_panel
from ui.sidebar import render_quick_setup, render_sidebar
from ui.stl_workflow import render_stl_multilayer_view

# ---------------------------------------------------------------------------
# Performance: cached wrappers for expensive geometry/toolpath computations.
# Shapes are passed as WKT strings so Streamlit can hash them correctly.
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _cached_plan_layer(
    shape_wkt: str,
    infill_wkt: str,
    settings: ToolpathSettings,
    layer: int,
    infill_angle_deg: float | None = None,
):
    from shapely import wkt
    return plan_layer(
        wkt.loads(shape_wkt),
        wkt.loads(infill_wkt),
        settings,
        layer=layer,
        infill_angle_deg=infill_angle_deg,
    )


@st.cache_data(show_spinner="Computing production layers...")
def _cached_production_segments(
    shape_wkt: str,
    infill_wkt: str,
    settings: ToolpathSettings,
    layer_count: int,
    alternate_angle: bool,
    layer_limit: int,
):
    from shapely import wkt
    return build_production_segments(
        wkt.loads(shape_wkt),
        wkt.loads(infill_wkt),
        settings,
        layer_count=layer_count,
        alternate_angle=alternate_angle,
        layer_limit=layer_limit,
    )


@st.cache_data(show_spinner="Ranking infill patterns...")
def _cached_rank_infill_patterns(
    infill_wkt: str,
    patterns: tuple[str, ...],
    settings: ToolpathSettings,
):
    from shapely import wkt
    return rank_infill_patterns(wkt.loads(infill_wkt), list(patterns), settings)


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
            --ms-soft: #eef2f7;
            --ms-blue: #1d4ed8;
            --ms-teal: #0f766e;
            --ms-amber: #b45309;
            --ms-green: #15803d;
            --ms-red: #b91c1c;
            --ms-shadow: 0 16px 38px rgba(23, 32, 51, 0.08);
        }
        .stApp { background: linear-gradient(180deg, #eef3f8 0%, #f8fafc 24rem, #ffffff 52rem); }
        .block-container { padding-top: 0.65rem; padding-bottom: 2rem; max-width: 1600px; }
        .ms-header {
            background: #172033; border: 1px solid rgba(255,255,255,0.10);
            border-radius: 8px; padding: 1rem 1.15rem 0.95rem; margin-bottom: 0.75rem;
            display: flex; align-items: center; gap: 0.85rem;
            box-shadow: 0 18px 42px rgba(23, 32, 51, 0.16);
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
        .launch-ribbon {
            display: grid; grid-template-columns: minmax(14rem, 1fr) auto minmax(9rem, auto);
            gap: 1rem; align-items: center; background: rgba(255,255,255,0.92);
            border: 1px solid var(--ms-line); border-radius: 8px; padding: 0.85rem 1rem;
            margin: 0.1rem 0 0.9rem; box-shadow: var(--ms-shadow);
        }
        .launch-kicker { color: var(--ms-muted); font-size: 0.72rem; text-transform: uppercase; font-weight: 760; }
        .launch-title { color: var(--ms-ink); font-size: 1.05rem; font-weight: 780; line-height: 1.2; }
        .launch-sub { color: var(--ms-muted); font-size: 0.8rem; margin-top: 0.1rem; }
        .launch-pills { display: flex; flex-wrap: wrap; justify-content: center; gap: 0.45rem; }
        .launch-money { text-align: right; color: var(--ms-muted); font-size: 0.76rem; }
        .launch-money strong { display: block; color: var(--ms-ink); font-size: 1.32rem; line-height: 1.1; }
        .ms-pill {
            display: inline-flex; align-items: center; min-height: 1.75rem; border-radius: 6px;
            padding: 0.18rem 0.66rem; font-size: 0.76rem; font-weight: 720;
            border: 1px solid var(--ms-line); background: #ffffff; color: var(--ms-ink);
        }
        .ms-pill-ok { border-color: #bbf7d0; background: #f0fdf4; color: #166534; }
        .ms-pill-warn { border-color: #fde68a; background: #fffbeb; color: #92400e; }
        .ms-pill-bad { border-color: #fecaca; background: #fef2f2; color: #991b1b; }
        .exec-hero {
            display: grid; grid-template-columns: minmax(0, 1fr) minmax(8rem, auto); gap: 1rem;
            align-items: center; background: #172033; border-radius: 8px;
            padding: 1.15rem 1.25rem; margin-bottom: 0.9rem; box-shadow: var(--ms-shadow);
        }
        .exec-eyebrow { color: #8dd6cc; text-transform: uppercase; font-size: 0.72rem; font-weight: 760; }
        .exec-hero h2 { color: #ffffff; font-size: 1.55rem; margin: 0.1rem 0; line-height: 1.2; }
        .exec-hero p { color: #cbd5e1; margin: 0; font-size: 0.86rem; }
        .exec-score {
            display: grid; grid-template-columns: auto auto; column-gap: 0.2rem; align-items: end;
            background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.13);
            border-radius: 8px; padding: 0.75rem 0.95rem; min-width: 8.5rem; text-align: right;
        }
        .exec-score span { grid-column: 1 / -1; color: #cbd5e1; font-size: 0.75rem; font-weight: 720; }
        .exec-score strong { color: #ffffff; font-size: 2.3rem; line-height: 0.95; }
        .exec-score small { color: #cbd5e1; font-size: 0.85rem; margin-bottom: 0.2rem; }
        .exec-strip {
            display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.75rem;
            margin: 0.2rem 0 0.9rem;
        }
        .exec-card {
            background: #ffffff; border: 1px solid var(--ms-line); border-radius: 8px;
            padding: 0.9rem 0.95rem; min-height: 5.6rem; box-shadow: 0 10px 24px rgba(23, 32, 51, 0.055);
        }
        .exec-label { color: var(--ms-muted); font-size: 0.76rem; font-weight: 650; margin-bottom: 0.25rem; }
        .exec-value { color: var(--ms-ink); font-size: 1.35rem; font-weight: 760; line-height: 1.2; }
        .exec-note { color: var(--ms-muted); font-size: 0.78rem; margin-top: 0.25rem; }
        .exec-text-ok { color: var(--ms-green); }
        .exec-text-warn { color: var(--ms-amber); }
        .exec-text-bad { color: var(--ms-red); }
        .exec-text-neutral { color: var(--ms-ink); }
        .quality-hero {
            display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1rem; align-items: center;
            background: #ffffff; border: 1px solid var(--ms-line); border-left: 4px solid var(--ms-blue);
            border-radius: 8px; padding: 1rem 1.05rem; margin: 0.1rem 0 0.8rem; box-shadow: var(--ms-shadow);
        }
        .quality-hero.quality-ok { border-left-color: var(--ms-green); }
        .quality-hero.quality-warn { border-left-color: var(--ms-amber); }
        .quality-hero.quality-bad { border-left-color: var(--ms-red); }
        .quality-kicker { color: var(--ms-muted); text-transform: uppercase; font-size: 0.72rem; font-weight: 760; }
        .quality-hero h3 { color: var(--ms-ink); margin: 0.08rem 0; font-size: 1.35rem; line-height: 1.2; }
        .quality-hero p { color: var(--ms-muted); margin: 0; font-size: 0.82rem; }
        .quality-total { color: var(--ms-ink); font-size: 2.3rem; font-weight: 830; line-height: 1; text-align: right; }
        .quality-total span { color: var(--ms-muted); font-size: 0.85rem; font-weight: 680; }
        .quality-grid {
            display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.65rem;
            margin: 0 0 0.85rem;
        }
        .quality-card {
            background: #ffffff; border: 1px solid var(--ms-line); border-radius: 8px;
            padding: 0.82rem 0.88rem; min-height: 7.1rem; box-shadow: 0 10px 22px rgba(23, 32, 51, 0.045);
        }
        .quality-ok { border-top: 3px solid var(--ms-green); }
        .quality-warn { border-top: 3px solid var(--ms-amber); }
        .quality-bad { border-top: 3px solid var(--ms-red); }
        .quality-top { color: var(--ms-muted); font-size: 0.72rem; text-transform: uppercase; font-weight: 760; }
        .quality-score {
            color: var(--ms-ink); font-size: 1.55rem; font-weight: 820; line-height: 1.1; margin-top: 0.25rem;
        }
        .quality-score span { color: var(--ms-muted); font-size: 0.72rem; font-weight: 680; }
        .quality-state { color: var(--ms-ink); font-size: 0.82rem; font-weight: 720; margin-top: 0.16rem; }
        .quality-signal { color: var(--ms-muted); font-size: 0.76rem; line-height: 1.25; margin-top: 0.2rem; }
        .pattern-winner {
            display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1rem; align-items: center;
            background: #ffffff; border: 1px solid var(--ms-line); border-left: 4px solid var(--ms-teal);
            border-radius: 8px; padding: 0.95rem 1rem; margin: 0 0 0.75rem; box-shadow: var(--ms-shadow);
        }
        .pattern-kicker { color: var(--ms-muted); text-transform: uppercase; font-size: 0.72rem; font-weight: 760; }
        .pattern-name { color: var(--ms-ink); font-size: 1.3rem; font-weight: 790; line-height: 1.15; }
        .pattern-note { color: var(--ms-muted); font-size: 0.8rem; margin-top: 0.2rem; }
        .pattern-score { color: var(--ms-teal); font-size: 2rem; font-weight: 820; line-height: 1; text-align: right; }
        .pattern-score span { color: var(--ms-muted); font-size: 0.78rem; font-weight: 680; }
        .export-package {
            display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 0.75rem; align-items: center;
            background: #ffffff; border: 1px solid var(--ms-line); border-radius: 8px;
            padding: 0.9rem 1rem; margin: 0.2rem 0 0.85rem; box-shadow: var(--ms-shadow);
        }
        .export-kicker { color: var(--ms-muted); text-transform: uppercase; font-size: 0.72rem; font-weight: 760; }
        .export-title { color: var(--ms-ink); font-size: 1.12rem; font-weight: 790; line-height: 1.2; }
        .export-note { color: var(--ms-muted); font-size: 0.8rem; margin-top: 0.14rem; }
        .export-stat { text-align: right; border-left: 1px solid var(--ms-line); padding-left: 1rem; min-width: 7rem; }
        .export-stat span { color: var(--ms-muted); font-size: 0.72rem; font-weight: 720; display: block; }
        .export-stat strong { color: var(--ms-ink); font-size: 1.12rem; line-height: 1.2; }
        @media (max-width: 980px) {
            .exec-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .quality-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .launch-ribbon { grid-template-columns: 1fr; }
            .launch-pills { justify-content: flex-start; }
            .launch-money { text-align: left; }
        }
        @media (max-width: 640px) {
            .exec-strip, .exec-hero, .quality-grid, .quality-hero, .pattern-winner, .export-package {
                grid-template-columns: 1fr;
            }
            .exec-score { text-align: left; }
            .quality-total, .pattern-score, .export-stat { text-align: left; }
            .export-stat { border-left: 0; border-top: 1px solid var(--ms-line); padding: 0.65rem 0 0; }
        }
        [data-testid="stSidebar"] { border-right: 1px solid var(--ms-line); background: var(--ms-surface); }
        [data-testid="stSidebar"] h2 { letter-spacing: 0; color: var(--ms-ink); }
        [data-testid="stSidebar"] div[data-testid="stExpander"] {
            border: 1px solid #dbe2ee; background: rgba(255,255,255,0.82); box-shadow: none;
        }
        button[kind="primary"], div[data-testid="stDownloadButton"] button {
            border-radius: 6px !important; font-weight: 720 !important;
        }
        button[kind="primary"] {
            background: #172033 !important; border: 1px solid #172033 !important;
        }
        div[data-testid="stTabs"] button {
            border-radius: 6px 6px 0 0; font-weight: 680;
        }
        [data-testid="stMetric"] {
            background: var(--ms-panel); border: 1px solid var(--ms-line); border-radius: 8px;
            padding: 0.72rem 0.9rem; box-shadow: 0 10px 24px rgba(23, 32, 51, 0.045);
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
            box-shadow: var(--ms-shadow);
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
                <p class="ms-header-sub">
                    Launch desk for additive planning, quoting, readiness, and traceable exports
                </p>
            </div>
            <div class="ms-header-badge">Manufacturing Command Center</div>
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
    process_mode,
    advanced,
    SHAPES,
    PATTERNS,
    SHAPE_ICONS,
    PATTERN_ICONS,
)
# Explicit unpacking of every sidebar setting consumed below. This documents
# the app's full input surface and keeps the data flow visible to static
# analysis (a previous locals().update() hid all of it).

# Import (SVG / STL)
uploaded_svg = controls["uploaded_svg"]
svg_target_width = controls["svg_target_width"]
uploaded_stl = controls["uploaded_stl"]
stl_target_width = controls["stl_target_width"]
stl_bytes = controls["stl_bytes"]
stl_info = controls["stl_info"]
stl_slice_z = controls["stl_slice_z"]

# Shape
shape_type = controls["shape_type"]
width = controls["width"]
height = controls["height"]
radius = controls["radius"]
corner_radius = controls["corner_radius"]
sides = controls["sides"]
points = controls["points"]
inner_radius = controls["inner_radius"]
size = controls["size"]
arm_width = controls["arm_width"]
length = controls["length"]
head_width = controls["head_width"]
shaft_width = controls["shaft_width"]
coords_text = controls["coords_text"]

# Toolpath
perimeter_count = controls["perimeter_count"]
perimeter_spacing = controls["perimeter_spacing"]
infill_pattern = controls["infill_pattern"]
infill_mode = controls["infill_mode"]
infill_density = controls["infill_density"]
infill_spacing = controls["infill_spacing"]
infill_angle = controls["infill_angle"]
alternate_angle = controls["alternate_angle"]
infill_clearance = controls["infill_clearance"]
infill_overlap = controls["infill_overlap"]
perimeter_speed_mult = controls["perimeter_speed_mult"]

# Print settings
printer_profile_name = controls["printer_profile_name"]
layer_number = controls["layer_number"]
model_height = controls["model_height"]
material_choice = controls["material_choice"]
material_cost = controls["material_cost"]
layer_height = controls["layer_height"]
nozzle_diameter = controls["nozzle_diameter"]
print_speed = controls["print_speed"]
travel_speed = controls["travel_speed"]
filament_diameter = controls["filament_diameter"]
acceleration_mm_s2 = controls["acceleration_mm_s2"]

# Business / launch
job_name = controls["job_name"]
customer_name = controls["customer_name"]
owner_name = controls["owner_name"]
job_id = controls["job_id"]
batch_quantity = controls["batch_quantity"]
target_unit_price = controls["target_unit_price"]
application_type = controls["application_type"]
conventional_route = controls["conventional_route"]
urgency = controls["urgency"]
qualification_level = controls["qualification_level"]
material_strategy = controls["material_strategy"]
quote_profile = controls["quote_profile"]
machine_rate_per_h = controls["machine_rate_per_h"]
labor_rate_per_h = controls["labor_rate_per_h"]
setup_time_min = controls["setup_time_min"]
postprocess_time_min = controls["postprocess_time_min"]
scrap_allowance_pct = controls["scrap_allowance_pct"]
margin_pct = controls["margin_pct"]
max_lead_time_h = controls["max_lead_time_h"]
finish_tolerance_mm = controls["finish_tolerance_mm"]
annual_quantity = controls["annual_quantity"]
ndt_required = controls["ndt_required"]
redesign_required = controls["redesign_required"]

# DED / wire-arc process
ded_enabled = controls["ded_enabled"]
ded_profile = controls["ded_profile"]
ded_envelope_x_mm = controls["ded_envelope_x_mm"]
ded_envelope_y_mm = controls["ded_envelope_y_mm"]
ded_envelope_z_mm = controls["ded_envelope_z_mm"]
ded_wire_diameter_mm = controls["ded_wire_diameter_mm"]
ded_wire_feed_m_min = controls["ded_wire_feed_m_min"]
ded_arc_current_a = controls["ded_arc_current_a"]
ded_arc_voltage_v = controls["ded_arc_voltage_v"]
ded_arc_efficiency_pct = controls["ded_arc_efficiency_pct"]
ded_deposition_efficiency_pct = controls["ded_deposition_efficiency_pct"]
ded_robot_utilization_pct = controls["ded_robot_utilization_pct"]
ded_machining_allowance_pct = controls["ded_machining_allowance_pct"]
ded_billet_buy_to_fly = controls["ded_billet_buy_to_fly"]
ded_conventional_lead_time_weeks = controls["ded_conventional_lead_time_weeks"]
ded_machine_capacity_h_week = controls["ded_machine_capacity_h_week"]
ded_preheat_temp_c = controls["ded_preheat_temp_c"]
ded_interpass_limit_c = controls["ded_interpass_limit_c"]
ded_cooling_rate_c_min = controls["ded_cooling_rate_c_min"]
ded_heat_retention_pct = controls["ded_heat_retention_pct"]
ded_robot_reach_mm = controls["ded_robot_reach_mm"]
ded_positioner_payload_kg = controls["ded_positioner_payload_kg"]
ded_fixture_mass_kg = controls["ded_fixture_mass_kg"]
ded_torch_clearance_mm = controls["ded_torch_clearance_mm"]
ded_program_point_limit = controls["ded_program_point_limit"]

# Placement
show_plate = controls["show_plate"]
scale_pct = controls["scale_pct"]
rotate_deg = controls["rotate_deg"]
center_on_plate = controls["center_on_plate"]
fit_to_plate = controls["fit_to_plate"]
plate_margin = controls["plate_margin"]
plate_w = controls["plate_w"]
plate_d = controls["plate_d"]
mirror_x = controls["mirror_x"]
mirror_y = controls["mirror_y"]
translate_x = controls["translate_x"]
translate_y = controls["translate_y"]

# Preview appearance and quality/export
color_scheme = controls["color_scheme"]
line_width_scale = controls["line_width_scale"]
show_boundary = controls["show_boundary"]
show_perimeters = controls["show_perimeters"]
show_infill = controls["show_infill"]
show_dimensions = controls["show_dimensions"]
show_travel = controls["show_travel"]
show_seams = controls["show_seams"]
show_start_end = controls["show_start_end"]
show_arrows = controls["show_arrows"]
show_extrusion = controls["show_extrusion"]
optimize_perimeters = controls["optimize_perimeters"]
optimize_infill = controls["optimize_infill"]
reverse_lines = controls["reverse_lines"]
simplify_tolerance = controls["simplify_tolerance"]
min_segment_length = controls["min_segment_length"]
z_hop = controls["z_hop"]
extrusion_per_mm = controls["extrusion_per_mm"]
include_e = controls["include_e"]

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

infill_shape = shape
net_clearance = max(0.0, float(infill_clearance) - float(infill_overlap))
if net_clearance > 0:
    inset = largest_polygon(shape.buffer(-net_clearance))
    if inset is None:
        st.warning("Wall clearance is too large for this shape; infill uses the full shape.")
    else:
        infill_shape = inset

toolpath_settings = ToolpathSettings(
    perimeter_count=int(perimeter_count),
    perimeter_spacing_mm=float(perimeter_spacing),
    infill_pattern=str(infill_pattern),
    infill_spacing_mm=float(effective_spacing),
    infill_angle_deg=float(effective_angle),
    optimize_perimeters=bool(optimize_perimeters),
    optimize_infill=bool(optimize_infill),
    allow_line_reverse=bool(reverse_lines),
    simplify_tolerance_mm=float(simplify_tolerance),
    min_segment_length_mm=float(min_segment_length),
)

_shape_wkt = shape.wkt
_infill_wkt = infill_shape.wkt

active_plan = _cached_plan_layer(_shape_wkt, _infill_wkt, toolpath_settings, int(layer_number))
boundary = active_plan.boundary
perimeters = active_plan.perimeters
infill_lines = active_plan.infill_lines
segments = active_plan.segments
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

layer_count = max(1, ceil(float(model_height) / float(layer_height)))
production_layer_limit = 600
production_segments = _cached_production_segments(
    _shape_wkt,
    _infill_wkt,
    toolpath_settings,
    layer_count=layer_count,
    alternate_angle=bool(alternate_angle),
    layer_limit=production_layer_limit,
)
plan_fingerprint = build_plan_fingerprint(
    shape,
    toolpath_settings,
    layer_count=layer_count,
    process_mode=str(process_mode),
    material=str(material_choice),
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
    machine_rate_per_h=float(machine_rate_per_h),
    labor_rate_per_h=float(labor_rate_per_h),
    setup_time_min=float(setup_time_min),
    postprocess_time_min=float(postprocess_time_min),
    scrap_allowance_pct=float(scrap_allowance_pct),
    margin_pct=float(margin_pct),
    batch_quantity=int(batch_quantity),
)
ded_analysis = None
if bool(ded_enabled):
    ded_analysis = estimate_ded_process(
        metrics=metrics,
        material_density_g_cm3=float(MATERIAL_DENSITY.get(material_choice, 7.99)),
        full_weight_g=full_weight_g,
        full_time_s=full_time_s,
        model_height_mm=float(model_height),
        bbox_width_mm=float(metrics["bbox_width_mm"]),
        bbox_depth_mm=float(metrics["bbox_height_mm"]),
        layer_height_mm=float(layer_height),
        bead_width_mm=float(nozzle_diameter),
        print_speed_mm_s=float(print_speed),
        wire_diameter_mm=float(ded_wire_diameter_mm),
        wire_feed_m_min=float(ded_wire_feed_m_min),
        arc_current_a=float(ded_arc_current_a),
        arc_voltage_v=float(ded_arc_voltage_v),
        arc_efficiency_pct=float(ded_arc_efficiency_pct),
        deposition_efficiency_pct=float(ded_deposition_efficiency_pct),
        robot_utilization_pct=float(ded_robot_utilization_pct),
        machining_allowance_pct=float(ded_machining_allowance_pct),
        billet_buy_to_fly=float(ded_billet_buy_to_fly),
        conventional_lead_time_weeks=float(ded_conventional_lead_time_weeks),
        machine_capacity_h_week=float(ded_machine_capacity_h_week),
        envelope_x_mm=float(ded_envelope_x_mm),
        envelope_y_mm=float(ded_envelope_y_mm),
        envelope_z_mm=float(ded_envelope_z_mm),
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
commercial_fit = assess_commercial_fit(
    economics=economics,
    target_unit_price=float(target_unit_price),
    max_lead_time_h=float(max_lead_time_h),
)
partner_fit = assess_manufacturing_partner_fit(
    ded_analysis=ded_analysis,
    economics=economics,
    commercial_fit=commercial_fit,
    application_type=str(application_type),
    conventional_route=str(conventional_route),
    urgency=str(urgency),
    qualification_level=str(qualification_level),
    material_strategy=str(material_strategy),
    finish_tolerance_mm=float(finish_tolerance_mm),
    annual_quantity=int(annual_quantity),
    ndt_required=bool(ndt_required),
    redesign_required=bool(redesign_required),
) if ded_analysis is not None else None
thermal_plan = None
robot_handoff = None
qualification_plan = None
if ded_analysis is not None:
    thermal_plan = estimate_thermal_management(
        ded_analysis=ded_analysis,
        layer_count=layer_count,
        preheat_temp_c=float(ded_preheat_temp_c),
        interpass_limit_c=float(ded_interpass_limit_c),
        cooling_rate_c_min=float(ded_cooling_rate_c_min),
        heat_retention_pct=float(ded_heat_retention_pct),
    )
    robot_handoff = estimate_robot_cell_handoff(
        ded_analysis=ded_analysis,
        production_segment_count=len(production_segments),
        robot_reach_mm=float(ded_robot_reach_mm),
        positioner_payload_kg=float(ded_positioner_payload_kg),
        fixture_mass_kg=float(ded_fixture_mass_kg),
        torch_clearance_mm=float(ded_torch_clearance_mm),
        program_point_limit=int(ded_program_point_limit),
    )
    qualification_plan = build_qualification_plan(
        partner_fit=partner_fit,
        thermal_plan=thermal_plan,
        robot_handoff=robot_handoff,
        qualification_level=str(qualification_level),
        material_strategy=str(material_strategy),
        ndt_required=bool(ndt_required),
        finish_tolerance_mm=float(finish_tolerance_mm),
    )
launch_score = compute_launch_score(
    readiness=readiness,
    risk=program_risk,
    commercial_fit=commercial_fit,
)
production_enabled = (
    readiness["status"] != "Blocked"
    and str(process_mode).startswith("FDM")
    and layer_count <= production_layer_limit
)
quality_scorecard = build_quality_scorecard(
    readiness=readiness,
    economics=economics,
    commercial_fit=commercial_fit,
    metrics=metrics,
    production_enabled=production_enabled,
    plan_fingerprint=plan_fingerprint,
)
pattern_ranking = _cached_rank_infill_patterns(_infill_wkt, tuple(PATTERNS), toolpath_settings)
recommended_pattern = pattern_ranking[0]["pattern"] if pattern_ranking else str(infill_pattern)
launch_recommendations = build_launch_recommendations(
    readiness=readiness,
    commercial_fit=commercial_fit,
    metrics=metrics,
    economics=economics,
    quality_scorecard=quality_scorecard,
    production_enabled=production_enabled,
    fits_plate=fits_plate,
    travel_ratio_pct=float(travel_ratio),
    effective_spacing_mm=float(effective_spacing),
    nozzle_diameter_mm=float(nozzle_diameter),
    layer_count=layer_count,
    recommended_pattern=str(recommended_pattern),
)
if ded_analysis is not None:
    launch_recommendations = sorted(
        [
            *launch_recommendations,
            *build_ded_recommendations(ded_analysis),
            *build_production_handoff_recommendations(
                thermal_plan=thermal_plan,
                robot_handoff=robot_handoff,
                qualification_plan=qualification_plan,
            ),
        ],
        key=lambda item: (-int(item["priority_score"]), str(item["area"]), str(item["title"])),
    )
scenario_quantities = sorted({
    1,
    int(batch_quantity),
    max(2, int(batch_quantity) * 2),
    10,
    25,
})
batch_scenarios = build_batch_scenarios(
    metrics=metrics,
    layer_count=layer_count,
    layer_height_mm=float(layer_height),
    nozzle_diameter_mm=float(nozzle_diameter),
    print_speed_mm_s=float(print_speed),
    full_time_s=full_time_s,
    full_weight_g=full_weight_g,
    material_cost_per_kg=float(material_cost),
    machine_rate_per_h=float(machine_rate_per_h),
    labor_rate_per_h=float(labor_rate_per_h),
    setup_time_min=float(setup_time_min),
    postprocess_time_min=float(postprocess_time_min),
    scrap_allowance_pct=float(scrap_allowance_pct),
    margin_pct=float(margin_pct),
    target_unit_price=float(target_unit_price),
    max_lead_time_h=float(max_lead_time_h),
    quantities=scenario_quantities,
)
optimization_playbook = build_optimization_playbook(
    current_pattern=str(infill_pattern),
    pattern_ranking=pattern_ranking,
    metrics=metrics,
    economics=economics,
    batch_scenarios=batch_scenarios,
    print_speed_mm_s=float(print_speed),
    layer_height_mm=float(layer_height),
    nozzle_diameter_mm=float(nozzle_diameter),
    travel_ratio_pct=float(travel_ratio),
    production_enabled=production_enabled,
)
release_checklist = build_release_checklist(
    readiness=readiness,
    commercial_fit=commercial_fit,
    production_enabled=production_enabled,
    plan_fingerprint=plan_fingerprint,
    export_segment_count=len(production_segments),
)

# ---------------------------------------------------------------------------
# Top metrics strip
# ---------------------------------------------------------------------------
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
    ("Plan", plan_fingerprint),
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

# ---------------------------------------------------------------------------
# Recommended next action banner
# ---------------------------------------------------------------------------
render_next_action(
    readiness=readiness,
    commercial_fit=commercial_fit,
    metrics=metrics,
    economics=economics,
    fits_plate=fits_plate,
    travel_ratio=travel_ratio,
    launch_score=launch_score,
)

render_launch_ribbon(
    job_name=str(job_name),
    customer_name=str(customer_name),
    launch_score=launch_score,
    readiness=readiness,
    commercial_fit=commercial_fit,
    program_risk=program_risk,
    economics=economics,
)

# ---------------------------------------------------------------------------
# Three-workspace tab layout: Design | Plan | Release
# ---------------------------------------------------------------------------
tab_design, tab_plan, tab_release = st.tabs(["Design", "Plan", "Release"])

# ---- Design -----------------------------------------------------------------
with tab_design:
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
        preview_infill = _cached_plan_layer(
            _shape_wkt, _infill_wkt, toolpath_settings,
            layer=preview_layer, infill_angle_deg=layer_angle,
        ).infill_lines

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

    if stl_bytes is not None:
        st.markdown("---")
        st.markdown("#### STL Multi-Layer Preview")
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
    else:
        with st.expander("3D / Multi-layer preview", expanded=False):
            st.info(
                "Import an STL file to enable multi-layer and 3D stack views. "
                "Use the Import controls in the sidebar to upload an STL."
            )

# ---- Plan -------------------------------------------------------------------
with tab_plan:
    with st.expander("Pattern Ranking & Comparison", expanded=True):
        st.markdown("### Pattern Ranking")
        ranking = pattern_ranking
        render_pattern_ranking(ranking)

        if ranking:
            # Decision-oriented summary: label each pattern's best quality
            best_speed = min(ranking, key=lambda r: r["line_count"])
            best_travel = min(ranking, key=lambda r: r["travel_mm"])
            best_coverage = max(ranking, key=lambda r: r["path_mm"])
            best_efficiency = max(ranking, key=lambda r: r["efficiency_pct"])
            decision_items = [
                ("Fewest moves (fastest)", best_speed["pattern"], f"{best_speed['line_count']} lines"),
                ("Lowest travel", best_travel["pattern"], f"{best_travel['travel_mm']:.1f} mm travel"),
                ("Most coverage", best_coverage["pattern"], f"{best_coverage['path_mm']:.1f} mm path"),
                ("Best efficiency", best_efficiency["pattern"], f"{best_efficiency['efficiency_pct']:.1f}%"),
            ]
            di_cols = st.columns(4)
            for col, (label, pattern, stat) in zip(di_cols, decision_items, strict=True):
                col.metric(label, pattern, stat)

        st.markdown("### Head-to-Head Inspection")
        ca, cb = st.columns(2)
        recommended_a = ranking[0]["pattern"] if ranking else infill_pattern
        recommended_b = ranking[1]["pattern"] if len(ranking) > 1 else "Grid"
        pattern_a = ca.selectbox(
            "Pattern A", PATTERNS, index=PATTERNS.index(recommended_a),
            format_func=lambda p: f"{PATTERN_ICONS.get(p, '')} {p}",
        )
        pattern_b = cb.selectbox(
            "Pattern B", PATTERNS, index=PATTERNS.index(recommended_b),
            format_func=lambda p: f"{PATTERN_ICONS.get(p, '')} {p}",
        )

        auto_compare = st.checkbox("Auto-compare on change", value=True)
        run_compare = st.button("Compare now", type="primary") or auto_compare

        if run_compare:
            infill_a = _cached_plan_layer(
                _shape_wkt, _infill_wkt,
                replace(toolpath_settings, infill_pattern=pattern_a),
                layer=int(layer_number),
            ).infill_lines
            infill_b = _cached_plan_layer(
                _shape_wkt, _infill_wkt,
                replace(toolpath_settings, infill_pattern=pattern_b),
                layer=int(layer_number),
            ).infill_lines
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

    with st.expander("Toolpath Animation", expanded=False):
        if segments:
            st.plotly_chart(create_animated_figure(boundary, segments), width="stretch")
        else:
            st.info("No segments to animate - try adjusting perimeter count or infill spacing.")

    with st.expander("Metrics Detail", expanded=False):
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

# ---- Release ----------------------------------------------------------------
with tab_release:
    # Executive summary
    render_executive_dashboard(
        job_name=str(job_name),
        job_id=str(job_id),
        customer_name=str(customer_name),
        owner_name=str(owner_name),
        source_label=source_label,
        process_mode=str(process_mode),
        material_choice=material_choice,
        batch_quantity=int(batch_quantity),
        layer_count=layer_count,
        production_segment_count=len(production_segments),
        metrics=metrics,
        economics=economics,
        readiness=readiness,
        commercial_fit=commercial_fit,
        program_risk=program_risk,
        launch_score=launch_score,
        travel_ratio=travel_ratio,
        target_unit_price=float(target_unit_price),
        quote_profile=str(quote_profile),
        max_lead_time_h=float(max_lead_time_h),
        machine_rate_per_h=float(machine_rate_per_h),
        labor_rate_per_h=float(labor_rate_per_h),
        setup_time_min=float(setup_time_min),
        postprocess_time_min=float(postprocess_time_min),
        scrap_allowance_pct=float(scrap_allowance_pct),
        margin_pct=float(margin_pct),
    )
    st.markdown("### Release Gates")
    render_release_gate_matrix(
        readiness=readiness,
        commercial_fit=commercial_fit,
        program_risk=program_risk,
        launch_score=launch_score,
        production_enabled=production_enabled,
        export_segment_count=len(production_segments),
    )

    st.markdown("---")
    st.markdown("### Launch Optimizer")
    render_launch_optimizer(
        launch_recommendations,
        batch_scenarios,
        release_checklist,
        optimization_playbook,
    )

    st.markdown("---")
    render_ded_process_panel(ded_analysis)
    if ded_analysis is not None:
        st.markdown("---")
    render_partner_fit_panel(partner_fit)
    if partner_fit is not None:
        st.markdown("---")
    render_production_handoff_panel(thermal_plan, robot_handoff, qualification_plan)
    if qualification_plan is not None:
        st.markdown("---")

    # Quality scorecard + Advisor side by side
    rel_left, rel_right = st.columns([3, 2])

    with rel_left:
        st.markdown("### Quality Scorecard")
        render_quality_scorecard(quality_scorecard)

    with rel_right:
        st.markdown("### Advisor")
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
        st.markdown("#### Release Snapshot")
        ad1, ad2 = st.columns(2)
        ad1.metric("Travel share", f"{travel_ratio:.1f}%", delta_color="inverse")
        ad2.metric("Path efficiency", f"{metrics['path_efficiency_pct']:.1f}%")
        st.metric("Blockers", readiness["blockers"])
        st.metric("Warnings", readiness["warnings"])
        st.metric("Launch score", f"{launch_score}/100")
        st.metric("Commercial fit", commercial_fit["status"])
        density_actual = (
            100 * float(nozzle_diameter) / max(effective_spacing, 0.01)
            if effective_spacing > 0 else 0
        )
        st.metric("Actual density", f"{min(density_actual, 100):.0f}%")

    st.markdown("---")

    # Segment data
    with st.expander("Segment Ledger", expanded=False):
        df = segments_to_dataframe(segments)
        st.caption(
            f"{len(df):,} active-layer segments with stable export columns "
            "for downstream QA, quoting, and traceability."
        )
        st.dataframe(df, width="stretch")

    # Export panel
    st.markdown("### Export")
    params = {
        "shape_type": source_label, "process_mode": process_mode, "profile": profile,
        "plan_fingerprint": plan_fingerprint,
        "job_metadata": {
            "job_name": job_name,
            "job_id": job_id,
            "customer_name": customer_name,
            "owner_name": owner_name,
        },
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
        "launch_score": launch_score,
        "commercial_fit": commercial_fit,
        "quality_scorecard": quality_scorecard,
        "launch_recommendations": launch_recommendations,
        "batch_scenarios": batch_scenarios,
        "release_checklist": release_checklist,
        "optimization_playbook": optimization_playbook,
        "ded_process": ded_analysis,
        "manufacturing_partner_fit": partner_fit,
        "thermal_plan": thermal_plan,
        "robot_handoff": robot_handoff,
        "qualification_plan": qualification_plan,
        "ded_assumptions": {
            "profile": ded_profile,
            "wire_diameter_mm": float(ded_wire_diameter_mm),
            "wire_feed_m_min": float(ded_wire_feed_m_min),
            "arc_current_a": float(ded_arc_current_a),
            "arc_voltage_v": float(ded_arc_voltage_v),
            "arc_efficiency_pct": float(ded_arc_efficiency_pct),
            "deposition_efficiency_pct": float(ded_deposition_efficiency_pct),
            "robot_utilization_pct": float(ded_robot_utilization_pct),
            "machining_allowance_pct": float(ded_machining_allowance_pct),
            "billet_buy_to_fly": float(ded_billet_buy_to_fly),
            "preheat_temp_c": float(ded_preheat_temp_c),
            "interpass_limit_c": float(ded_interpass_limit_c),
            "cooling_rate_c_min": float(ded_cooling_rate_c_min),
            "heat_retention_pct": float(ded_heat_retention_pct),
            "robot_reach_mm": float(ded_robot_reach_mm),
            "positioner_payload_kg": float(ded_positioner_payload_kg),
            "fixture_mass_kg": float(ded_fixture_mass_kg),
            "torch_clearance_mm": float(ded_torch_clearance_mm),
            "program_point_limit": int(ded_program_point_limit),
        },
        "business_assumptions": {
            "quote_profile": quote_profile,
            "batch_quantity": int(batch_quantity),
            "target_unit_price": float(target_unit_price),
            "application_type": application_type,
            "conventional_route": conventional_route,
            "urgency": urgency,
            "qualification_level": qualification_level,
            "material_strategy": material_strategy,
            "finish_tolerance_mm": float(finish_tolerance_mm),
            "annual_quantity": int(annual_quantity),
            "ndt_required": bool(ndt_required),
            "redesign_required": bool(redesign_required),
            "machine_rate_per_h": float(machine_rate_per_h),
            "labor_rate_per_h": float(labor_rate_per_h),
            "setup_time_min": float(setup_time_min),
            "postprocess_time_min": float(postprocess_time_min),
            "scrap_allowance_pct": float(scrap_allowance_pct),
            "margin_pct": float(margin_pct),
            "max_lead_time_h": float(max_lead_time_h),
        },
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
        f"Launch score:   {launch_score}/100",
        f"Commercial fit: {commercial_fit['status']}",
        f"Plan ID:        {plan_fingerprint}",
        f"Generated:      layer {int(layer_number)} of {layer_count}",
        f"Job:            {job_id} - {job_name}",
        f"Customer:       {customer_name}",
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
        f"Unit quote:     ${economics['quoted_price']:.2f}",
        f"Batch quote:    ${economics['quoted_batch_price']:.2f} ({int(batch_quantity)} pcs)",
        f"Build plate fit:{' yes' if fits_plate else ' NO - shape outside plate'}",
        "",
        "Readiness Findings",
        *readiness_lines,
        "",
        "Planning output only - validate machine-specific start/end code and process limits before production.",
    ])
    dossier_md = generate_job_dossier_markdown(
        job_name=str(job_name),
        params=params,
        metrics=metrics,
        readiness=readiness,
        economics=economics,
        full_time_text=fmt_time(full_time_s),
        full_weight_g=full_weight_g,
        layer_count=layer_count,
        risk=program_risk,
        commercial_fit=commercial_fit,
        launch_score=launch_score,
        quality_scorecard=quality_scorecard,
        recommendations=launch_recommendations,
        batch_scenarios=batch_scenarios,
        release_checklist=release_checklist,
        optimization_playbook=optimization_playbook,
        ded_analysis=ded_analysis,
        partner_fit=partner_fit,
        thermal_plan=thermal_plan,
        robot_handoff=robot_handoff,
        qualification_plan=qualification_plan,
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
