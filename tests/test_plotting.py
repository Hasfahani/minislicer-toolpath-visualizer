# Purpose: Tests Plotly figure builders for paths, maps, metrics, 3D views, and animations.
# Reason: Visualization tests catch empty or broken figures before the app is shown live.
"""Tests for src/plotting.py - figure construction and trace validation."""

from __future__ import annotations

import plotly.graph_objects as go
from shapely.geometry import LineString

from src.geometry import create_rectangle
from src.plotting import (
    create_3d_figure,
    create_infill_length_histogram,
    create_metrics_figure,
    create_multilayer_animated_figure,
    create_path_density_figure,
    create_speed_map_figure,
    create_time_map_figure,
    create_toolpath_figure,
    shape_boundary,
)
from src.toolpaths import (
    generate_inward_perimeters,
    generate_parallel_infill,
)

# -- Helpers -------------------------------------------------------------------

def _rect_paths():
    shape = create_rectangle(30.0, 20.0)
    boundary = shape_boundary(shape)
    perims = generate_inward_perimeters(shape, count=2, spacing=1.0)
    infill = generate_parallel_infill(shape, spacing=5.0, angle_deg=45.0)
    return shape, boundary, perims, infill


def _has_trace_type(fig: go.Figure, trace_type: type) -> bool:
    return any(isinstance(t, trace_type) for t in fig.data)


def _trace_names(fig: go.Figure) -> set[str]:
    return {t.name for t in fig.data if t.name}


# -- create_toolpath_figure ----------------------------------------------------

def test_toolpath_figure_returns_figure() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_toolpath_figure(boundary, perims, infill)
    assert isinstance(fig, go.Figure)


def test_toolpath_figure_has_scatter_traces() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_toolpath_figure(boundary, perims, infill)
    assert _has_trace_type(fig, go.Scatter)


def test_toolpath_figure_has_non_empty_data() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_toolpath_figure(boundary, perims, infill)
    assert len(fig.data) > 0


def test_toolpath_figure_perimeters_in_legend() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_toolpath_figure(boundary, perims, infill, show_perimeters=True)
    names = _trace_names(fig)
    assert any("Perimeter" in n or "erimeter" in n for n in names)


def test_toolpath_figure_infill_suppressed_when_disabled() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_toolpath_figure(boundary, perims, infill, show_infill=False)
    names = _trace_names(fig)
    assert not any("Infill" in n for n in names)


def test_toolpath_figure_travel_trace_added_when_requested() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_toolpath_figure(boundary, perims, infill, show_travel_moves=True)
    names = _trace_names(fig)
    assert any("Travel" in n for n in names)


def test_toolpath_figure_color_schemes() -> None:
    shape, boundary, perims, infill = _rect_paths()
    for scheme in ("Classic", "Colorblind", "Dark", "Neon", "High Contrast"):
        fig = create_toolpath_figure(boundary, perims, infill, color_scheme=scheme)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0


def test_toolpath_figure_build_plate_adds_trace() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig_no_plate = create_toolpath_figure(boundary, perims, infill)
    fig_with_plate = create_toolpath_figure(boundary, perims, infill,
                                            build_plate_size=(220.0, 220.0))
    assert len(fig_with_plate.data) > len(fig_no_plate.data)


def test_toolpath_figure_max_path_index_limits_paths() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig_all = create_toolpath_figure(boundary, perims, infill)
    fig_limited = create_toolpath_figure(boundary, perims, infill, max_path_index=1)
    assert len(fig_limited.data) <= len(fig_all.data)


def test_toolpath_figure_empty_perimeters_and_infill() -> None:
    shape, boundary, _, _ = _rect_paths()
    fig = create_toolpath_figure(boundary, [], [])
    assert isinstance(fig, go.Figure)


# -- create_speed_map_figure ---------------------------------------------------

def test_speed_map_returns_figure() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_speed_map_figure(boundary, perims, infill, 50.0, 100.0)
    assert isinstance(fig, go.Figure)


def test_speed_map_has_scatter_traces() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_speed_map_figure(boundary, perims, infill, 50.0, 100.0)
    assert _has_trace_type(fig, go.Scatter)


# -- create_time_map_figure ----------------------------------------------------

def test_time_map_returns_figure() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_time_map_figure(boundary, perims, infill, 50.0)
    assert isinstance(fig, go.Figure)


def test_time_map_with_no_infill() -> None:
    shape, boundary, perims, _ = _rect_paths()
    fig = create_time_map_figure(boundary, perims, [], 50.0)
    assert isinstance(fig, go.Figure)


# -- create_path_density_figure ------------------------------------------------

def test_path_density_returns_figure() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_path_density_figure(perims, infill, boundary)
    assert isinstance(fig, go.Figure)


def test_path_density_has_histogram2d_when_paths_exist() -> None:
    shape, boundary, perims, infill = _rect_paths()
    fig = create_path_density_figure(perims, infill, boundary)
    assert _has_trace_type(fig, go.Histogram2d)


def test_path_density_empty_paths() -> None:
    shape, boundary, _, _ = _rect_paths()
    fig = create_path_density_figure([], [], boundary)
    assert isinstance(fig, go.Figure)


# -- create_infill_length_histogram --------------------------------------------

def test_infill_histogram_returns_figure() -> None:
    shape, _, _, infill = _rect_paths()
    fig = create_infill_length_histogram(infill, print_speed_mm_s=50.0)
    assert isinstance(fig, go.Figure)


def test_infill_histogram_empty_returns_figure() -> None:
    fig = create_infill_length_histogram([])
    assert isinstance(fig, go.Figure)


def test_infill_histogram_has_histogram_trace() -> None:
    shape, _, _, infill = _rect_paths()
    fig = create_infill_length_histogram(infill)
    assert _has_trace_type(fig, go.Histogram)


# -- create_metrics_figure -----------------------------------------------------

def test_metrics_figure_returns_figure() -> None:
    metrics = {
        "perimeter_length_mm": 100.0,
        "infill_length_mm": 200.0,
        "travel_length_mm": 50.0,
    }
    fig = create_metrics_figure(metrics, print_speed_mm_s=50.0, travel_speed_mm_s=100.0)
    assert isinstance(fig, go.Figure)


def test_metrics_figure_has_pie_and_bar() -> None:
    metrics = {
        "perimeter_length_mm": 100.0,
        "infill_length_mm": 200.0,
        "travel_length_mm": 50.0,
    }
    fig = create_metrics_figure(metrics, 50.0, 100.0)
    assert _has_trace_type(fig, go.Pie)
    assert _has_trace_type(fig, go.Bar)


# -- create_3d_figure ----------------------------------------------------------

def test_3d_figure_returns_figure() -> None:
    shape = create_rectangle(30.0, 20.0)
    fig = create_3d_figure(shape, layer_count=3, perimeter_count=2,
                           perimeter_spacing=1.0, infill_spacing=5.0,
                           layer_height_mm=0.2)
    assert isinstance(fig, go.Figure)


def test_3d_figure_has_scatter3d_traces() -> None:
    shape = create_rectangle(30.0, 20.0)
    fig = create_3d_figure(shape, layer_count=3, perimeter_count=2,
                           perimeter_spacing=1.0, infill_spacing=5.0,
                           layer_height_mm=0.2)
    assert _has_trace_type(fig, go.Scatter3d)


# -- create_multilayer_animated_figure -----------------------------------------

def test_multilayer_animated_figure_returns_figure() -> None:
    shape = create_rectangle(30.0, 20.0)
    layers = []
    for i in range(3):
        z = float(i) * 0.2
        perims = generate_inward_perimeters(shape, 2, 1.0)
        infill = generate_parallel_infill(shape, 5.0, 45.0)
        layers.append((z, perims, infill))
    fig = create_multilayer_animated_figure(layers)
    assert isinstance(fig, go.Figure)


def test_multilayer_animated_figure_has_frames() -> None:
    shape = create_rectangle(30.0, 20.0)
    layers = [
        (float(i) * 0.2,
         generate_inward_perimeters(shape, 2, 1.0),
         generate_parallel_infill(shape, 5.0, 45.0))
        for i in range(4)
    ]
    fig = create_multilayer_animated_figure(layers)
    assert len(fig.frames) == 4


def test_multilayer_animated_figure_has_play_button() -> None:
    shape = create_rectangle(30.0, 20.0)
    layers = [(0.0, generate_inward_perimeters(shape, 1, 1.0), [])]
    fig = create_multilayer_animated_figure(layers)
    assert fig.layout.updatemenus is not None
    assert len(fig.layout.updatemenus) > 0


def test_multilayer_animated_figure_empty_layers() -> None:
    fig = create_multilayer_animated_figure([])
    assert isinstance(fig, go.Figure)


# -- shape_boundary ------------------------------------------------------------

def test_shape_boundary_returns_linestring() -> None:
    shape = create_rectangle(10.0, 5.0)
    boundary = shape_boundary(shape)
    assert isinstance(boundary, LineString)
    assert boundary.length > 0
