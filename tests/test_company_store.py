# Purpose: Verifies durable users, build approvals, model lifecycle, recommendations, and audit logs.
# Reason: The operational database is the trust boundary for company use.
"""Tests for the MiniSlicer company operational store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.company_store import CompanyStore, model_version_for_records
from src.process_intelligence import (
    BuildFeatures,
    BuildRecord,
    ProcessParameters,
    QualityOutcome,
    evaluate_recommendation_engine,
)


def _record(index: int) -> BuildRecord:
    return BuildRecord(
        build_id=f"build-{index}",
        machine_id="DED-01",
        material_id="steel-a",
        material_batch_id="batch-a",
        geometry_family="wall",
        started_at=(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)).isoformat(),
        features=BuildFeatures(100 + index, 50 + index, 20 + index, 10, 2, 0.1, 1.2, 1.0),
        parameters=ProcessParameters(7, 5.5, 180, 23, 220),
        outcome=QualityOutcome(True, 0.2, 0.1, 20, 88),
        plan_fingerprint=f"plan-{index}",
    )


def test_user_authentication_and_audit(tmp_path) -> None:
    store = CompanyStore(tmp_path / "company.db")
    store.create_user("Admin", "correct horse battery", "admin", actor="system")

    assert store.authenticate("admin", "wrong password") is None
    user = store.authenticate("ADMIN", "correct horse battery")

    assert user is not None
    assert user.role == "admin"
    assert any(event["action"] == "session.login" for event in store.audit_events())


def test_build_submission_and_review_roundtrip(tmp_path) -> None:
    store = CompanyStore(tmp_path / "company.db")
    records = [_record(1), _record(2)]

    result = store.submit_build_records(records, actor="operator")
    store.review_build("build-1", "approved", actor="engineer", note="Inspection passed.")

    assert result == {"inserted": 2, "updated": 0}
    assert len(store.list_builds(state="submitted")) == 1
    approved = store.approved_records(machine_id="DED-01", material_id="steel-a")
    assert [record.build_id for record in approved] == ["build-1"]


def test_model_approval_retires_previous_domain_model(tmp_path) -> None:
    store = CompanyStore(tmp_path / "company.db")
    records = [_record(index) for index in range(12)]
    store.submit_build_records(records, actor="operator")
    for record in records:
        store.review_build(record.build_id, "approved", actor="engineer")

    version_one = model_version_for_records(
        records,
        machine_id="DED-01",
        material_id="steel-a",
        neighbors=5,
        max_applicability_distance=3.0,
    )
    store.register_model(
        model_version=version_one,
        machine_id="DED-01",
        material_id="steel-a",
        build_ids=[record.build_id for record in records],
        metrics={"build_count": 12},
        actor="engineer",
    )
    store.review_model(version_one, "approved", actor="admin")

    extra = _record(20)
    store.submit_build_records([extra], actor="operator")
    store.review_build(extra.build_id, "approved", actor="engineer")
    all_records = [*records, extra]
    version_two = model_version_for_records(
        all_records,
        machine_id="DED-01",
        material_id="steel-a",
        neighbors=5,
        max_applicability_distance=3.0,
    )
    store.register_model(
        model_version=version_two,
        machine_id="DED-01",
        material_id="steel-a",
        build_ids=[record.build_id for record in all_records],
        metrics={"build_count": 13},
        actor="engineer",
    )
    store.review_model(version_two, "approved", actor="admin")

    states = {model["model_version"]: model["state"] for model in store.list_models()}
    assert states[version_one] == "retired"
    assert states[version_two] == "approved"


def test_recommendation_lifecycle_is_audited(tmp_path) -> None:
    store = CompanyStore(tmp_path / "company.db")
    records = [_record(index) for index in range(12)]
    store.submit_build_records(records, actor="operator")
    for record in records:
        store.review_build(record.build_id, "approved", actor="engineer")
    version = model_version_for_records(
        records,
        machine_id="DED-01",
        material_id="steel-a",
        neighbors=5,
        max_applicability_distance=3.0,
    )
    store.register_model(
        model_version=version,
        machine_id="DED-01",
        material_id="steel-a",
        build_ids=[record.build_id for record in records],
        metrics={},
        actor="engineer",
    )
    store.review_model(version, "approved", actor="admin")
    store.log_recommendation(
        recommendation_id="rec-1",
        model_version=version,
        machine_id="DED-01",
        material_id="steel-a",
        request={"part_volume_cm3": 120},
        result={"status": "Recommend"},
        actor="operator",
    )
    store.review_recommendation("rec-1", "approved", actor="engineer")

    recommendation = store.list_recommendations()[0]
    assert recommendation["state"] == "approved"
    assert recommendation["reviewed_by"] == "engineer"
    assert store.counts()["pending_recommendations"] == 0


def test_grouped_model_evaluation_reports_parameter_error() -> None:
    records = [_record(index) for index in range(20)]

    metrics = evaluate_recommendation_engine(records)

    assert metrics["status"] == "evaluated"
    assert metrics["train_builds"] == 16
    assert metrics["test_builds"] == 4
    assert metrics["coverage"] > 0
    assert set(metrics["mae"]) == {
        "travel_speed_mm_s",
        "wire_feed_m_min",
        "arc_current_a",
        "arc_voltage_v",
        "interpass_limit_c",
    }
