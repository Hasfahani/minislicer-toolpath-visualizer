"""Tests for src/exporters.py CSV and G-code-like exports."""

import io
import json

import pandas as pd

from src.exporters import (
    CSV_COLUMNS,
    ProductionExportError,
    export_gcode_like,
    export_production_gcode,
    export_segments_csv,
    export_segments_json,
    segments_to_dataframe,
)
from src.profiles import FDM_MACHINE_PROFILES
from src.toolpaths import Segment


def _sample_segments() -> list[Segment]:
    return [
        Segment("boundary", 0, 0.0, 0.0, 10.0, 0.0, 10.0, 1),
        Segment("perimeter", 1, 10.0, 0.0, 10.0, 5.0, 5.0, 1),
        Segment("infill", 2, 0.0, 1.0, 10.0, 1.0, 10.0, 1),
    ]


def _sample_multilayer_segments() -> list[Segment]:
    return [
        *_sample_segments(),
        Segment("perimeter", 3, 0.0, 0.0, 10.0, 0.0, 10.0, 2),
        Segment("infill", 4, 0.0, 2.0, 10.0, 2.0, 10.0, 2),
    ]


def test_csv_export_contains_required_headers() -> None:
    csv_text = export_segments_csv(_sample_segments())
    header_line = csv_text.splitlines()[0]
    for col in CSV_COLUMNS:
        assert col in header_line


def test_csv_export_row_count_matches_segments() -> None:
    segs = _sample_segments()
    csv_text = export_segments_csv(segs)
    # Header + one row per segment
    lines = [l for l in csv_text.splitlines() if l.strip()]
    assert len(lines) == len(segs) + 1


def test_dataframe_schema() -> None:
    df = segments_to_dataframe(_sample_segments())
    assert list(df.columns) == CSV_COLUMNS
    assert len(df) == 3


def test_dataframe_segment_id_starts_at_one() -> None:
    df = segments_to_dataframe(_sample_segments())
    assert df["segment_id"].iloc[0] == 1


def test_dataframe_path_types_preserved() -> None:
    df = segments_to_dataframe(_sample_segments())
    assert set(df["path_type"]) == {"boundary", "perimeter", "infill"}


def test_dataframe_length_mm_positive() -> None:
    df = segments_to_dataframe(_sample_segments())
    assert (df["length_mm"] > 0).all()


def test_gcode_like_export_has_moves() -> None:
    gcode = export_gcode_like(_sample_segments(), print_speed_mm_s=15.0)
    assert "G0 X" in gcode
    assert "G1 X" in gcode


def test_gcode_like_export_has_disclaimer() -> None:
    gcode = export_gcode_like(_sample_segments(), print_speed_mm_s=15.0)
    assert "educational only" in gcode


def test_gcode_like_export_has_feedrate() -> None:
    gcode = export_gcode_like(_sample_segments(), print_speed_mm_s=10.0)
    # 10 mm/s -> 600 mm/min
    assert "F600.0" in gcode


def test_gcode_like_export_has_end_marker() -> None:
    gcode = export_gcode_like(_sample_segments(), print_speed_mm_s=20.0)
    assert "M2" in gcode


def test_gcode_like_export_segment_comments() -> None:
    gcode = export_gcode_like(_sample_segments(), print_speed_mm_s=20.0)
    assert "boundary" in gcode
    assert "infill" in gcode


def test_csv_roundtrip_via_pandas() -> None:
    csv_text = export_segments_csv(_sample_segments())
    df = pd.read_csv(io.StringIO(csv_text))
    assert list(df.columns) == CSV_COLUMNS
    assert len(df) == 3


def test_json_export_contains_parameters_and_segments() -> None:
    params = {"profile": "Balanced", "layer": 2}
    payload = json.loads(export_segments_json(_sample_segments(), parameters=params))
    assert payload["schema_version"] == 1
    assert payload["parameters"]["profile"] == "Balanced"
    assert len(payload["segments"]) == 3
    assert payload["segments"][0]["path_type"] == "boundary"


def test_gcode_export_includes_e_values_when_enabled() -> None:
    gcode = export_gcode_like(
        _sample_segments(),
        print_speed_mm_s=20.0,
        include_e_values=True,
        extrusion_per_mm=0.05,
    )
    assert "M82" in gcode
    assert " E" in gcode


def test_gcode_export_includes_z_hop_when_enabled() -> None:
    gcode = export_gcode_like(
        _sample_segments(),
        print_speed_mm_s=20.0,
        layer_height_mm=0.2,
        z_hop_mm=0.3,
    )
    assert "Z-hop" in gcode
    assert "return to layer Z" in gcode


def test_production_gcode_includes_machine_start_and_end_sequence() -> None:
    machine = FDM_MACHINE_PROFILES["Generic Marlin 220x220"]
    gcode = export_production_gcode(
        _sample_segments(),
        machine=machine,
        print_speed_mm_s=20.0,
        layer_height_mm=0.2,
        travel_speed_mm_s=100.0,
        extrusion_per_mm=0.04,
        job_name="test job",
    )

    assert "; MiniSlicer production FDM export" in gcode
    assert "; Layers: 1" in gcode
    assert "; Segments: 3" in gcode
    assert "; Toolpath-SHA256:" in gcode
    assert "M190 S60" in gcode
    assert "M109 S205" in gcode
    assert "G28" in gcode
    assert "M104 S0" in gcode
    assert "M140 S0" in gcode
    assert " E" in gcode


def test_production_gcode_rejects_out_of_bounds_moves() -> None:
    machine = FDM_MACHINE_PROFILES["Generic Marlin 220x220"]
    bad_segments = [Segment("infill", 0, 0.0, 0.0, 300.0, 0.0, 300.0, 1)]

    try:
        export_production_gcode(
            bad_segments,
            machine=machine,
            print_speed_mm_s=20.0,
            layer_height_mm=0.2,
            travel_speed_mm_s=100.0,
            extrusion_per_mm=0.04,
        )
    except ProductionExportError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("Expected out-of-bounds production export to fail")


def test_production_gcode_rejects_missing_extrusion_calibration() -> None:
    machine = FDM_MACHINE_PROFILES["Generic Marlin 220x220"]

    try:
        export_production_gcode(
            _sample_segments(),
            machine=machine,
            print_speed_mm_s=20.0,
            layer_height_mm=0.2,
            travel_speed_mm_s=100.0,
            extrusion_per_mm=0.0,
        )
    except ProductionExportError as exc:
        assert "Extrusion" in str(exc)
    else:
        raise AssertionError("Expected zero extrusion calibration to fail")


def test_production_gcode_exports_all_layers() -> None:
    machine = FDM_MACHINE_PROFILES["Generic Marlin 220x220"]
    gcode = export_production_gcode(
        _sample_multilayer_segments(),
        machine=machine,
        print_speed_mm_s=20.0,
        layer_height_mm=0.2,
        travel_speed_mm_s=100.0,
        extrusion_per_mm=0.04,
    )

    assert "; Layers: 2" in gcode
    assert ";LAYER:1" in gcode
    assert ";LAYER:2" in gcode
    assert "G1 Z0.400" in gcode
