"""Printer material profiles for FDM and LPBF (powder-bed fusion) processes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrinterProfile:
    """Process parameters for a specific material and printing technology.

    Attributes:
        name: Human-readable profile name.
        process: Technology label — ``"FDM"`` or ``"LPBF"``.
        scan_speed_mm_s: Print/scan speed in mm/s.
        layer_thickness_mm: Layer height in mm.
        hatch_spacing_mm: Extrusion/nozzle width (FDM) or laser hatch spacing (LPBF) in mm.
        material: Material key matching ``MATERIAL_DENSITY`` in ``src.metrics``.
        description: Short one-line description shown in the UI sidebar.
    """

    name: str
    process: str
    scan_speed_mm_s: float
    layer_thickness_mm: float
    hatch_spacing_mm: float
    material: str
    description: str


@dataclass(frozen=True)
class MachineGcodeProfile:
    """Machine-specific settings needed for production FDM G-code export."""

    name: str
    bed_size_x_mm: float
    bed_size_y_mm: float
    max_z_mm: float
    nozzle_temp_c: int
    bed_temp_c: int
    fan_speed: int
    start_gcode: tuple[str, ...]
    end_gcode: tuple[str, ...]


# ── Built-in profiles ─────────────────────────────────────────────────────────

PRINTER_PROFILES: dict[str, PrinterProfile] = {
    "— Custom —": PrinterProfile(
        name="— Custom —",
        process="FDM",
        scan_speed_mm_s=50.0,
        layer_thickness_mm=0.20,
        hatch_spacing_mm=0.40,
        material="PLA",
        description="Manually configured — no preset applied.",
    ),
    "PLA – FDM 0.4 mm": PrinterProfile(
        name="PLA – FDM 0.4 mm",
        process="FDM",
        scan_speed_mm_s=50.0,
        layer_thickness_mm=0.20,
        hatch_spacing_mm=0.40,
        material="PLA",
        description="Generic FDM PLA on a 0.4 mm nozzle, balanced quality/speed.",
    ),
    "PETG – FDM 0.4 mm": PrinterProfile(
        name="PETG – FDM 0.4 mm",
        process="FDM",
        scan_speed_mm_s=40.0,
        layer_thickness_mm=0.20,
        hatch_spacing_mm=0.40,
        material="PETG",
        description="PETG on a 0.4 mm nozzle — slower than PLA for layer adhesion.",
    ),
    "ABS – FDM 0.4 mm": PrinterProfile(
        name="ABS – FDM 0.4 mm",
        process="FDM",
        scan_speed_mm_s=45.0,
        layer_thickness_mm=0.20,
        hatch_spacing_mm=0.40,
        material="ABS",
        description="ABS on a 0.4 mm nozzle; enclosure strongly recommended.",
    ),
    "316L – LPBF": PrinterProfile(
        name="316L – LPBF",
        process="LPBF",
        scan_speed_mm_s=700.0,
        layer_thickness_mm=0.03,
        hatch_spacing_mm=0.10,
        material="Steel 316L",
        description="316L stainless steel LPBF — 70 W laser, 80 µm spot (typical parameters).",
    ),
    "Ti-6Al-4V – LPBF": PrinterProfile(
        name="Ti-6Al-4V – LPBF",
        process="LPBF",
        scan_speed_mm_s=600.0,
        layer_thickness_mm=0.03,
        hatch_spacing_mm=0.10,
        material="Titanium Ti-6Al-4V",
        description="Titanium alloy LPBF — slower scan speed improves fusion depth.",
    ),
    "Inconel 625 – LPBF": PrinterProfile(
        name="Inconel 625 – LPBF",
        process="LPBF",
        scan_speed_mm_s=800.0,
        layer_thickness_mm=0.04,
        hatch_spacing_mm=0.11,
        material="Inconel 625",
        description="Inconel 625 LPBF — high scan speed, good for complex geometries.",
    ),
}

QUALITY_PROFILES: dict[str, dict[str, float | int]] = {
    "Fast Preview": {"layer_height": 0.32, "speed": 90.0, "perimeters": 1, "spacing": 6.0},
    "Draft": {"layer_height": 0.28, "speed": 70.0, "perimeters": 2, "spacing": 4.0},
    "Balanced": {"layer_height": 0.20, "speed": 50.0, "perimeters": 3, "spacing": 3.0},
    "Strong": {"layer_height": 0.20, "speed": 45.0, "perimeters": 5, "spacing": 2.2},
    "Fine": {"layer_height": 0.12, "speed": 35.0, "perimeters": 4, "spacing": 2.0},
}

FDM_MACHINE_PROFILES: dict[str, MachineGcodeProfile] = {
    "Generic Marlin 220x220": MachineGcodeProfile(
        name="Generic Marlin 220x220",
        bed_size_x_mm=220.0,
        bed_size_y_mm=220.0,
        max_z_mm=250.0,
        nozzle_temp_c=205,
        bed_temp_c=60,
        fan_speed=255,
        start_gcode=(
            "G21 ; units in millimeters",
            "G90 ; absolute positioning",
            "M82 ; absolute extrusion",
            "M140 S{bed_temp} ; set bed temperature",
            "M104 S{nozzle_temp} ; set nozzle temperature",
            "G28 ; home all axes",
            "M190 S{bed_temp} ; wait for bed temperature",
            "M109 S{nozzle_temp} ; wait for nozzle temperature",
            "G92 E0",
            "G1 Z2.000 F3000",
            "G1 X5.000 Y5.000 F6000",
            "G1 X60.000 E9.000 F900 ; prime line",
            "G92 E0",
        ),
        end_gcode=(
            "G92 E0",
            "G1 E-1.000 F1800 ; retract",
            "G1 Z{safe_z:.3f} F3000",
            "G1 X0 Y{park_y:.3f} F6000 ; park head",
            "M104 S0 ; hotend off",
            "M140 S0 ; bed off",
            "M107 ; fan off",
            "M84 ; disable motors",
        ),
    ),
    "Prusa MK3/MK4 250x210": MachineGcodeProfile(
        name="Prusa MK3/MK4 250x210",
        bed_size_x_mm=250.0,
        bed_size_y_mm=210.0,
        max_z_mm=210.0,
        nozzle_temp_c=215,
        bed_temp_c=60,
        fan_speed=255,
        start_gcode=(
            "G21",
            "G90",
            "M82",
            "M140 S{bed_temp}",
            "M104 S{nozzle_temp}",
            "G28 W",
            "M190 S{bed_temp}",
            "M109 S{nozzle_temp}",
            "G92 E0",
            "G1 Z0.280 F720",
            "G1 X10.000 Y-3.000 F1000",
            "G1 X60.000 E9.000 F1000",
            "G92 E0",
        ),
        end_gcode=(
            "G92 E0",
            "G1 E-1.000 F1800",
            "G1 Z{safe_z:.3f} F720",
            "G1 X0 Y{park_y:.3f} F6000",
            "M104 S0",
            "M140 S0",
            "M107",
            "M84",
        ),
    ),
}


def profile_names() -> list[str]:
    """Return the sorted list of available profile names (Custom first)."""
    names = sorted(k for k in PRINTER_PROFILES if k != "— Custom —")
    return ["— Custom —"] + names
