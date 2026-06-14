# Purpose: Tests sample jobs and JSON-export re-apply mapping for sidebar defaults.
# Reason: Scenario tests keep one-click demos and restored planning packages reliable.
"""Tests for the sample-job scenarios and config re-apply mapping."""

from __future__ import annotations

from src.scenarios import (
    OVERRIDE_KEYS,
    SAMPLE_JOBS,
    as_float,
    as_int,
    option_index,
    overrides_from_export,
    scenario_names,
    scenario_overrides,
)


def test_every_sample_job_uses_known_override_keys() -> None:
    for name, job in SAMPLE_JOBS.items():
        unknown = set(job) - set(OVERRIDE_KEYS)
        assert not unknown, f"{name} has unknown override keys: {unknown}"


def test_sample_jobs_define_a_process_and_shape() -> None:
    for name, job in SAMPLE_JOBS.items():
        assert job.get("process_mode") in {"FDM", "Metal (LPBF/DED)"}, name
        assert "shape_type" in job, name


def test_scenario_overrides_returns_independent_copy() -> None:
    name = scenario_names()[0]
    first = scenario_overrides(name)
    first["perimeter_count"] = 999
    second = scenario_overrides(name)
    assert second["perimeter_count"] != 999


def test_scenario_overrides_unknown_name_is_empty() -> None:
    assert scenario_overrides("does not exist") == {}


def test_option_index_handles_missing_and_present() -> None:
    options = ["a", "b", "c"]
    assert option_index(options, "b") == 1
    assert option_index(options, "z", fallback=2) == 2
    assert option_index(options, None) == 0


def test_numeric_coercion_helpers() -> None:
    assert as_int("4", 1) == 4
    assert as_int(4.6, 1) == 5
    assert as_int(None, 7) == 7
    assert as_int("oops", 3) == 3
    assert as_float("2.5", 1.0) == 2.5
    assert as_float(None, 1.5) == 1.5
    assert as_float("nope", 0.5) == 0.5


def _sample_export() -> dict:
    return {
        "shape_type": "Rectangle",
        "process_mode": "FDM",
        "profile": "Strong",
        "perimeter_count": 4,
        "infill_pattern": "Honeycomb",
        "infill_spacing_mm": 2.5,
        "layer_height_mm": 0.2,
        "model_height_mm": 30.0,
        "material": "PETG",
        "plate": {"enabled": True, "width_mm": 300.0, "depth_mm": 300.0},
        "job_metadata": {"job_name": "Bracket", "customer_name": "Acme"},
        "business_assumptions": {"batch_quantity": 10, "target_unit_price": 45.0},
    }


def test_overrides_from_export_maps_core_fields() -> None:
    overrides = overrides_from_export(_sample_export())
    assert overrides["profile"] == "Strong"
    assert overrides["process_mode"] == "FDM"
    assert overrides["perimeter_count"] == 4
    assert overrides["infill_pattern"] == "Honeycomb"
    assert overrides["infill_mode"] == "Spacing"
    assert overrides["infill_spacing"] == 2.5
    assert overrides["material_choice"] == "PETG"
    assert overrides["model_height"] == 30.0
    assert overrides["shape_type"] == "Rectangle"
    assert overrides["quick_plate"] == "300 x 300"
    assert overrides["job_name"] == "Bracket"
    assert overrides["customer_name"] == "Acme"
    assert overrides["batch_quantity"] == 10
    assert overrides["target_unit_price"] == 45.0


def test_overrides_from_export_only_emits_known_keys() -> None:
    overrides = overrides_from_export(_sample_export())
    assert set(overrides) <= set(OVERRIDE_KEYS)


def test_overrides_from_export_skips_imported_geometry_shape() -> None:
    params = _sample_export()
    params["shape_type"] = "STL slice Z=1.50"
    overrides = overrides_from_export(params)
    assert "shape_type" not in overrides


def test_overrides_from_export_maps_disabled_plate_to_none() -> None:
    params = _sample_export()
    params["plate"] = {"enabled": False, "width_mm": 220.0}
    assert overrides_from_export(params)["quick_plate"] == "None"


def test_overrides_from_export_handles_non_dict() -> None:
    assert overrides_from_export([]) == {}
    assert overrides_from_export({}) == {}
