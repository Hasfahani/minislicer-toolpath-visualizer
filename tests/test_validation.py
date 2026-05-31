"""Tests for job readiness assessment."""

from src.validation import assess_job_readiness, readiness_to_dict


def _base_metrics() -> dict[str, float | int]:
    return {
        "perimeter_path_count": 2,
        "path_efficiency_pct": 85.0,
        "total_motion_length_mm": 100.0,
    }


def test_ready_job_scores_high() -> None:
    readiness = assess_job_readiness(
        fits_plate=True,
        metrics=_base_metrics(),
        perimeter_count=2,
        infill_line_count=12,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        effective_spacing_mm=3.0,
        perimeter_spacing_mm=0.45,
        segment_count=300,
        travel_ratio_pct=12.0,
        process_mode="FDM",
        imported_stl=True,
        imported_svg=False,
    )

    assert readiness["status"] == "Ready"
    assert readiness["score"] >= 90
    assert readiness["blockers"] == 0


def test_plate_overflow_blocks_job() -> None:
    readiness = assess_job_readiness(
        fits_plate=False,
        metrics=_base_metrics(),
        perimeter_count=2,
        infill_line_count=12,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        effective_spacing_mm=3.0,
        perimeter_spacing_mm=0.45,
        segment_count=300,
        travel_ratio_pct=12.0,
        process_mode="FDM",
        imported_stl=True,
        imported_svg=False,
    )

    assert readiness["status"] == "Blocked"
    assert readiness["blockers"] == 1
    assert any(issue.title == "Build plate overflow" for issue in readiness["issues"])


def test_high_travel_and_tall_layer_create_warnings() -> None:
    readiness = assess_job_readiness(
        fits_plate=True,
        metrics=_base_metrics(),
        perimeter_count=2,
        infill_line_count=12,
        layer_height_mm=0.36,
        nozzle_diameter_mm=0.4,
        effective_spacing_mm=3.0,
        perimeter_spacing_mm=0.45,
        segment_count=300,
        travel_ratio_pct=40.0,
        process_mode="FDM",
        imported_stl=True,
        imported_svg=False,
    )

    assert readiness["status"] == "Review"
    assert readiness["warnings"] == 2


def test_readiness_to_dict_is_json_safe() -> None:
    readiness = assess_job_readiness(
        fits_plate=False,
        metrics=_base_metrics(),
        perimeter_count=2,
        infill_line_count=12,
        layer_height_mm=0.2,
        nozzle_diameter_mm=0.4,
        effective_spacing_mm=3.0,
        perimeter_spacing_mm=0.45,
        segment_count=300,
        travel_ratio_pct=12.0,
        process_mode="FDM",
        imported_stl=True,
        imported_svg=False,
    )

    payload = readiness_to_dict(readiness)

    assert isinstance(payload["issues"][0], dict)
    assert payload["issues"][0]["severity"] == "blocker"
