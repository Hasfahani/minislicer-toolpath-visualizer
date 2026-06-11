"""Metrics for simplified toolpath plans."""

from __future__ import annotations

import math
from typing import Any

from shapely.geometry import Polygon

from src.geometry import bounding_box, polygon_area
from src.toolpaths import Segment, total_travel_distance

# Material densities in g/cm3 (FDM polymers + DED metals)
MATERIAL_DENSITY: dict[str, float] = {
    # FDM polymers
    "PLA": 1.24,
    "PETG": 1.27,
    "ABS": 1.04,
    "TPU": 1.21,
    "ASA": 1.07,
    # DED metals
    "Steel 316L": 7.99,
    "Steel H13": 7.76,
    "Titanium Ti-6Al-4V": 4.43,
    "Inconel 625": 8.44,
    "Aluminum AlSi10Mg": 2.67,
    "Copper CuCr1Zr": 8.90,
}


def total_path_length(segments: list[Segment]) -> float:
    """Compute total movement length in millimeters."""
    return float(sum(seg.length_mm for seg in segments))


def estimate_print_time_seconds(total_length_mm: float, print_speed_mm_s: float) -> float:
    """Estimate print time in seconds using constant speed."""
    if print_speed_mm_s <= 0:
        return math.inf
    return float(total_length_mm / print_speed_mm_s)


def _move_time_s(length_mm: float, speed_mm_s: float, accel_mm_s2: float) -> float:
    """Trapezoidal velocity profile time for a single motion segment.

    For short moves that cannot reach full speed the profile is triangular;
    for longer moves a cruise phase is added between the ramp-up and ramp-down.
    Falls back to constant-speed if acceleration is zero or negative.
    """
    if length_mm <= 0 or speed_mm_s <= 0:
        return 0.0
    if accel_mm_s2 <= 0:
        return length_mm / speed_mm_s
    # Distance consumed by a full ramp-up + ramp-down (both symmetric)
    d_ramp = speed_mm_s ** 2 / accel_mm_s2
    if length_mm >= d_ramp:
        # Cruise phase exists: t = V/A (ramp) + (L - d_ramp)/V (cruise)
        return speed_mm_s / accel_mm_s2 + (length_mm - d_ramp) / speed_mm_s
    # Triangular profile - peak speed never reached
    return 2.0 * math.sqrt(length_mm / accel_mm_s2)


def estimate_material(
    total_path_length_mm: float,
    layer_height_mm: float,
    nozzle_diameter_mm: float,
    filament_diameter_mm: float,
    material: str = "PLA",
) -> dict[str, float]:
    """Estimate material usage for a single layer.

    Uses the rectangular extrusion cross-section model:
      material_volume = path_length * layer_height * nozzle_diameter
    Then back-calculates filament length consumed and weight.
    """
    density = MATERIAL_DENSITY.get(material, 1.24)

    # Volume of material deposited (mm3) using elliptical bead cross-section:
    #   A_bead approx (pi/4) x nozzle_diameter x layer_height
    # This is more accurate than a rectangular cross-section because the
    # extruded bead rounds at the edges; pi/4 approx 0.785 reduces the estimate
    # by ~21% compared to the flat rectangular model.
    material_volume_mm3 = (math.pi / 4.0) * total_path_length_mm * layer_height_mm * nozzle_diameter_mm

    # Filament volume -> filament length
    filament_radius_mm = filament_diameter_mm / 2.0
    filament_volume_mm3 = math.pi * filament_radius_mm ** 2
    filament_length_mm = (
        material_volume_mm3 / filament_volume_mm3 if filament_volume_mm3 > 0 else 0.0
    )

    # Weight: convert mm3 -> cm3 (* 0.001), then multiply by density (g/cm3)
    weight_g = material_volume_mm3 * 0.001 * density

    return {
        "material_volume_mm3": material_volume_mm3,
        "filament_length_mm": filament_length_mm,
        "filament_length_m": filament_length_mm / 1000.0,
        "weight_g": weight_g,
    }


def summarize_metrics(
    shape: Polygon,
    segments: list[Segment],
    perimeter_paths: list[object],
    infill_lines: list[object],
    print_speed_mm_s: float,
    travel_speed_mm_s: float | None = None,
    layer_height_mm: float = 0.2,
    nozzle_diameter_mm: float = 0.4,
    filament_diameter_mm: float = 1.75,
    material: str = "PLA",
    acceleration_mm_s2: float = 500.0,
    perimeter_speed_mult: float = 0.8,
) -> dict[str, Any]:
    """Return a full metric summary dictionary for UI display."""
    total_len = total_path_length(segments)
    bbox = bounding_box(shape)
    area = polygon_area(shape)

    perimeter_length = sum(
        seg.length_mm for seg in segments if seg.path_type == "perimeter"
    )
    infill_length = sum(
        seg.length_mm for seg in segments if seg.path_type == "infill"
    )
    travel_length = total_travel_distance([*perimeter_paths, *infill_lines])
    total_motion = total_len + travel_length
    path_efficiency_pct = (100.0 * total_len / total_motion) if total_motion > 0 else 0.0
    travel_speed = max(float(travel_speed_mm_s or print_speed_mm_s), 0.1)

    # Per-segment trapezoidal velocity profile accounts for acceleration and the
    # slower perimeter speed; more accurate than dividing total length by speed.
    perim_speed = max(0.1, print_speed_mm_s * perimeter_speed_mult)
    estimated_motion_time_s = sum(
        _move_time_s(
            seg.length_mm,
            perim_speed if seg.path_type == "perimeter" else print_speed_mm_s,
            acceleration_mm_s2,
        )
        for seg in segments
    ) + _move_time_s(travel_length, travel_speed, acceleration_mm_s2)

    mat = estimate_material(
        total_path_length_mm=total_len,
        layer_height_mm=layer_height_mm,
        nozzle_diameter_mm=nozzle_diameter_mm,
        filament_diameter_mm=filament_diameter_mm,
        material=material,
    )

    return {
        "total_path_length_mm": total_len,
        "segment_count": len(segments),
        "perimeter_path_count": len(perimeter_paths),
        "infill_line_count": len(infill_lines),
        "estimated_print_time_s": estimate_print_time_seconds(total_len, print_speed_mm_s),
        "estimated_motion_time_s": estimated_motion_time_s,
        "bbox_width_mm": bbox.width,
        "bbox_height_mm": bbox.height,
        "area_mm2": area,
        "perimeter_length_mm": perimeter_length,
        "infill_length_mm": infill_length,
        "travel_length_mm": travel_length,
        "total_motion_length_mm": total_motion,
        "path_efficiency_pct": path_efficiency_pct,
        "bbox_diagonal_mm": math.hypot(bbox.width, bbox.height),
        # Material estimates
        "material_volume_mm3": mat["material_volume_mm3"],
        "filament_length_m": mat["filament_length_m"],
        "weight_g": mat["weight_g"],
    }
