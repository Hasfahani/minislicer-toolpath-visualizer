<!-- # Purpose: Explains the software architecture and how app, UI, source modules, validation, and export connect. -->
<!-- # Reason: This document helps reviewers understand the project structure without reading every file first. -->
# MiniSlicer Architecture

MiniSlicer is organized around a simple pipeline:

```text
User controls
  -> geometry normalization
  -> toolpath planning
  -> metrics and job analysis
  -> readiness validation
  -> optional process-intelligence advice
  -> visualization and export
```

The Streamlit UI is intentionally thin where possible. It gathers inputs,
renders charts, and delegates planning, validation, metrics, and export logic to
modules under `src/`.

## Streamlit Interface

`app.py` is the application entry point. It coordinates page layout, session
state, cached planning calls, release dashboards, and export assembly.

The `ui/` package splits user-facing controls into smaller modules:

- `ui/sidebar.py`: top-level setup and sidebar orchestration.
- `ui/shape_controls.py`: built-in shape and custom polygon controls.
- `ui/stl_workflow.py`: JSON config upload, SVG/STL import controls, and
  multi-layer STL preview helpers.
- `ui/process_controls.py`: toolpath, print, business, DED, placement, and
  preview controls.
- `ui/dashboard.py`: executive release, quality, DED, partner-fit, and handoff
  panels.
- `ui/export_panel.py`: download buttons, preview panes, and guarded production
  G-code export state.
- `pages/process_intelligence.py`: qualified-build dataset review and bounded
  DED parameter recommendations.

## Geometry Layer

Geometry is represented with Shapely objects. This keeps offsets, clipping,
validation, transforms, and measurements in a well-tested geometry library
instead of custom handwritten computational geometry.

- `src/geometry.py` creates built-in shapes and validates user polygons.
- `src/workflow.py` applies placement operations such as scale, rotation,
  translation, mirroring, centering, and plate fitting.
- `src/svg_import.py` extracts practical closed outlines from SVG files.
- `src/stl_import.py` inspects STL meshes and slices horizontal cross-sections
  into polygons for 2D planning studies.

## Planner and Toolpaths

`src/planner.py` is the planning boundary between UI inputs and generated
segments. `ToolpathSettings` is immutable and validated, which makes planning
calls deterministic and easier to test.

Planner responsibilities:

- create a complete `LayerPlan`
- generate perimeters and infill for one layer
- build full-build segment lists under a configured layer limit
- alternate infill angles by layer when requested
- rank candidate infill patterns
- create deterministic plan fingerprints

`src/toolpaths.py` contains the lower-level path generation and ordering
algorithms:

- inward perimeters
- parallel, zigzag, grid, triangular, honeycomb, and concentric infill
- short-segment filtering
- line simplification
- optional path ordering and line reversal
- segment conversion for downstream metrics and exports

## Metrics and Job Analysis

`src/metrics.py` converts segments and geometry into engineering signals:

- path length
- travel distance
- acceleration-aware motion time
- material volume and mass
- bounding boxes and area
- efficiency ratios

`src/job_analysis.py` adds business and launch-planning models:

- unit and batch quote estimates
- productivity and cost-stack views
- program risk classification
- commercial fit
- launch recommendations
- batch scenarios
- release checklist
- DED/WAAM process estimates
- manufacturing partner fit
- thermal/interpass planning
- robot-cell handoff checks
- qualification package planning
- quality scorecards
- markdown and HTML dossier generation

The analysis layer is deliberately transparent. Default assumptions are visible
in code and should be replaced with organization-specific rates, machine data,
and process knowledge for real business decisions.

## Process Intelligence Boundary

`src/process_intelligence.py` introduces a separate advisory layer over completed
and inspected builds. Its responsibilities are:

- validate a versioned build-level data contract
- preserve machine, material-batch, geometry-family, and plan traceability
- exclude rejected builds from parameter recipes
- require a minimum accepted-build count for each machine/material domain
- split evaluation by complete build and time
- reject candidates outside historical applicability
- clamp recommendations to engineer-approved parameter envelopes
- return confidence, warnings, and evidence build IDs

The module does not modify geometry, generate toolpaths, generate robot code, or
override release validation. Raw sensor streams remain outside the compact
build-record file and are linked using `build_id`.

## Validation Gates

`src/validation.py` turns geometry, planning, print, and process state into
readiness issues. It checks practical problems such as:

- no generated paths
- part outside the build plate
- layer height too large for nozzle/bead width
- sparse infill
- excessive travel share
- very high segment count
- tall build warnings
- volumetric-flow risk
- missing STL review for metal planning

These gates are planning aids. They do not certify production readiness.

## Visualization and Export

Visualization is handled by:

- `src/plotting.py`: static Plotly figures for toolpaths, metrics, speed maps,
  density maps, comparison views, and 3D layer stacks.
- `src/animation.py`: animated layer/toolpath previews.

Export is handled by `src/exporters.py`:

- CSV segment tables
- JSON payloads with parameters and segments
- SVG path preview
- educational preview G-code
- guarded FDM production G-code

Production G-code remains intentionally constrained. It is FDM-only, requires
passing readiness state, and still needs target-machine validation.

## Testing Boundaries

The tests exercise module behavior independently from the UI wherever possible.
The Streamlit smoke test catches import and default-render regressions. This
keeps the project useful as both a demo app and a maintainable engineering code
base.
