"""Polished dashboard surfaces for MiniSlicer."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _pill(label: str, tone: str = "neutral") -> str:
    return f'<span class="ms-pill ms-pill-{tone}">{escape(label)}</span>'


def _signal_row(signal: str, value: object) -> dict[str, str]:
    return {"signal": signal, "value": str(value)}


def _tone_for_status(status: str) -> str:
    if status in {"Ready", "Fit", "Low"}:
        return "ok"
    if status in {"Review", "Medium"}:
        return "warn"
    if status in {"Blocked", "High", "No-bid"}:
        return "bad"
    return "neutral"


def render_launch_ribbon(
    *,
    job_name: str,
    customer_name: str,
    launch_score: int,
    readiness: dict[str, Any],
    commercial_fit: dict[str, Any],
    program_risk: str,
    economics: dict[str, float],
) -> None:
    """Render the compact launch status ribbon below the top metrics."""
    st.markdown(
        f"""
        <div class="launch-ribbon">
            <div class="launch-id">
                <div class="launch-kicker">Active planning package</div>
                <div class="launch-title">{escape(job_name)}</div>
                <div class="launch-sub">{escape(customer_name)} - {int(economics["batch_quantity"])} pcs</div>
            </div>
            <div class="launch-pills">
                {_pill(f"Launch {launch_score}/100", _tone_for_status(readiness.get("status", "")))}
                {_pill(f"Readiness {readiness.get('status', 'Review')}", _tone_for_status(readiness.get("status", "")))}
                {_pill(f"Risk {program_risk}", _tone_for_status(program_risk))}
                {_pill(f"Commercial {commercial_fit.get('status', 'Review')}", _tone_for_status(commercial_fit.get("status", "")))}
            </div>
            <div class="launch-money">
                <span>Unit quote</span>
                <strong>{_money(economics["quoted_price"])}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_executive_dashboard(
    *,
    job_name: str,
    job_id: str,
    customer_name: str,
    owner_name: str,
    source_label: str,
    process_mode: str,
    material_choice: str,
    batch_quantity: int,
    layer_count: int,
    production_segment_count: int,
    metrics: dict[str, Any],
    economics: dict[str, float],
    readiness: dict[str, Any],
    commercial_fit: dict[str, Any],
    program_risk: str,
    launch_score: int,
    travel_ratio: float,
    target_unit_price: float,
    quote_profile: str,
    max_lead_time_h: float,
    machine_rate_per_h: float,
    labor_rate_per_h: float,
    setup_time_min: float,
    postprocess_time_min: float,
    scrap_allowance_pct: float,
    margin_pct: float,
) -> None:
    """Render the launch-grade Executive tab."""
    status_tone = _tone_for_status(readiness.get("status", "Review"))
    risk_tone = _tone_for_status(program_risk)
    commercial_tone = _tone_for_status(commercial_fit.get("status", "Review"))
    price_delta = commercial_fit.get("price_delta_pct", 0.0)
    target_text = "Target not set" if target_unit_price <= 0 else f"{price_delta:+.1f}% vs target"

    st.markdown(
        f"""
        <section class="exec-hero">
            <div>
                <div class="exec-eyebrow">Launch command center</div>
                <h2>{escape(job_name)}</h2>
                <p>{escape(job_id)} - {escape(customer_name)} - Owner {escape(owner_name)}</p>
            </div>
            <div class="exec-score exec-score-{status_tone}">
                <span>Launch score</span>
                <strong>{launch_score}</strong>
                <small>/100</small>
            </div>
        </section>
        <div class="exec-strip">
            <div class="exec-card">
                <div class="exec-label">Release State</div>
                <div class="exec-value">{escape(readiness["status"])} - {readiness["score"]}/100</div>
                <div class="exec-note">{readiness["blockers"]} blockers, {readiness["warnings"]} warnings</div>
            </div>
            <div class="exec-card">
                <div class="exec-label">Unit / Batch Quote</div>
                <div class="exec-value">{_money(economics["quoted_price"])}</div>
                <div class="exec-note">{_money(economics["quoted_batch_price"])} for {int(batch_quantity)} pcs</div>
            </div>
            <div class="exec-card">
                <div class="exec-label">Commercial Fit</div>
                <div class="exec-value exec-text-{commercial_tone}">{escape(commercial_fit["status"])}</div>
                <div class="exec-note">{escape(target_text)}</div>
            </div>
            <div class="exec-card">
                <div class="exec-label">Program Risk</div>
                <div class="exec-value exec-text-{risk_tone}">{escape(program_risk)}</div>
                <div class="exec-note">{economics["batch_machine_hours"]:.1f} h batch machine time</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, middle, right = st.columns([1.1, 1.05, 0.95])
    with left:
        st.markdown("### Manufacturing Packet")
        st.dataframe(
            [
                _signal_row("Geometry", source_label),
                _signal_row("Process", process_mode),
                _signal_row("Material", material_choice),
                _signal_row("Batch", int(batch_quantity)),
                _signal_row("Layers", layer_count),
                _signal_row("Path efficiency", f"{metrics['path_efficiency_pct']:.1f}%"),
                _signal_row("Travel share", f"{travel_ratio:.1f}%"),
                _signal_row("Build productivity", f"{economics['build_rate_cm3_h']:.2f} cm3/h"),
                _signal_row("Volumetric flow", f"{economics['volumetric_flow_mm3_s']:.2f} mm3/s"),
                _signal_row("Segment export", f"{production_segment_count:,} moves"),
            ],
            hide_index=True,
            width="stretch",
        )

    with middle:
        st.markdown("### Quote Cockpit")
        st.bar_chart({
            "USD / unit": {
                "Material": economics["material_cost"],
                "Machine": economics["machine_cost"],
                "Setup": economics["setup_labor_cost"] / max(int(batch_quantity), 1),
                "Postprocess": economics["postprocess_labor_cost"],
                "Scrap + margin": max(
                    0.0,
                    economics["quoted_price"]
                    - economics["material_cost"]
                    - economics["machine_cost"]
                    - economics["setup_labor_cost"] / max(int(batch_quantity), 1)
                    - economics["postprocess_labor_cost"],
                ),
            }
        })
        quote_rows = [
            {"assumption": "Machine rate", "value": f"${machine_rate_per_h:.2f}/h"},
            {"assumption": "Quote profile", "value": quote_profile},
            {"assumption": "Labor rate", "value": f"${labor_rate_per_h:.2f}/h"},
            {"assumption": "Setup", "value": f"{setup_time_min:.1f} min"},
            {"assumption": "Postprocess", "value": f"{postprocess_time_min:.1f} min/part"},
            {"assumption": "Scrap", "value": f"{scrap_allowance_pct:.1f}%"},
            {"assumption": "Margin", "value": f"{margin_pct:.1f}%"},
            {"assumption": "Lead target", "value": f"{max_lead_time_h:.1f} machine h"},
        ]
        st.dataframe(quote_rows, hide_index=True, width="stretch")

    with right:
        st.markdown("### Action Queue")
        if readiness["issues"]:
            for issue in readiness["issues"][:4]:
                message = f"{issue.title}: {issue.action}"
                if issue.severity == "blocker":
                    st.error(message)
                elif issue.severity == "warning":
                    st.warning(message)
                else:
                    st.info(message)
        else:
            st.success("Engineering checks are clear for planning review.")

        if commercial_fit["findings"]:
            for finding in commercial_fit["findings"]:
                st.warning(finding)
        else:
            st.success("Commercial guardrails are inside target.")


def render_release_gate_matrix(
    *,
    readiness: dict[str, Any],
    commercial_fit: dict[str, Any],
    program_risk: str,
    launch_score: int,
    production_enabled: bool,
    export_segment_count: int,
) -> None:
    """Render a compact go/no-go gate matrix for launch reviews."""
    gates = [
        {
            "gate": "Engineering",
            "state": readiness.get("status", "Review"),
            "signal": f"{readiness.get('score', 0)}/100 readiness",
            "tone": _tone_for_status(readiness.get("status", "Review")),
        },
        {
            "gate": "Commercial",
            "state": commercial_fit.get("status", "Review"),
            "signal": "Target price and lead time",
            "tone": _tone_for_status(commercial_fit.get("status", "Review")),
        },
        {
            "gate": "Program Risk",
            "state": program_risk,
            "signal": "Flow, warnings, and build hours",
            "tone": _tone_for_status(program_risk),
        },
        {
            "gate": "Production Export",
            "state": "Enabled" if production_enabled else "Guarded",
            "signal": f"{export_segment_count:,} export moves",
            "tone": "ok" if production_enabled else "warn",
        },
        {
            "gate": "Launch",
            "state": "Pass" if launch_score >= 85 else "Review" if launch_score >= 65 else "Hold",
            "signal": f"{launch_score}/100 launch score",
            "tone": "ok" if launch_score >= 85 else "warn" if launch_score >= 65 else "bad",
        },
    ]
    cards = "\n".join(
        f"""
        <div class="gate-card gate-{gate['tone']}">
            <div class="gate-top">{escape(gate['gate'])}</div>
            <div class="gate-state">{escape(gate['state'])}</div>
            <div class="gate-signal">{escape(gate['signal'])}</div>
        </div>
        """
        for gate in gates
    )
    st.markdown(f'<div class="gate-grid">{cards}</div>', unsafe_allow_html=True)


def render_quality_scorecard(scorecard: dict[str, Any]) -> None:
    """Render an operator QA scorecard for the planning package."""
    rows = list(scorecard.get("rows", []))
    overall = int(scorecard.get("overall_score", 0))
    status = str(scorecard.get("overall_status", "Review"))
    tone = _tone_for_score(overall)
    cards = "\n".join(
        f"""
        <div class="quality-card quality-{_tone_for_score(int(row['score']))}">
            <div class="quality-top">{escape(str(row['area']))}</div>
            <div class="quality-score">{int(row['score'])}<span>/100</span></div>
            <div class="quality-state">{escape(str(row['status']))}</div>
            <div class="quality-signal">{escape(str(row['signal']))}</div>
        </div>
        """
        for row in rows
    )
    st.markdown(
        f"""
        <section class="quality-hero quality-{tone}">
            <div>
                <div class="quality-kicker">Operator QA</div>
                <h3>Quality package score</h3>
                <p>{escape(status)} across engineering, process, commercial, export, and traceability checks.</p>
            </div>
            <div class="quality-total">{overall}<span>/100</span></div>
        </section>
        <div class="quality-grid">{cards}</div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(rows, hide_index=True, width="stretch")


def render_pattern_ranking(ranking: list[dict[str, Any]]) -> None:
    """Render an operator-friendly ranking of generated infill patterns."""
    if not ranking:
        st.info("No pattern candidates available for ranking.")
        return

    best = ranking[0]
    st.markdown(
        f"""
        <div class="pattern-winner">
            <div>
                <div class="pattern-kicker">Recommended pattern</div>
                <div class="pattern-name">{escape(str(best['pattern']))}</div>
                <div class="pattern-note">
                    {float(best['path_mm']):.1f} mm path - {float(best['travel_mm']):.1f} mm travel -
                    {int(best['line_count'])} lines
                </div>
            </div>
            <div class="pattern-score">{int(best['score'])}<span>/100</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(
        [
            {
                "rank": idx + 1,
                "pattern": row["pattern"],
                "score": int(row["score"]),
                "path_mm": round(float(row["path_mm"]), 1),
                "travel_mm": round(float(row["travel_mm"]), 1),
                "lines": int(row["line_count"]),
                "efficiency_%": round(float(row["efficiency_pct"]), 1),
            }
            for idx, row in enumerate(ranking)
        ],
        hide_index=True,
        width="stretch",
    )


def render_launch_optimizer(
    recommendations: list[dict[str, Any]],
    batch_scenarios: list[dict[str, Any]],
    release_checklist: list[dict[str, str]],
) -> None:
    """Render ranked next moves, batch scenarios, and release checklist."""
    left, right = st.columns([1.22, 1.0])

    with left:
        st.markdown("#### Top Moves")
        cards = "\n".join(
            f"""
            <div class="optimizer-card optimizer-{_tone_for_priority(str(row['priority']))}">
                <div class="optimizer-top">
                    <span>{escape(str(row['priority']))}</span>
                    <small>{escape(str(row['area']))}</small>
                </div>
                <div class="optimizer-title">{escape(str(row['title']))}</div>
                <div class="optimizer-action">{escape(str(row['action']))}</div>
                <div class="optimizer-impact">{escape(str(row['impact']))}</div>
                <div class="optimizer-owner">Owner: {escape(str(row['owner']))}</div>
            </div>
            """
            for row in recommendations[:6]
        )
        st.markdown(f'<div class="optimizer-grid">{cards}</div>', unsafe_allow_html=True)

    with right:
        st.markdown("#### Release Checklist")
        st.dataframe(release_checklist, hide_index=True, width="stretch")

        st.markdown("#### Batch Scenarios")
        scenario_rows = [
            {
                "qty": int(row["quantity"]),
                "unit quote": _money(float(row["unit_quote"])),
                "batch quote": _money(float(row["batch_quote"])),
                "machine h": f"{float(row['batch_machine_hours']):.2f}",
                "target": f"{float(row['target_delta_pct']):+.1f}%",
                "lead delta": f"{float(row['lead_time_delta_h']):+.1f} h",
                "status": row["status"],
            }
            for row in batch_scenarios
        ]
        st.dataframe(scenario_rows, hide_index=True, width="stretch")


def render_next_action(
    *,
    readiness: dict[str, Any],
    commercial_fit: dict[str, Any],
    metrics: dict[str, Any],
    economics: dict[str, Any],
    fits_plate: bool,
    travel_ratio: float,
    launch_score: int,
) -> None:
    """Render a single prioritised recommended-next-action banner."""
    blockers = int(readiness.get("blockers", 0))
    warnings = int(readiness.get("warnings", 0))
    status = readiness.get("status", "Review")
    commercial_status = commercial_fit.get("status", "Review")

    if blockers > 0:
        tone = "bad"
        icon = "X"
        heading = f"Fix {blockers} blocker{'s' if blockers != 1 else ''} before releasing"
        detail = "Open the Release tab - Advisor section to see the required fixes."
    elif not fits_plate:
        tone = "warn"
        icon = "!"
        heading = "Geometry does not fit the build plate"
        detail = "Use Center on plate or scale down in the sidebar placement controls."
    elif commercial_status == "No-bid":
        tone = "warn"
        icon = "!"
        heading = "Quote exceeds target - re-check business assumptions"
        detail = "Adjust batch size, rates, or target price in the Business controls."
    elif warnings > 2:
        tone = "warn"
        icon = "!"
        heading = f"Review {warnings} warnings before releasing"
        detail = "Open the Release tab - Advisor section for the full findings list."
    elif launch_score < 60:
        tone = "warn"
        icon = "!"
        heading = "Launch score is low - review Quality scorecard"
        detail = "Open Release - Quality to see per-area scores and improvement signals."
    elif travel_ratio > 30:
        tone = "warn"
        icon = "!"
        heading = f"High travel ratio ({travel_ratio:.0f}%) - enable path optimization"
        detail = "Turn on Nearest Neighbour in the Toolpath controls to reduce travel moves."
    elif status == "Ready":
        tone = "ok"
        icon = "OK"
        heading = "Job is ready - generate dossier and exports"
        detail = "Go to the Release tab to download CSV, JSON, G-code, and dossier packages."
    else:
        tone = "neutral"
        icon = "->"
        heading = "Review metrics in the Plan tab before releasing"
        detail = "Check path efficiency, infill comparison, and animation before exporting."

    css_border = {
        "ok": "#15803d",
        "warn": "#b45309",
        "bad": "#b91c1c",
        "neutral": "#1d4ed8",
    }.get(tone, "#1d4ed8")
    css_bg = {
        "ok": "#f0fdf4",
        "warn": "#fffbeb",
        "bad": "#fef2f2",
        "neutral": "#eff6ff",
    }.get(tone, "#eff6ff")
    css_ink = {
        "ok": "#14532d",
        "warn": "#78350f",
        "bad": "#7f1d1d",
        "neutral": "#1e3a5f",
    }.get(tone, "#1e3a5f")
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:0.85rem;
                    background:{css_bg};border:1px solid {css_border};
                    border-left:4px solid {css_border};border-radius:8px;
                    padding:0.75rem 1rem;margin:0 0 0.85rem;">
            <div style="font-size:0.72rem;font-weight:820;color:{css_border};
                        background:rgba(255,255,255,0.7);border:1px solid {css_border};
                        border-radius:5px;padding:0.18rem 0.55rem;white-space:nowrap;">
                {escape(icon)}
            </div>
            <div>
                <div style="color:{css_ink};font-size:0.9rem;font-weight:760;line-height:1.2;">
                    {escape(heading)}
                </div>
                <div style="color:{css_ink};opacity:0.75;font-size:0.8rem;margin-top:0.18rem;">
                    {escape(detail)}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _tone_for_score(score: int) -> str:
    if score >= 90:
        return "ok"
    if score >= 60:
        return "warn"
    return "bad"


def _tone_for_priority(priority: str) -> str:
    if priority == "Critical":
        return "bad"
    if priority == "High":
        return "warn"
    if priority == "Ready":
        return "ok"
    return "neutral"
