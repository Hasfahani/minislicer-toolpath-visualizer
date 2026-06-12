# Engineering Validation

MiniSlicer uses automated tests to validate the software model and a written
safety boundary to separate planning output from machine-qualified production
use.

## What the Test Suite Covers

The current pytest suite validates:

- shape creation and polygon validation
- built-in shape and infill catalogs
- perimeter and infill generation
- triangular, honeycomb, zigzag, grid, parallel, and concentric path behavior
- path ordering, travel distance, and segment conversion
- immutable planner settings and layer-plan outputs
- full-build segment generation and layer limits
- deterministic planning fingerprints
- path length, material, area, bounding-box, and time estimates
- acceleration-aware motion-time behavior
- manufacturability/readiness gates
- CSV, JSON, SVG, preview G-code, and production G-code exporters
- guarded production G-code failure modes
- STL metadata and horizontal slicing helpers
- SVG outline parsing
- quote, productivity, launch, quality, DED, robot, thermal, and qualification
  analysis helpers
- markdown and HTML dossier generation
- Plotly visualization builders
- the default Streamlit app shell
- repository text quality checks

The Streamlit smoke tests render the real app in default, Advanced-controls,
and Metal-process modes, which locks the settings contract between the sidebar
control modules and the application script.

Run the suite with:

```powershell
.\scripts\test.ps1
```

This lints with ruff first, then runs pytest. Or run the steps directly:

```powershell
python -m ruff check .
python -m pytest -q
```

## What the Tests Mean

Passing tests mean the code is behaving consistently with its current planning
assumptions. They are especially useful for protecting deterministic planning
logic, export schemas, readiness blockers, and calculation formulas from
regression.

They do not mean a generated plan is safe to run on a machine.

## Required Real-World Validation

Any real production use still requires qualified review outside this project:

- printer-specific slicer comparison
- dry-run or air-print validation
- target firmware review
- bed/nozzle/tool calibration
- extrusion or deposition calibration
- material qualification
- thermal and distortion review
- fixture and workholding review
- robot collision checking for DED/WAAM cells
- interpass and heat-input validation
- coupon testing where required
- inspection-plan approval
- operator and manufacturing engineer sign-off

## G-code Boundary

MiniSlicer has two different G-code concepts:

- Preview G-code: educational motion-style output for inspection and learning.
- Guarded FDM production G-code: machine-profiled output that is only enabled
  when the app readiness state allows it.

The guarded export adds checks, but it is still not a substitute for
printer-specific slicing, simulation, and physical validation.

## DED/WAAM Boundary

The metal process model is a neutral feasibility estimate. It is useful for
portfolio demos, early customer conversations, and comparing order-of-magnitude
process assumptions. It is not a qualified WAAM/DED procedure specification,
metallurgical model, or robot program generator.
