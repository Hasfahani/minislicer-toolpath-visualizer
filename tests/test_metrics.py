"""Tests for src/metrics.py - path length, print time, bounding box, material estimate."""

from __future__ import annotations

import math

import pytest

from src.geometry import create_circle, create_rectangle
from src.metrics import (
    MATERIAL_DENSITY,
    estimate_material,
    estimate_print_time_seconds,
    summarize_metrics,
    total_path_length,
)
from src.plotting import shape_boundary
from src.toolpaths import (
    Segment,
    build_ordered_segments,
    generate_inward_perimeters,
    generate_parallel_infill,
)

# -- Fixtures ------------------------------------------------------------------

def _make_segments() -> list[Segment]:
    return [
        Segment("boundary",  0,  0.0,  0.0, 10.0,  0.0, 10.0, 1),
        Segment("perimeter", 1, 10.0,  0.0, 10.0, 10.0, 10.0, 1),
        Segment("infill",    2,  0.0,  5.0, 10.0,  5.0, 10.0, 1),
    ]


def _rect_segments(layer: int = 1) -> tuple:
    """Return (shape, boundary, perimeters, infill, segments) for a 20x10 rectangle."""
    shape = create_rectangle(20.0, 10.0)
    boundary = shape_boundary(shape)
    perimeters = generate_inward_perimeters(shape, count=2, spacing=1.0)
    infill = generate_parallel_infill(shape, spacing=4.0, angle_deg=0.0)
    segments = build_ordered_segments(boundary, perimeters, infill, layer=layer)
    return shape, boundary, perimeters, infill, segments


# -- total_path_length ---------------------------------------------------------

def test_total_path_length_sums_segment_lengths() -> None:
    segs = _make_segments()
    assert total_path_length(segs) == pytest.approx(30.0)


def test_total_path_length_empty_is_zero() -> None:
    assert total_path_length([]) == 0.0


def test_total_path_length_positive_for_rectangle() -> None:
    _, _, _, _, segments = _rect_segments()
    assert total_path_length(segments) > 0.0


def test_total_path_length_increases_with_more_segments() -> None:
    shape = create_rectangle(20.0, 10.0)
    boundary = shape_boundary(shape)
    seg_few = build_ordered_segments(boundary, [], [], layer=1)
    perims = generate_inward_perimeters(shape, 3, 1.0)
    infill = generate_parallel_infill(shape, 4.0, 0.0)
    seg_many = build_ordered_segments(boundary, perims, infill, layer=1)
    assert total_path_length(seg_many) > total_path_length(seg_few)


# -- estimate_print_time_seconds ------------------------------------------------

def test_print_time_basic_formula() -> None:
    # 100 mm at 10 mm/s -> 10 s
    assert estimate_print_time_seconds(100.0, 10.0) == pytest.approx(10.0)


def test_print_time_zero_speed_returns_inf() -> None:
    assert math.isinf(estimate_print_time_seconds(100.0, 0.0))


def test_print_time_negative_speed_returns_inf() -> None:
    assert math.isinf(estimate_print_time_seconds(100.0, -5.0))


def test_print_time_zero_length() -> None:
    assert estimate_print_time_seconds(0.0, 50.0) == pytest.approx(0.0)


def test_print_time_scales_linearly_with_length() -> None:
    t1 = estimate_print_time_seconds(100.0, 20.0)
    t2 = estimate_print_time_seconds(200.0, 20.0)
    assert t2 == pytest.approx(t1 * 2.0)


def test_print_time_scales_inversely_with_speed() -> None:
    t1 = estimate_print_time_seconds(100.0, 10.0)
    t2 = estimate_print_time_seconds(100.0, 20.0)
    assert t1 == pytest.approx(t2 * 2.0)


# -- estimate_material ---------------------------------------------------------

def test_material_estimate_returns_positive_values() -> None:
    result = estimate_material(
        total_path_length_mm=1000.0,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        filament_diameter_mm=1.75,
        material="PLA",
    )
    assert result["material_volume_mm3"] > 0
    assert result["filament_length_mm"] > 0
    assert result["filament_length_m"] > 0
    assert result["weight_g"] > 0


def test_material_estimate_volume_formula() -> None:
    # Elliptical bead cross-section: volume = (pi/4) x length x layer_height x nozzle_diameter
    result = estimate_material(
        total_path_length_mm=100.0,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        filament_diameter_mm=1.75,
        material="PLA",
    )
    assert result["material_volume_mm3"] == pytest.approx((math.pi / 4.0) * 100.0 * 0.2 * 0.4)


def test_material_estimate_weight_uses_density() -> None:
    pla_result = estimate_material(100.0, 0.2, 0.4, 1.75, material="PLA")
    steel_result = estimate_material(100.0, 0.2, 0.4, 1.75, material="Steel 316L")
    # Steel is denser than PLA
    assert steel_result["weight_g"] > pla_result["weight_g"]


def test_material_density_dict_has_expected_keys() -> None:
    assert "PLA" in MATERIAL_DENSITY
    assert "Steel 316L" in MATERIAL_DENSITY
    assert "Titanium Ti-6Al-4V" in MATERIAL_DENSITY
    for density in MATERIAL_DENSITY.values():
        assert density > 0.0


# -- summarize_metrics ---------------------------------------------------------

def test_summarize_metrics_required_keys() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    required = {
        "total_path_length_mm", "segment_count", "perimeter_path_count",
        "infill_line_count", "estimated_print_time_s", "estimated_motion_time_s",
        "bbox_width_mm", "bbox_height_mm", "area_mm2", "perimeter_length_mm",
        "infill_length_mm", "travel_length_mm", "total_motion_length_mm",
        "path_efficiency_pct", "bbox_diagonal_mm", "material_volume_mm3",
        "filament_length_m", "weight_g",
    }
    assert required.issubset(result.keys())


def test_summarize_metrics_bbox_matches_shape() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    assert result["bbox_width_mm"] == pytest.approx(20.0)
    assert result["bbox_height_mm"] == pytest.approx(10.0)


def test_summarize_metrics_area_correct() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    assert result["area_mm2"] == pytest.approx(200.0)


def test_summarize_metrics_segment_count_matches() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    assert result["segment_count"] == len(segs)


def test_summarize_metrics_path_efficiency_in_range() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    assert 0.0 <= result["path_efficiency_pct"] <= 100.0


def test_summarize_metrics_print_time_positive() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    assert result["estimated_print_time_s"] > 0.0


def test_summarize_metrics_motion_time_geq_print_time() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    # Total motion includes travel moves, so motion time >= pure print time
    assert result["estimated_motion_time_s"] >= result["estimated_print_time_s"]


def test_summarize_metrics_circle_area() -> None:
    shape = create_circle(10.0)
    boundary = shape_boundary(shape)
    segs = build_ordered_segments(boundary, [], [], layer=1)
    result = summarize_metrics(shape, segs, [], [], print_speed_mm_s=20.0)
    assert result["area_mm2"] == pytest.approx(math.pi * 100.0, rel=1e-3)


def test_summarize_metrics_perimeter_length_nonzero() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    assert result["perimeter_length_mm"] > 0.0


def test_summarize_metrics_diagonal_formula() -> None:
    shape, _, perims, infill, segs = _rect_segments()
    result = summarize_metrics(shape, segs, perims, infill, print_speed_mm_s=30.0)
    expected_diag = math.hypot(20.0, 10.0)
    assert result["bbox_diagonal_mm"] == pytest.approx(expected_diag)
