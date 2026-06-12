"""Tests for src/geometry.py shape creation and validation."""

import math

import pytest
from shapely.geometry import Polygon

from src.geometry import (
    BoundingBox,
    bounding_box,
    bounding_box_dimensions,
    create_circle,
    create_rectangle,
    create_regular_polygon,
    create_rounded_rectangle,
    create_star,
    create_triangle,
    parse_custom_polygon,
    polygon_area,
    polygon_centroid,
    validate_polygon,
)

# -- Shape creation ------------------------------------------------------------

def test_basic_shapes_are_valid() -> None:
    assert create_rectangle(20.0, 10.0).is_valid
    assert create_circle(5.0).is_valid
    assert create_triangle(20.0, 10.0).is_valid


def test_rectangle_dimensions() -> None:
    rect = create_rectangle(30.0, 15.0)
    bb = bounding_box(rect)
    assert bb.width == 30.0
    assert bb.height == 15.0


def test_rectangle_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        create_rectangle(0.0, 10.0)
    with pytest.raises(ValueError):
        create_rectangle(10.0, -1.0)


def test_circle_area_approximate() -> None:
    circ = create_circle(10.0)
    # Polygon approximation; allow 0.1% relative error
    assert circ.area == pytest.approx(math.pi * 100.0, rel=1e-3)


def test_circle_vertex_count_respects_n_vertices() -> None:
    # n_vertices=12 -> quad_segs=3 -> 12 boundary vertices + closure
    circ = create_circle(10.0, n_vertices=12)
    # Shapely closes the ring, so coords count = n_vertices + 1
    assert len(circ.exterior.coords) == 13


def test_circle_rejects_non_positive_radius() -> None:
    with pytest.raises(ValueError):
        create_circle(0.0)
    with pytest.raises(ValueError):
        create_circle(-5.0)


def test_circle_rejects_too_few_vertices() -> None:
    with pytest.raises(ValueError):
        create_circle(5.0, n_vertices=2)


def test_triangle_has_three_exterior_coords() -> None:
    tri = create_triangle(20.0, 10.0)
    # Shapely closes the ring: first coord == last coord -> 4 entries
    assert len(tri.exterior.coords) == 4


def test_triangle_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        create_triangle(0.0, 10.0)
    with pytest.raises(ValueError):
        create_triangle(10.0, -3.0)


def test_regular_polygon_sides() -> None:
    poly = create_regular_polygon(radius=10.0, sides=6)
    assert poly.is_valid
    assert len(poly.exterior.coords) == 7


def test_star_shape_is_valid() -> None:
    star = create_star(outer_radius=10.0, inner_radius=4.0, points=5)
    assert star.is_valid
    assert len(star.exterior.coords) == 11


def test_rounded_rectangle_respects_bounds() -> None:
    rounded = create_rounded_rectangle(width=30.0, height=20.0, corner_radius=4.0)
    bb = bounding_box(rounded)
    assert bb.width == pytest.approx(30.0)
    assert bb.height == pytest.approx(20.0)


# -- Polygon validation --------------------------------------------------------

def test_validate_polygon_rejects_empty() -> None:
    assert validate_polygon(Polygon()) is None


def test_validate_polygon_passes_valid() -> None:
    result = validate_polygon(create_rectangle(10.0, 10.0))
    assert result is not None and result.is_valid


def test_custom_polygon_self_intersecting_repaired_or_none() -> None:
    # Bowtie (figure-8) - self-intersecting; must either be repaired or rejected
    poly = parse_custom_polygon("0,0; 10,10; 10,0; 0,10")
    if poly is not None:
        assert poly.is_valid, "Repaired polygon must be valid"


# -- Custom polygon parsing ----------------------------------------------------

def test_custom_polygon_parsing_success() -> None:
    poly = parse_custom_polygon("0,0; 10,0; 10,10; 0,10")
    assert isinstance(poly, Polygon)
    assert poly.area == 100.0


def test_custom_polygon_too_few_points() -> None:
    assert parse_custom_polygon("0,0; 10,0") is None


def test_custom_polygon_malformed_non_numeric() -> None:
    assert parse_custom_polygon("abc,def; 10,0; 10,10") is None


def test_custom_polygon_empty_string() -> None:
    assert parse_custom_polygon("") is None


def test_custom_polygon_wrong_pair_format() -> None:
    # Three values in one pair
    assert parse_custom_polygon("0,0,1; 10,0; 10,10") is None


def test_custom_polygon_trailing_semicolon_tolerated() -> None:
    # Trailing semicolon should not cause a failure
    poly = parse_custom_polygon("0,0; 10,0; 10,10; 0,10;")
    assert isinstance(poly, Polygon)


def test_custom_polygon_tab_whitespace_tolerated() -> None:
    poly = parse_custom_polygon("0,0;\t10,0;\t10,10")
    assert isinstance(poly, Polygon)


def test_custom_polygon_newline_whitespace_tolerated() -> None:
    poly = parse_custom_polygon("0,0;\n10,0;\n10,10")
    assert isinstance(poly, Polygon)


# -- Bounding box --------------------------------------------------------------

def test_bounding_box_returns_named_tuple() -> None:
    bb = bounding_box(create_rectangle(40.0, 25.0))
    assert isinstance(bb, BoundingBox)
    assert bb.width == 40.0
    assert bb.height == 25.0


def test_bounding_box_dimensions_alias() -> None:
    # Backward-compatible alias must return the same result
    bb = bounding_box_dimensions(create_rectangle(10.0, 5.0))
    assert bb.width == 10.0
    assert bb.height == 5.0


# -- Geometry utilities --------------------------------------------------------

def test_polygon_area_rectangle() -> None:
    area = polygon_area(create_rectangle(10.0, 4.0))
    assert area == pytest.approx(40.0)


def test_polygon_area_circle_approximate() -> None:
    area = polygon_area(create_circle(5.0))
    assert area == pytest.approx(math.pi * 25.0, rel=1e-3)


def test_polygon_centroid_rectangle() -> None:
    cx, cy = polygon_centroid(create_rectangle(20.0, 10.0))
    assert cx == pytest.approx(10.0)
    assert cy == pytest.approx(5.0)


def test_polygon_centroid_circle() -> None:
    cx, cy = polygon_centroid(create_circle(8.0))
    assert cx == pytest.approx(0.0, abs=1e-9)
    assert cy == pytest.approx(0.0, abs=1e-9)
