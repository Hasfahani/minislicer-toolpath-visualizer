"""Tests for business and manufacturability analysis."""

from src.job_analysis import (
    classify_program_risk,
    estimate_job_economics,
    generate_job_dossier_html,
    generate_job_dossier_markdown,
)


def _metrics() -> dict[str, float]:
    return {
        "material_volume_mm3": 100.0,
        "path_efficiency_pct": 82.0,
    }


def test_economics_returns_quote_and_process_kpis() -> None:
    economics = estimate_job_economics(
        metrics=_metrics(),
        layer_count=10,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        print_speed_mm_s=50.0,
        full_time_s=3600.0,
        full_weight_g=20.0,
        material_cost_per_kg=25.0,
    )

    assert economics["quoted_price"] > economics["material_cost"]
    assert economics["build_rate_cm3_h"] == 1.0
    assert economics["volumetric_flow_mm3_s"] == 4.0


def test_risk_is_blocked_when_readiness_is_blocked() -> None:
    economics = estimate_job_economics(
        metrics=_metrics(),
        layer_count=1,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        print_speed_mm_s=50.0,
        full_time_s=60.0,
        full_weight_g=1.0,
        material_cost_per_kg=25.0,
    )

    assert classify_program_risk({"status": "Blocked", "warnings": 0}, economics) == "Blocked"


def test_risk_flags_high_volumetric_flow() -> None:
    economics = estimate_job_economics(
        metrics=_metrics(),
        layer_count=1,
        layer_height_mm=0.4,
        nozzle_diameter_mm=0.8,
        print_speed_mm_s=60.0,
        full_time_s=60.0,
        full_weight_g=1.0,
        material_cost_per_kg=25.0,
    )

    assert classify_program_risk({"status": "Review", "warnings": 0}, economics) == "High"


def test_dossier_contains_traceable_summary() -> None:
    economics = estimate_job_economics(
        metrics=_metrics(),
        layer_count=2,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        print_speed_mm_s=50.0,
        full_time_s=120.0,
        full_weight_g=2.0,
        material_cost_per_kg=25.0,
    )
    dossier = generate_job_dossier_markdown(
        job_name="sample",
        params={
            "process_mode": "FDM",
            "profile": "Balanced",
            "shape_type": "Rectangle",
            "infill_pattern": "Grid",
            "infill_spacing_mm": 3.0,
            "perimeter_count": 3,
            "perimeter_spacing_mm": 0.45,
        },
        metrics=_metrics(),
        readiness={"status": "Ready", "score": 96, "issues": []},
        economics=economics,
        full_time_text="2m",
        full_weight_g=2.0,
        layer_count=2,
        risk="Low",
    )
    html = generate_job_dossier_html(dossier)

    assert "Executive Summary" in dossier
    assert "Estimated quote" in dossier
    assert "<!doctype html>" in html
