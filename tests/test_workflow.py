# Purpose: Tests app workflow helpers for time formatting, shape building, and placement transforms.
# Reason: Workflow helpers connect UI inputs to geometry, so they need focused regression coverage.
"""Tests for application workflow helpers."""

from shapely.geometry import MultiPolygon, Polygon

from src.geometry import create_rectangle
from src.workflow import apply_placement, build_shape, fmt_time, largest_polygon


def test_fmt_time_uses_compact_units() -> None:
    assert fmt_time(4.25) == "4.2s"
    assert fmt_time(125.0) == "2m 5s"
    assert fmt_time(3725.0) == "1h 2m"


def test_build_shape_creates_selected_polygon() -> None:
    shape = build_shape(
        "Rectangle",
        {
            "width": 40.0,
            "height": 20.0,
        },
    )

    assert shape is not None
    assert round(shape.area, 3) == 800.0


def test_build_shape_falls_back_to_custom_polygon() -> None:
    shape = build_shape(
        "Custom Polygon",
        {
            "coords_text": "0,0;\n10,0;\n10,10;\n0,10",
        },
    )

    assert shape is not None
    assert round(shape.area, 3) == 100.0


def test_largest_polygon_selects_largest_member() -> None:
    small = create_rectangle(2.0, 2.0)
    large = create_rectangle(5.0, 5.0)

    selected = largest_polygon(MultiPolygon([small, large]))

    assert selected is not None
    assert round(selected.area, 3) == 25.0


def test_largest_polygon_returns_none_for_non_polygon_geometry() -> None:
    assert largest_polygon(object()) is None


def test_apply_placement_centers_and_fits_to_plate() -> None:
    shape = create_rectangle(100.0, 50.0)
    placed = apply_placement(
        shape,
        {
            "scale_pct": 100,
            "mirror_x": False,
            "mirror_y": False,
            "rotate_deg": 0,
            "translate_x": 0.0,
            "translate_y": 0.0,
            "fit_to_plate": True,
            "center_on_plate": True,
            "show_plate": True,
            "plate_w": 80.0,
            "plate_d": 80.0,
            "plate_margin": 5.0,
        },
    )
    min_x, min_y, max_x, max_y = placed.bounds

    assert isinstance(placed, Polygon)
    assert min_x >= 0
    assert min_y >= 0
    assert max_x <= 80.0
    assert max_y <= 80.0
