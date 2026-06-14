# Purpose: Converts validated geometry and toolpath settings into complete layer and build plans.
# Reason: This is the planning boundary that makes outputs deterministic, testable, and traceable.
"""Planning engine services for MiniSlicer."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from shapely.geometry import LineString, Polygon

from src.plotting import shape_boundary
from src.toolpaths import (
    Segment,
    build_ordered_segments,
    filter_short_lines,
    generate_infill,
    generate_inward_perimeters,
    optimize_path_order,
    simplify_lines,
    total_travel_distance,
)


@dataclass(frozen=True)
class ToolpathSettings:
    """Immutable settings used by the backend planner."""

    perimeter_count: int
    perimeter_spacing_mm: float
    infill_pattern: str
    infill_spacing_mm: float
    infill_angle_deg: float
    optimize_perimeters: bool = False
    optimize_infill: bool = True
    allow_line_reverse: bool = True
    simplify_tolerance_mm: float = 0.0
    min_segment_length_mm: float = 0.0

    def __post_init__(self) -> None:
        if self.perimeter_count < 0:
            raise ValueError("perimeter_count must be non-negative.")
        if self.perimeter_spacing_mm <= 0:
            raise ValueError("perimeter_spacing_mm must be positive.")
        if self.infill_spacing_mm <= 0:
            raise ValueError("infill_spacing_mm must be positive.")
        if self.simplify_tolerance_mm < 0:
            raise ValueError("simplify_tolerance_mm must be non-negative.")
        if self.min_segment_length_mm < 0:
            raise ValueError("min_segment_length_mm must be non-negative.")


@dataclass(frozen=True)
class LayerPlan:
    """Generated paths and segments for one layer."""

    boundary: LineString
    perimeters: list[LineString]
    infill_lines: list[LineString]
    segments: list[Segment]
    layer: int


def plan_layer(
    perimeter_shape: Polygon,
    infill_shape: Polygon,
    settings: ToolpathSettings,
    *,
    layer: int,
    infill_angle_deg: float | None = None,
) -> LayerPlan:
    """Generate a complete layer plan from validated geometry and settings."""
    angle = float(settings.infill_angle_deg if infill_angle_deg is None else infill_angle_deg)
    boundary = shape_boundary(perimeter_shape)
    perimeters = generate_inward_perimeters(
        perimeter_shape,
        int(settings.perimeter_count),
        float(settings.perimeter_spacing_mm),
    )
    infill_lines = generate_infill(
        infill_shape,
        settings.infill_pattern,
        float(settings.infill_spacing_mm),
        angle,
    )

    if settings.optimize_perimeters:
        perimeters = optimize_path_order(perimeters, allow_reverse=False)
    if settings.optimize_infill:
        infill_lines = optimize_path_order(infill_lines, allow_reverse=settings.allow_line_reverse)
    if settings.simplify_tolerance_mm > 0:
        perimeters = simplify_lines(perimeters, settings.simplify_tolerance_mm)
        infill_lines = simplify_lines(infill_lines, settings.simplify_tolerance_mm)
    if settings.min_segment_length_mm > 0:
        perimeters = filter_short_lines(perimeters, settings.min_segment_length_mm)
        infill_lines = filter_short_lines(infill_lines, settings.min_segment_length_mm)

    segments = build_ordered_segments(None, perimeters, infill_lines, int(layer))
    return LayerPlan(boundary, perimeters, infill_lines, segments, int(layer))


def build_production_segments(
    perimeter_shape: Polygon,
    infill_shape: Polygon,
    settings: ToolpathSettings,
    *,
    layer_count: int,
    alternate_angle: bool,
    layer_limit: int = 600,
) -> list[Segment]:
    """Generate full-build segments when the layer count is inside the export limit."""
    if layer_count > layer_limit:
        return plan_layer(perimeter_shape, infill_shape, settings, layer=1).segments

    production: list[Segment] = []
    for prod_layer in range(1, max(1, int(layer_count)) + 1):
        angle = alternating_layer_angle(settings.infill_angle_deg, prod_layer, alternate_angle)
        production.extend(
            plan_layer(
                perimeter_shape,
                infill_shape,
                settings,
                layer=prod_layer,
                infill_angle_deg=angle,
            ).segments
        )
    return production


def alternating_layer_angle(base_angle_deg: float, layer: int, alternate_angle: bool) -> float:
    """Return the active infill angle for a layer."""
    if not alternate_angle:
        return float(base_angle_deg)
    return 45.0 if int(layer) % 2 == 1 else -45.0


def rank_infill_patterns(
    shape: Polygon,
    patterns: list[str],
    settings: ToolpathSettings,
) -> list[dict[str, Any]]:
    """Score available infill patterns for the active layer."""
    rows: list[dict[str, Any]] = []
    for pattern in patterns:
        candidate_settings = ToolpathSettings(
            **{**asdict(settings), "infill_pattern": pattern}
        )
        candidate = plan_layer(shape, shape, candidate_settings, layer=1)
        path_mm = float(sum(line.length for line in candidate.infill_lines))
        travel_mm = float(total_travel_distance(candidate.infill_lines))
        total_motion = path_mm + travel_mm
        efficiency_pct = 100.0 * path_mm / total_motion if total_motion > 0 else 0.0
        rows.append({
            "pattern": pattern,
            "path_mm": path_mm,
            "travel_mm": travel_mm,
            "line_count": len(candidate.infill_lines),
            "efficiency_pct": efficiency_pct,
        })

    if not rows:
        return []

    max_path = max(row["path_mm"] for row in rows) or 1.0
    max_travel = max(row["travel_mm"] for row in rows) or 1.0
    max_lines = max(row["line_count"] for row in rows) or 1
    for row in rows:
        path_score = 1.0 - (row["path_mm"] / max_path)
        travel_score = 1.0 - (row["travel_mm"] / max_travel)
        density_score = 1.0 - (row["line_count"] / max_lines)
        efficiency_score = row["efficiency_pct"] / 100.0
        row["score"] = round(100.0 * (
            0.36 * travel_score
            + 0.28 * efficiency_score
            + 0.22 * path_score
            + 0.14 * density_score
        ))
    return sorted(rows, key=lambda item: (-item["score"], item["travel_mm"], item["path_mm"]))


def build_plan_fingerprint(
    shape: Polygon,
    settings: ToolpathSettings,
    *,
    layer_count: int,
    process_mode: str,
    material: str,
) -> str:
    """Return a deterministic short fingerprint for traceability."""
    payload = {
        "settings": asdict(settings),
        "layer_count": int(layer_count),
        "process_mode": process_mode,
        "material": material,
        "geometry_wkb_sha256": sha256(shape.wkb).hexdigest(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()[:16]
