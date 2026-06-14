# Purpose: Converts planned segments into CSV, JSON, SVG, preview G-code, and guarded FDM G-code.
# Reason: Export logic is isolated so file formats and machine safety checks can be tested directly.
"""Export helpers for toolpath segments."""

from __future__ import annotations

import io
import json
from hashlib import sha256

import pandas as pd
from shapely.geometry import LineString

from src.profiles import MachineGcodeProfile
from src.toolpaths import Segment

CSV_COLUMNS = [
    "segment_id",
    "path_type",
    "order_index",
    "x_start",
    "y_start",
    "x_end",
    "y_end",
    "length_mm",
    "layer",
]


class ProductionExportError(ValueError):
    """Raised when a toolpath is not safe to export as production G-code."""


def segments_to_dataframe(segments: list[Segment]) -> pd.DataFrame:
    """Convert segments to a DataFrame with a stable schema."""
    records: list[dict[str, object]] = []
    for idx, seg in enumerate(segments, start=1):
        records.append(
            {
                "segment_id": idx,
                "path_type": seg.path_type,
                "order_index": seg.order_index,
                "x_start": seg.x_start,
                "y_start": seg.y_start,
                "x_end": seg.x_end,
                "y_end": seg.y_end,
                "length_mm": seg.length_mm,
                "layer": seg.layer,
            }
        )
    return pd.DataFrame(records, columns=CSV_COLUMNS)


def export_segments_csv(segments: list[Segment]) -> str:
    """Export segment rows to CSV text."""
    df = segments_to_dataframe(segments)
    return df.to_csv(index=False)


def export_segments_json(
    segments: list[Segment],
    parameters: dict[str, object] | None = None,
) -> str:
    """Export segments and optional run parameters as formatted JSON text."""
    payload = {
        "schema_version": 1,
        "parameters": parameters or {},
        "segments": segments_to_dataframe(segments).to_dict(orient="records"),
    }
    return json.dumps(payload, indent=2)


def export_gcode_like(
    segments: list[Segment],
    print_speed_mm_s: float,
    layer_height_mm: float = 0.2,
    travel_speed_mm_s: float | None = None,
    z_hop_mm: float = 0.0,
    include_e_values: bool = False,
    extrusion_per_mm: float = 0.04,
) -> str:
    """Build a simple educational G-code-like motion file.

    This output is not machine-ready and is only for demonstration.
    """
    feed_rate_mm_min = max(print_speed_mm_s, 0.1) * 60.0
    travel_feed_rate_mm_min = max(travel_speed_mm_s or print_speed_mm_s, 0.1) * 60.0

    buffer = io.StringIO()
    buffer.write("; MiniSlicer Toolpath Export (educational only)\n")
    buffer.write("; Not for production 3D printing workflows\n")
    buffer.write("G21 ; units in mm\n")
    buffer.write("G90 ; absolute coordinates\n")
    buffer.write(f"G0 Z{layer_height_mm:.3f} ; raise to layer height\n")
    buffer.write(f"G1 F{feed_rate_mm_min:.1f} ; set print feed rate\n")
    buffer.write(f"G0 F{travel_feed_rate_mm_min:.1f} ; set travel feed rate\n")
    if include_e_values:
        buffer.write("M82 ; absolute extrusion mode\n")
        buffer.write("G92 E0 ; zero extruder\n")
    buffer.write("\n")

    current_type = None
    e_position = 0.0
    for seg in segments:
        if seg.path_type != current_type:
            current_type = seg.path_type
            buffer.write(f"; --- {current_type} (layer {seg.layer}) ---\n")
        if z_hop_mm > 0:
            buffer.write(f"G0 Z{layer_height_mm + z_hop_mm:.3f} ; Z-hop\n")
        buffer.write(
            f"G0 X{seg.x_start:.3f} Y{seg.y_start:.3f} F{travel_feed_rate_mm_min:.1f} ; travel\n"
        )
        if z_hop_mm > 0:
            buffer.write(f"G0 Z{layer_height_mm:.3f} ; return to layer Z\n")

        if include_e_values:
            e_position += max(0.0, seg.length_mm) * max(0.0, extrusion_per_mm)
            buffer.write(
                f"G1 X{seg.x_end:.3f} Y{seg.y_end:.3f} E{e_position:.5f} "
                f"F{feed_rate_mm_min:.1f} ; print\n"
            )
        else:
            buffer.write(
                f"G1 X{seg.x_end:.3f} Y{seg.y_end:.3f} F{feed_rate_mm_min:.1f} ; print\n"
            )

    buffer.write("\nM2 ; end of program\n")
    return buffer.getvalue()


def export_production_gcode(
    segments: list[Segment],
    machine: MachineGcodeProfile,
    print_speed_mm_s: float,
    layer_height_mm: float,
    travel_speed_mm_s: float,
    extrusion_per_mm: float,
    z_hop_mm: float = 0.0,
    job_name: str = "MiniSlicer job",
) -> str:
    """Export guarded FDM G-code using a concrete machine profile.

    This path is intentionally stricter than ``export_gcode_like``: it refuses
    empty jobs, out-of-bounds motion, non-positive extrusion, and invalid layer
    heights before writing temperature, homing, purge, fan, and shutdown code.
    """
    _validate_production_gcode_inputs(
        segments=segments,
        machine=machine,
        layer_height_mm=layer_height_mm,
        extrusion_per_mm=extrusion_per_mm,
    )

    feed_rate_mm_min = max(print_speed_mm_s, 0.1) * 60.0
    travel_feed_rate_mm_min = max(travel_speed_mm_s, 0.1) * 60.0
    safe_z = min(machine.max_z_mm, max((seg.layer + 1) * layer_height_mm for seg in segments) + 5.0)
    park_y = min(machine.bed_size_y_mm, max(0.0, machine.bed_size_y_mm - 5.0))

    buffer = io.StringIO()
    buffer.write("; MiniSlicer production FDM export\n")
    buffer.write(f"; Job: {job_name}\n")
    buffer.write(f"; Machine: {machine.name}\n")
    buffer.write(f"; Layers: {len({seg.layer for seg in segments})}\n")
    buffer.write(f"; Segments: {len(segments)}\n")
    buffer.write(f"; Toolpath-SHA256: {_segments_digest(segments)}\n")
    buffer.write("; Review machine, filament, and bed preparation before running.\n")
    for line in machine.start_gcode:
        buffer.write(line.format(
            bed_temp=machine.bed_temp_c,
            nozzle_temp=machine.nozzle_temp_c,
            safe_z=safe_z,
            park_y=park_y,
        ) + "\n")
    if machine.fan_speed > 0:
        buffer.write(f"M106 S{machine.fan_speed} ; part cooling fan\n")
    buffer.write(f"G1 F{feed_rate_mm_min:.1f} ; print feed rate\n")
    buffer.write(f"G0 F{travel_feed_rate_mm_min:.1f} ; travel feed rate\n")
    buffer.write("\n")

    e_position = 0.0
    current_layer = None
    current_type = None
    for seg in segments:
        layer_z = max(layer_height_mm, seg.layer * layer_height_mm)
        if seg.layer != current_layer:
            current_layer = seg.layer
            current_type = None
            buffer.write(f";LAYER:{seg.layer}\n")
            buffer.write(f"G1 Z{layer_z:.3f} F3000\n")
        if seg.path_type != current_type:
            current_type = seg.path_type
            buffer.write(f";TYPE:{seg.path_type.upper()}\n")

        if z_hop_mm > 0:
            buffer.write(f"G0 Z{min(layer_z + z_hop_mm, machine.max_z_mm):.3f} F3000 ; z-hop\n")
        buffer.write(
            f"G0 X{seg.x_start:.3f} Y{seg.y_start:.3f} F{travel_feed_rate_mm_min:.1f}\n"
        )
        if z_hop_mm > 0:
            buffer.write(f"G0 Z{layer_z:.3f} F3000\n")
        e_position += max(0.0, seg.length_mm) * extrusion_per_mm
        buffer.write(
            f"G1 X{seg.x_end:.3f} Y{seg.y_end:.3f} "
            f"E{e_position:.5f} F{feed_rate_mm_min:.1f}\n"
        )

    buffer.write("\n")
    for line in machine.end_gcode:
        buffer.write(line.format(
            bed_temp=machine.bed_temp_c,
            nozzle_temp=machine.nozzle_temp_c,
            safe_z=safe_z,
            park_y=park_y,
        ) + "\n")
    return buffer.getvalue()


def _validate_production_gcode_inputs(
    *,
    segments: list[Segment],
    machine: MachineGcodeProfile,
    layer_height_mm: float,
    extrusion_per_mm: float,
) -> None:
    if not segments:
        raise ProductionExportError("Cannot export production G-code without toolpath segments.")
    if layer_height_mm <= 0:
        raise ProductionExportError("Layer height must be positive.")
    if extrusion_per_mm <= 0:
        raise ProductionExportError("Extrusion per millimeter must be positive.")

    for seg in segments:
        if seg.length_mm <= 0:
            raise ProductionExportError("Production G-code cannot contain zero-length moves.")
        for x, y in ((seg.x_start, seg.y_start), (seg.x_end, seg.y_end)):
            if x < 0 or y < 0 or x > machine.bed_size_x_mm or y > machine.bed_size_y_mm:
                raise ProductionExportError(
                    f"Move ({x:.3f}, {y:.3f}) is outside {machine.name} build area."
                )
        if seg.layer * layer_height_mm > machine.max_z_mm:
            raise ProductionExportError(
                f"Layer {seg.layer} exceeds {machine.name} maximum Z height."
            )


def _segments_digest(segments: list[Segment]) -> str:
    digest = sha256()
    for seg in segments:
        digest.update(
            (
                f"{seg.layer}|{seg.path_type}|{seg.x_start:.5f}|{seg.y_start:.5f}|"
                f"{seg.x_end:.5f}|{seg.y_end:.5f}|{seg.length_mm:.5f}\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def export_svg(
    boundary: LineString,
    perimeters: list[LineString],
    infill_lines: list[LineString],
    margin: float = 5.0,
) -> str:
    """Export the toolpath as an SVG string."""
    all_lines: list[LineString] = [boundary, *perimeters, *infill_lines]

    all_x = [x for line in all_lines for x, *_ in line.coords]
    all_y = [y for line in all_lines for _, y, *_ in line.coords]

    if not all_x:
        return '<svg xmlns="http://www.w3.org/2000/svg"/>'

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    vw = max_x - min_x + 2 * margin
    vh = max_y - min_y + 2 * margin

    def pts(line: LineString) -> str:
        return " ".join(
            f"{x - min_x + margin:.3f},{max_y - y + margin:.3f}"
            for x, y, *_ in line.coords
        )

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {vw:.3f} {vh:.3f}" '
        f'width="{vw:.0f}mm" height="{vh:.0f}mm">',
        f'<polyline points="{pts(boundary)}" '
        f'fill="none" stroke="#475569" stroke-width="0.5" stroke-dasharray="2,1"/>',
    ]

    for line in perimeters:
        parts.append(
            f'<polyline points="{pts(line)}" fill="none" stroke="#2563eb" stroke-width="0.5"/>'
        )

    for line in infill_lines:
        parts.append(
            f'<polyline points="{pts(line)}" fill="none" stroke="#f97316" stroke-width="0.3"/>'
        )

    parts.append("</svg>")
    return "\n".join(parts)
