"""Geometry helpers for educational toolpath visualization."""

from __future__ import annotations

from typing import NamedTuple

import math

from shapely.geometry import MultiPolygon, Point, Polygon


# -- Public types --------------------------------------------------------------

class BoundingBox(NamedTuple):
    """Width and height of a polygon's axis-aligned bounding box (mm)."""

    width: float
    height: float


# -- Shape creation ------------------------------------------------------------

def create_rectangle(width: float, height: float) -> Polygon:
    """Create an axis-aligned rectangle with lower-left corner at (0, 0).

    Raises:
        ValueError: if width or height is not positive.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Rectangle dimensions must be positive (got {width=}, {height=})")
    return Polygon([(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)])


def create_circle(radius: float, n_vertices: int = 128) -> Polygon:
    """Create a circular polygon approximation centered at the origin.

    Args:
        radius: Circle radius in mm.
        n_vertices: Number of polygon vertices used to approximate the circle.
            Higher values are smoother but slower. Defaults to 128.

    Raises:
        ValueError: if radius is not positive or n_vertices < 3.
    """
    if radius <= 0:
        raise ValueError(f"Circle radius must be positive (got {radius=})")
    if n_vertices < 3:
        raise ValueError(f"n_vertices must be at least 3 (got {n_vertices=})")
    # Shapely's quad_segs is vertices per quadrant; divide by 4, minimum 1
    quad_segs = max(1, n_vertices // 4)
    return Point(0.0, 0.0).buffer(radius, quad_segs=quad_segs)


def create_triangle(base: float, height: float) -> Polygon:
    """Create an isosceles triangle with the base on the X-axis, apex centred above it.

    Raises:
        ValueError: if base or height is not positive.
    """
    if base <= 0 or height <= 0:
        raise ValueError(f"Triangle dimensions must be positive (got {base=}, {height=})")
    return Polygon([(0.0, 0.0), (base, 0.0), (base / 2.0, height)])


def create_regular_polygon(radius: float, sides: int) -> Polygon:
    """Create a regular polygon centered at the origin."""
    if radius <= 0:
        raise ValueError(f"Polygon radius must be positive (got {radius=})")
    if sides < 3:
        raise ValueError(f"Regular polygon needs at least 3 sides (got {sides=})")

    start_angle = math.pi / 2.0
    points = [
        (
            radius * math.cos(start_angle + 2.0 * math.pi * idx / sides),
            radius * math.sin(start_angle + 2.0 * math.pi * idx / sides),
        )
        for idx in range(sides)
    ]
    return Polygon(points)


def create_star(outer_radius: float, inner_radius: float, points: int) -> Polygon:
    """Create a centered star polygon with alternating outer and inner vertices."""
    if outer_radius <= 0 or inner_radius <= 0:
        raise ValueError(
            f"Star radii must be positive (got {outer_radius=}, {inner_radius=})"
        )
    if inner_radius >= outer_radius:
        raise ValueError("Star inner radius must be smaller than outer radius")
    if points < 3:
        raise ValueError(f"Star needs at least 3 points (got {points=})")

    vertices: list[tuple[float, float]] = []
    start_angle = math.pi / 2.0
    for idx in range(points * 2):
        radius = outer_radius if idx % 2 == 0 else inner_radius
        angle = start_angle + math.pi * idx / points
        vertices.append((radius * math.cos(angle), radius * math.sin(angle)))
    return Polygon(vertices)


def create_rounded_rectangle(width: float, height: float, corner_radius: float) -> Polygon:
    """Create a rounded rectangle using constructive geometry."""
    if width <= 0 or height <= 0:
        raise ValueError(f"Rounded rectangle dimensions must be positive (got {width=}, {height=})")
    if corner_radius < 0:
        raise ValueError(f"Corner radius cannot be negative (got {corner_radius=})")

    base = create_rectangle(width, height)
    max_radius = min(width, height) / 2.0
    radius = min(corner_radius, max_radius)
    if radius == 0:
        return base
    return base.buffer(-radius).buffer(radius)


def create_ellipse(width: float, height: float, n_vertices: int = 128) -> Polygon:
    """Create an axis-aligned ellipse centered at the origin."""
    if width <= 0 or height <= 0:
        raise ValueError(f"Ellipse dimensions must be positive (got {width=}, {height=})")
    if n_vertices < 8:
        raise ValueError(f"n_vertices must be at least 8 (got {n_vertices=})")
    a = width / 2.0
    b = height / 2.0
    points = [
        (a * math.cos(2.0 * math.pi * i / n_vertices),
         b * math.sin(2.0 * math.pi * i / n_vertices))
        for i in range(n_vertices)
    ]
    return Polygon(points)


def create_cross(size: float, arm_width: float) -> Polygon:
    """Create a symmetric plus/cross shape centered at the origin.

    ``size`` is the overall span (bounding square side); ``arm_width`` is each arm's thickness.
    """
    if size <= 0:
        raise ValueError(f"Cross size must be positive (got {size=})")
    arm_width = min(max(float(arm_width), 0.1), float(size) - 0.01)
    h = size / 2.0
    w = arm_width / 2.0
    coords = [
        (-w, -h), (w, -h), (w, -w), (h, -w), (h, w),
        (w,  w),  (w,  h), (-w, h), (-w, w),  (-h, w),
        (-h, -w), (-w, -w),
    ]
    return Polygon(coords)


def create_capsule(width: float, height: float) -> Polygon:
    """Create a stadium/capsule shape (rectangle with semicircular ends) centered at the origin.

    Semicircles cap the longer dimension automatically.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Capsule dimensions must be positive (got {width=}, {height=})")
    n_cap = 32
    if width >= height:
        r = height / 2.0
        rect_half = (width - height) / 2.0
        if rect_half <= 0:
            return create_circle(r, n_cap * 4)
        angles_right = [-math.pi / 2.0 + math.pi * i / n_cap for i in range(n_cap + 1)]
        angles_left  = [ math.pi / 2.0 + math.pi * i / n_cap for i in range(n_cap + 1)]
        pts = (
            [(rect_half  + r * math.cos(a), r * math.sin(a)) for a in angles_right]
            + [(-rect_half + r * math.cos(a), r * math.sin(a)) for a in angles_left]
        )
    else:
        r = width / 2.0
        rect_half = (height - width) / 2.0
        if rect_half <= 0:
            return create_circle(r, n_cap * 4)
        angles_top = [math.pi * i / n_cap for i in range(n_cap + 1)]
        angles_bot = [math.pi + math.pi * i / n_cap for i in range(n_cap + 1)]
        pts = (
            [(r * math.cos(a),  rect_half + r * math.sin(a)) for a in angles_top]
            + [(r * math.cos(a), -rect_half + r * math.sin(a)) for a in angles_bot]
        )
    return Polygon(pts)


def create_arrow_shape(length: float, head_width: float, shaft_width: float) -> Polygon:
    """Create a right-pointing arrow shape centered at the origin."""
    if length <= 0:
        raise ValueError(f"Arrow length must be positive (got {length=})")
    shaft_width = min(max(float(shaft_width), 0.5), float(length))
    head_width  = min(max(float(head_width),  shaft_width + 0.1), float(length) * 1.5)
    head_len = min(length * 0.4, head_width * 0.6)
    shaft_len = length - head_len
    sw = shaft_width / 2.0
    hw = head_width / 2.0
    x0 = -length / 2.0
    coords = [
        (x0,           -sw),
        (x0 + shaft_len, -sw),
        (x0 + shaft_len, -hw),
        (x0 + length,    0.0),
        (x0 + shaft_len,  hw),
        (x0 + shaft_len,  sw),
        (x0,            sw),
    ]
    return Polygon(coords)


# -- Polygon validation --------------------------------------------------------

def validate_polygon(shape: Polygon) -> Polygon | None:
    """Return a valid polygon if possible, otherwise ``None``.

    Attempts topological cleanup via ``buffer(0)`` for self-intersections.
    If cleanup produces a MultiPolygon, the largest sub-polygon is returned.
    """
    if shape.is_empty:
        return None
    if shape.is_valid:
        return shape

    cleaned = shape.buffer(0)

    if cleaned.is_empty:
        return None
    if isinstance(cleaned, Polygon) and cleaned.is_valid:
        return cleaned
    if isinstance(cleaned, MultiPolygon):
        largest = max(cleaned.geoms, key=lambda p: p.area)
        return largest if largest.is_valid and not largest.is_empty else None
    return None


# -- Custom polygon parsing ----------------------------------------------------

def parse_custom_polygon(coords_text: str) -> Polygon | None:
    """Parse a polygon from a string like ``x,y; x,y; x,y``.

    Handles tabs, newlines, and trailing separators gracefully.
    Returns ``None`` for malformed input, too few points, or invalid geometry.
    """
    try:
        points = _parse_points(coords_text)
    except ValueError:
        return None

    if len(points) < 3:
        return None

    return validate_polygon(Polygon(points))


# -- Geometry utilities --------------------------------------------------------

def bounding_box(shape: Polygon) -> BoundingBox:
    """Return the axis-aligned bounding box dimensions of ``shape``."""
    min_x, min_y, max_x, max_y = shape.bounds
    return BoundingBox(width=max_x - min_x, height=max_y - min_y)


def polygon_area(shape: Polygon) -> float:
    """Return the area of ``shape`` in mm2."""
    return float(shape.area)


def polygon_centroid(shape: Polygon) -> tuple[float, float]:
    """Return the (x, y) centroid of ``shape`` in mm."""
    c = shape.centroid
    return (float(c.x), float(c.y))


# -- Backward-compatible alias -------------------------------------------------

def bounding_box_dimensions(shape: Polygon) -> BoundingBox:
    """Alias for :func:`bounding_box` kept for compatibility."""
    return bounding_box(shape)


# -- Internal helpers ----------------------------------------------------------

def _parse_points(coords_text: str) -> list[tuple[float, float]]:
    """Parse coordinate pairs from semi-colon separated text.

    Tolerates tabs, newlines, and trailing separators.
    Raises ``ValueError`` on malformed input.
    """
    normalized = coords_text.strip().replace("\t", " ").replace("\n", " ")
    if not normalized:
        raise ValueError("Empty coordinate input")

    points: list[tuple[float, float]] = []
    for raw in normalized.split(";"):
        item = raw.strip()
        if not item:
            continue  # skip trailing/double separators
        pieces = item.split(",")
        if len(pieces) != 2:
            raise ValueError(f"Expected 'x,y' but got {item!r}")
        x = float(pieces[0].strip())
        y = float(pieces[1].strip())
        points.append((x, y))
    return points
