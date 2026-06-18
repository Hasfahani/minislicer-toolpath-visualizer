# Purpose: Tests conservative process learning, traceability, and applicability safeguards.
# Reason: An industrial recommendation feature must fail closed outside qualified evidence.
"""Tests for MiniSlicer's process-intelligence foundation."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from src.process_intelligence import (
    MIN_TRAINING_BUILDS,
    BuildFeatures,
    BuildRecord,
    ParameterEnvelope,
    ProcessParameters,
    ProcessRecommendationEngine,
    QualityOutcome,
    dataset_summary,
    grouped_time_split,
    load_build_records_jsonl,
    save_build_record_jsonl,
)


def _features(index: int = 0) -> BuildFeatures:
    return BuildFeatures(
        part_volume_cm3=800.0 + index * 10,
        surface_area_cm2=500.0 + index * 4,
        height_mm=200.0 + index,
        max_section_mm=120.0 + index * 0.5,
        wall_thickness_mm=8.0 + index * 0.05,
        overhang_fraction=0.1 + index * 0.002,
        wire_diameter_mm=1.2,
        layer_height_mm=1.0,
    )


def _parameters(index: int = 0) -> ProcessParameters:
    return ProcessParameters(
        travel_speed_mm_s=7.0 + index * 0.02,
        wire_feed_m_min=5.5 + index * 0.01,
        arc_current_a=175.0 + index * 0.2,
        arc_voltage_v=23.0 + index * 0.01,
        interpass_limit_c=220.0 + index * 0.1,
    )


def _outcome(*, accepted: bool = True) -> QualityOutcome:
    return QualityOutcome(
        accepted=accepted,
        dimensional_error_mm=0.25,
        porosity_pct=0.15,
        surface_roughness_ra_um=22.0,
        deposition_efficiency_pct=88.0,
        interruption_count=0,
    )


def _record(index: int, *, accepted: bool = True, machine_id: str = "DED-01") -> BuildRecord:
    started = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)
    return BuildRecord(
        build_id=f"build-{index:03d}",
        machine_id=machine_id,
        material_id="steel-wire-a",
        material_batch_id=f"batch-{index // 4}",
        geometry_family="wall-coupon" if index % 2 == 0 else "box-section",
        started_at=started.isoformat(),
        features=_features(index),
        parameters=_parameters(index),
        outcome=_outcome(accepted=accepted),
        plan_fingerprint=f"plan-{index:03d}",
    )


def _envelope() -> ParameterEnvelope:
    return ParameterEnvelope(
        minimum=ProcessParameters(4.0, 3.0, 120.0, 18.0, 150.0),
        maximum=ProcessParameters(12.0, 9.0, 260.0, 32.0, 350.0),
    )


def test_jsonl_roundtrip_is_traceable(tmp_path) -> None:
    path = tmp_path / "builds.jsonl"
    record = _record(0)
    save_build_record_jsonl(path, record)

    loaded = load_build_records_jsonl(path)

    assert loaded == [record]
    assert loaded[0].plan_fingerprint == "plan-000"


def test_rejected_builds_are_not_used_as_recipes() -> None:
    records = [_record(index) for index in range(MIN_TRAINING_BUILDS)]
    records.extend(_record(100 + index, accepted=False) for index in range(3))
    engine = ProcessRecommendationEngine().fit(
        records,
        machine_id="DED-01",
        material_id="steel-wire-a",
    )

    assert engine.training_build_count == MIN_TRAINING_BUILDS


def test_fit_requires_enough_accepted_machine_material_evidence() -> None:
    records = [_record(index) for index in range(MIN_TRAINING_BUILDS - 1)]

    with pytest.raises(ValueError, match="accepted builds"):
        ProcessRecommendationEngine().fit(
            records,
            machine_id="DED-01",
            material_id="steel-wire-a",
        )


def test_nearby_job_gets_bounded_recommendation() -> None:
    records = [_record(index) for index in range(20)]
    engine = ProcessRecommendationEngine(neighbors=5).fit(
        records,
        machine_id="DED-01",
        material_id="steel-wire-a",
    )

    recommendation = engine.recommend(_features(8), envelope=_envelope())

    assert recommendation.status in {"Recommend", "Engineering review"}
    assert recommendation.parameters is not None
    assert recommendation.evidence_build_ids
    assert 0.0 <= recommendation.confidence <= 1.0
    assert 4.0 <= recommendation.parameters.travel_speed_mm_s <= 12.0


def test_out_of_domain_job_fails_closed() -> None:
    records = [_record(index) for index in range(20)]
    engine = ProcessRecommendationEngine(max_applicability_distance=2.0).fit(
        records,
        machine_id="DED-01",
        material_id="steel-wire-a",
    )
    distant = replace(
        _features(0),
        part_volume_cm3=100_000.0,
        height_mm=1400.0,
        max_section_mm=900.0,
    )

    recommendation = engine.recommend(distant, envelope=_envelope())

    assert recommendation.status == "Insufficient evidence"
    assert recommendation.parameters is None
    assert recommendation.confidence == 0.0


def test_grouped_time_split_keeps_builds_unique_and_chronological() -> None:
    records = [_record(index) for index in range(20)]

    train, test = grouped_time_split(reversed(records), test_fraction=0.25)

    assert len(train) == 15
    assert len(test) == 5
    assert {row.build_id for row in train}.isdisjoint(row.build_id for row in test)
    assert max(row.started_at for row in train) < min(row.started_at for row in test)


def test_dataset_summary_reports_coverage() -> None:
    records = [_record(index) for index in range(5)]
    records.append(_record(8, accepted=False, machine_id="DED-02"))

    summary = dataset_summary(records)

    assert summary["build_count"] == 6
    assert summary["accepted_build_count"] == 5
    assert summary["rejected_build_count"] == 1
    assert summary["machine_count"] == 2
