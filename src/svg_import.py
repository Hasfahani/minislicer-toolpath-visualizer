"""Parse SVG files into Shapely polygons for toolpath slicing."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from shapely.geometry import MultiPolygon, Polygon


def parse_svg_to_polygon(
    svg_bytes: bytes,
    target_width_mm: float | None = None,
) -> tuple[Polygon | None, str]:
    """Extract the first usable closed shape from an SVG file.

    Returns (polygon, error_message). polygon is None on failure.
    If target_width_mm is set, the shape is scaled to that width.
    """
    try:
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as exc:
        return None, f"Invalid SVG file: {exc}"

    # Strip XML namespaces so tag matching is simple
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]

    svg_height = _get_svg_height(root)

    pts: list[tuple[float, float]] | None = None
    for elem in root.iter():
        tag = elem.tag.lower()

        if tag == "polygon":
            pts = _parse_points_attr(elem.get("points", ""))

        elif tag == "polyline":
            pts = _parse_points_attr(elem.get("points", ""))

        elif tag == "rect":
            try:
                x = float(elem.get("x", 0))
                y = float(elem.get("y", 0))
                w = float(elem.get("width", 0))
                h = float(elem.get("height", 0))
                if w > 0 and h > 0:
                    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            except ValueError:
                continue

        elif tag == "path":
            pts = _parse_path_d(elem.get("d", ""))

        if pts and len(pts) >= 3:
            break

    if not pts or len(pts) < 3:
        return None, (
            "No usable shape found in the SVG. "
            "Supported elements: <polygon>, <polyline>, <rect>, <path> (M/L/Z only)."
        )

    # Flip Y axis: SVG has Y=0 at top; our coordinate system has Y=0 at bottom
    if svg_height is not None:
        pts = [(x, svg_height - y) for x, y in pts]
    else:
        max_y = max(y for _, y in pts)
        pts = [(x, max_y - y) for x, y in pts]

    try:
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if isinstance(poly, MultiPolygon):
            poly = max(poly.geoms, key=lambda p: p.area)
        if poly.is_empty or not poly.is_valid:
            return None, "The parsed shape is geometrically invalid."
    except Exception as exc:  # noqa: BLE001
        return None, f"Could not build polygon: {exc}"

    if target_width_mm is not None and target_width_mm > 0:
        poly = _scale_to_width(poly, target_width_mm)

    return poly, ""


# -- Internal helpers ----------------------------------------------------------

def _get_svg_height(root: ET.Element) -> float | None:
    """Return the SVG document height in user units, or None."""
    vb = root.get("viewBox", "")
    if vb:
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", vb)
        if len(nums) >= 4:
            return float(nums[3])
    h_attr = root.get("height", "")
    nums = re.findall(r"[-+]?\d*\.?\d+", h_attr)
    if nums:
        return float(nums[0])
    return None


def _parse_points_attr(points_str: str) -> list[tuple[float, float]] | None:
    """Parse SVG 'points' attribute: 'x1,y1 x2,y2 ...' or 'x1 y1 x2 y2 ...'."""
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", points_str)
    if len(nums) < 6 or len(nums) % 2 != 0:
        return None
    return [(float(nums[i]), float(nums[i + 1])) for i in range(0, len(nums), 2)]


def _parse_path_d(d: str) -> list[tuple[float, float]] | None:
    """Parse SVG path 'd' attribute supporting M, L, H, V, Z (and lowercase variants)."""
    pts: list[tuple[float, float]] = []
    normalized = re.sub(r"([MmLlHhVvZzCcSsQqTtAa])", r" \1 ", d).strip()
    tokens = normalized.split()

    i = 0
    current: tuple[float, float] = (0.0, 0.0)
    start: tuple[float, float] = (0.0, 0.0)
    cmd = "M"

    while i < len(tokens):
        token = tokens[i]
        if token.isalpha() and len(token) == 1:
            cmd = token
            i += 1
            continue
        try:
            if cmd == "M":
                x, y = float(tokens[i]), float(tokens[i + 1])
                current = (x, y)
                start = current
                pts.append(current)
                i += 2
                cmd = "L"
            elif cmd == "m":
                dx, dy = float(tokens[i]), float(tokens[i + 1])
                current = (current[0] + dx, current[1] + dy)
                if not pts:
                    start = current
                pts.append(current)
                i += 2
                cmd = "l"
            elif cmd == "L":
                x, y = float(tokens[i]), float(tokens[i + 1])
                current = (x, y)
                pts.append(current)
                i += 2
            elif cmd == "l":
                dx, dy = float(tokens[i]), float(tokens[i + 1])
                current = (current[0] + dx, current[1] + dy)
                pts.append(current)
                i += 2
            elif cmd == "H":
                current = (float(tokens[i]), current[1])
                pts.append(current)
                i += 1
            elif cmd == "h":
                current = (current[0] + float(tokens[i]), current[1])
                pts.append(current)
                i += 1
            elif cmd == "V":
                current = (current[0], float(tokens[i]))
                pts.append(current)
                i += 1
            elif cmd == "v":
                current = (current[0], current[1] + float(tokens[i]))
                pts.append(current)
                i += 1
            elif cmd in ("Z", "z"):
                current = start
                i += 1
            else:
                i += 1
        except (IndexError, ValueError):
            break

    return pts if len(pts) >= 3 else None


def _scale_to_width(poly: Polygon, target_width_mm: float) -> Polygon:
    """Scale polygon so its bounding-box width equals target_width_mm."""
    min_x, min_y, max_x, max_y = poly.bounds
    current_width = max_x - min_x
    if current_width <= 0:
        return poly
    scale = target_width_mm / current_width
    from shapely import affinity
    return affinity.scale(poly, xfact=scale, yfact=scale, origin=(min_x, min_y))
