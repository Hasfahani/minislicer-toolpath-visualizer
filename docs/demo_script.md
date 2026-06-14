<!-- # Purpose: Provides a short presentation script and demo flow for explaining MiniSlicer live. -->
<!-- # Reason: A prepared script helps communicate the engineering value clearly in interviews or reviews. -->
# 60-90 Second Demo Script

## Audience

This script works for recruiters, professors, product reviewers, and
manufacturing engineers. Adjust the emphasis based on who is watching:

- Recruiters: emphasize full-stack engineering, tests, packaging, and clear
  product thinking.
- Professors: emphasize geometry, planning assumptions, validation boundaries,
  and engineering communication.
- Product reviewers: emphasize workflow, quote signals, release readiness, and
  customer-facing exports.
- Manufacturing engineers: emphasize checks, limitations, DED assumptions, and
  the safety boundary.

## Script

"MiniSlicer is an additive manufacturing planning workbench built in Python and
Streamlit. It lets me move from geometry to toolpath planning, readiness review,
cost estimates, and exportable planning packages in one place.

I start in the Design workspace by choosing a shape or importing SVG/STL
geometry. The geometry is normalized into Shapely polygons, then the planner
generates perimeters and infill patterns like zigzag, grid, triangular,
honeycomb, and concentric.

In the Plan view, I can compare patterns and inspect path length, travel share,
estimated time, material, and visual maps for speed, time, density, and
extrusion width. The planner creates deterministic fingerprints, so a package
can be traced back to its geometry and settings.

The Release view is where the project becomes more than a visualizer. It checks
manufacturability issues, estimates quote and productivity signals, and creates
a quality scorecard and action list. In metal mode, it also shows a neutral
DED/WAAM feasibility model for wire demand, heat input, envelope fit, robot
reach, payload, and qualification evidence.

Finally, I can export CSV, JSON, SVG, preview G-code, guarded FDM production
G-code, and markdown or HTML dossiers. The important safety boundary is that
this is a planning and visualization tool. It does not claim production
certification; every real job still needs machine-specific validation and
qualified engineering sign-off."

## Suggested Live Flow

1. Open `http://localhost:8501`.
2. Keep the default shape for speed or import a simple SVG.
3. Switch between two infill patterns and point out the metric changes.
4. Open Release and show readiness, Launch Optimizer, Quality Scorecard, and
   Advisor.
5. Switch to Metal mode if the audience cares about DED/WAAM.
6. Show the export panel and explain the difference between preview G-code,
   guarded FDM production G-code, and the dossier.

## Closing Line

"The goal of the project is to show that I can build engineering software that
connects math, manufacturing constraints, product workflow, testing, and honest
safety boundaries."
