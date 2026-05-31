# MiniSlicer — Python Toolpath Visualizer for Additive Manufacturing

A small but complete Python project that demonstrates core slicer and path-planning concepts
used in additive manufacturing. Built as a portfolio piece for a working-student application.

> **Disclaimer:** This is **not** an industrial metal 3D printing slicer.
> It is a simplified educational toolpath visualizer intended to demonstrate Python skills,
> geometry reasoning, and clean software design — not to replace production slicer software.

---

## App Preview

Run the Streamlit app locally to interact with the visualizer:

```powershell
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Features

| Area | What it does |
|---|---|
| **Shapes / Imports** | 11 built-in shapes (Rectangle, Rounded Rectangle, Circle, Ellipse, Triangle, Regular Polygon, Star, Cross, Capsule, Arrow, Custom Polygon), plus SVG outlines and STL mesh slicing |
| **Multi-layer STL** | Slice an STL across a Z range with configurable step; generates per-layer toolpaths and renders an animated 3D build-up with play/pause and a layer slider |
| **Perimeters** | Inward offset rings using Shapely negative buffer; configurable count and spacing |
| **Infill** | Parallel/grid/concentric/honeycomb/zigzag/triangles modes, custom angle slider, optional alternating angle, or density-based spacing |
| **Visualization** | 8 preview modes: Toolpath, Extrusion, Perimeters only, Infill only, Travel only, Speed map, Time map, and Path Density |
| **Metrics** | Path length, segment count, perimeter and infill counts, estimated print time, bounding box, material volume and weight |
| **Path planning** | Greedy nearest-neighbour ordering for perimeters and infill; before/after travel-distance comparison shown in the Metrics tab |
| **Material profiles** | 6 built-in printer presets (PLA FDM, PETG FDM, ABS FDM, 316L LPBF, Ti-6Al-4V LPBF, Inconel 625 LPBF) that pre-fill speed, layer height, hatch spacing, and material |
| **Transforms** | Scale, mirror, rotate, translate, center, and fit shapes to a configurable build plate |
| **Quality controls** | Geometry simplification tolerance and minimum segment-length filtering |
| **Reproducibility** | Import prior run settings from JSON and re-apply parameter snapshots |
| **Motion realism** | Separate travel speed, optional Z-hop, and optional E-value output in educational G-code |
| **UI** | Dark/light theme toggle, sidebar setup-progress indicator, inline G-code preview with copy button |
| **Export** | CSV, SVG, JSON (with parameters), G-code-like educational text, and PNG image |

---

## Tech Stack

- **Python 3.11+**
- [Streamlit](https://streamlit.io/) — web UI
- [Shapely](https://shapely.readthedocs.io/) — 2D geometry and polygon operations
- [NumPy](https://numpy.org/) — array maths for infill line sampling
- [Plotly](https://plotly.com/python/) — interactive visualization
- [Pandas](https://pandas.pydata.org/) — tabular data and CSV export
- [Trimesh](https://trimesh.org/) - STL mesh loading and cross-section slicing
- [SciPy](https://scipy.org/) / [NetworkX](https://networkx.org/) - mesh section graph processing
- [Pytest](https://docs.pytest.org/) — automated tests

---

## Installation

### Quick Setup (Windows PowerShell)

```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```

Run tests with:

```powershell
.\scripts\test.ps1
```

### Quick Setup (Windows CMD / double-click friendly)

```bat
scripts\setup.cmd
scripts\run.cmd
```

Run tests with:

```bat
scripts\test.cmd
```

These wrappers call the PowerShell scripts with execution-policy bypass for convenience on locked-down machines.

For quickest launch from Explorer (double-click):

```bat
Setup-MiniSlicer.cmd
Start-MiniSlicer.cmd
```

### Manual Setup

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the app
streamlit run app.py
```

The app opens automatically in your default browser at `http://localhost:8501`.

---

## Run Tests

```powershell
pytest -q
```

All tests live in `tests/` and run without a database or external services.

---

## Project Structure

```
minislicer-toolpath-visualizer/
├── app.py                  # Streamlit UI entry point
├── pages/
│   └── tutorial.py         # In-app tutorial page (accessible from sidebar)
├── pyproject.toml          # Project metadata and tool configuration
├── requirements.txt
├── conftest.py             # Pytest path setup
├── README.md
├── .streamlit/
│   └── config.toml         # Streamlit runtime and theme defaults
├── scripts/
│   ├── setup.ps1           # One-command local machine setup
│   ├── run.ps1             # Launch app with project venv
│   ├── test.ps1            # Run test suite with project venv
│   ├── setup.cmd           # Windows CMD wrapper for setup
│   ├── run.cmd             # Windows CMD wrapper for run
│   └── test.cmd            # Windows CMD wrapper for tests
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── geometry.py         # Shape creation and polygon validation
│   ├── toolpaths.py        # Perimeter and infill generation, Segment dataclass
│   ├── metrics.py          # Path length, print-time estimate, bounding box, material
│   ├── profiles.py         # Printer material presets (FDM + LPBF)
│   ├── stl_import.py       # STL metadata, single-Z and multi-layer slice extraction
│   ├── exporters.py        # CSV, SVG, JSON, and G-code-like text export
│   ├── plotting.py         # Plotly 2D/3D figure builders incl. multi-layer animation
│   ├── animation.py        # Nozzle-path playback animation
│   └── svg_import.py       # SVG outline → Shapely polygon
├── tests/
│   ├── test_geometry.py    # Shape creation and validation
│   ├── test_toolpaths.py   # Perimeter/infill generation and path ordering
│   ├── test_exporters.py   # CSV, JSON, G-code export
│   ├── test_metrics.py     # Path length, print time, material estimate
│   ├── test_plotting.py    # Figure structure and trace types
│   └── test_stl_import.py  # STL slicing with trimesh mock mesh
└── screenshots/
    └── .gitkeep
```

---

## What I Learned / Purpose

This project was built to practice and demonstrate:

- **Computational geometry** — using Shapely for polygon buffering, clipping, and coordinate
  extraction; handling edge cases like self-intersecting polygons and disappearing insets
- **Path-planning basics** — how slicers decompose a cross-section into ordered motion paths
  (outer perimeter → inner perimeters → infill), and why infill angle alternates between layers
- **Clean module design** — separating geometry, path logic, metrics, rendering, and export into
  focused, independently testable modules
- **Defensive input handling** — graceful fallbacks for invalid polygons, zero-area shapes, and
  spacing values that would produce no paths
- **Streamlit UI patterns** — sidebar controls, disabled widgets, expanders, metric cards,
  and download buttons
- **Pytest practices** — deterministic fixtures, boundary conditions, geometry invariant checks

---

## Future Improvements

- **Support structure generation** — detect overhangs and add basic support geometry
- **Thermal constraint awareness** — flag regions with high local heat accumulation (relevant
  for metal powder-bed processes)
- **True G-code output** — validated, machine-ready output with proper start/end sequences
- **Multi-material / multi-nozzle** — assign different materials to perimeter vs. infill regions

---

## Exports

### CSV (`toolpaths_layer_N.csv`)

| Column | Description |
|---|---|
| `segment_id` | 1-based row index |
| `path_type` | `boundary`, `perimeter`, or `infill` |
| `order_index` | 0-based execution order |
| `x_start`, `y_start` | Start coordinates in mm |
| `x_end`, `y_end` | End coordinates in mm |
| `length_mm` | Euclidean segment length |
| `layer` | Layer number from the UI |

### G-code-like text (`toolpaths_layer_N.gcode.txt`)

Educational G0/G1 motion file with comments. **Not machine-ready.**
Intended to illustrate the structure of a motion program, not to run on a real machine.

### JSON (`toolpaths_layer_N.json`)

Includes:

- `schema_version`
- `parameters` snapshot (shape, infill, process, transform, optimization, quality)
- `segments` table rows for downstream tooling or reproducible comparisons

You can re-import this JSON in the app sidebar under **Config Import (JSON)** to apply the saved parameter set.

### PNG (`toolpaths_layer_N.png`)

High-resolution rendered image (1600×1100 px, 2× scale) of the current toolpath visualization.
Requires the optional `kaleido` package: `pip install kaleido`.

---

## Professional Workflow Notes

- Use `scripts/setup.ps1` for first-time setup on a new machine.
- Use `scripts/run.ps1` and `scripts/test.ps1` for repeatable run/test commands.
- `pyproject.toml` includes project metadata and basic lint/test tool config for cleaner onboarding.
- The app now supports profile presets (`Draft`, `Balanced`, `Fine`) to standardize parameter sets.
