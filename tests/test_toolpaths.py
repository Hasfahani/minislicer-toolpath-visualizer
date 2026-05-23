"""Tests for src/toolpaths.py path generation and segment building."""

from shapely.geometry import LineString

from src.geometry import create_circle, create_rectangle
from src.metrics import summarize_metrics, total_path_length
from src.plotting import shape_boundary
from src.toolpaths import (
    Segment,
    build_ordered_segments,
    filter_short_lines,
    generate_inward_perimeters,
    generate_parallel_infill,
    generate_triangular_infill,
    generate_zigzag_infill,
    optimize_path_order,
    simplify_lines,
    total_travel_distance,
)


def test_perimeters_generated_for_large_shape() -> None:
    shape = create_rectangle(30.0, 20.0)
    perimeters = generate_inward_perimeters(shape, count=3, spacing=1.0)
    assert len(perimeters) >= 1
    assert all(isinstance(p, LineString) for p in perimeters)


def test_perimeters_count_limited_by_shape_size() -> None:
    # Tiny shape — cannot fit 10 perimeters at 5mm spacing
    shape = create_rectangle(4.0, 4.0)
    perimeters = generate_inward_perimeters(shape, count=10, spacing=5.0)
    assert len(perimeters) < 10


def test_infill_lines_generated() -> None:
    shape = create_rectangle(30.0, 20.0)
    infill = generate_parallel_infill(shape, spacing=5.0, angle_deg=45.0)
    assert len(infill) > 0


def test_infill_lines_within_shape() -> None:
    shape = create_rectangle(40.0, 30.0)
    for angle in [0.0, 45.0, 90.0, -45.0]:
        infill = generate_parallel_infill(shape, spacing=5.0, angle_deg=angle)
        for line in infill:
            # Each clipped infill line must lie within (or on the boundary of) the shape
            assert shape.covers(line), (
                f"Infill line at angle={angle} extends outside the shape: {line}"
            )


def test_infill_lines_within_circle() -> None:
    shape = create_circle(15.0)
    infill = generate_parallel_infill(shape, spacing=4.0, angle_deg=0.0)
    assert len(infill) > 0
    # Use a tiny tolerance buffer because the circle is a polygon approximation;
    # intersection endpoints can land at floating-point distances from the boundary.
    shape_tolerance = shape.buffer(1e-9)
    for line in infill:
        assert shape_tolerance.covers(line)


def test_infill_zero_spacing_returns_empty() -> None:
    shape = create_rectangle(20.0, 10.0)
    infill = generate_parallel_infill(shape, spacing=0.0, angle_deg=0.0)
    assert infill == []


def test_triangular_infill_uses_three_line_families() -> None:
    shape = create_rectangle(40.0, 30.0)
    triangular = generate_triangular_infill(shape, spacing=8.0, angle_deg=0.0)
    parallel = generate_parallel_infill(shape, spacing=8.0, angle_deg=0.0)
    assert len(triangular) > len(parallel)
    assert all(shape.covers(line) for line in triangular)


def test_zigzag_infill_alternates_direction_within_shape() -> None:
    shape = create_rectangle(40.0, 30.0)
    zigzag = generate_zigzag_infill(shape, spacing=6.0, angle_deg=0.0)
    assert len(zigzag) > 1
    assert all(shape.covers(line) for line in zigzag)
    first = list(zigzag[0].coords)
    second = list(zigzag[1].coords)
    assert first[0][0] != second[0][0]


def test_perimeters_zero_count_returns_empty() -> None:
    shape = create_rectangle(20.0, 10.0)
    perimeters = generate_inward_perimeters(shape, count=0, spacing=1.0)
    assert perimeters == []


def test_segments_have_positive_length() -> None:
    shape = create_rectangle(20.0, 10.0)
    boundary = shape_boundary(shape)
    perimeters = generate_inward_perimeters(shape, count=2, spacing=1.0)
    infill = generate_parallel_infill(shape, spacing=4.0, angle_deg=0.0)
    segments = build_ordered_segments(boundary, perimeters, infill, layer=1)

    assert len(segments) > 0
    assert all(seg.length_mm > 0 for seg in segments)


def test_segments_order_index_is_sequential() -> None:
    shape = create_rectangle(20.0, 10.0)
    boundary = shape_boundary(shape)
    perimeters = generate_inward_perimeters(shape, count=1, spacing=1.0)
    infill = generate_parallel_infill(shape, spacing=5.0, angle_deg=0.0)
    segments = build_ordered_segments(boundary, perimeters, infill, layer=3)

    indices = [seg.order_index for seg in segments]
    assert indices == list(range(len(segments)))


def test_segments_layer_assigned_correctly() -> None:
    shape = create_rectangle(20.0, 10.0)
    boundary = shape_boundary(shape)
    segments = build_ordered_segments(boundary, [], [], layer=7)
    assert all(seg.layer == 7 for seg in segments)


def test_segments_path_type_values() -> None:
    shape = create_rectangle(20.0, 10.0)
    boundary = shape_boundary(shape)
    perimeters = generate_inward_perimeters(shape, count=1, spacing=1.0)
    infill = generate_parallel_infill(shape, spacing=5.0, angle_deg=0.0)
    segments = build_ordered_segments(boundary, perimeters, infill, layer=1)

    types = {seg.path_type for seg in segments}
    assert "boundary" in types


def test_metrics_summary_keys_present() -> None:
    shape = create_rectangle(20.0, 10.0)
    boundary = shape_boundary(shape)
    perimeters = generate_inward_perimeters(shape, count=2, spacing=1.0)
    infill = generate_parallel_infill(shape, spacing=4.0, angle_deg=0.0)
    segments = build_ordered_segments(boundary, perimeters, infill, layer=2)

    summary = summarize_metrics(
        shape=shape,
        segments=segments,
        perimeter_paths=perimeters,
        infill_lines=infill,
        print_speed_mm_s=20.0,
    )

    expected_keys = {
        "total_path_length_mm",
        "segment_count",
        "perimeter_path_count",
        "infill_line_count",
        "estimated_print_time_s",
        "estimated_motion_time_s",
        "bbox_width_mm",
        "bbox_height_mm",
        "travel_length_mm",
        "total_motion_length_mm",
        "path_efficiency_pct",
    }
    assert expected_keys.issubset(summary.keys())
    assert summary["segment_count"] == len(segments)
    assert summary["perimeter_path_count"] == len(perimeters)
    assert summary["infill_line_count"] == len(infill)
    assert summary["estimated_print_time_s"] > 0
    assert summary["total_path_length_mm"] > 0


def test_total_path_length_positive() -> None:
    shape = create_rectangle(20.0, 10.0)
    boundary = shape_boundary(shape)
    segments = build_ordered_segments(boundary, [], [], layer=1)
    assert total_path_length(segments) > 0


def test_alternating_angle_produces_different_infill() -> None:
    shape = create_rectangle(40.0, 30.0)
    infill_45 = generate_parallel_infill(shape, spacing=5.0, angle_deg=45.0)
    infill_neg45 = generate_parallel_infill(shape, spacing=5.0, angle_deg=-45.0)
    # Same count expected by symmetry, but first endpoints differ
    assert len(infill_45) > 0
    assert len(infill_neg45) > 0
    # Verify they are not identical
    coords_45 = [list(l.coords) for l in infill_45]
    coords_neg45 = [list(l.coords) for l in infill_neg45]
    assert coords_45 != coords_neg45


def test_optimize_path_order_reduces_or_keeps_travel_distance() -> None:
    lines = [
        LineString([(0, 0), (1, 0)]),
        LineString([(10, 0), (11, 0)]),
        LineString([(2, 0), (3, 0)]),
    ]

    before = total_travel_distance(lines)
    after = total_travel_distance(optimize_path_order(lines, allow_reverse=True))
    assert after <= before


def test_optimize_path_order_can_reverse_lines() -> None:
    lines = [
        LineString([(0, 0), (1, 0)]),
        LineString([(6, 0), (5, 0)]),
    ]

    optimized = optimize_path_order(lines, allow_reverse=True)
    second_start = list(optimized[1].coords)[0]
    # With reversal enabled, second path should start at x=5.0 (closer to x=1.0).
    assert second_start[0] == 5.0


def test_simplify_lines_reduces_vertex_count_for_noisy_line() -> None:
    noisy = LineString(
        [(0, 0), (1, 0.01), (2, -0.01), (3, 0.01), (4, 0)]
    )
    simplified = simplify_lines([noisy], tolerance_mm=0.05)
    assert len(simplified) == 1
    assert len(simplified[0].coords) < len(noisy.coords)


def test_filter_short_lines_drops_short_segments() -> None:
    lines = [
        LineString([(0, 0), (0.05, 0)]),
        LineString([(0, 0), (2.0, 0)]),
    ]
    filtered = filter_short_lines(lines, min_length_mm=0.1)
    assert len(filtered) == 1
    assert filtered[0].length == 2.0
