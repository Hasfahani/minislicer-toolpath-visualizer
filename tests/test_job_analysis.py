"""Tests for business and manufacturability analysis."""

from src.job_analysis import (
    assess_commercial_fit,
    assess_manufacturing_partner_fit,
    build_batch_scenarios,
    build_ded_recommendations,
    build_launch_recommendations,
    build_optimization_playbook,
    build_quality_scorecard,
    build_release_checklist,
    classify_program_risk,
    compute_launch_score,
    estimate_ded_process,
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
    assert economics["quoted_batch_price"] == economics["quoted_price"]
    assert economics["build_rate_cm3_h"] == 1.0
    assert economics["volumetric_flow_mm3_s"] == 4.0


def test_batch_quantity_amortizes_setup_cost() -> None:
    single = estimate_job_economics(
        metrics=_metrics(),
        layer_count=10,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        print_speed_mm_s=50.0,
        full_time_s=3600.0,
        full_weight_g=20.0,
        material_cost_per_kg=25.0,
        batch_quantity=1,
    )
    batch = estimate_job_economics(
        metrics=_metrics(),
        layer_count=10,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        print_speed_mm_s=50.0,
        full_time_s=3600.0,
        full_weight_g=20.0,
        material_cost_per_kg=25.0,
        batch_quantity=10,
    )

    assert batch["quoted_price"] < single["quoted_price"]
    assert batch["quoted_batch_price"] > batch["quoted_price"]
    assert batch["batch_machine_hours"] == 10.0


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


def test_commercial_fit_flags_price_and_lead_time_targets() -> None:
    economics = estimate_job_economics(
        metrics=_metrics(),
        layer_count=10,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        print_speed_mm_s=50.0,
        full_time_s=3600.0,
        full_weight_g=20.0,
        material_cost_per_kg=25.0,
        batch_quantity=10,
    )

    fit = assess_commercial_fit(
        economics=economics,
        target_unit_price=1.0,
        max_lead_time_h=4.0,
    )

    assert fit["status"] == "No-bid"
    assert fit["price_delta_pct"] > 0
    assert fit["lead_time_delta_h"] == 6.0


def test_launch_score_combines_technical_and_commercial_readiness() -> None:
    score = compute_launch_score(
        readiness={"score": 95},
        risk="Medium",
        commercial_fit={"status": "Review"},
    )

    assert score == 75


def test_quality_scorecard_covers_operational_package() -> None:
    economics = estimate_job_economics(
        metrics=_metrics(),
        layer_count=5,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        print_speed_mm_s=50.0,
        full_time_s=600.0,
        full_weight_g=5.0,
        material_cost_per_kg=25.0,
    )
    scorecard = build_quality_scorecard(
        readiness={"status": "Ready", "score": 96, "blockers": 0, "warnings": 0},
        economics=economics,
        commercial_fit={"status": "Fit", "price_delta_pct": -2.0},
        metrics={"path_efficiency_pct": 90.0},
        production_enabled=True,
        plan_fingerprint="abcdef1234567890",
    )

    assert scorecard["overall_score"] >= 90
    assert scorecard["overall_status"] == "Excellent"
    assert {row["area"] for row in scorecard["rows"]} == {
        "Engineering readiness",
        "Motion efficiency",
        "Process envelope",
        "Commercial fit",
        "Production export",
        "Traceability",
    }


def test_quality_scorecard_penalizes_blocked_exports_and_bad_flow() -> None:
    scorecard = build_quality_scorecard(
        readiness={"status": "Blocked", "score": 30, "blockers": 1, "warnings": 2},
        economics={"volumetric_flow_mm3_s": 18.0},
        commercial_fit={"status": "No-bid", "price_delta_pct": 50.0},
        metrics={"path_efficiency_pct": 52.0},
        production_enabled=False,
        plan_fingerprint="",
    )

    assert scorecard["overall_score"] < 50
    assert scorecard["overall_status"] == "Needs work"


def test_launch_recommendations_prioritize_blockers_and_commercial_risk() -> None:
    scorecard = {
        "rows": [
            {
                "area": "Motion efficiency",
                "score": 45,
                "status": "Needs work",
                "signal": "52.0% path efficiency",
            }
        ]
    }
    recommendations = build_launch_recommendations(
        readiness={
            "status": "Blocked",
            "blockers": 1,
            "warnings": 0,
            "issues": [
                {
                    "severity": "blocker",
                    "title": "Build plate overflow",
                    "detail": "Geometry extends outside the selected plate.",
                    "action": "Scale the part down.",
                }
            ],
        },
        commercial_fit={"status": "No-bid", "findings": ["Unit price is 40.0% above target."]},
        metrics={"path_efficiency_pct": 52.0},
        economics={"volumetric_flow_mm3_s": 16.0},
        quality_scorecard=scorecard,
        production_enabled=False,
        fits_plate=False,
        travel_ratio_pct=42.0,
        effective_spacing_mm=6.0,
        nozzle_diameter_mm=0.4,
        layer_count=20,
        recommended_pattern="Concentric",
    )

    assert recommendations[0]["priority"] == "Critical"
    assert recommendations[0]["title"] == "Build plate overflow"
    assert any(row["area"] == "Commercial" for row in recommendations)
    assert any(row["area"] == "Export" for row in recommendations)


def test_launch_recommendations_return_ready_state_when_clean() -> None:
    recommendations = build_launch_recommendations(
        readiness={"status": "Ready", "blockers": 0, "warnings": 0, "issues": []},
        commercial_fit={"status": "Fit", "findings": []},
        metrics={"path_efficiency_pct": 92.0},
        economics={"volumetric_flow_mm3_s": 4.0},
        quality_scorecard={"rows": []},
        production_enabled=True,
        fits_plate=True,
        travel_ratio_pct=8.0,
        effective_spacing_mm=3.0,
        nozzle_diameter_mm=0.4,
        layer_count=20,
        recommended_pattern="Grid",
    )

    assert recommendations == [
        {
            "priority": "Ready",
            "priority_score": 1,
            "area": "Release",
            "title": "Package ready for sign-off",
            "action": "Export the dossier, CSV, JSON, SVG, and any enabled production G-code.",
            "impact": "No automated blockers or high-priority guardrail failures were found.",
            "owner": "Program",
        }
    ]


def test_batch_scenarios_show_setup_amortization() -> None:
    scenarios = build_batch_scenarios(
        metrics=_metrics(),
        layer_count=10,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        print_speed_mm_s=50.0,
        full_time_s=3600.0,
        full_weight_g=20.0,
        material_cost_per_kg=25.0,
        machine_rate_per_h=18.0,
        labor_rate_per_h=45.0,
        setup_time_min=12.0,
        postprocess_time_min=8.0,
        scrap_allowance_pct=8.0,
        margin_pct=35.0,
        target_unit_price=0.0,
        max_lead_time_h=24.0,
        quantities=[1, 10],
    )

    assert [row["quantity"] for row in scenarios] == [1, 10]
    assert scenarios[1]["setup_per_part"] < scenarios[0]["setup_per_part"]
    assert scenarios[1]["unit_quote"] < scenarios[0]["unit_quote"]


def test_release_checklist_tracks_export_and_traceability() -> None:
    checklist = build_release_checklist(
        readiness={"status": "Ready", "score": 96, "blockers": 0},
        commercial_fit={"status": "Fit"},
        production_enabled=True,
        plan_fingerprint="abcdef1234567890",
        export_segment_count=125,
    )

    assert {row["item"] for row in checklist} == {
        "Engineering gates",
        "Commercial guardrails",
        "Production export",
        "Traceability",
        "Segment ledger",
    }
    assert checklist[2]["state"] == "Ready"
    assert checklist[3]["state"] == "Locked"


def test_optimization_playbook_quantifies_pattern_and_batch_levers() -> None:
    batch_scenarios = [
        {
            "quantity": 1,
            "unit_quote": 20.0,
            "batch_quote": 20.0,
            "batch_machine_hours": 1.0,
            "target_delta_pct": 0.0,
            "lead_time_delta_h": 0.0,
            "status": "Fit",
        },
        {
            "quantity": 10,
            "unit_quote": 12.0,
            "batch_quote": 120.0,
            "batch_machine_hours": 10.0,
            "target_delta_pct": 0.0,
            "lead_time_delta_h": 0.0,
            "status": "Fit",
        },
    ]
    playbook = build_optimization_playbook(
        current_pattern="Grid",
        pattern_ranking=[
            {
                "pattern": "Concentric",
                "path_mm": 80.0,
                "travel_mm": 10.0,
                "line_count": 8,
                "efficiency_pct": 88.9,
            },
            {
                "pattern": "Grid",
                "path_mm": 110.0,
                "travel_mm": 25.0,
                "line_count": 20,
                "efficiency_pct": 81.5,
            },
        ],
        metrics={"path_efficiency_pct": 82.0},
        economics={"batch_quantity": 1.0, "volumetric_flow_mm3_s": 4.0},
        batch_scenarios=batch_scenarios,
        print_speed_mm_s=50.0,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        travel_ratio_pct=12.0,
        production_enabled=True,
    )

    assert playbook[0]["lever"] == "Pattern switch"
    assert any(row["lever"] == "Batch sizing" for row in playbook)
    assert any(row["lever"] == "Release package" for row in playbook)


def test_optimization_playbook_flags_high_flow_reduction() -> None:
    playbook = build_optimization_playbook(
        current_pattern="Grid",
        pattern_ranking=[],
        metrics={"path_efficiency_pct": 72.0},
        economics={"batch_quantity": 1.0, "volumetric_flow_mm3_s": 19.2},
        batch_scenarios=[],
        print_speed_mm_s=60.0,
        layer_height_mm=0.4,
        nozzle_diameter_mm=0.8,
        travel_ratio_pct=18.0,
        production_enabled=False,
    )

    flow = next(row for row in playbook if row["lever"] == "Flow envelope")
    assert flow["confidence"] == "High"
    assert "under the high-risk warning band" in flow["estimated_delta"]


def test_ded_process_estimates_wire_feed_energy_and_lead_time() -> None:
    ded = estimate_ded_process(
        metrics={"material_volume_mm3": 250_000.0},
        material_density_g_cm3=7.99,
        full_weight_g=2200.0,
        full_time_s=7200.0,
        model_height_mm=300.0,
        bbox_width_mm=220.0,
        bbox_depth_mm=180.0,
        layer_height_mm=1.2,
        bead_width_mm=4.0,
        print_speed_mm_s=8.0,
        wire_diameter_mm=1.2,
        wire_feed_m_min=6.0,
        arc_current_a=180.0,
        arc_voltage_v=24.0,
        arc_efficiency_pct=80.0,
        deposition_efficiency_pct=88.0,
        robot_utilization_pct=72.0,
        machining_allowance_pct=12.0,
        billet_buy_to_fly=3.5,
        conventional_lead_time_weeks=20.0,
        machine_capacity_h_week=80.0,
        envelope_x_mm=500.0,
        envelope_y_mm=500.0,
        envelope_z_mm=1500.0,
    )

    assert ded["envelope_fit"] is True
    assert ded["wire_mass_kg_h"] > ded["deposited_kg_h"]
    assert ded["deposited_kg_h"] > 2.0
    assert ded["heat_input_kj_mm"] > 0
    assert ded["material_saved_pct"] > 50
    assert ded["lead_time_compression_pct"] > 90


def test_ded_recommendations_flag_envelope_feed_and_heat_risks() -> None:
    ded = estimate_ded_process(
        metrics={"material_volume_mm3": 100_000.0},
        material_density_g_cm3=7.99,
        full_weight_g=1000.0,
        full_time_s=3600.0,
        model_height_mm=1600.0,
        bbox_width_mm=600.0,
        bbox_depth_mm=450.0,
        layer_height_mm=2.0,
        bead_width_mm=8.0,
        print_speed_mm_s=5.0,
        wire_diameter_mm=1.0,
        wire_feed_m_min=1.0,
        arc_current_a=420.0,
        arc_voltage_v=34.0,
        arc_efficiency_pct=85.0,
        deposition_efficiency_pct=80.0,
        robot_utilization_pct=60.0,
        machining_allowance_pct=20.0,
        billet_buy_to_fly=4.0,
        conventional_lead_time_weeks=12.0,
        machine_capacity_h_week=60.0,
        envelope_x_mm=500.0,
        envelope_y_mm=500.0,
        envelope_z_mm=1500.0,
    )
    recommendations = build_ded_recommendations(ded)

    assert any(row["title"] == "DED envelope overflow" for row in recommendations)
    assert any("Wire feed" in row["title"] for row in recommendations)
    assert any(row["title"] == "High heat input" for row in recommendations)


def test_manufacturing_partner_fit_scores_urgent_low_volume_ded_candidate() -> None:
    ded = {
        "lead_time_compression_pct": 88.0,
        "material_saved_pct": 72.0,
        "envelope_fit": True,
        "cell_time_h": 24.0,
    }
    fit = assess_manufacturing_partner_fit(
        ded_analysis=ded,
        economics={"quoted_price": 4000.0, "build_hours": 24.0},
        commercial_fit={"status": "Fit"},
        application_type="Wear part / crusher component",
        conventional_route="Casting",
        urgency="Line-down / launch critical",
        qualification_level="Industrial",
        material_strategy="Wear-facing / gradient",
        finish_tolerance_mm=0.5,
        annual_quantity=3,
        ndt_required=True,
        redesign_required=True,
    )

    assert fit["score"] >= 70
    assert fit["verdict"] in {"Strong candidate", "Engineering review"}
    assert fit["value_delta"] > 0
    assert "Material transition and wear-zone strategy" in fit["deliverables"]


def test_manufacturing_partner_fit_flags_tight_tolerance_blocker() -> None:
    fit = assess_manufacturing_partner_fit(
        ded_analysis={
            "lead_time_compression_pct": 30.0,
            "material_saved_pct": 20.0,
            "envelope_fit": True,
            "cell_time_h": 12.0,
        },
        economics={"quoted_price": 1000.0, "build_hours": 12.0},
        commercial_fit={"status": "Review"},
        application_type="General machine component",
        conventional_route="Machining from billet",
        urgency="Normal procurement",
        qualification_level="Industrial",
        material_strategy="Single material",
        finish_tolerance_mm=0.05,
        annual_quantity=80,
        ndt_required=False,
        redesign_required=False,
    )

    assert fit["score"] < 65
    assert any("Tolerance" in blocker for blocker in fit["blockers"])


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
        commercial_fit={"status": "Fit", "findings": []},
        launch_score=94,
        quality_scorecard={
            "overall_score": 95,
            "overall_status": "Excellent",
            "rows": [
                {
                    "area": "Traceability",
                    "score": 100,
                    "status": "Locked",
                    "signal": "Plan ID abcdef1234567890",
                }
            ],
        },
        recommendations=[
            {
                "priority": "Ready",
                "area": "Release",
                "title": "Package ready for sign-off",
                "action": "Export release package.",
            }
        ],
        batch_scenarios=[
            {
                "quantity": 1,
                "unit_quote": 12.0,
                "batch_quote": 12.0,
                "batch_machine_hours": 1.0,
                "status": "Fit",
            }
        ],
        release_checklist=[
            {"item": "Traceability", "state": "Locked", "detail": "Plan ID abcdef1234567890"}
        ],
        optimization_playbook=[
            {
                "lever": "Pattern switch",
                "current": "Grid",
                "proposed": "Concentric",
                "estimated_delta": "12.0% less active-layer motion",
                "confidence": "High",
            }
        ],
        ded_analysis={
            "envelope_fit": True,
            "deposited_kg_h": 2.5,
            "required_wire_feed_m_min": 5.4,
            "heat_input_kj_mm": 0.6,
            "arc_energy_kwh": 4.2,
            "wire_required_kg": 1.3,
            "material_saved_kg": 3.1,
            "material_saved_pct": 70.0,
            "additive_lead_weeks": 0.2,
            "lead_time_compression_pct": 95.0,
        },
        partner_fit={
            "score": 86,
            "verdict": "Strong candidate",
            "application_type": "Wear part / crusher component",
            "conventional_route": "Casting",
            "service_unit_estimate": 1200.0,
            "conventional_unit_estimate": 1800.0,
            "value_delta": 600.0,
            "value_delta_pct": 33.3,
            "deliverables": ["DfAM redesign review", "Post-machining and inspection plan"],
        },
    )
    html = generate_job_dossier_html(dossier)

    assert "Executive Summary" in dossier
    assert "Estimated unit quote" in dossier
    assert "Quality score" in dossier
    assert "Quality Scorecard" in dossier
    assert "Commercial fit" in dossier
    assert "Launch Optimizer" in dossier
    assert "Batch Scenarios" in dossier
    assert "What-If Playbook" in dossier
    assert "DED Process Model" in dossier
    assert "Manufacturing Partner Fit" in dossier
    assert "Release Checklist" in dossier
    assert "<!doctype html>" in html
