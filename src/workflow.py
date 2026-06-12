"""Application workflow helpers for MiniSlicer."""

from __future__ import annotations

import math
from typing import Any

from shapely import affinity
from shapely.geometry import Polygon

from src.geometry import (
    create_arrow_shape,
    create_capsule,
    create_circle,
    create_cross,
    create_ellipse,
    create_rectangle,
    create_regular_polygon,
    create_rounded_rectangle,
    create_star,
    create_triangle,
    parse_custom_polygon,
)


def fmt_time(seconds: float) -> str:
    """Format seconds as compact operator-facing duration text."""
    if math.isinf(seconds):
        return "inf"
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    if seconds >= 60:
        return f"{int(seconds // 60)}m {seconds % 60:.0f}s"
    return f"{seconds:.1f}s"


def largest_polygon(geometry: object) -> Polygon | None:
    """Return the largest polygon from a polygonal geometry."""
    if isinstance(geometry, Polygon) and not geometry.is_empty:
        return geometry
    geoms = getattr(geometry, "geoms", None)
    if geoms is None:
        return None
    polys = [geom for geom in geoms if isinstance(geom, Polygon) and not geom.is_empty]
    return max(polys, key=lambda poly: poly.area) if polys else None


def build_shape(shape_type: str, settings: dict[str, Any]) -> Polygon | None:
    """Build a Shapely polygon from the selected shape type and UI settings."""
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
    """Apply scale, mirror, rotation, translation, and build-plate placement."""
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
