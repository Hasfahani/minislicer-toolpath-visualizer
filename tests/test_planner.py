# Purpose: Tests layer planning, production segment generation, infill ranking, and fingerprints.
# Reason: Planner tests protect the deterministic contract between geometry, settings, and exports.
"""Tests for the MiniSlicer planning engine service."""

import pytest

from src.geometry import create_rectangle
from src.planner import (
    ToolpathSettings,
    alternating_layer_angle,
    build_plan_fingerprint,
    build_production_segments,
    plan_layer,
    rank_infill_patterns,
)


def _settings() -> ToolpathSettings:
    return ToolpathSettings(
        perimeter_count=2,
        perimeter_spacing_mm=0.45,
        infill_pattern="Zigzag",
        infill_spacing_mm=3.0,
        infill_angle_deg=45.0,
        optimize_infill=True,
        allow_line_reverse=True,
    )


def test_plan_layer_returns_complete_layer_plan() -> None:
    shape = create_rectangle(40.0, 30.0)
    plan = plan_layer(shape, shape, _settings(), layer=3)

    assert plan.layer == 3
    assert plan.boundary.length > 0
    assert len(plan.perimeters) == 2
    assert len(plan.infill_lines) > 0
    assert len(plan.segments) > 0
    assert all(segment.layer == 3 for segment in plan.segments)


def test_production_segments_cover_all_layers_when_inside_limit() -> None:
    shape = create_rectangle(30.0, 20.0)
    segments = build_production_segments(
        shape,
        shape,
        _settings(),
        layer_count=4,
        alternate_angle=True,
        layer_limit=10,
    )

    assert {segment.layer for segment in segments} == {1, 2, 3, 4}


def test_production_segments_fall_back_when_layer_limit_exceeded() -> None:
    shape = create_rectangle(30.0, 20.0)
    segments = build_production_segments(
        shape,
        shape,
        _settings(),
        layer_count=20,
        alternate_angle=True,
        layer_limit=10,
    )

    assert {segment.layer for segment in segments} == {1}


def test_alternating_layer_angle_switches_by_layer_parity() -> None:
    assert alternating_layer_angle(10.0, 1, True) == 45.0
    assert alternating_layer_angle(10.0, 2, True) == -45.0
    assert alternating_layer_angle(10.0, 2, False) == 10.0


def test_pattern_ranking_returns_scored_candidates() -> None:
    shape = create_rectangle(40.0, 30.0)
    ranking = rank_infill_patterns(
        shape,
        ["Parallel Lines", "Zigzag", "Grid"],
        _settings(),
    )

    assert [row["score"] for row in ranking] == sorted(
        [row["score"] for row in ranking],
        reverse=True,
    )
    assert {row["pattern"] for row in ranking} == {"Parallel Lines", "Zigzag", "Grid"}
    assert all(row["path_mm"] >= 0 for row in ranking)


def test_plan_fingerprint_is_stable_and_changes_with_settings() -> None:
    shape = create_rectangle(40.0, 30.0)
    first = build_plan_fingerprint(
        shape,
        _settings(),
        layer_count=10,
        process_mode="FDM",
        material="PLA",
    )
    second = build_plan_fingerprint(
        shape,
        _settings(),
        layer_count=10,
        process_mode="FDM",
        material="PLA",
    )
    changed = build_plan_fingerprint(
        shape,
        ToolpathSettings(
            perimeter_count=2,
            perimeter_spacing_mm=0.45,
            infill_pattern="Grid",
            infill_spacing_mm=3.0,
            infill_angle_deg=45.0,
        ),
        layer_count=10,
        process_mode="FDM",
        material="PLA",
    )

    assert first == second
    assert first != changed
    assert len(first) == 16


def test_toolpath_settings_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="infill_spacing"):
        ToolpathSettings(
            perimeter_count=2,
            perimeter_spacing_mm=0.45,
            infill_pattern="Grid",
            infill_spacing_mm=0.0,
            infill_angle_deg=45.0,
        )
