# MiniSlicer Toolpath Planner

MiniSlicer is a Streamlit-based additive manufacturing planning workbench for
visualizing 2D slicer logic, comparing infill strategies, reviewing print
readiness, and exporting traceable planning packages.

It is designed for engineering demos, startup prototyping workflows, quoting
discussions, and technical portfolio review. Production G-code export is guarded
by readiness checks and machine bounds, but every job must still be validated on
the target machine before release.

## Product Capabilities

| Area | Capability |
|---|---|
| Geometry | Built-in parametric shapes, custom polygons, SVG outline import, and STL cross-section slicing |
| Toolpaths | Inward perimeters, parallel, zigzag, grid, triangular, honeycomb, and concentric infill |
| Planning Engine | Typed toolpath settings, reusable layer planner, full-build segment generation, pattern ranking, and deterministic plan fingerprints |
| Planning | Per-layer and full-build path estimates, acceleration-aware motion time, travel share, and material use |
| Executive Review | Launch score, readiness score, program risk, unit/batch quote, productivity, launch optimizer, what-if playbook, batch scenarios, release checklist, quality scorecard, and cost-stack view |
| Quality Gates | Plate fit, missing paths, tall layer height, sparse infill, high travel, heavy path count, tall builds, and volumetric flow |
| Commercial Controls | Customer/job metadata, batch quantity, target price, machine rate, labor rate, setup time, postprocess time, scrap, margin, and lead-time guardrails |
| Visualization | Toolpath, extrusion-width, speed map, time map, density map, animation, and 3D layer stack views |
| Export | CSV, JSON, SVG, preview G-code, guarded FDM production G-code, markdown dossier, HTML dossier, and text report |
| Reproducibility | JSON parameter snapshots can be re-imported to recreate prior planning runs |

## Quick Start

```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```

The app opens at:

```text
http://localhost:8501
```

Run the test suite:

```powershell
.\scripts\test.ps1
```

The suite covers backend geometry/toolpath behavior, exports, job economics,
STL/SVG handling, the default Streamlit app shell, and repository text quality
so demo-facing screens stay free of encoding artifacts.

Manual launch:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Workflow

1. Choose a quality profile, build plate, process mode, and control depth in
   Quick Setup.
2. Import SVG/STL geometry or use a built-in parametric shape.
3. Tune perimeters, infill, print settings, placement, optimization, and preview
   appearance.
4. Set job metadata, batch quantity, quote assumptions, target price, and
   machine-time guardrails in Business / Launch.
5. Review the Executive, Quality, and Advisor tabs before exporting.
6. Use the Launch Optimizer to review top moves, what-if levers, batch scenarios, and release checklist status.
7. Export a dossier for sign-off, plus data files for engineering traceability.
8. Use production G-code only when readiness is unblocked, process mode is FDM,
   and the selected machine profile matches the physical printer.

## Engineering Model

MiniSlicer uses Shapely for geometric offsets, clipping, and polygon validation.
Motion time uses a trapezoidal/triangular acceleration model instead of only
dividing path length by speed. Material estimation uses an elliptical bead
cross-section approximation based on path length, layer height, nozzle diameter,
filament diameter, and material density.

The backend planning engine is isolated from the Streamlit UI. `ToolpathSettings`
defines validated immutable inputs, `plan_layer` returns a complete layer plan,
`build_production_segments` generates full-build exports inside a configured
layer limit, and `rank_infill_patterns` scores candidates for operator review.
Every planning package receives a deterministic fingerprint based on geometry,
toolpath settings, process, material, and layer count.

The quote model is transparent by design. Setup labor is amortized across the
batch, while machine time, material, and postprocess labor remain per-part
drivers:

```text
unit quote =
  (((material + machine time + postprocess labor) * batch quantity + setup labor)
   * scrap allowance * margin) / batch quantity
```

Default business assumptions are intentionally conservative and visible in the
analysis code so teams can replace them with their own rates.

Commercial fit compares the calculated unit quote and batch machine hours
against the target price and lead-time guardrails. The launch score combines
technical readiness, program risk, and commercial fit into one executive signal.

## Project Structure

```text
app.py                  Streamlit application entry point
src/geometry.py         Shape creation and polygon validation
src/catalog.py          Shared shape and infill pattern catalogs
src/workflow.py         App workflow helpers for shape construction, placement, and time formatting
src/toolpaths.py        Perimeters, infill generation, ordering, and segments
src/planner.py          Typed planning engine, production segment generation, ranking, and fingerprints
src/metrics.py          Path, time, material, and efficiency metrics
src/job_analysis.py     Quote, productivity, risk, and dossier generation
src/validation.py       Manufacturability readiness checks
src/exporters.py        CSV, JSON, SVG, preview G-code, and production G-code
src/plotting.py         Plotly 2D/3D visualization builders
src/stl_import.py       STL metadata and cross-section slicing
src/svg_import.py       SVG outline parsing
ui/                     Streamlit controls and panels
tests/                  Pytest coverage plus Streamlit smoke and text-quality checks
```

## Safety Note

This is a planning and visualization tool. It does not replace a qualified
manufacturing engineer, printer-specific slicer validation, material process
qualification, fixture review, collision checking, or machine commissioning.
