# Purpose: Streamlit workspace for qualified-build datasets and bounded DED recommendations.
# Reason: Process learning must be inspectable, evidence-backed, and separate from machine motion.
"""Process-intelligence workspace for MiniSlicer."""

from __future__ import annotations

import json
from collections import Counter

import streamlit as st

from src.process_intelligence import (
    MIN_TRAINING_BUILDS,
    BuildFeatures,
    BuildRecord,
    ParameterEnvelope,
    ProcessParameters,
    ProcessRecommendationEngine,
    QualityOutcome,
    dataset_summary,
    parse_build_records_jsonl,
)

st.set_page_config(
    page_title="MiniSlicer - Process Intelligence",
    page_icon=":material/model_training:",
    layout="wide",
)

st.title("Process Intelligence")
st.caption(
    "Learn conservative DED starting parameters from completed, inspected builds. "
    "Toolpaths, hard limits, and release approval remain deterministic."
)

st.warning(
    "Advisory output only. A recommendation is not a qualified procedure specification "
    "and must be verified through a monitored development build."
)

uploaded = st.file_uploader(
    "Qualified build records (JSONL)",
    type=["jsonl", "json"],
    help="One versioned BuildRecord per line. Keep raw sensor streams outside this file and link by build_id.",
)


def _example_record() -> BuildRecord:
    return BuildRecord(
        build_id="example-build-001",
        machine_id="DED-01",
        material_id="steel-wire-a",
        material_batch_id="wire-batch-2026-01",
        geometry_family="wall-coupon",
        started_at="2026-06-18T08:00:00+00:00",
        plan_fingerprint="example-plan",
        features=BuildFeatures(
            part_volume_cm3=850.0,
            surface_area_cm2=520.0,
            height_mm=220.0,
            max_section_mm=130.0,
            wall_thickness_mm=8.0,
            overhang_fraction=0.10,
            wire_diameter_mm=1.2,
            layer_height_mm=1.0,
        ),
        parameters=ProcessParameters(
            travel_speed_mm_s=7.2,
            wire_feed_m_min=5.6,
            arc_current_a=180.0,
            arc_voltage_v=23.5,
            interpass_limit_c=220.0,
        ),
        outcome=QualityOutcome(
            accepted=True,
            dimensional_error_mm=0.30,
            porosity_pct=0.20,
            surface_roughness_ra_um=25.0,
            deposition_efficiency_pct=88.0,
            interruption_count=0,
        ),
    )


st.download_button(
    "Download record template",
    data=json.dumps(_example_record().to_dict(), sort_keys=True) + "\n",
    file_name="minislicer-build-record-template.jsonl",
    mime="application/x-ndjson",
)

records: list[BuildRecord] = []
if uploaded is not None:
    try:
        records = parse_build_records_jsonl(uploaded.getvalue().decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        st.error(f"Dataset could not be loaded: {exc}")

if not records:
    st.info(
        "No qualified dataset loaded. Start by recording complete builds, machine/material IDs, "
        "commanded parameters, inspection results, and accepted/rejected disposition."
    )
    st.markdown(
        """
        **Minimum responsible pilot**

        1. Freeze one machine and one material specification.
        2. Print controlled coupons across the approved process window.
        3. Record machine telemetry and material batch IDs.
        4. Measure dimensions, porosity, roughness, efficiency, and interruptions.
        5. Collect at least 12 accepted builds before enabling recommendations.
        6. Validate chronologically on complete unseen builds.
        """
    )
    st.stop()

summary = dataset_summary(records)
summary_columns = st.columns(6)
summary_columns[0].metric("Builds", summary["build_count"])
summary_columns[1].metric("Accepted", summary["accepted_build_count"])
summary_columns[2].metric("Rejected", summary["rejected_build_count"])
summary_columns[3].metric("Machines", summary["machine_count"])
summary_columns[4].metric("Materials", summary["material_count"])
summary_columns[5].metric("Geometry families", summary["geometry_family_count"])

pair_counts = Counter(
    (record.machine_id, record.material_id)
    for record in records
    if record.outcome.accepted
)
pairs = sorted(pair_counts)
if not pairs:
    st.error("The dataset has no accepted builds. Recommendations remain disabled.")
    st.stop()

pair_labels = {
    f"{machine} / {material} ({pair_counts[(machine, material)]} accepted)": (machine, material)
    for machine, material in pairs
}
selected_label = st.selectbox("Qualified machine / material domain", list(pair_labels))
machine_id, material_id = pair_labels[selected_label]
accepted_count = pair_counts[(machine_id, material_id)]

if accepted_count < MIN_TRAINING_BUILDS:
    st.warning(
        f"This domain has {accepted_count} accepted builds; {MIN_TRAINING_BUILDS} are required. "
        "Continue controlled data collection."
    )
    st.stop()

st.subheader("Candidate job")
geometry_columns = st.columns(4)
part_volume = geometry_columns[0].number_input("Part volume (cm3)", 0.1, value=850.0)
surface_area = geometry_columns[1].number_input("Surface area (cm2)", 0.1, value=520.0)
height = geometry_columns[2].number_input("Height (mm)", 0.1, value=220.0)
max_section = geometry_columns[3].number_input("Maximum section (mm)", 0.1, value=130.0)

process_columns = st.columns(4)
wall_thickness = process_columns[0].number_input("Wall thickness (mm)", 0.1, value=8.0)
overhang_fraction = process_columns[1].number_input(
    "Overhang fraction", 0.0, 1.0, value=0.10, step=0.01
)
wire_diameter = process_columns[2].number_input("Wire diameter (mm)", 0.1, value=1.2)
layer_height = process_columns[3].number_input("Layer height (mm)", 0.1, value=1.0)

with st.expander("Engineer-approved parameter envelope", expanded=False):
    envelope_rows = {
        "travel_speed_mm_s": st.columns(2),
        "wire_feed_m_min": st.columns(2),
        "arc_current_a": st.columns(2),
        "arc_voltage_v": st.columns(2),
        "interpass_limit_c": st.columns(2),
    }
    defaults = {
        "travel_speed_mm_s": (4.0, 12.0),
        "wire_feed_m_min": (3.0, 9.0),
        "arc_current_a": (120.0, 260.0),
        "arc_voltage_v": (18.0, 32.0),
        "interpass_limit_c": (150.0, 350.0),
    }
    envelope_values: dict[str, tuple[float, float]] = {}
    for name, columns in envelope_rows.items():
        low_default, high_default = defaults[name]
        low = columns[0].number_input(f"{name} minimum", 0.01, value=low_default)
        high = columns[1].number_input(f"{name} maximum", 0.01, value=high_default)
        envelope_values[name] = (low, high)

if st.button("Generate bounded recommendation", type="primary"):
    try:
        engine = ProcessRecommendationEngine().fit(
            records,
            machine_id=machine_id,
            material_id=material_id,
        )
        recommendation = engine.recommend(
            BuildFeatures(
                part_volume_cm3=part_volume,
                surface_area_cm2=surface_area,
                height_mm=height,
                max_section_mm=max_section,
                wall_thickness_mm=wall_thickness,
                overhang_fraction=overhang_fraction,
                wire_diameter_mm=wire_diameter,
                layer_height_mm=layer_height,
            ),
            envelope=ParameterEnvelope(
                minimum=ProcessParameters(**{
                    name: values[0] for name, values in envelope_values.items()
                }),
                maximum=ProcessParameters(**{
                    name: values[1] for name, values in envelope_values.items()
                }),
            ),
        )
    except (RuntimeError, ValueError) as exc:
        st.error(str(exc))
    else:
        st.subheader(recommendation.status)
        result_columns = st.columns(3)
        result_columns[0].metric("Confidence", f"{recommendation.confidence * 100:.1f}%")
        result_columns[1].metric(
            "Applicability distance", f"{recommendation.applicability_distance:.2f}"
        )
        result_columns[2].metric("Evidence builds", len(recommendation.evidence_build_ids))

        if recommendation.parameters is not None:
            st.dataframe(
                {
                    "Parameter": [
                        "Travel speed",
                        "Wire feed",
                        "Arc current",
                        "Arc voltage",
                        "Interpass limit",
                    ],
                    "Recommended": [
                        f"{recommendation.parameters.travel_speed_mm_s:.2f} mm/s",
                        f"{recommendation.parameters.wire_feed_m_min:.2f} m/min",
                        f"{recommendation.parameters.arc_current_a:.1f} A",
                        f"{recommendation.parameters.arc_voltage_v:.1f} V",
                        f"{recommendation.parameters.interpass_limit_c:.1f} C",
                    ],
                },
                hide_index=True,
                width="stretch",
            )
        for warning in recommendation.warnings:
            st.warning(warning)
        st.caption("Evidence: " + ", ".join(recommendation.evidence_build_ids))
