"""Business and manufacturability analysis for MiniSlicer jobs."""

from __future__ import annotations

import math
from typing import Any


def estimate_job_economics(
    *,
    metrics: dict[str, Any],
    layer_count: int,
    layer_height_mm: float,
    nozzle_diameter_mm: float,
    print_speed_mm_s: float,
    full_time_s: float,
    full_weight_g: float,
    material_cost_per_kg: float,
    machine_rate_per_h: float = 18.0,
    labor_rate_per_h: float = 45.0,
    setup_time_min: float = 12.0,
    postprocess_time_min: float = 8.0,
    scrap_allowance_pct: float = 8.0,
    margin_pct: float = 35.0,
) -> dict[str, float]:
    """Return quote-ready production economics and process KPIs.

    The estimates are intentionally transparent: every number comes from path
    length, material usage, motion time, and user-visible rate assumptions.
    """
    build_hours = max(float(full_time_s), 0.0) / 3600.0
    material_cost = max(float(full_weight_g), 0.0) / 1000.0 * max(float(material_cost_per_kg), 0.0)
    machine_cost = build_hours * max(float(machine_rate_per_h), 0.0)
    labor_hours = (max(float(setup_time_min), 0.0) + max(float(postprocess_time_min), 0.0)) / 60.0
    labor_cost = labor_hours * max(float(labor_rate_per_h), 0.0)
    scrap_multiplier = 1.0 + max(float(scrap_allowance_pct), 0.0) / 100.0
    subtotal = (material_cost + machine_cost + labor_cost) * scrap_multiplier
    quoted_price = subtotal * (1.0 + max(float(margin_pct), 0.0) / 100.0)

    volume_cm3 = max(float(metrics.get("material_volume_mm3", 0.0)), 0.0) * max(layer_count, 1) / 1000.0
    build_rate_cm3_h = volume_cm3 / build_hours if build_hours > 0 else 0.0
    volumetric_flow_mm3_s = (
        max(float(print_speed_mm_s), 0.0)
        * max(float(layer_height_mm), 0.0)
        * max(float(nozzle_diameter_mm), 0.0)
    )
    cost_per_part = quoted_price
    cost_per_cm3 = quoted_price / volume_cm3 if volume_cm3 > 0 else math.inf

    return {
        "build_hours": build_hours,
        "material_cost": material_cost,
        "machine_cost": machine_cost,
        "labor_cost": labor_cost,
        "subtotal_with_scrap": subtotal,
        "quoted_price": quoted_price,
        "cost_per_part": cost_per_part,
        "cost_per_cm3": cost_per_cm3,
        "volume_cm3": volume_cm3,
        "build_rate_cm3_h": build_rate_cm3_h,
        "volumetric_flow_mm3_s": volumetric_flow_mm3_s,
        "scrap_allowance_pct": max(float(scrap_allowance_pct), 0.0),
        "margin_pct": max(float(margin_pct), 0.0),
    }


def classify_program_risk(readiness: dict[str, Any], economics: dict[str, float]) -> str:
    """Convert engineering and cost signals into a buyer-facing risk label."""
    if readiness.get("status") == "Blocked":
        return "Blocked"
    if economics["volumetric_flow_mm3_s"] > 14.0:
        return "High"
    if readiness.get("warnings", 0) >= 2 or economics["build_hours"] > 12.0:
        return "Medium"
    return "Low"


def generate_job_dossier_markdown(
    *,
    job_name: str,
    params: dict[str, Any],
    metrics: dict[str, Any],
    readiness: dict[str, Any],
    economics: dict[str, float],
    full_time_text: str,
    full_weight_g: float,
    layer_count: int,
    risk: str,
) -> str:
    """Build a concise production dossier suitable for customers and managers."""
    issues = readiness.get("issues", [])
    if issues:
        issue_lines = [
            f"- {issue.severity.upper()}: {issue.title} - {issue.detail} Action: {issue.action}"
            for issue in issues
        ]
    else:
        issue_lines = ["- PASS: Automated manufacturability checks passed."]

    return "\n".join([
        f"# MiniSlicer Job Dossier: {job_name}",
        "",
        "## Executive Summary",
        f"- Readiness: {readiness.get('status', 'Review')} ({readiness.get('score', 0)}/100)",
        f"- Program risk: {risk}",
        f"- Estimated build time: {full_time_text}",
        f"- Estimated material: {full_weight_g:.2f} g",
        f"- Estimated quote: ${economics['quoted_price']:.2f}",
        "",
        "## Manufacturing Plan",
        f"- Process: {params.get('process_mode', 'Unknown')}",
        f"- Profile: {params.get('profile', 'Custom')}",
        f"- Geometry source: {params.get('shape_type', 'Unknown')}",
        f"- Layers: {layer_count}",
        f"- Infill: {params.get('infill_pattern', 'Unknown')} at "
        f"{params.get('infill_spacing_mm', 0):.2f} mm",
        f"- Perimeters: {params.get('perimeter_count', 0)} at "
        f"{params.get('perimeter_spacing_mm', 0):.2f} mm",
        "",
        "## Production KPIs",
        f"- Path efficiency: {metrics.get('path_efficiency_pct', 0):.1f}%",
        f"- Build rate: {economics['build_rate_cm3_h']:.2f} cm3/h",
        f"- Material volume: {economics['volume_cm3']:.2f} cm3",
        f"- Volumetric flow: {economics['volumetric_flow_mm3_s']:.2f} mm3/s",
        f"- Cost per cm3: ${economics['cost_per_cm3']:.2f}",
        "",
        "## Cost Model",
        f"- Material: ${economics['material_cost']:.2f}",
        f"- Machine time: ${economics['machine_cost']:.2f}",
        f"- Labor: ${economics['labor_cost']:.2f}",
        f"- Scrap allowance: {economics['scrap_allowance_pct']:.1f}%",
        f"- Margin: {economics['margin_pct']:.1f}%",
        f"- Quote total: ${economics['quoted_price']:.2f}",
        "",
        "## Findings",
        *issue_lines,
        "",
        "Planning output only. Validate machine-specific process limits, fixture strategy, "
        "material batch, and start/end code before production release.",
    ])


def generate_job_dossier_html(markdown_text: str) -> str:
    """Wrap the dossier text in a simple standalone HTML document."""
    escaped = (
        markdown_text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return "\n".join([
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\">",
        "<title>MiniSlicer Job Dossier</title>",
        "<style>",
        "body{font-family:Inter,Segoe UI,Arial,sans-serif;margin:40px;color:#172033;line-height:1.5}",
        "pre{white-space:pre-wrap;background:#f5f7fb;border:1px solid #d7dde8;padding:24px;border-radius:8px}",
        "</style></head><body>",
        "<pre>",
        escaped,
        "</pre>",
        "</body></html>",
    ])
