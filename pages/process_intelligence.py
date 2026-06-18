# Purpose: Provides MiniSlicer's authenticated company operations and process-intelligence workflow.
# Reason: Builds, models, recommendations, approvals, and audit records must persist across sessions.
"""Authenticated operational workspace for qualified additive-manufacturing data."""

from __future__ import annotations

import json
import secrets
from collections import Counter
from dataclasses import asdict

import pandas as pd
import streamlit as st

from src.company_auth import can_review, is_admin, require_user
from src.company_store import CompanyStore, model_version_for_records
from src.process_intelligence import (
    MIN_TRAINING_BUILDS,
    BuildFeatures,
    BuildRecord,
    ParameterEnvelope,
    ProcessParameters,
    ProcessRecommendation,
    ProcessRecommendationEngine,
    QualityOutcome,
    dataset_summary,
    evaluate_recommendation_engine,
    parse_build_records_jsonl,
)

st.set_page_config(
    page_title="MiniSlicer - Company Operations",
    page_icon=":material/factory:",
    layout="wide",
)

store = CompanyStore()
user = require_user(store)

st.title("Company Operations")
st.caption(
    "Persistent qualified-build data, controlled model promotion, bounded recommendations, "
    "engineering approvals, and immutable audit history."
)
st.warning(
    "This application supports planning and controlled process development. "
    "It does not autonomously control machinery or replace a qualified procedure specification."
)


def example_record() -> BuildRecord:
    return BuildRecord(
        build_id="example-build-001",
        machine_id="DED-01",
        material_id="steel-wire-a",
        material_batch_id="wire-batch-2026-01",
        geometry_family="wall-coupon",
        started_at="2026-06-18T08:00:00+00:00",
        plan_fingerprint="example-plan",
        features=BuildFeatures(850, 520, 220, 130, 8, 0.10, 1.2, 1.0),
        parameters=ProcessParameters(7.2, 5.6, 180, 23.5, 220),
        outcome=QualityOutcome(True, 0.30, 0.20, 25, 88, 0),
    )


def recommendation_payload(recommendation: ProcessRecommendation) -> dict[str, object]:
    return {
        "status": recommendation.status,
        "parameters": asdict(recommendation.parameters) if recommendation.parameters else None,
        "confidence": recommendation.confidence,
        "applicability_distance": recommendation.applicability_distance,
        "evidence_build_ids": list(recommendation.evidence_build_ids),
        "warnings": list(recommendation.warnings),
    }


overview_tab, builds_tab, models_tab, recommendations_tab, audit_tab, admin_tab = st.tabs(
    ["Overview", "Builds", "Models", "Recommendations", "Audit", "Administration"]
)

with overview_tab:
    counts = store.counts()
    columns = st.columns(6)
    columns[0].metric("Active users", counts["users"])
    columns[1].metric("Build records", counts["builds"])
    columns[2].metric("Builds awaiting review", counts["pending_builds"])
    columns[3].metric("Approved models", counts["approved_models"])
    columns[4].metric("Recommendations", counts["recommendations"])
    columns[5].metric("Recommendations awaiting review", counts["pending_recommendations"])

    st.markdown(
        """
        **Controlled workflow**

        1. Operators submit completed build and inspection records.
        2. Engineers approve or reject each build.
        3. Engineers create a candidate model snapshot from approved builds.
        4. An administrator promotes the candidate after reviewing chronological evaluation.
        5. Operators generate bounded recommendations from the approved snapshot.
        6. Engineers approve a recommendation before it becomes a released starting recipe.
        """
    )

with builds_tab:
    st.subheader("Qualified-build records")
    if user.role in {"admin", "engineer", "operator"}:
        uploaded = st.file_uploader(
            "Submit build records (JSONL)",
            type=["jsonl", "json"],
            help="Submitting an existing build ID replaces it and resets its approval.",
        )
        col_template, col_submit = st.columns([1, 1])
        col_template.download_button(
            "Download record template",
            data=json.dumps(example_record().to_dict(), sort_keys=True) + "\n",
            file_name="minislicer-build-record-template.jsonl",
            mime="application/x-ndjson",
        )
        if uploaded is not None and col_submit.button("Store submitted builds", type="primary"):
            try:
                records = parse_build_records_jsonl(uploaded.getvalue().decode("utf-8-sig"))
                result = store.submit_build_records(records, actor=user.username)
            except (UnicodeDecodeError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Stored {result['inserted']} new and {result['updated']} replacement records."
                )
                st.rerun()

    build_state = st.selectbox("Build-state filter", ["all", "submitted", "approved", "rejected"])
    build_rows = store.list_builds(state=None if build_state == "all" else build_state)
    st.dataframe(pd.DataFrame(build_rows), hide_index=True, width="stretch")

    if can_review(user):
        pending = store.list_builds(state="submitted")
        if pending:
            st.markdown("#### Engineering review")
            selected_build = st.selectbox(
                "Build awaiting review",
                [row["build_id"] for row in pending],
            )
            review_note = st.text_area("Build review note")
            approve_col, reject_col = st.columns(2)
            if approve_col.button("Approve build", type="primary"):
                store.review_build(
                    selected_build,
                    "approved",
                    actor=user.username,
                    note=review_note,
                )
                st.rerun()
            if reject_col.button("Reject build"):
                store.review_build(
                    selected_build,
                    "rejected",
                    actor=user.username,
                    note=review_note,
                )
                st.rerun()
        else:
            st.info("No builds are awaiting engineering review.")

with models_tab:
    st.subheader("Model registry")
    approved_records = store.approved_records()
    pair_counts = Counter((record.machine_id, record.material_id) for record in approved_records)

    if can_review(user) and pair_counts:
        pair_labels = {
            f"{machine} / {material} ({count} approved builds)": (machine, material)
            for (machine, material), count in sorted(pair_counts.items())
        }
        selected_pair = st.selectbox("Training domain", list(pair_labels))
        machine_id, material_id = pair_labels[selected_pair]
        neighbors = st.number_input("Neighbor count", 1, 20, 5)
        maximum_distance = st.number_input("Maximum applicability distance", 0.1, 10.0, 3.0)
        domain_records = store.approved_records(
            machine_id=machine_id,
            material_id=material_id,
        )
        if len(domain_records) < MIN_TRAINING_BUILDS:
            st.warning(
                f"{len(domain_records)} approved builds are available; "
                f"{MIN_TRAINING_BUILDS} are required."
            )
        elif st.button("Register candidate model snapshot", type="primary"):
            version = model_version_for_records(
                domain_records,
                machine_id=machine_id,
                material_id=material_id,
                neighbors=int(neighbors),
                max_applicability_distance=float(maximum_distance),
            )
            summary = dataset_summary(domain_records)
            evaluation = evaluate_recommendation_engine(
                domain_records,
                neighbors=int(neighbors),
                max_applicability_distance=float(maximum_distance),
            )
            metrics = {
                **summary,
                "neighbors": int(neighbors),
                "max_applicability_distance": float(maximum_distance),
                "evaluation": evaluation,
            }
            try:
                store.register_model(
                    model_version=version,
                    machine_id=machine_id,
                    material_id=material_id,
                    build_ids=[record.build_id for record in domain_records],
                    metrics=metrics,
                    actor=user.username,
                )
            except Exception as exc:
                st.error(str(exc))
            else:
                st.success(f"Registered candidate {version}.")
                st.rerun()

    model_rows = store.list_models()
    display_models = [
        {
            "model_version": row["model_version"],
            "machine_id": row["machine_id"],
            "material_id": row["material_id"],
            "state": row["state"],
            "build_count": len(row["build_ids"]),
            "evaluation_status": row["metrics"].get("evaluation", {}).get("status"),
            "coverage": row["metrics"].get("evaluation", {}).get("coverage"),
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "reviewed_by": row["reviewed_by"],
        }
        for row in model_rows
    ]
    st.dataframe(pd.DataFrame(display_models), hide_index=True, width="stretch")

    if is_admin(user):
        candidates = [row for row in model_rows if row["state"] == "candidate"]
        if candidates:
            st.markdown("#### Administrator model promotion")
            selected_model = st.selectbox(
                "Candidate model",
                [row["model_version"] for row in candidates],
            )
            candidate = next(row for row in candidates if row["model_version"] == selected_model)
            st.json(candidate["metrics"])
            model_note = st.text_area("Model review note")
            approve_model_col, retire_model_col = st.columns(2)
            if approve_model_col.button("Approve model", type="primary"):
                store.review_model(selected_model, "approved", actor=user.username, note=model_note)
                st.rerun()
            if retire_model_col.button("Retire candidate"):
                store.review_model(selected_model, "retired", actor=user.username, note=model_note)
                st.rerun()

with recommendations_tab:
    st.subheader("Controlled parameter recommendations")
    approved_models = store.list_models(state="approved")
    if not approved_models:
        st.info("No approved model is available. Promote a reviewed model snapshot first.")
    elif user.role in {"admin", "engineer", "operator"}:
        model_labels = {
            f"{row['machine_id']} / {row['material_id']} - {row['model_version']}": row
            for row in approved_models
        }
        selected_model_label = st.selectbox("Approved model", list(model_labels))
        model = model_labels[selected_model_label]

        st.markdown("#### Candidate job")
        feature_columns = st.columns(4)
        feature_values = {
            "part_volume_cm3": feature_columns[0].number_input("Part volume (cm3)", 0.1, value=850.0),
            "surface_area_cm2": feature_columns[1].number_input("Surface area (cm2)", 0.1, value=520.0),
            "height_mm": feature_columns[2].number_input("Height (mm)", 0.1, value=220.0),
            "max_section_mm": feature_columns[3].number_input("Maximum section (mm)", 0.1, value=130.0),
        }
        feature_columns_two = st.columns(4)
        feature_values.update({
            "wall_thickness_mm": feature_columns_two[0].number_input("Wall thickness (mm)", 0.1, value=8.0),
            "overhang_fraction": feature_columns_two[1].number_input(
                "Overhang fraction", 0.0, 1.0, value=0.10, step=0.01
            ),
            "wire_diameter_mm": feature_columns_two[2].number_input("Wire diameter (mm)", 0.1, value=1.2),
            "layer_height_mm": feature_columns_two[3].number_input("Layer height (mm)", 0.1, value=1.0),
        })

        defaults = {
            "travel_speed_mm_s": (4.0, 12.0),
            "wire_feed_m_min": (3.0, 9.0),
            "arc_current_a": (120.0, 260.0),
            "arc_voltage_v": (18.0, 32.0),
            "interpass_limit_c": (150.0, 350.0),
        }
        envelope_values: dict[str, tuple[float, float]] = {}
        with st.expander("Engineer-approved parameter envelope", expanded=False):
            for name, values in defaults.items():
                columns = st.columns(2)
                envelope_values[name] = (
                    columns[0].number_input(f"{name} minimum", 0.01, value=values[0]),
                    columns[1].number_input(f"{name} maximum", 0.01, value=values[1]),
                )

        if st.button("Generate and log recommendation", type="primary"):
            records = store.approved_records(build_ids=model["build_ids"])
            metrics = model["metrics"]
            engine = ProcessRecommendationEngine(
                neighbors=int(metrics.get("neighbors", 5)),
                max_applicability_distance=float(metrics.get("max_applicability_distance", 3.0)),
            ).fit(
                records,
                machine_id=model["machine_id"],
                material_id=model["material_id"],
            )
            features = BuildFeatures(**feature_values)
            envelope = ParameterEnvelope(
                minimum=ProcessParameters(**{
                    name: values[0] for name, values in envelope_values.items()
                }),
                maximum=ProcessParameters(**{
                    name: values[1] for name, values in envelope_values.items()
                }),
            )
            recommendation = engine.recommend(features, envelope=envelope)
            recommendation_id = f"rec-{secrets.token_hex(8)}"
            request_payload = {
                "features": asdict(features),
                "envelope": {
                    "minimum": asdict(envelope.minimum),
                    "maximum": asdict(envelope.maximum),
                },
            }
            result_payload = recommendation_payload(recommendation)
            store.log_recommendation(
                recommendation_id=recommendation_id,
                model_version=model["model_version"],
                machine_id=model["machine_id"],
                material_id=model["material_id"],
                request=request_payload,
                result=result_payload,
                actor=user.username,
            )
            st.session_state["_latest_recommendation"] = {
                "recommendation_id": recommendation_id,
                **result_payload,
            }

        latest = st.session_state.get("_latest_recommendation")
        if latest:
            st.markdown(f"#### {latest['status']}")
            st.json(latest)

    recommendation_rows = store.list_recommendations()
    display_recommendations = [
        {
            "recommendation_id": row["recommendation_id"],
            "model_version": row["model_version"],
            "machine_id": row["machine_id"],
            "material_id": row["material_id"],
            "result_status": row["result"].get("status"),
            "confidence": row["result"].get("confidence"),
            "state": row["state"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "reviewed_by": row["reviewed_by"],
        }
        for row in recommendation_rows
    ]
    st.dataframe(pd.DataFrame(display_recommendations), hide_index=True, width="stretch")

    if can_review(user):
        pending_recommendations = [
            row for row in recommendation_rows if row["state"] == "generated"
        ]
        if pending_recommendations:
            st.markdown("#### Engineering recommendation release")
            selected_recommendation = st.selectbox(
                "Recommendation awaiting review",
                [row["recommendation_id"] for row in pending_recommendations],
            )
            selected = next(
                row for row in pending_recommendations
                if row["recommendation_id"] == selected_recommendation
            )
            st.json({"request": selected["request"], "result": selected["result"]})
            recommendation_note = st.text_area("Recommendation review note")
            approve_rec_col, reject_rec_col = st.columns(2)
            if approve_rec_col.button("Approve recommendation", type="primary"):
                store.review_recommendation(
                    selected_recommendation,
                    "approved",
                    actor=user.username,
                    note=recommendation_note,
                )
                st.rerun()
            if reject_rec_col.button("Reject recommendation"):
                store.review_recommendation(
                    selected_recommendation,
                    "rejected",
                    actor=user.username,
                    note=recommendation_note,
                )
                st.rerun()

with audit_tab:
    st.subheader("Immutable operational audit")
    if user.role in {"admin", "engineer", "viewer"}:
        st.dataframe(pd.DataFrame(store.audit_events()), hide_index=True, width="stretch")
    else:
        st.info("Audit history is available to engineers, administrators, and read-only reviewers.")

with admin_tab:
    st.subheader("Users and access")
    if not is_admin(user):
        st.info("Only administrators can manage company users.")
    else:
        with st.form("create-user"):
            new_username = st.text_input("New username")
            new_password = st.text_input("Temporary password", type="password")
            new_role = st.selectbox("Role", ["operator", "engineer", "viewer", "admin"])
            create_submitted = st.form_submit_button("Create user", type="primary")
        if create_submitted:
            try:
                store.create_user(
                    new_username,
                    new_password,
                    new_role,
                    actor=user.username,
                )
            except Exception as exc:
                st.error(str(exc))
            else:
                st.success(f"Created {new_username.strip().lower()}.")
                st.rerun()

        users = store.list_users()
        st.dataframe(pd.DataFrame(users), hide_index=True, width="stretch")
        other_users = [row for row in users if row["username"] != user.username]
        if other_users:
            selected_user = st.selectbox(
                "User status",
                [row["username"] for row in other_users],
            )
            selected_user_row = next(row for row in other_users if row["username"] == selected_user)
            active = bool(selected_user_row["active"])
            if st.button("Deactivate user" if active else "Reactivate user"):
                store.set_user_active(selected_user, not active, actor=user.username)
                st.rerun()
