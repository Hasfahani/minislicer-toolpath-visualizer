"""Business and manufacturability analysis for MiniSlicer jobs."""

from __future__ import annotations

import math
from typing import Any

PRIORITY_RANK = {
    "Critical": 5,
    "High": 4,
    "Medium": 3,
    "Low": 2,
    "Ready": 1,
}


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
    batch_quantity: int = 1,
) -> dict[str, float]:
    """Return quote-ready production economics and process KPIs.

    The estimates are intentionally transparent: every number comes from path
    length, material usage, motion time, and user-visible rate assumptions.
    """
    quantity = max(int(batch_quantity), 1)
    build_hours = max(float(full_time_s), 0.0) / 3600.0
    material_cost = max(float(full_weight_g), 0.0) / 1000.0 * max(float(material_cost_per_kg), 0.0)
    machine_cost = build_hours * max(float(machine_rate_per_h), 0.0)
    setup_labor_cost = max(float(setup_time_min), 0.0) / 60.0 * max(float(labor_rate_per_h), 0.0)
    postprocess_labor_cost = (
        max(float(postprocess_time_min), 0.0) / 60.0 * max(float(labor_rate_per_h), 0.0)
    )
    labor_cost = setup_labor_cost + postprocess_labor_cost
    scrap_multiplier = 1.0 + max(float(scrap_allowance_pct), 0.0) / 100.0
    variable_unit_cost = material_cost + machine_cost + postprocess_labor_cost
    batch_subtotal_before_scrap = variable_unit_cost * quantity + setup_labor_cost
    subtotal = batch_subtotal_before_scrap * scrap_multiplier
    quoted_batch_price = subtotal * (1.0 + max(float(margin_pct), 0.0) / 100.0)
    quoted_price = quoted_batch_price / quantity

    volume_cm3 = max(float(metrics.get("material_volume_mm3", 0.0)), 0.0) * max(layer_count, 1) / 1000.0
    build_rate_cm3_h = volume_cm3 / build_hours if build_hours > 0 else 0.0
    volumetric_flow_mm3_s = (
        max(float(print_speed_mm_s), 0.0)
        * max(float(layer_height_mm), 0.0)
        * max(float(nozzle_diameter_mm), 0.0)
    )
    cost_per_part = quoted_price
    cost_per_cm3 = quoted_price / volume_cm3 if volume_cm3 > 0 else math.inf
    batch_machine_hours = build_hours * quantity

    return {
        "batch_quantity": float(quantity),
        "build_hours": build_hours,
        "batch_machine_hours": batch_machine_hours,
        "material_cost": material_cost,
        "machine_cost": machine_cost,
        "setup_labor_cost": setup_labor_cost,
        "postprocess_labor_cost": postprocess_labor_cost,
        "labor_cost": labor_cost,
        "variable_unit_cost": variable_unit_cost,
        "subtotal_with_scrap": subtotal,
        "quoted_price": quoted_price,
        "quoted_batch_price": quoted_batch_price,
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


def assess_commercial_fit(
    *,
    economics: dict[str, float],
    target_unit_price: float,
    max_lead_time_h: float,
) -> dict[str, Any]:
    """Assess price and lead-time fit against buyer-facing targets."""
    findings: list[str] = []
    target = max(float(target_unit_price), 0.0)
    lead_limit = max(float(max_lead_time_h), 0.0)
    unit_price = float(economics["quoted_price"])
    batch_hours = float(economics.get("batch_machine_hours", economics["build_hours"]))

    price_delta_pct = 0.0
    if target > 0:
        price_delta_pct = 100.0 * (unit_price - target) / target
        if price_delta_pct > 10:
            findings.append(f"Unit price is {price_delta_pct:.1f}% above target.")
        elif price_delta_pct < -10:
            findings.append(f"Unit price is {abs(price_delta_pct):.1f}% below target.")

    lead_time_delta_h = batch_hours - lead_limit if lead_limit > 0 else 0.0
    if lead_limit > 0 and lead_time_delta_h > 0:
        findings.append(f"Batch machine time exceeds the target by {lead_time_delta_h:.1f} h.")

    status = "Fit"
    if any("above target" in finding or "exceeds" in finding for finding in findings):
        status = "Review"
    if target > 0 and price_delta_pct > 35:
        status = "No-bid"
    if lead_limit > 0 and lead_time_delta_h > max(lead_limit * 0.5, 8.0):
        status = "No-bid"

    return {
        "status": status,
        "target_unit_price": target,
        "max_lead_time_h": lead_limit,
        "price_delta_pct": price_delta_pct,
        "lead_time_delta_h": lead_time_delta_h,
        "findings": findings,
    }


def compute_launch_score(
    *,
    readiness: dict[str, Any],
    risk: str,
    commercial_fit: dict[str, Any],
) -> int:
    """Compute a market-launch score from technical and commercial readiness."""
    score = int(readiness.get("score", 0))
    score -= {"Low": 0, "Medium": 10, "High": 24, "Blocked": 45}.get(risk, 12)
    score -= {"Fit": 0, "Review": 10, "No-bid": 30}.get(commercial_fit.get("status", "Review"), 10)
    return max(0, min(100, score))


def build_launch_recommendations(
    *,
    readiness: dict[str, Any],
    commercial_fit: dict[str, Any],
    metrics: dict[str, Any],
    economics: dict[str, float],
    quality_scorecard: dict[str, Any],
    production_enabled: bool,
    fits_plate: bool,
    travel_ratio_pct: float,
    effective_spacing_mm: float,
    nozzle_diameter_mm: float,
    layer_count: int,
    recommended_pattern: str | None = None,
) -> list[dict[str, Any]]:
    """Return ranked, operator-facing recommendations for improving a job."""
    recommendations: list[dict[str, Any]] = []

    def add(
        *,
        priority: str,
        area: str,
        title: str,
        action: str,
        impact: str,
        owner: str,
    ) -> None:
        recommendations.append({
            "priority": priority,
            "priority_score": PRIORITY_RANK.get(priority, 0),
            "area": area,
            "title": title,
            "action": action,
            "impact": impact,
            "owner": owner,
        })

    for issue in readiness.get("issues", []):
        severity = str(_issue_value(issue, "severity", "info"))
        priority = {"blocker": "Critical", "warning": "High", "info": "Medium"}.get(
            severity, "Medium"
        )
        add(
            priority=priority,
            area="Readiness",
            title=str(_issue_value(issue, "title", "Readiness finding")),
            action=str(_issue_value(issue, "action", "Review the finding.")),
            impact=str(_issue_value(issue, "detail", "Automated readiness finding.")),
            owner="Engineering",
        )

    has_plate_overflow = any(row["title"] == "Build plate overflow" for row in recommendations)
    if not fits_plate and not has_plate_overflow:
        add(
            priority="Critical",
            area="Geometry",
            title="Build plate overflow",
            action="Center the part, reduce scale, or enable fit-inside-plate.",
            impact="Production export remains unsafe while geometry sits outside the plate.",
            owner="Engineering",
        )

    commercial_status = str(commercial_fit.get("status", "Review"))
    if commercial_status != "Fit":
        findings = commercial_fit.get("findings") or ["Commercial targets need review."]
        for finding in findings:
            add(
                priority="High" if commercial_status == "No-bid" else "Medium",
                area="Commercial",
                title=f"Commercial fit is {commercial_status}",
                action="Tune batch size, cost assumptions, target price, or toolpath time.",
                impact=str(finding),
                owner="Commercial",
            )

    if not production_enabled:
        if readiness.get("status") == "Blocked":
            action = "Clear readiness blockers before generating machine-profiled G-code."
            impact = "Production G-code is guarded until engineering checks pass."
        elif layer_count > 600:
            action = "Reduce model height or increase layer height, then regenerate the package."
            impact = (
                "Full-build export is capped at 600 layers; "
                f"this job has {layer_count:,} layers."
            )
        else:
            action = "Use FDM process mode and a valid machine profile for production G-code."
            impact = "Preview exports remain available, but production G-code is guarded."
        add(
            priority="High",
            area="Export",
            title="Production export guarded",
            action=action,
            impact=impact,
            owner="Manufacturing",
        )

    efficiency = float(metrics.get("path_efficiency_pct", 0.0))
    if travel_ratio_pct > 30 or efficiency < 72:
        pattern_text = f" and compare against {recommended_pattern}" if recommended_pattern else ""
        add(
            priority="High" if travel_ratio_pct > 35 else "Medium",
            area="Motion",
            title="Motion efficiency needs attention",
            action=f"Keep path optimization enabled{pattern_text}.",
            impact=f"{travel_ratio_pct:.1f}% travel share and {efficiency:.1f}% path efficiency.",
            owner="Process",
        )

    volumetric_flow = float(economics.get("volumetric_flow_mm3_s", 0.0))
    if volumetric_flow > 14.0:
        add(
            priority="High",
            area="Process",
            title="Volumetric flow above safe default",
            action="Reduce speed, layer height, or nozzle width unless the hotend is qualified.",
            impact=f"{volumetric_flow:.1f} mm3/s requested flow.",
            owner="Process",
        )
    elif volumetric_flow > 10.0:
        add(
            priority="Medium",
            area="Process",
            title="Volumetric flow elevated",
            action="Confirm filament and hotend can sustain the selected flow rate.",
            impact=f"{volumetric_flow:.1f} mm3/s requested flow.",
            owner="Process",
        )

    if effective_spacing_mm > nozzle_diameter_mm * 12:
        add(
            priority="Medium",
            area="Strength",
            title="Sparse infill may under-support the part",
            action="Use density mode or reduce infill spacing.",
            impact=(
                f"{effective_spacing_mm:.2f} mm spacing with a "
                f"{nozzle_diameter_mm:.2f} mm nozzle."
            ),
            owner="Engineering",
        )

    for row in quality_scorecard.get("rows", []):
        score = int(row.get("score", 0))
        if score < 75:
            add(
                priority="Medium",
                area="Quality",
                title=f"Raise {row.get('area', 'quality')} score",
                action=f"Review signal: {row.get('signal', 'No signal available')}.",
                impact=f"{score}/100, status {row.get('status', 'Review')}.",
                owner="Program",
            )

    if not recommendations:
        add(
            priority="Ready",
            area="Release",
            title="Package ready for sign-off",
            action="Export the dossier, CSV, JSON, SVG, and any enabled production G-code.",
            impact="No automated blockers or high-priority guardrail failures were found.",
            owner="Program",
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in recommendations:
        key = (str(row["area"]), str(row["title"]))
        if key not in seen:
            deduped.append(row)
            seen.add(key)

    return sorted(
        deduped,
        key=lambda item: (-int(item["priority_score"]), str(item["area"]), str(item["title"])),
    )


def build_batch_scenarios(
    *,
    metrics: dict[str, Any],
    layer_count: int,
    layer_height_mm: float,
    nozzle_diameter_mm: float,
    print_speed_mm_s: float,
    full_time_s: float,
    full_weight_g: float,
    material_cost_per_kg: float,
    machine_rate_per_h: float,
    labor_rate_per_h: float,
    setup_time_min: float,
    postprocess_time_min: float,
    scrap_allowance_pct: float,
    margin_pct: float,
    target_unit_price: float,
    max_lead_time_h: float,
    quantities: list[int] | tuple[int, ...] | None = None,
) -> list[dict[str, Any]]:
    """Return quote and lead-time scenarios for common batch quantities."""
    raw_quantities = quantities or (1, 5, 10, 25, 50)
    scenario_quantities = sorted({max(1, int(quantity)) for quantity in raw_quantities})
    rows: list[dict[str, Any]] = []

    for quantity in scenario_quantities:
        scenario_economics = estimate_job_economics(
            metrics=metrics,
            layer_count=layer_count,
            layer_height_mm=layer_height_mm,
            nozzle_diameter_mm=nozzle_diameter_mm,
            print_speed_mm_s=print_speed_mm_s,
            full_time_s=full_time_s,
            full_weight_g=full_weight_g,
            material_cost_per_kg=material_cost_per_kg,
            machine_rate_per_h=machine_rate_per_h,
            labor_rate_per_h=labor_rate_per_h,
            setup_time_min=setup_time_min,
            postprocess_time_min=postprocess_time_min,
            scrap_allowance_pct=scrap_allowance_pct,
            margin_pct=margin_pct,
            batch_quantity=quantity,
        )
        fit = assess_commercial_fit(
            economics=scenario_economics,
            target_unit_price=target_unit_price,
            max_lead_time_h=max_lead_time_h,
        )
        rows.append({
            "quantity": quantity,
            "unit_quote": scenario_economics["quoted_price"],
            "batch_quote": scenario_economics["quoted_batch_price"],
            "batch_machine_hours": scenario_economics["batch_machine_hours"],
            "setup_per_part": scenario_economics["setup_labor_cost"] / quantity,
            "target_delta_pct": fit["price_delta_pct"],
            "lead_time_delta_h": fit["lead_time_delta_h"],
            "status": fit["status"],
        })

    return rows


def build_release_checklist(
    *,
    readiness: dict[str, Any],
    commercial_fit: dict[str, Any],
    production_enabled: bool,
    plan_fingerprint: str,
    export_segment_count: int,
) -> list[dict[str, str]]:
    """Return a compact release checklist for operator review."""
    return [
        {
            "item": "Engineering gates",
            "state": "Pass" if readiness.get("status") != "Blocked" else "Hold",
            "detail": (
                f"{readiness.get('score', 0)}/100 readiness, "
                f"{readiness.get('blockers', 0)} blockers"
            ),
        },
        {
            "item": "Commercial guardrails",
            "state": "Pass" if commercial_fit.get("status") == "Fit" else "Review",
            "detail": str(commercial_fit.get("status", "Review")),
        },
        {
            "item": "Production export",
            "state": "Ready" if production_enabled else "Guarded",
            "detail": f"{export_segment_count:,} full-build moves available",
        },
        {
            "item": "Traceability",
            "state": "Locked" if len(str(plan_fingerprint).strip()) >= 12 else "Review",
            "detail": f"Plan ID {plan_fingerprint or 'missing'}",
        },
        {
            "item": "Segment ledger",
            "state": "Ready" if export_segment_count > 0 else "Review",
            "detail": "CSV and JSON exports include stable segment columns",
        },
    ]


def build_optimization_playbook(
    *,
    current_pattern: str,
    pattern_ranking: list[dict[str, Any]],
    metrics: dict[str, Any],
    economics: dict[str, float],
    batch_scenarios: list[dict[str, Any]],
    print_speed_mm_s: float,
    layer_height_mm: float,
    nozzle_diameter_mm: float,
    travel_ratio_pct: float,
    production_enabled: bool,
) -> list[dict[str, Any]]:
    """Return quantified what-if levers for improving launch outcomes."""
    rows: list[dict[str, Any]] = []

    def add(
        *,
        lever: str,
        current: str,
        proposed: str,
        estimated_delta: str,
        confidence: str,
        impact_score: int,
    ) -> None:
        rows.append({
            "lever": lever,
            "current": current,
            "proposed": proposed,
            "estimated_delta": estimated_delta,
            "confidence": confidence,
            "impact_score": int(impact_score),
        })

    current_rank = next(
        (row for row in pattern_ranking if row.get("pattern") == current_pattern),
        None,
    )
    best_pattern = pattern_ranking[0] if pattern_ranking else None
    if best_pattern and current_rank:
        current_motion = float(current_rank["path_mm"]) + float(current_rank["travel_mm"])
        best_motion = float(best_pattern["path_mm"]) + float(best_pattern["travel_mm"])
        saving_pct = 100.0 * max(0.0, current_motion - best_motion) / current_motion
        if best_pattern["pattern"] != current_pattern and saving_pct >= 1.0:
            add(
                lever="Pattern switch",
                current=current_pattern,
                proposed=str(best_pattern["pattern"]),
                estimated_delta=f"{saving_pct:.1f}% less active-layer motion",
                confidence="High",
                impact_score=90,
            )
        else:
            add(
                lever="Pattern selection",
                current=current_pattern,
                proposed="Keep current pattern",
                estimated_delta="Current pattern is already near the ranked best",
                confidence="High",
                impact_score=45,
            )

    current_qty = max(1, int(economics.get("batch_quantity", 1)))
    current_scenario = next(
        (row for row in batch_scenarios if int(row["quantity"]) == current_qty),
        None,
    )
    best_batch = min(batch_scenarios, key=lambda row: float(row["unit_quote"]), default=None)
    if current_scenario and best_batch:
        current_quote = float(current_scenario["unit_quote"])
        best_quote = float(best_batch["unit_quote"])
        saving = max(0.0, current_quote - best_quote)
        if int(best_batch["quantity"]) != current_qty and saving > 0:
            saving_pct = 100.0 * saving / current_quote if current_quote > 0 else 0.0
            add(
                lever="Batch sizing",
                current=f"{current_qty} pcs",
                proposed=f"{int(best_batch['quantity'])} pcs",
                estimated_delta=f"${saving:.2f}/part lower quote ({saving_pct:.1f}%)",
                confidence="Medium",
                impact_score=78,
            )

    flow = float(economics.get("volumetric_flow_mm3_s", 0.0))
    bead_area = max(float(layer_height_mm) * float(nozzle_diameter_mm), 0.0)
    default_safe_speed = 10.0 / bead_area if bead_area > 0 else print_speed_mm_s
    warning_speed = 14.0 / bead_area if bead_area > 0 else print_speed_mm_s
    if flow > 14.0:
        add(
            lever="Flow envelope",
            current=f"{print_speed_mm_s:.0f} mm/s, {flow:.1f} mm3/s",
            proposed=f"{warning_speed:.0f} mm/s or lower",
            estimated_delta="Brings flow back under the high-risk warning band",
            confidence="High",
            impact_score=88,
        )
    elif flow < 8.0 and travel_ratio_pct < 25:
        proposed_speed = min(float(print_speed_mm_s) * 1.15, default_safe_speed)
        if proposed_speed > float(print_speed_mm_s) + 1.0:
            time_gain_pct = 100.0 * (1.0 - float(print_speed_mm_s) / proposed_speed)
            add(
                lever="Speed tuning",
                current=f"{print_speed_mm_s:.0f} mm/s",
                proposed=f"{proposed_speed:.0f} mm/s",
                estimated_delta=f"Up to {time_gain_pct:.1f}% shorter extrusion time",
                confidence="Medium",
                impact_score=64,
            )

    if travel_ratio_pct > 22:
        add(
            lever="Travel reduction",
            current=f"{travel_ratio_pct:.1f}% travel share",
            proposed="Keep optimization on and compare low-travel patterns",
            estimated_delta="Reduces non-extruding motion and idle machine time",
            confidence="Medium",
            impact_score=70,
        )

    if production_enabled:
        add(
            lever="Release package",
            current="Guardrails clear",
            proposed="Export dossier plus production G-code",
            estimated_delta="Ready for controlled machine-specific review",
            confidence="High",
            impact_score=58,
        )
    else:
        add(
            lever="Release package",
            current="Production export guarded",
            proposed="Clear release gates before G-code handoff",
            estimated_delta="Prevents unsafe or incomplete production release",
            confidence="High",
            impact_score=86,
        )

    return sorted(rows, key=lambda row: -int(row["impact_score"]))


def estimate_ded_process(
    *,
    metrics: dict[str, Any],
    material_density_g_cm3: float,
    full_weight_g: float,
    full_time_s: float,
    model_height_mm: float,
    bbox_width_mm: float,
    bbox_depth_mm: float,
    layer_height_mm: float,
    bead_width_mm: float,
    print_speed_mm_s: float,
    wire_diameter_mm: float,
    wire_feed_m_min: float,
    arc_current_a: float,
    arc_voltage_v: float,
    arc_efficiency_pct: float,
    deposition_efficiency_pct: float,
    robot_utilization_pct: float,
    machining_allowance_pct: float,
    billet_buy_to_fly: float,
    conventional_lead_time_weeks: float,
    machine_capacity_h_week: float,
    envelope_x_mm: float,
    envelope_y_mm: float,
    envelope_z_mm: float,
) -> dict[str, Any]:
    """Estimate wire-arc DED process, energy, feedstock, and lead-time KPIs."""
    density = max(float(material_density_g_cm3), 0.001)
    net_mass_kg = max(float(full_weight_g), 0.0) / 1000.0
    deposition_eff = max(float(deposition_efficiency_pct), 0.1) / 100.0
    arc_eff = max(float(arc_efficiency_pct), 0.0) / 100.0
    utilization = max(float(robot_utilization_pct), 0.1) / 100.0
    allowance_multiplier = 1.0 + max(float(machining_allowance_pct), 0.0) / 100.0
    near_net_mass_kg = net_mass_kg * allowance_multiplier

    wire_area_mm2 = math.pi * (max(float(wire_diameter_mm), 0.001) / 2.0) ** 2
    wire_feed_mm_s = max(float(wire_feed_m_min), 0.0) * 1000.0 / 60.0
    wire_volume_mm3_s = wire_area_mm2 * wire_feed_mm_s
    wire_mass_kg_h = wire_volume_mm3_s * density * 0.0036
    deposited_kg_h = wire_mass_kg_h * deposition_eff

    deposition_time_h = near_net_mass_kg / deposited_kg_h if deposited_kg_h > 0 else math.inf
    toolpath_time_h = max(float(full_time_s), 0.0) / 3600.0
    cell_time_h = max(deposition_time_h, toolpath_time_h) / utilization
    deposited_mass_kg = near_net_mass_kg
    wire_required_kg = deposited_mass_kg / deposition_eff if deposition_eff > 0 else math.inf

    arc_power_kw = max(float(arc_current_a), 0.0) * max(float(arc_voltage_v), 0.0) / 1000.0
    effective_arc_power_kw = arc_power_kw * arc_eff
    arc_energy_kwh = arc_power_kw * deposition_time_h if math.isfinite(deposition_time_h) else math.inf
    specific_energy_kwh_kg = arc_energy_kwh / deposited_mass_kg if deposited_mass_kg > 0 else 0.0
    heat_input_kj_mm = (
        max(float(arc_current_a), 0.0)
        * max(float(arc_voltage_v), 0.0)
        * arc_eff
        / (max(float(print_speed_mm_s), 0.001) * 1000.0)
    )

    bead_area_mm2 = (math.pi / 4.0) * max(float(layer_height_mm), 0.0) * max(float(bead_width_mm), 0.0)
    path_deposition_kg_h = max(float(print_speed_mm_s), 0.0) * bead_area_mm2 * density * 0.0036
    required_wire_feed_m_min = (
        (path_deposition_kg_h / deposition_eff)
        / (wire_area_mm2 * density * 0.0036)
        * 60.0
        / 1000.0
        if wire_area_mm2 > 0 and deposition_eff > 0 else math.inf
    )
    feed_supply_ratio = (
        wire_feed_m_min / required_wire_feed_m_min
        if required_wire_feed_m_min and math.isfinite(required_wire_feed_m_min) else math.inf
    )

    billet_mass_kg = net_mass_kg * max(float(billet_buy_to_fly), 1.0)
    material_saved_kg = max(0.0, billet_mass_kg - wire_required_kg)
    material_saved_pct = 100.0 * material_saved_kg / billet_mass_kg if billet_mass_kg > 0 else 0.0

    additive_lead_weeks = cell_time_h / max(float(machine_capacity_h_week), 0.001)
    lead_time_saved_weeks = max(0.0, float(conventional_lead_time_weeks) - additive_lead_weeks)
    lead_time_compression_pct = (
        100.0 * lead_time_saved_weeks / float(conventional_lead_time_weeks)
        if conventional_lead_time_weeks > 0 else 0.0
    )

    envelope_fit = (
        max(float(bbox_width_mm), 0.0) <= max(float(envelope_x_mm), 0.0)
        and max(float(bbox_depth_mm), 0.0) <= max(float(envelope_y_mm), 0.0)
        and max(float(model_height_mm), 0.0) <= max(float(envelope_z_mm), 0.0)
    )
    z_utilization_pct = 100.0 * max(float(model_height_mm), 0.0) / max(float(envelope_z_mm), 0.001)
    footprint_utilization_pct = 100.0 * max(float(bbox_width_mm), 0.0) * max(float(bbox_depth_mm), 0.0) / max(
        float(envelope_x_mm) * float(envelope_y_mm),
        0.001,
    )

    return {
        "enabled": True,
        "net_mass_kg": net_mass_kg,
        "near_net_mass_kg": near_net_mass_kg,
        "wire_required_kg": wire_required_kg,
        "wire_mass_kg_h": wire_mass_kg_h,
        "deposited_kg_h": deposited_kg_h,
        "deposition_time_h": deposition_time_h,
        "toolpath_time_h": toolpath_time_h,
        "cell_time_h": cell_time_h,
        "arc_power_kw": arc_power_kw,
        "effective_arc_power_kw": effective_arc_power_kw,
        "arc_energy_kwh": arc_energy_kwh,
        "specific_energy_kwh_kg": specific_energy_kwh_kg,
        "heat_input_kj_mm": heat_input_kj_mm,
        "bead_area_mm2": bead_area_mm2,
        "path_deposition_kg_h": path_deposition_kg_h,
        "required_wire_feed_m_min": required_wire_feed_m_min,
        "feed_supply_ratio": feed_supply_ratio,
        "billet_mass_kg": billet_mass_kg,
        "material_saved_kg": material_saved_kg,
        "material_saved_pct": material_saved_pct,
        "additive_lead_weeks": additive_lead_weeks,
        "lead_time_saved_weeks": lead_time_saved_weeks,
        "lead_time_compression_pct": lead_time_compression_pct,
        "envelope_fit": envelope_fit,
        "z_utilization_pct": z_utilization_pct,
        "footprint_utilization_pct": footprint_utilization_pct,
        "bbox_width_mm": float(bbox_width_mm),
        "bbox_depth_mm": float(bbox_depth_mm),
        "model_height_mm": float(model_height_mm),
        "envelope_x_mm": float(envelope_x_mm),
        "envelope_y_mm": float(envelope_y_mm),
        "envelope_z_mm": float(envelope_z_mm),
        "material_volume_cm3": max(float(metrics.get("material_volume_mm3", 0.0)), 0.0) / 1000.0,
    }


def build_ded_recommendations(ded: dict[str, Any]) -> list[dict[str, Any]]:
    """Return launch recommendations from the DED process model."""
    recommendations: list[dict[str, Any]] = []

    def add(priority: str, title: str, action: str, impact: str) -> None:
        recommendations.append({
            "priority": priority,
            "priority_score": PRIORITY_RANK.get(priority, 0),
            "area": "DED process",
            "title": title,
            "action": action,
            "impact": impact,
            "owner": "Process",
        })

    if not ded.get("envelope_fit", False):
        add(
            "Critical",
            "DED envelope overflow",
            "Reduce scale, change orientation, segment the part, or select a larger cell.",
            "The current bounding box exceeds the configured DED build envelope.",
        )

    if float(ded.get("feed_supply_ratio", 1.0)) < 0.9:
        add(
            "High",
            "Wire feed cannot support selected bead speed",
            "Lower travel speed, reduce bead area, or increase validated wire feed.",
            (
                f"Configured feed supplies {float(ded.get('feed_supply_ratio', 0.0)):.2f}x "
                "of the estimated wire demand."
            ),
        )

    if float(ded.get("heat_input_kj_mm", 0.0)) > 1.2:
        add(
            "High",
            "High heat input",
            "Reduce current/voltage, increase travel speed, or add interpass controls.",
            f"Estimated heat input is {float(ded.get('heat_input_kj_mm', 0.0)):.2f} kJ/mm.",
        )
    elif float(ded.get("heat_input_kj_mm", 0.0)) < 0.15:
        add(
            "Medium",
            "Low heat input",
            "Confirm fusion quality with coupons before quoting the build.",
            f"Estimated heat input is {float(ded.get('heat_input_kj_mm', 0.0)):.2f} kJ/mm.",
        )

    if float(ded.get("z_utilization_pct", 0.0)) > 90:
        add(
            "Medium",
            "Build height near cell limit",
            "Review torch clearance, fixturing, and robot reach before release.",
            f"Z utilization is {float(ded.get('z_utilization_pct', 0.0)):.1f}%.",
        )

    return recommendations


def assess_manufacturing_partner_fit(
    *,
    ded_analysis: dict[str, Any] | None,
    economics: dict[str, float],
    commercial_fit: dict[str, Any],
    application_type: str,
    conventional_route: str,
    urgency: str,
    qualification_level: str,
    material_strategy: str,
    finish_tolerance_mm: float,
    annual_quantity: int,
    ndt_required: bool,
    redesign_required: bool,
) -> dict[str, Any]:
    """Score fit for a high-mix large-metal-AM manufacturing service workflow."""
    ded = ded_analysis or {}
    lead_compression = float(ded.get("lead_time_compression_pct", 0.0))
    material_saved = float(ded.get("material_saved_pct", 0.0))
    envelope_fit = bool(ded.get("envelope_fit", True))
    cell_time_h = float(ded.get("cell_time_h", economics.get("build_hours", 0.0)))
    unit_quote = float(economics.get("quoted_price", 0.0))
    quantity = max(int(annual_quantity), 1)

    route_multiplier = {
        "Casting": 1.65,
        "Forging": 1.85,
        "Machining from billet": 1.45,
        "Weld fabrication": 1.20,
    }.get(conventional_route, 1.25)
    urgency_multiplier = {
        "Normal procurement": 1.00,
        "Expedite": 1.12,
        "Line-down / launch critical": 1.28,
    }.get(urgency, 1.00)
    qualification_multiplier = {
        "Prototype": 0.10,
        "Industrial": 0.18,
        "Aerospace / safety critical": 0.35,
    }.get(qualification_level, 0.18)
    inspection_multiplier = 0.08 if ndt_required else 0.03
    redesign_multiplier = 0.12 if redesign_required else 0.04

    conventional_unit_estimate = unit_quote * route_multiplier * urgency_multiplier
    qualification_cost = unit_quote * qualification_multiplier
    inspection_cost = unit_quote * inspection_multiplier
    redesign_cost = unit_quote * redesign_multiplier
    service_unit_estimate = unit_quote + qualification_cost + inspection_cost + redesign_cost
    value_delta = conventional_unit_estimate - service_unit_estimate
    value_delta_pct = (
        100.0 * value_delta / conventional_unit_estimate
        if conventional_unit_estimate > 0 else 0.0
    )

    lead_score = _clamp_score(lead_compression)
    material_score = _clamp_score(material_saved)
    route_score = {
        "Casting": 82,
        "Forging": 88,
        "Machining from billet": 76,
        "Weld fabrication": 64,
    }.get(conventional_route, 70)
    urgency_score = {
        "Normal procurement": 58,
        "Expedite": 78,
        "Line-down / launch critical": 94,
    }.get(urgency, 58)
    quantity_score = 82 if quantity <= 5 else 68 if quantity <= 25 else 44
    tolerance_penalty = 16 if finish_tolerance_mm < 0.15 else 8 if finish_tolerance_mm < 0.35 else 0
    qualification_penalty = {
        "Prototype": 0,
        "Industrial": 8,
        "Aerospace / safety critical": 20,
    }.get(qualification_level, 8)
    multi_material_bonus = 8 if material_strategy != "Single material" else 0
    route_fit_score = round(
        0.23 * lead_score
        + 0.20 * material_score
        + 0.17 * route_score
        + 0.15 * urgency_score
        + 0.12 * quantity_score
        + 0.13 * max(0, min(100, value_delta_pct + 50))
        + multi_material_bonus
        - tolerance_penalty
        - qualification_penalty
    )
    if not envelope_fit:
        route_fit_score -= 35
    if commercial_fit.get("status") == "No-bid":
        route_fit_score -= 20
    route_fit_score = max(0, min(100, route_fit_score))

    if route_fit_score >= 82:
        verdict = "Strong candidate"
    elif route_fit_score >= 65:
        verdict = "Engineering review"
    elif route_fit_score >= 45:
        verdict = "Niche / conditional"
    else:
        verdict = "Poor fit"

    deliverables = [
        "Customer geometry and requirements intake",
        "DfAM redesign review" if redesign_required else "Geometry manufacturability review",
        "DED route simulation and build envelope check",
        "Wire, energy, lead-time, and material-savings estimate",
        "Post-machining and inspection plan",
    ]
    if ndt_required:
        deliverables.append("NDT / inspection evidence package")
    if material_strategy != "Single material":
        deliverables.append("Material transition and wear-zone strategy")
    if qualification_level == "Aerospace / safety critical":
        deliverables.append("Qualification coupon and traceability plan")

    blockers: list[str] = []
    if not envelope_fit:
        blockers.append("Part exceeds configured DED build envelope.")
    if finish_tolerance_mm < 0.1:
        blockers.append("Tolerance is tighter than a near-net DED process should promise directly.")
    if cell_time_h > 200:
        blockers.append("Cell time is high enough to require segmentation or fixture strategy review.")

    return {
        "score": route_fit_score,
        "verdict": verdict,
        "application_type": application_type,
        "conventional_route": conventional_route,
        "urgency": urgency,
        "qualification_level": qualification_level,
        "material_strategy": material_strategy,
        "service_unit_estimate": service_unit_estimate,
        "conventional_unit_estimate": conventional_unit_estimate,
        "value_delta": value_delta,
        "value_delta_pct": value_delta_pct,
        "qualification_cost": qualification_cost,
        "inspection_cost": inspection_cost,
        "redesign_cost": redesign_cost,
        "annual_quantity": float(quantity),
        "deliverables": deliverables,
        "blockers": blockers,
        "signals": [
            f"{lead_compression:.1f}% lead-time compression",
            f"{material_saved:.1f}% material reduction versus billet assumption",
            f"{quantity} pcs annual demand",
            f"{qualification_level} qualification burden",
        ],
    }


def estimate_thermal_management(
    *,
    ded_analysis: dict[str, Any],
    layer_count: int,
    preheat_temp_c: float,
    interpass_limit_c: float,
    cooling_rate_c_min: float,
    heat_retention_pct: float,
    specific_heat_j_kg_c: float = 500.0,
) -> dict[str, Any]:
    """Estimate interpass temperature risk and dwell time for a DED build."""
    layers = max(int(layer_count), 1)
    mass_kg = max(float(ded_analysis.get("near_net_mass_kg", 0.0)), 0.001)
    heat_capacity_kj_c = mass_kg * max(float(specific_heat_j_kg_c), 1.0) / 1000.0
    energy_kj_per_layer = max(float(ded_analysis.get("arc_energy_kwh", 0.0)), 0.0) * 3600.0 / layers
    retained_energy_kj = energy_kj_per_layer * max(float(heat_retention_pct), 0.0) / 100.0
    raw_rise_c_per_layer = retained_energy_kj / heat_capacity_kj_c if heat_capacity_kj_c > 0 else 0.0
    layer_time_min = max(float(ded_analysis.get("deposition_time_h", 0.0)), 0.0) * 60.0 / layers
    passive_cooling_c = max(float(cooling_rate_c_min), 0.0) * layer_time_min
    net_rise_c_per_layer = max(0.0, raw_rise_c_per_layer - passive_cooling_c)
    accumulation_layers = min(layers, 12)
    estimated_interpass_c = max(float(preheat_temp_c), 0.0) + net_rise_c_per_layer * accumulation_layers
    over_limit_c = max(0.0, estimated_interpass_c - max(float(interpass_limit_c), 0.0))
    dwell_min_per_layer = (
        over_limit_c / max(float(cooling_rate_c_min), 0.001)
        if over_limit_c > 0 else 0.0
    )
    total_dwell_h = dwell_min_per_layer * max(layers - 1, 0) / 60.0

    if over_limit_c <= 0:
        status = "Controlled"
        score = 100
    elif total_dwell_h <= max(float(ded_analysis.get("cell_time_h", 0.0)), 0.0) * 0.15:
        status = "Dwell required"
        score = 76
    else:
        status = "Thermal review"
        score = 48

    return {
        "status": status,
        "score": score,
        "layer_time_min": layer_time_min,
        "energy_kj_per_layer": energy_kj_per_layer,
        "raw_rise_c_per_layer": raw_rise_c_per_layer,
        "passive_cooling_c_per_layer": passive_cooling_c,
        "net_rise_c_per_layer": net_rise_c_per_layer,
        "estimated_interpass_c": estimated_interpass_c,
        "interpass_limit_c": float(interpass_limit_c),
        "over_limit_c": over_limit_c,
        "dwell_min_per_layer": dwell_min_per_layer,
        "total_dwell_h": total_dwell_h,
        "heat_retention_pct": float(heat_retention_pct),
    }


def estimate_robot_cell_handoff(
    *,
    ded_analysis: dict[str, Any],
    production_segment_count: int,
    robot_reach_mm: float,
    positioner_payload_kg: float,
    fixture_mass_kg: float,
    torch_clearance_mm: float,
    program_point_limit: int,
) -> dict[str, Any]:
    """Estimate robot-cell reach, payload, and program-size feasibility."""
    width = max(float(ded_analysis.get("bbox_width_mm", 0.0)), 0.0)
    depth = max(float(ded_analysis.get("bbox_depth_mm", 0.0)), 0.0)
    height = max(float(ded_analysis.get("model_height_mm", 0.0)), 0.0)
    half_diagonal = math.hypot(width / 2.0, depth / 2.0)
    reach_required_mm = math.hypot(half_diagonal + max(float(torch_clearance_mm), 0.0), height * 0.35)
    reach_utilization_pct = 100.0 * reach_required_mm / max(float(robot_reach_mm), 0.001)

    payload_required_kg = (
        max(float(ded_analysis.get("near_net_mass_kg", 0.0)), 0.0)
        + max(float(fixture_mass_kg), 0.0)
    )
    payload_utilization_pct = 100.0 * payload_required_kg / max(float(positioner_payload_kg), 0.001)
    point_utilization_pct = 100.0 * max(int(production_segment_count), 0) / max(int(program_point_limit), 1)

    blockers: list[str] = []
    warnings: list[str] = []
    if reach_utilization_pct > 100:
        blockers.append("Estimated tool center point exceeds configured robot reach.")
    elif reach_utilization_pct > 85:
        warnings.append("Robot reach utilization is high; review orientation and positioner strategy.")
    if payload_utilization_pct > 100:
        blockers.append("Part plus fixture mass exceeds positioner payload.")
    elif payload_utilization_pct > 85:
        warnings.append("Payload utilization is high; verify fixture and dynamic load assumptions.")
    if point_utilization_pct > 100:
        warnings.append("Robot program may need splitting or path compression.")

    score = 100 - 35 * len(blockers) - 12 * len(warnings)
    score = max(0, min(100, score))
    status = "Blocked" if blockers else "Review" if warnings else "Ready"
    return {
        "status": status,
        "score": score,
        "reach_required_mm": reach_required_mm,
        "reach_utilization_pct": reach_utilization_pct,
        "payload_required_kg": payload_required_kg,
        "payload_utilization_pct": payload_utilization_pct,
        "program_points": int(production_segment_count),
        "point_utilization_pct": point_utilization_pct,
        "blockers": blockers,
        "warnings": warnings,
    }


def build_qualification_plan(
    *,
    partner_fit: dict[str, Any] | None,
    thermal_plan: dict[str, Any] | None,
    robot_handoff: dict[str, Any] | None,
    qualification_level: str,
    material_strategy: str,
    ndt_required: bool,
    finish_tolerance_mm: float,
) -> dict[str, Any]:
    """Build a practical evidence plan for customer and production sign-off."""
    qualification = str(qualification_level)
    coupons = {
        "Prototype": 2,
        "Industrial": 4,
        "Aerospace / safety critical": 8,
    }.get(qualification, 4)
    if material_strategy != "Single material":
        coupons += 2
    if thermal_plan and thermal_plan.get("status") != "Controlled":
        coupons += 2

    inspections = ["Dimensional inspection", "Visual weld bead review"]
    if ndt_required:
        inspections.extend(["Dye penetrant or magnetic particle inspection", "Ultrasonic inspection"])
    if finish_tolerance_mm < 0.25:
        inspections.append("CMM inspection after finish machining")
    if qualification == "Aerospace / safety critical":
        inspections.extend(["Tensile coupons", "Metallography", "Hardness map", "Traceability dossier"])
    elif qualification == "Industrial":
        inspections.extend(["Hardness spot checks", "Macro-section coupon"])

    risks: list[str] = []
    if partner_fit and partner_fit.get("blockers"):
        risks.extend(str(item) for item in partner_fit.get("blockers", []))
    if thermal_plan and thermal_plan.get("status") == "Thermal review":
        risks.append("Interpass temperature control requires process development.")
    if robot_handoff and robot_handoff.get("status") == "Blocked":
        risks.extend(str(item) for item in robot_handoff.get("blockers", []))

    score = 100
    score -= 10 if qualification == "Industrial" else 22 if qualification == "Aerospace / safety critical" else 0
    score -= 8 if material_strategy != "Single material" else 0
    score -= 7 if ndt_required else 0
    score -= 25 if risks else 0
    score = max(0, min(100, score))
    status = "Release ready" if score >= 82 else "Engineering review" if score >= 60 else "Qualification hold"

    return {
        "status": status,
        "score": score,
        "coupon_count": coupons,
        "inspection_steps": inspections,
        "risks": risks,
        "records": [
            "Frozen CAD and parameter snapshot",
            "Plan fingerprint and segment ledger",
            "Machine setup sheet",
            "Wire lot and shielding gas traceability",
            "Post-machining and inspection report",
        ],
    }


def build_production_handoff_recommendations(
    *,
    thermal_plan: dict[str, Any] | None,
    robot_handoff: dict[str, Any] | None,
    qualification_plan: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return prioritized actions from thermal, robot, and qualification plans."""
    rows: list[dict[str, Any]] = []

    def add(priority: str, area: str, title: str, action: str, impact: str) -> None:
        rows.append({
            "priority": priority,
            "priority_score": PRIORITY_RANK.get(priority, 0),
            "area": area,
            "title": title,
            "action": action,
            "impact": impact,
            "owner": "Manufacturing",
        })

    if thermal_plan:
        if thermal_plan.get("status") == "Thermal review":
            add(
                "High",
                "Thermal",
                "Interpass control needs process development",
                "Add dwell, lower heat input, or split the build into controlled sequences.",
                f"Estimated interpass is {float(thermal_plan['estimated_interpass_c']):.1f} C.",
            )
        elif thermal_plan.get("status") == "Dwell required":
            add(
                "Medium",
                "Thermal",
                "Interpass dwell required",
                "Add programmed dwell or active cooling before production release.",
                f"{float(thermal_plan['dwell_min_per_layer']):.1f} min/layer estimated dwell.",
            )

    if robot_handoff:
        for blocker in robot_handoff.get("blockers", []):
            add(
                "Critical",
                "Robot cell",
                "Robot handoff blocked",
                "Review cell reach, payload, fixturing, or build segmentation.",
                str(blocker),
            )
        for warning in robot_handoff.get("warnings", []):
            add(
                "Medium",
                "Robot cell",
                "Robot handoff review",
                "Validate offline program, reach envelope, and fixture assumptions.",
                str(warning),
            )

    if qualification_plan and qualification_plan.get("status") == "Qualification hold":
        add(
            "High",
            "Qualification",
            "Qualification evidence is not release-ready",
            "Complete coupon, inspection, and traceability plan before customer handoff.",
            f"Qualification score is {int(qualification_plan.get('score', 0))}/100.",
        )

    return sorted(
        rows,
        key=lambda item: (-int(item["priority_score"]), str(item["area"]), str(item["title"])),
    )


def build_quality_scorecard(
    *,
    readiness: dict[str, Any],
    economics: dict[str, float],
    commercial_fit: dict[str, Any],
    metrics: dict[str, Any],
    production_enabled: bool,
    plan_fingerprint: str,
) -> dict[str, Any]:
    """Return an operator-facing quality scorecard for the planning package."""
    readiness_score = int(readiness.get("score", 0))
    efficiency = float(metrics.get("path_efficiency_pct", 0.0))
    volumetric_flow = float(economics.get("volumetric_flow_mm3_s", 0.0))
    commercial_status = str(commercial_fit.get("status", "Review"))

    motion_score = _banded_score(efficiency, excellent=88.0, good=78.0, review=65.0)
    flow_score = 100 if volumetric_flow <= 10.0 else 78 if volumetric_flow <= 14.0 else 45
    commercial_score = {"Fit": 100, "Review": 72, "No-bid": 30}.get(commercial_status, 65)
    export_score = 100 if production_enabled else 62 if readiness.get("status") != "Blocked" else 25
    trace_score = 100 if len(str(plan_fingerprint).strip()) >= 12 else 50

    rows = [
        {
            "area": "Engineering readiness",
            "score": readiness_score,
            "status": str(readiness.get("status", "Review")),
            "signal": f"{readiness.get('blockers', 0)} blockers, {readiness.get('warnings', 0)} warnings",
        },
        {
            "area": "Motion efficiency",
            "score": motion_score,
            "status": _score_status(motion_score),
            "signal": f"{efficiency:.1f}% path efficiency",
        },
        {
            "area": "Process envelope",
            "score": flow_score,
            "status": _score_status(flow_score),
            "signal": f"{volumetric_flow:.2f} mm3/s volumetric flow",
        },
        {
            "area": "Commercial fit",
            "score": commercial_score,
            "status": commercial_status,
            "signal": f"{float(commercial_fit.get('price_delta_pct', 0.0)):+.1f}% vs target",
        },
        {
            "area": "Production export",
            "score": export_score,
            "status": "Enabled" if production_enabled else "Guarded",
            "signal": "Full-build FDM export ready" if production_enabled else "Export guardrails active",
        },
        {
            "area": "Traceability",
            "score": trace_score,
            "status": "Locked" if trace_score == 100 else "Review",
            "signal": f"Plan ID {plan_fingerprint or 'missing'}",
        },
    ]
    overall = round(sum(row["score"] for row in rows) / len(rows))
    return {
        "overall_score": overall,
        "overall_status": _score_status(overall),
        "rows": rows,
    }


def _banded_score(value: float, *, excellent: float, good: float, review: float) -> int:
    if value >= excellent:
        return 100
    if value >= good:
        return 86
    if value >= review:
        return 70
    return 45


def _clamp_score(value: float) -> int:
    return max(0, min(100, round(float(value))))


def _score_status(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Ready"
    if score >= 60:
        return "Review"
    return "Needs work"


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
    commercial_fit: dict[str, Any] | None = None,
    launch_score: int | None = None,
    quality_scorecard: dict[str, Any] | None = None,
    recommendations: list[dict[str, Any]] | None = None,
    batch_scenarios: list[dict[str, Any]] | None = None,
    release_checklist: list[dict[str, str]] | None = None,
    optimization_playbook: list[dict[str, Any]] | None = None,
    ded_analysis: dict[str, Any] | None = None,
    partner_fit: dict[str, Any] | None = None,
    thermal_plan: dict[str, Any] | None = None,
    robot_handoff: dict[str, Any] | None = None,
    qualification_plan: dict[str, Any] | None = None,
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

    metadata = params.get("job_metadata", {}) if isinstance(params.get("job_metadata", {}), dict) else {}
    assumptions = (
        params.get("business_assumptions", {})
        if isinstance(params.get("business_assumptions", {}), dict) else {}
    )
    commercial_fit = commercial_fit or {"status": "Not set", "findings": []}
    commercial_findings = commercial_fit.get("findings", []) or ["Commercial guardrails are within target."]
    quality_scorecard = quality_scorecard or {"overall_score": "N/A", "overall_status": "Not scored", "rows": []}
    quality_lines = [
        f"- {row['area']}: {row['score']}/100 ({row['status']}) - {row['signal']}"
        for row in quality_scorecard.get("rows", [])
    ] or ["- Quality scorecard was not generated."]
    recommendation_lines = [
        f"- {row['priority']} / {row['area']}: {row['title']} - {row['action']}"
        for row in (recommendations or [])[:8]
    ] or ["- No prioritized recommendations were generated."]
    scenario_lines = [
        "- Qty {quantity}: unit ${unit_quote:.2f}, batch ${batch_quote:.2f}, "
        "{batch_machine_hours:.2f} machine h, {status}".format(**row)
        for row in (batch_scenarios or [])
    ] or ["- No batch scenarios were generated."]
    checklist_lines = [
        f"- {row['item']}: {row['state']} - {row['detail']}"
        for row in (release_checklist or [])
    ] or ["- Release checklist was not generated."]
    playbook_lines = [
        "- {lever}: {current} -> {proposed} ({estimated_delta}, {confidence} confidence)".format(
            **row
        )
        for row in (optimization_playbook or [])
    ] or ["- Optimization playbook was not generated."]
    ded_lines = (
        [
            f"- Envelope fit: {'Yes' if ded_analysis.get('envelope_fit') else 'No'}",
            f"- Deposition rate: {ded_analysis.get('deposited_kg_h', 0.0):.2f} kg/h",
            f"- Required wire feed: {ded_analysis.get('required_wire_feed_m_min', 0.0):.2f} m/min",
            f"- Heat input: {ded_analysis.get('heat_input_kj_mm', 0.0):.2f} kJ/mm",
            f"- Arc energy: {ded_analysis.get('arc_energy_kwh', 0.0):.2f} kWh",
            f"- Wire required: {ded_analysis.get('wire_required_kg', 0.0):.2f} kg",
            f"- Material saved vs billet: {ded_analysis.get('material_saved_kg', 0.0):.2f} kg "
            f"({ded_analysis.get('material_saved_pct', 0.0):.1f}%)",
            f"- Additive lead time: {ded_analysis.get('additive_lead_weeks', 0.0):.2f} weeks",
            f"- Lead-time compression: {ded_analysis.get('lead_time_compression_pct', 0.0):.1f}%",
        ]
        if ded_analysis else ["- DED process model was not enabled for this run."]
    )
    partner_lines = (
        [
            f"- Fit score: {partner_fit.get('score', 0)}/100 ({partner_fit.get('verdict', 'Review')})",
            f"- Application: {partner_fit.get('application_type', 'Unknown')}",
            f"- Conventional route: {partner_fit.get('conventional_route', 'Unknown')}",
            f"- Service estimate: ${partner_fit.get('service_unit_estimate', 0.0):.2f}",
            f"- Conventional estimate: ${partner_fit.get('conventional_unit_estimate', 0.0):.2f}",
            f"- Value delta: ${partner_fit.get('value_delta', 0.0):.2f} "
            f"({partner_fit.get('value_delta_pct', 0.0):+.1f}%)",
            "- Deliverables: " + "; ".join(partner_fit.get("deliverables", [])),
        ]
        if partner_fit else ["- Manufacturing partner fit was not assessed for this run."]
    )
    thermal_lines = (
        [
            f"- Status: {thermal_plan.get('status', 'Review')}",
            f"- Estimated interpass: {thermal_plan.get('estimated_interpass_c', 0.0):.1f} C",
            f"- Interpass limit: {thermal_plan.get('interpass_limit_c', 0.0):.1f} C",
            f"- Dwell per layer: {thermal_plan.get('dwell_min_per_layer', 0.0):.1f} min",
            f"- Total dwell: {thermal_plan.get('total_dwell_h', 0.0):.2f} h",
        ]
        if thermal_plan else ["- Thermal / interpass model was not enabled for this run."]
    )
    robot_lines = (
        [
            f"- Status: {robot_handoff.get('status', 'Review')}",
            f"- Reach utilization: {robot_handoff.get('reach_utilization_pct', 0.0):.1f}%",
            f"- Payload utilization: {robot_handoff.get('payload_utilization_pct', 0.0):.1f}%",
            f"- Program points: {robot_handoff.get('program_points', 0):,}",
            *[f"- BLOCKER: {item}" for item in robot_handoff.get("blockers", [])],
            *[f"- REVIEW: {item}" for item in robot_handoff.get("warnings", [])],
        ]
        if robot_handoff else ["- Robot-cell handoff model was not enabled for this run."]
    )
    qualification_lines = (
        [
            f"- Status: {qualification_plan.get('status', 'Review')}",
            f"- Coupon count: {qualification_plan.get('coupon_count', 0)}",
            "- Inspections: " + "; ".join(qualification_plan.get("inspection_steps", [])),
            "- Records: " + "; ".join(qualification_plan.get("records", [])),
            *[f"- RISK: {item}" for item in qualification_plan.get("risks", [])],
        ]
        if qualification_plan else ["- Qualification package was not generated for this run."]
    )

    return "\n".join([
        f"# MiniSlicer Job Dossier: {job_name}",
        "",
        "## Executive Summary",
        f"- Readiness: {readiness.get('status', 'Review')} ({readiness.get('score', 0)}/100)",
        f"- Program risk: {risk}",
        f"- Launch score: {launch_score if launch_score is not None else 'N/A'}",
        f"- Quality score: {quality_scorecard.get('overall_score', 'N/A')} "
        f"({quality_scorecard.get('overall_status', 'Not scored')})",
        f"- Commercial fit: {commercial_fit.get('status', 'Not set')}",
        f"- Estimated build time: {full_time_text}",
        f"- Estimated material: {full_weight_g:.2f} g",
        f"- Estimated unit quote: ${economics['quoted_price']:.2f}",
        f"- Estimated batch quote: ${economics['quoted_batch_price']:.2f}",
        "",
        "## Job Metadata",
        f"- Job ID: {metadata.get('job_id', 'Unassigned')}",
        f"- Plan fingerprint: {params.get('plan_fingerprint', 'Unassigned')}",
        f"- Customer: {metadata.get('customer_name', 'Internal')}",
        f"- Owner: {metadata.get('owner_name', 'Engineering')}",
        f"- Quote profile: {assumptions.get('quote_profile', 'Service Bureau')}",
        f"- Batch quantity: {int(economics['batch_quantity'])}",
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
        f"- Batch machine time: {economics['batch_machine_hours']:.2f} h",
        "",
        "## Cost Model",
        f"- Material per unit: ${economics['material_cost']:.2f}",
        f"- Machine time per unit: ${economics['machine_cost']:.2f}",
        f"- Setup labor: ${economics['setup_labor_cost']:.2f}",
        f"- Postprocess labor per unit: ${economics['postprocess_labor_cost']:.2f}",
        f"- Scrap allowance: {economics['scrap_allowance_pct']:.1f}%",
        f"- Margin: {economics['margin_pct']:.1f}%",
        f"- Unit quote: ${economics['quoted_price']:.2f}",
        f"- Batch quote: ${economics['quoted_batch_price']:.2f}",
        "",
        "## Commercial Guardrails",
        *[f"- {finding}" for finding in commercial_findings],
        "",
        "## Launch Optimizer",
        *recommendation_lines,
        "",
        "## Batch Scenarios",
        *scenario_lines,
        "",
        "## What-If Playbook",
        *playbook_lines,
        "",
        "## DED Process Model",
        *ded_lines,
        "",
        "## Manufacturing Partner Fit",
        *partner_lines,
        "",
        "## Production Handoff",
        "### Thermal / Interpass",
        *thermal_lines,
        "",
        "### Robot Cell",
        *robot_lines,
        "",
        "### Qualification Package",
        *qualification_lines,
        "",
        "## Release Checklist",
        *checklist_lines,
        "",
        "## Quality Scorecard",
        *quality_lines,
        "",
        "## Findings",
        *issue_lines,
        "",
        "Planning output only. Validate machine-specific process limits, fixture strategy, "
        "material batch, and start/end code before production release.",
    ])


def _issue_value(issue: Any, field: str, default: Any) -> Any:
    if isinstance(issue, dict):
        return issue.get(field, default)
    return getattr(issue, field, default)


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
