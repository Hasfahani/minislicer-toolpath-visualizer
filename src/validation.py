"""Job readiness checks for MiniSlicer planning results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReadinessIssue:
    """A single production-readiness finding."""

    severity: str
    title: str
    detail: str
    action: str


def assess_job_readiness(
    *,
    fits_plate: bool,
    metrics: dict[str, Any],
    perimeter_count: int,
    infill_line_count: int,
    layer_height_mm: float,
    nozzle_diameter_mm: float,
    effective_spacing_mm: float,
    perimeter_spacing_mm: float,
    segment_count: int,
    travel_ratio_pct: float,
    process_mode: str,
    imported_stl: bool,
    imported_svg: bool,
    volumetric_flow_mm3_s: float | None = None,
    model_height_mm: float | None = None,
    layer_count: int | None = None,
) -> dict[str, Any]:
    """Return a readiness score, grade, and actionable findings for a job."""
    issues: list[ReadinessIssue] = []

    if not fits_plate:
        issues.append(ReadinessIssue(
            "blocker",
            "Build plate overflow",
            "The current geometry extends outside the selected build plate.",
            "Center the part, reduce scale, or enable fit-inside-plate before export.",
        ))

    if perimeter_count <= 0 or metrics.get("perimeter_path_count", 0) <= 0:
        issues.append(ReadinessIssue(
            "blocker",
            "No perimeter paths",
            "The planner did not produce closed wall paths for this layer.",
            "Increase the part size or reduce perimeter spacing.",
        ))

    if infill_line_count <= 0:
        issues.append(ReadinessIssue(
            "warning",
            "No infill paths",
            "This layer will only contain walls.",
            "Lower infill spacing, increase density, or reduce wall clearance.",
        ))

    if layer_height_mm > nozzle_diameter_mm * 0.8:
        issues.append(ReadinessIssue(
            "warning",
            "Tall layer height",
            f"Layer height is {layer_height_mm:.2f} mm for a {nozzle_diameter_mm:.2f} mm nozzle.",
            "Use a layer height at or below 80% of nozzle diameter for a safer preview.",
        ))

    if volumetric_flow_mm3_s is not None:
        if process_mode.startswith("FDM") and volumetric_flow_mm3_s > 14.0:
            issues.append(ReadinessIssue(
                "warning",
                "High volumetric flow",
                f"Requested flow is {volumetric_flow_mm3_s:.1f} mm3/s.",
                "Reduce speed, layer height, or nozzle width unless the hotend is validated for this flow.",
            ))
        elif process_mode.startswith("FDM") and volumetric_flow_mm3_s > 10.0:
            issues.append(ReadinessIssue(
                "info",
                "Elevated volumetric flow",
                f"Requested flow is {volumetric_flow_mm3_s:.1f} mm3/s.",
                "Confirm filament and hotend can sustain the selected flow rate.",
            ))

    if effective_spacing_mm > nozzle_diameter_mm * 12:
        issues.append(ReadinessIssue(
            "warning",
            "Sparse infill",
            f"Infill spacing is {effective_spacing_mm:.2f} mm.",
            "Use density mode or reduce spacing for stronger internal support.",
        ))

    if perimeter_spacing_mm > nozzle_diameter_mm * 1.5:
        issues.append(ReadinessIssue(
            "info",
            "Wide wall spacing",
            f"Perimeter spacing is {perimeter_spacing_mm:.2f} mm.",
            "Keep wall spacing close to extrusion width unless this is intentional.",
        ))

    if travel_ratio_pct > 35:
        issues.append(ReadinessIssue(
            "warning",
            "High travel share",
            f"Travel moves are {travel_ratio_pct:.1f}% of total motion.",
            "Try zigzag or concentric infill and keep infill optimization enabled.",
        ))
    elif travel_ratio_pct > 22:
        issues.append(ReadinessIssue(
            "info",
            "Moderate travel share",
            f"Travel moves are {travel_ratio_pct:.1f}% of total motion.",
            "Compare alternate infill patterns before exporting.",
        ))

    if segment_count > 10000:
        issues.append(ReadinessIssue(
            "warning",
            "Heavy toolpath",
            f"This layer has {segment_count:,} segments.",
            "Increase simplification or spacing to keep browser interaction responsive.",
        ))
    elif segment_count > 5000:
        issues.append(ReadinessIssue(
            "info",
            "Dense preview",
            f"This layer has {segment_count:,} segments.",
            "Use the data tab and simplification controls if interaction becomes slow.",
        ))

    if layer_count is not None and layer_count > 1200:
        issues.append(ReadinessIssue(
            "warning",
            "Long layer stack",
            f"The build has {layer_count:,} layers.",
            "Review layer height and model height before committing machine time.",
        ))

    if model_height_mm is not None and process_mode.startswith("FDM") and model_height_mm > 220:
        issues.append(ReadinessIssue(
            "info",
            "Tall FDM build",
            f"Model height is {model_height_mm:.1f} mm.",
            "Confirm printer Z capacity, enclosure stability, and collision clearance.",
        ))

    if (process_mode.startswith("DED") or process_mode.startswith("Metal")) and not imported_stl:
        issues.append(ReadinessIssue(
            "info",
            "2D metal preview",
            "Metal / LPBF mode is being previewed from a 2D outline.",
            "Import an STL to review cross-sections across the actual Z range.",
        ))

    if not imported_stl and not imported_svg:
        issues.append(ReadinessIssue(
            "info",
            "Parametric sample shape",
            "The job is based on a generated test shape.",
            "Import customer geometry when preparing a real planning package.",
        ))

    penalties = {"blocker": 35, "warning": 12, "info": 4}
    score = max(0, 100 - sum(penalties[issue.severity] for issue in issues))
    if any(issue.severity == "blocker" for issue in issues):
        status = "Blocked"
    elif score >= 90:
        status = "Ready"
    elif score >= 75:
        status = "Review"
    else:
        status = "Needs work"

    return {
        "score": score,
        "status": status,
        "blockers": sum(issue.severity == "blocker" for issue in issues),
        "warnings": sum(issue.severity == "warning" for issue in issues),
        "infos": sum(issue.severity == "info" for issue in issues),
        "issues": issues,
    }


def readiness_to_dict(readiness: dict[str, Any]) -> dict[str, Any]:
    """Convert readiness output to a JSON-safe dictionary."""
    return {
        key: [
            {
                "severity": issue.severity,
                "title": issue.title,
                "detail": issue.detail,
                "action": issue.action,
            }
            for issue in value
        ] if key == "issues" else value
        for key, value in readiness.items()
    }
