# Purpose: Provides one-click sample jobs and maps exported JSON settings back into UI defaults.
# Reason: Scenarios make demos repeatable and let users reload prior planning packages safely.
"""Named sample jobs and config re-apply support for the MiniSlicer UI.

This module is intentionally pure (no Streamlit import) so it can be unit
tested. It defines a small set of demo-ready "scenarios" and a mapper that
turns a prior JSON export back into a control-override dictionary.

The UI stores the active overrides in ``st.session_state["_overrides"]`` and
each sidebar control reads its default from that dictionary. Because the
controls are keyless, changing an override changes the widget's default and the
widget adopts the new value - the same mechanism the quality-profile presets
already use. This keeps scenario loading and config re-apply free of
session-state/value conflicts.
"""

from __future__ import annotations

from typing import Any

# Override keys the controls understand. Anything outside this set is ignored
# when a config is re-applied, which keeps untrusted JSON from injecting noise.
OVERRIDE_KEYS: frozenset[str] = frozenset(
    {
        "profile",
        "process_mode",
        "quick_plate",
        "control_mode",
        "shape_type",
        "width",
        "height",
        "radius",
        "perimeter_count",
        "infill_pattern",
        "infill_mode",
        "infill_density",
        "infill_spacing",
        "material_choice",
        "model_height",
        "layer_number",
        "job_name",
        "customer_name",
        "batch_quantity",
        "target_unit_price",
    }
)

# Shapes whose only dimensions are width/height or radius, so a scenario can set
# them without needing shape-specific fields (corner radius, sides, etc.).
_SIMPLE_SHAPES: frozenset[str] = frozenset(
    {"Rectangle", "Circle", "Ellipse", "Triangle", "Capsule"}
)


# Coherent, demo-ready jobs. Each is a complete "story" a presenter can load in
# one click. Values stay inside the documented control ranges and are sized for
# a snappy first render: modest layer counts and coarse infill keep the
# full-build path generation fast, the same scale as the default sample shape.
SAMPLE_JOBS: dict[str, dict[str, Any]] = {
    "FDM bracket (PLA)": {
        "profile": "Balanced",
        "process_mode": "FDM",
        "quick_plate": "220 x 220",
        "shape_type": "Rectangle",
        "width": 55.0,
        "height": 38.0,
        "perimeter_count": 3,
        "infill_pattern": "Grid",
        "infill_mode": "Density",
        "infill_density": 12,
        "material_choice": "PLA",
        "model_height": 3.0,
        "layer_number": 1,
        "job_name": "Demo bracket",
        "customer_name": "Acme Robotics",
        "batch_quantity": 25,
        "target_unit_price": 18.0,
    },
    "PETG enclosure": {
        "profile": "Strong",
        "process_mode": "FDM",
        "quick_plate": "300 x 300",
        "shape_type": "Rectangle",
        "width": 75.0,
        "height": 50.0,
        "perimeter_count": 4,
        "infill_pattern": "Zigzag",
        "infill_mode": "Density",
        "infill_density": 11,
        "material_choice": "PETG",
        "model_height": 4.0,
        "layer_number": 1,
        "job_name": "Demo enclosure",
        "customer_name": "Northwind Devices",
        "batch_quantity": 10,
        "target_unit_price": 45.0,
    },
    "Metal DED hub (316L)": {
        "profile": "Balanced",
        "process_mode": "Metal (LPBF/DED)",
        "quick_plate": "300 x 300",
        "shape_type": "Circle",
        "radius": 45.0,
        "perimeter_count": 2,
        "infill_pattern": "Concentric",
        "infill_mode": "Spacing",
        "infill_spacing": 6.0,
        "material_choice": "Steel 316L",
        "model_height": 6.0,
        "layer_number": 1,
        "job_name": "Demo DED hub",
        "customer_name": "Meridian Aerospace",
        "batch_quantity": 1,
        "target_unit_price": 0.0,
    },
}


def option_index(options: Any, value: Any, fallback: int = 0) -> int:
    """Return the index of ``value`` in ``options``, or ``fallback`` if absent."""
    try:
        return list(options).index(value)
    except (ValueError, TypeError):
        return fallback


def as_int(value: Any, fallback: int) -> int:
    """Coerce an override value to int, clamping unparseable input to fallback."""
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return fallback


def as_float(value: Any, fallback: float) -> float:
    """Coerce an override value to float, clamping unparseable input to fallback."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def scenario_names() -> list[str]:
    """Return the sample-job names in definition order."""
    return list(SAMPLE_JOBS)


def scenario_overrides(name: str) -> dict[str, Any]:
    """Return a fresh override dict for a named scenario (empty if unknown)."""
    return dict(SAMPLE_JOBS.get(name, {}))


def _quick_plate_from_export(plate: Any) -> str | None:
    """Map an exported plate block to a Build plate choice."""
    if not isinstance(plate, dict):
        return None
    if not plate.get("enabled", True):
        return "None"
    width = plate.get("width_mm")
    try:
        return "300 x 300" if float(width) >= 290.0 else "220 x 220"
    except (TypeError, ValueError):
        return "220 x 220"


def overrides_from_export(params: dict[str, Any]) -> dict[str, Any]:
    """Translate a JSON export's ``parameters`` block into control overrides.

    Only the documented job-defining fields are mapped; imported-geometry
    sources (STL/SVG) are skipped because they cannot be reproduced from
    parameters alone. Unknown or malformed values are ignored.
    """
    if not isinstance(params, dict):
        return {}

    overrides: dict[str, Any] = {}

    def put(key: str, value: Any) -> None:
        if key in OVERRIDE_KEYS and value is not None:
            overrides[key] = value

    put("profile", params.get("profile"))
    put("process_mode", params.get("process_mode"))
    put("perimeter_count", params.get("perimeter_count"))
    put("infill_pattern", params.get("infill_pattern"))
    put("material_choice", params.get("material"))
    put("model_height", params.get("model_height_mm"))

    spacing = params.get("infill_spacing_mm")
    if spacing is not None:
        put("infill_mode", "Spacing")
        put("infill_spacing", spacing)

    shape_type = params.get("shape_type")
    if isinstance(shape_type, str) and shape_type in _SIMPLE_SHAPES:
        put("shape_type", shape_type)

    plate_choice = _quick_plate_from_export(params.get("plate"))
    if plate_choice is not None:
        put("quick_plate", plate_choice)

    metadata = params.get("job_metadata")
    if isinstance(metadata, dict):
        put("job_name", metadata.get("job_name"))
        put("customer_name", metadata.get("customer_name"))

    business = params.get("business_assumptions")
    if isinstance(business, dict):
        put("batch_quantity", business.get("batch_quantity"))
        put("target_unit_price", business.get("target_unit_price"))

    return overrides
