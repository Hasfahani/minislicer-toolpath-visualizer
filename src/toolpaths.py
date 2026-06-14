# Purpose: Generates perimeters, infill patterns, path ordering, simplification, and segment records.
# Reason: Keeping raw path algorithms here makes the planner small and the geometry behavior easy to test.
"""Toolpath generation utilities for simplified 2D planning."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
from shapely import affinity
from shapely.geometry import GeometryCollection, LineString, MultiLineString, Polygon


@dataclass(frozen=True)
class Segment:
    """Represents a single ordered toolpath segment."""

    path_type: str
    order_index: int
    x_start: float
    y_start: float
    x_end: float
    y_end: float
    length_mm: float
    layer: int


def generate_inward_perimeters(shape: Polygon, count: int, spacing: float) -> list[LineString]:
    """Generate inward perimeter rings from a polygon.

    The first perimeter is the outer boundary (polygon exterior).
    """
    if count <= 0 or spacing <= 0:
        return []

    perimeters: list[LineString] = [LineString(shape.exterior.coords)]

    for idx in range(1, count):
        offset_distance = spacing * idx
        inset = shape.buffer(-offset_distance)
        inset_polygon = _largest_polygon(inset)
        if inset_polygon is None:
            break
        perimeters.append(LineString(inset_polygon.exterior.coords))

    return perimeters


def generate_parallel_infill(shape: Polygon, spacing: float, angle_deg: float) -> list[LineString]:
    """Generate clipped parallel infill lines at a selected angle."""
    if spacing <= 0:
        return []

    centroid = shape.centroid
    rotated = affinity.rotate(shape, -angle_deg, origin=(centroid.x, centroid.y))

    min_x, min_y, max_x, max_y = rotated.bounds
    if max_y - min_y <= 0:
        return []

    lines: list[LineString] = []
    y_values = np.arange(min_y, max_y + spacing, spacing)

    for y in y_values:
        base_line = LineString([(min_x - spacing, y), (max_x + spacing, y)])
        clipped = rotated.intersection(base_line)
        parts = _extract_lines(clipped)
        for part in parts:
            restored = affinity.rotate(part, angle_deg, origin=(centroid.x, centroid.y))
            # Second clip in original space removes floating-point drift from the rotation
            final_parts = _extract_lines(shape.intersection(restored))
            for fp in final_parts:
                if fp.length > 0:
                    lines.append(fp)

    return lines


def build_ordered_segments(
    boundary: LineString | None,
    perimeters: list[LineString],
    infill_lines: list[LineString],
    layer: int,
) -> list[Segment]:
    """Flatten boundary, perimeter, and infill paths into ordered segments."""
    segments: list[Segment] = []
    index = 0

    for line in [boundary] if boundary is not None else []:
        new_segments = _line_to_segments(line, "boundary", index, layer)
        segments.extend(new_segments)
        index += len(new_segments)

    for line in perimeters:
        new_segments = _line_to_segments(line, "perimeter", index, layer)
        segments.extend(new_segments)
        index += len(new_segments)

    for line in infill_lines:
        new_segments = _line_to_segments(line, "infill", index, layer)
        segments.extend(new_segments)
        index += len(new_segments)

    return segments


def optimize_path_order(
    lines: list[LineString],
    allow_reverse: bool = True,
) -> list[LineString]:
    """Reorder line paths using a nearest-neighbor heuristic.

    This lowers non-print travel distance for independent paths such as infill.
    If ``allow_reverse`` is true, a line can be reversed when its end point is
    closer than its start point to the current head position.
    """
    if len(lines) <= 1:
        return list(lines)

    remaining = [line for line in lines if len(line.coords) >= 2]
    if not remaining:
        return []

    ordered: list[LineString] = []
    current = remaining.pop(0)
    ordered.append(current)

    while remaining:
        curr_end = _line_end(ordered[-1])
        best_idx = 0
        best_reversed = False
        best_dist = float("inf")

        for idx, cand in enumerate(remaining):
            start_dist = _point_distance(curr_end, _line_start(cand))
            if start_dist < best_dist:
                best_dist = start_dist
                best_idx = idx
                best_reversed = False

            if allow_reverse:
                end_dist = _point_distance(curr_end, _line_end(cand))
                if end_dist < best_dist:
                    best_dist = end_dist
                    best_idx = idx
                    best_reversed = True

        chosen = remaining.pop(best_idx)
        ordered.append(_reversed_line(chosen) if best_reversed else chosen)

    return ordered


def total_travel_distance(lines: list[LineString]) -> float:
    """Compute total non-printing travel distance between consecutive lines."""
    if len(lines) <= 1:
        return 0.0

    total = 0.0
    for idx in range(len(lines) - 1):
        a = lines[idx]
        b = lines[idx + 1]
        if len(a.coords) < 2 or len(b.coords) < 2:
            continue
        total += _point_distance(_line_end(a), _line_start(b))
    return float(total)


def simplify_lines(lines: list[LineString], tolerance_mm: float) -> list[LineString]:
    """Simplify path geometry to reduce vertex count.

    Uses Shapely line simplification with topology preservation. A non-positive
    tolerance returns the input as a shallow copy.
    """
    if tolerance_mm <= 0:
        return list(lines)

    simplified: list[LineString] = []
    for line in lines:
        if len(line.coords) < 2:
            continue
        out = line.simplify(tolerance_mm, preserve_topology=True)
        if isinstance(out, LineString) and len(out.coords) >= 2 and out.length > 0:
            simplified.append(out)
    return simplified


def filter_short_lines(lines: list[LineString], min_length_mm: float) -> list[LineString]:
    """Drop degenerate and very short lines using a minimum length threshold."""
    threshold = max(0.0, float(min_length_mm))
    return [line for line in lines if len(line.coords) >= 2 and line.length >= threshold]


def _line_to_segments(line: LineString, path_type: str, start_index: int, layer: int) -> list[Segment]:
    coords = list(line.coords)
    segments: list[Segment] = []

    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        part = LineString([(x0, y0), (x1, y1)])
        if part.length == 0:
            continue
        segments.append(
            Segment(
                path_type=path_type,
                order_index=start_index + len(segments),
                x_start=float(x0),
                y_start=float(y0),
                x_end=float(x1),
                y_end=float(y1),
                length_mm=float(part.length),
                layer=layer,
            )
        )
    return segments


def generate_grid_infill(shape: Polygon, spacing: float, angle_deg: float) -> list[LineString]:
    """Generate grid infill: two perpendicular sets of parallel lines."""
    lines_a = generate_parallel_infill(shape, spacing, angle_deg)
    lines_b = generate_parallel_infill(shape, spacing, angle_deg + 90.0)
    return lines_a + lines_b


def generate_triangular_infill(shape: Polygon, spacing: float, angle_deg: float) -> list[LineString]:
    """Generate triangular infill from three 60-degree-spaced line families."""
    lines: list[LineString] = []
    for offset in (0.0, 60.0, 120.0):
        lines.extend(generate_parallel_infill(shape, spacing, angle_deg + offset))
    return lines


def generate_zigzag_infill(shape: Polygon, spacing: float, angle_deg: float) -> list[LineString]:
    """Generate alternating-direction parallel infill for shorter line-to-line travels."""
    lines = generate_parallel_infill(shape, spacing, angle_deg)
    if len(lines) <= 1:
        return lines

    ordered = sorted(lines, key=_line_midpoint_sort_key)
    return [_reversed_line(line) if idx % 2 == 1 else line for idx, line in enumerate(ordered)]


def generate_honeycomb_infill(shape: Polygon, spacing: float, angle_deg: float = 0.0) -> list[LineString]:
    """Generate honeycomb (hexagonal) infill pattern.

    ``spacing`` is used as the hexagon circumradius (center-to-vertex distance),
    which controls cell size. Supports rotation via ``angle_deg``.
    """
    if spacing <= 0:
        return []

    a = max(float(spacing), 0.1)
    centroid = shape.centroid
    rotated = affinity.rotate(shape, -angle_deg, origin=(centroid.x, centroid.y))
    min_x, min_y, max_x, max_y = rotated.bounds
    pad = a * 2.0

    # Pointy-top hexagon: width=a*sqrt(3), height=2a, row spacing=1.5a
    hex_w = a * math.sqrt(3)
    row_step = a * 1.5

    raw_segs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    row_idx = 0
    cy = min_y - pad
    while cy <= max_y + pad:
        x_off = (row_idx % 2) * (hex_w * 0.5)
        cx = min_x - pad + x_off
        while cx <= max_x + pad:
            verts = [
                (cx + a * math.cos(math.radians(90.0 + 60.0 * i)),
                 cy + a * math.sin(math.radians(90.0 + 60.0 * i)))
                for i in range(6)
            ]
            for i in range(6):
                raw_segs.append((verts[i], verts[(i + 1) % 6]))
            cx += hex_w
        cy += row_step
        row_idx += 1

    if not raw_segs:
        return []

    multi = MultiLineString(raw_segs)
    clipped = rotated.intersection(multi)

    lines: list[LineString] = []
    for part in _extract_lines(clipped):
        if part.length > 0:
            restored = affinity.rotate(part, angle_deg, origin=(centroid.x, centroid.y))
            for fp in _extract_lines(shape.intersection(restored)):
                if fp.length > 0:
                    lines.append(fp)
    return lines


def generate_concentric_infill(shape: Polygon, spacing: float) -> list[LineString]:
    """Generate concentric infill rings offsetting inward from the shape boundary."""
    if spacing <= 0:
        return []
    lines: list[LineString] = []
    offset = spacing
    while True:
        inset = shape.buffer(-offset)
        poly = _largest_polygon(inset)
        if poly is None or poly.is_empty:
            break
        lines.append(LineString(poly.exterior.coords))
        offset += spacing
    return lines


def _extract_lines(geometry: GeometryCollection | LineString | MultiLineString) -> Iterable[LineString]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, LineString):
        return [geometry]
    if isinstance(geometry, MultiLineString):
        return [line for line in geometry.geoms if isinstance(line, LineString)]
    if isinstance(geometry, GeometryCollection):
        lines: list[LineString] = []
        for geom in geometry.geoms:
            if isinstance(geom, LineString):
                lines.append(geom)
            elif isinstance(geom, MultiLineString):
                lines.extend([line for line in geom.geoms if isinstance(line, LineString)])
        return lines
    return []


def _largest_polygon(geometry: object) -> Polygon | None:
    if isinstance(geometry, Polygon):
        return geometry if not geometry.is_empty else None

    geoms = getattr(geometry, "geoms", None)
    if geoms is None:
        return None

    polygons = [geom for geom in geoms if isinstance(geom, Polygon) and not geom.is_empty]
    if not polygons:
        return None
    return max(polygons, key=lambda poly: poly.area)


def _line_start(line: LineString) -> tuple[float, float]:
    x, y = line.coords[0]
    return (float(x), float(y))


def _line_end(line: LineString) -> tuple[float, float]:
    x, y = line.coords[-1]
    return (float(x), float(y))


def _point_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return float(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5)


def _reversed_line(line: LineString) -> LineString:
    return LineString(list(line.coords)[::-1])


def _line_midpoint_sort_key(line: LineString) -> tuple[float, float]:
    coords = list(line.coords)
    x0, y0 = coords[0]
    x1, y1 = coords[-1]
    return (float((y0 + y1) / 2.0), float((x0 + x1) / 2.0))


def generate_infill(
    shape: Polygon,
    pattern: str,
    spacing: float,
    angle_deg: float = 45.0,
) -> list[LineString]:
    """Dispatch to the right infill generator for the given pattern name."""
    if pattern == "Grid":
        return generate_grid_infill(shape, spacing=spacing, angle_deg=angle_deg)
    if pattern == "Triangles":
        return generate_triangular_infill(shape, spacing=spacing, angle_deg=angle_deg)
    if pattern == "Zigzag":
        return generate_zigzag_infill(shape, spacing=spacing, angle_deg=angle_deg)
    if pattern == "Honeycomb":
        return generate_honeycomb_infill(shape, spacing=spacing, angle_deg=angle_deg)
    if pattern == "Concentric":
        return generate_concentric_infill(shape, spacing=spacing)
    return generate_parallel_infill(shape, spacing=spacing, angle_deg=angle_deg)
