<!-- # Purpose: Introduces MiniSlicer, explains its capabilities, setup, architecture, limits, and license. -->
<!-- # Reason: The README is the first document interviewers or companies read to understand the project. -->
# MiniSlicer Toolpath Planner

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest%20%2B%20GitHub%20Actions-2E7D32)
![License](https://img.shields.io/badge/License-Proprietary-lightgrey)

MiniSlicer is a Streamlit-based additive manufacturing planning workbench. It
helps users explore slicer logic, compare infill strategies, review print
readiness, estimate time, material, and cost, and export traceable planning
packages.

This is an independent product-development project built from a mechatronics
engineering perspective. The goal is to turn practical manufacturing knowledge
into clear software that can support early process planning, internal reviews,
customer discussions, and future commercial use by engineering teams or
manufacturing companies.

MiniSlicer is intentionally honest about its scope: it is a planning,
visualization, and feasibility tool, not a certified production slicer.

Production FDM G-code export is guarded by readiness checks and machine bounds,
but every job must still be validated on the target machine before release.

## Preview

Representative screenshots captured from the live Streamlit app:

| Design workspace | Release dashboard |
|---|---|
| ![Design workspace](docs/images/design-workspace.png) | ![Release dashboard](docs/images/release-dashboard.png) |

| Pattern comparison | DED process model |
|---|---|
| ![Pattern comparison](docs/images/pattern-comparison.png) | ![DED process model](docs/images/ded-process-model.png) |

| Export package |
|---|
| ![Export package](docs/images/export-package.png) |

## Product Capabilities

| Area | Capability |
|---|---|
| Geometry | Built-in parametric shapes, custom polygons, SVG outline import, and STL cross-section slicing |
| Toolpaths | Inward perimeters, parallel, zigzag, grid, triangular, honeycomb, and concentric infill |
| Planning Engine | Typed settings, reusable layer planning, full-build segment generation, pattern ranking, and deterministic plan fingerprints |
| Estimates | Path length, travel share, motion time, material use, cost, productivity, and batch impact |
| Release Review | Readiness score, launch score, program risk, quality scorecard, checklist, and cost-stack view |
| Quality Gates | Build-plate fit, missing paths, layer height, sparse infill, high travel, path count, volumetric flow, and process evidence |
| Commercial Inputs | Customer/job metadata, application type, batch quantity, target price, machine rate, labor rate, setup time, postprocess time, scrap, and margin |
| Metal AM Review | Neutral DED/WAAM estimates for wire demand, heat input, deposition rate, energy, robot-cell feasibility, and qualification burden |
| Process Intelligence | Versioned qualified-build records, dataset coverage review, applicability gating, and bounded DED parameter recommendations |
| Company Operations | Password authentication, role-based approvals, persistent SQLite records, model registry, recommendation release, and audit history |
| Visualization | Toolpath views, extrusion-width maps, speed maps, time maps, density maps, animation, pattern comparison, and 3D layer stacks |
| Export | CSV, JSON, SVG, preview G-code, guarded FDM production G-code, markdown dossier, HTML dossier, and text report |
| Traceability | Exports include active parameters, segment data, and stable planning fingerprints |

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

Manual launch:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

For development (tests + lint), install the dev dependencies instead:

```powershell
pip install -r requirements-dev.txt
```

Docker launch:

```powershell
docker compose up --build
```

Then open:

```text
http://localhost:8501
```

## Example Use Cases

- Compare infill strategies for path length, travel share, time, and material.
- Review whether an imported SVG or STL cross-section is reasonable before
  deeper process planning.
- Produce a traceable planning packet for an early customer or internal
  design review.
- Explore how process assumptions affect FDM quote estimates and launch
  readiness.
- Review a neutral DED/WAAM feasibility screen covering envelope fit, wire
  demand, energy, interpass risk, robot reach, payload, and qualification
  burden.
- Support manufacturing, robotics, mechatronics, or CAD/CAM learning when the
  tool is used in an educational setting.

## Workflow

1. Choose a quality profile, build plate, process mode, and control depth in
   Quick Setup - or load a sample job to populate every control in one click.
2. Import SVG/STL geometry or use a built-in parametric shape. A prior JSON
   export can also re-apply its job parameters to the controls from the Import
   section.
3. Tune perimeters, infill, print settings, placement, optimization, and preview
   appearance.
4. Set job metadata, batch quantity, quote assumptions, target price, and
   machine-time guardrails in Business / Launch.
5. Review the Executive, Quality Scorecard, and Advisor sections in the Release
   tab before exporting.
6. In Metal mode, review the DED process model for envelope fit, wire demand,
   heat input, energy, material savings, and lead-time compression.
7. Review Manufacturing Partner Fit for DfAM suitability, route comparison,
   qualification burden, service deliverables, and value versus conventional
   sourcing.
8. Review Production Handoff for thermal/interpass controls, robot reach and
   payload feasibility, program size, coupons, inspections, and traceability
   records.
9. Use the Launch Optimizer to review top moves, what-if levers, batch
   scenarios, and release checklist status.
10. Export a dossier for sign-off, plus data files for engineering traceability.
11. Use production G-code only when readiness is unblocked, process mode is FDM,
    and the selected machine profile matches the physical printer.
12. Open Process Intelligence to upload qualified build records and request a
    bounded DED starting-parameter recommendation for a known machine/material domain.
13. Use the company workflow to approve build evidence, promote evaluated model
    snapshots, release recommendations, manage users, and review the audit trail.

## Project Direction

MiniSlicer is being developed as a practical engineering product, not only as a
software demonstration. It combines software, manufacturing logic, and
mechatronics thinking in one tool so that additive manufacturing decisions are
easier to inspect, compare, and explain.

The project focuses on:

- Clear geometry and toolpath visualization for engineering review.
- Deterministic planning outputs that can be repeated and compared.
- Practical readiness checks before a job moves toward a real machine.
- Transparent time, material, cost, and productivity estimates.
- Early FDM planning support with guarded production G-code export.
- Neutral DED/WAAM feasibility review for large-format metal AM discussions.
- Exportable dossiers that help communicate assumptions, risks, and results.

The long-term direction is to keep improving MiniSlicer into a useful tool for
companies, workshops, labs, and engineering teams that need simple, traceable
additive manufacturing planning support.

## Quick Architecture

```text
Streamlit UI (app.py, ui/)
  -> geometry/import layer (src/geometry.py, src/svg_import.py, src/stl_import.py)
  -> planner/toolpaths (src/planner.py, src/toolpaths.py)
  -> metrics and analysis (src/metrics.py, src/job_analysis.py)
  -> validation gates (src/validation.py)
  -> visualization/export (src/plotting.py, src/animation.py, src/exporters.py)
```

The Streamlit interface collects process, geometry, business, and export
settings. Geometry helpers normalize built-in shapes, SVG outlines, and STL
cross-sections into Shapely polygons. The planner converts validated settings
into per-layer or full-build segments. Metrics and job-analysis modules estimate
time, material, cost, productivity, DED feasibility, and release readiness.
Validation turns those results into user-facing blockers and warnings.
Exporters package the selected layer or full build for engineering review.

See [docs/architecture.md](docs/architecture.md) for a deeper module map.

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

Metal planning mode adds a neutral wire-arc DED process model. It estimates wire
mass flow from wire diameter and feed rate, deposited kg/h from deposition
efficiency, heat input from arc voltage/current and travel speed, energy per kg,
near-net machining allowance, feedstock required, material saved versus billet
buy-to-fly, build-envelope utilization, and additive lead-time compression.

The manufacturing-partner fit model scores whether a customer job is a good
candidate for a large-format metal AM service workflow. It combines lead-time
compression, material reduction, conventional route, urgency, annual quantity,
qualification burden, tolerances, inspection needs, and redesign effort into a
fit verdict with expected deliverables for customer collaboration.

The production handoff model adds three release-review views: thermal/interpass
planning, robot-cell feasibility, and qualification evidence. Thermal planning
uses arc energy, heat retention, part heat capacity, cooling rate, preheat, and
interpass limit assumptions to estimate dwell. Robot-cell feasibility checks
reach, payload, fixture mass, torch clearance, and program size. Qualification
planning converts the application risk into coupon counts, inspection steps, and
traceability records.

The Process Intelligence workspace adds an evidence-backed learning layer for
DED development. It stores versioned build-level records, filters training data
to accepted builds from one compatible machine/material domain, rejects
out-of-domain jobs, clamps recommendations to engineer-approved limits, and
shows confidence plus the build IDs used as evidence. It never generates robot
motion or bypasses deterministic release gates.

See [docs/process-intelligence.md](docs/process-intelligence.md) for the data
contract, validation boundary, and suggested company storage architecture.

Company deployments store operational state in `data/minislicer.db` by default.
Set `MINISLICER_DB_PATH` to place the SQLite database on a persistent volume.
The first visit to Company Operations creates the initial administrator; later
visits require authentication. Roles are `admin`, `engineer`, `operator`, and
`viewer`.

For multi-instance or high-concurrency deployments, migrate the storage adapter
to PostgreSQL before scaling beyond one Streamlit application instance.

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

## Engineering Validation

The automated test suite covers geometry helpers, toolpath generation, planner
contracts, metrics, validation gates, exporters, job economics, STL/SVG handling,
Plotly figure builders, the Streamlit app shell in default, advanced, and metal
modes, and text-quality checks. Ruff linting runs in CI alongside the tests.

```powershell
.\scripts\test.ps1
```

The script lints with ruff first, then runs pytest.

The tests validate software behavior and deterministic calculations. They do not
certify machine safety, material properties, printer firmware compatibility,
robot collision avoidance, metallurgy, or production readiness. Real deployment
still requires printer-specific slicing review, dry runs, fixturing checks,
material/process qualification, and sign-off by qualified manufacturing
engineers.

See [docs/validation.md](docs/validation.md) for details.

## Example Data

The repository includes small, reviewable example assets under `examples/`:

- `sample-bracket.svg`
- `demo-fdm-job.json`
- `demo-ded-job.json`
- `sample-job-dossier.md`
- `sample-job-dossier.html`

See [examples/README.md](examples/README.md). Large binary fixtures are
intentionally not included.

## Limitations

- This is not a certified production slicer.
- STL handling is focused on horizontal cross-section studies, not robust repair
  of arbitrary non-manifold meshes.
- SVG parsing supports practical closed outlines but is not a full SVG renderer.
- The DED/WAAM model is a neutral feasibility approximation, not a calibrated
  process recipe.
- Preview G-code is educational. Production G-code export is guarded and FDM
  only, and still requires machine validation.
- Collision checking, thermal simulation, support generation, path pressure
  advance, firmware-specific tuning, and closed-loop process control are out of
  scope today.

See [docs/limitations.md](docs/limitations.md) for the fuller list.

## Roadmap

- Extend config re-apply to advanced and DED fields (core job parameters -
  shape, toolpath, print, plate, and business basics - already repopulate the
  controls from a JSON export or a sample job).
- Add richer example STL fixtures with clear licenses and small file sizes.
- Add richer STL diagnostics for scale, units, watertightness, and slice quality.
- Add more machine profiles and explicit profile provenance notes.
- Expand production G-code safeguards with preview simulation and printer-family
  compatibility checks.
- Add optional report templates for customer-facing feasibility studies,
  internal engineering reviews, and production handoff packages.
- Add benchmark fixtures for large geometries and dense infill patterns.
- Add telemetry adapters for OPC UA, robot logs, thermal cameras, and inspection systems.
- Add immutable model cards and grouped chronological evaluation reports per machine/material domain.

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
src/process_intelligence.py Qualified-build schema and bounded recommendation engine
src/validation.py       Manufacturability readiness checks
src/exporters.py        CSV, JSON, SVG, preview G-code, and production G-code
src/plotting.py         Plotly 2D/3D visualization builders
src/stl_import.py       STL metadata and cross-section slicing
src/svg_import.py       SVG outline parsing
ui/                     Streamlit controls and panels
pages/tutorial.py       Built-in guide and teaching workflow
pages/process_intelligence.py Company dataset and recommendation workspace
docs/                   Architecture, validation, limitations, and demo notes
examples/               Small SVG, JSON, and dossier demo assets
tests/                  Pytest coverage plus Streamlit smoke and text-quality checks
```

## Safety Note

MiniSlicer is a planning and visualization tool. It does not replace a qualified
manufacturing engineer, printer-specific slicer validation, material process
qualification, fixture review, collision checking, or machine commissioning.

## License

This project is proprietary software. All rights are reserved. See
[LICENSE](LICENSE) for details.
