# Limitations

MiniSlicer is a planning, visualization, and portfolio demonstration tool. It is
not a certified production slicer, CAM package, robot programmer, or process
qualification system.

## Geometry and Imports

- STL support is focused on horizontal cross-section studies.
- STL files are treated as unitless geometry and scaled with a target-width
  control.
- Non-manifold, noisy, extremely dense, or self-intersecting meshes may fail to
  slice cleanly.
- SVG parsing supports practical closed outlines made from common path and
  polygon data, but it is not a full SVG rendering engine.
- Imported geometry is reduced to 2D planning polygons; details such as
  textures, colors, assemblies, and CAD feature history are ignored.

## Toolpath Planning

- The planner models simplified 2D slicer behavior.
- Support generation is not implemented.
- Adaptive layer heights are not implemented.
- Overhang analysis is not implemented.
- Seam optimization is limited to simple ordering and preview controls.
- Pressure advance, flow calibration, retraction tuning, and firmware-specific
  extrusion behavior are not modeled.
- Honeycomb and other infill patterns are planning approximations, not exact
  replicas of commercial slicer implementations.

## Time, Material, and Cost Estimates

- Motion time uses a simplified acceleration model and does not include every
  machine firmware behavior.
- Material estimates use bead/cross-section approximations.
- Default rates and cost assumptions are placeholders for planning demos.
- Quote outputs should be replaced with organization-specific rates, labor
  standards, scrap data, and machine utilization assumptions before business
  use.

## Production G-code

- Preview G-code is educational and is not machine-ready.
- Production G-code export is guarded and limited to FDM-style workflows.
- A passing readiness state does not certify the generated output.
- Production output still requires printer-specific slicing review, simulation
  where available, dry runs, and operator sign-off.

## Metal DED/WAAM Model

- DED and WAAM calculations are neutral feasibility estimates.
- The app does not generate robot code.
- Robot reach and payload checks are simplified planning checks, not collision
  simulation.
- Thermal/interpass estimates are coarse calculations, not finite-element
  thermal simulation.
- Metallurgy, dilution, residual stress, bead geometry calibration, shielding,
  wire chemistry, NDT acceptance criteria, and procedure qualification remain
  outside the current model.

## Reliability and Deployment

- The app is optimized for interactive demos and engineering review, not
  multi-user production scheduling.
- Large imported geometries or very dense infill settings can be slow.
- JSON exports include parameters and segment data, but exported settings do not
  yet fully repopulate every UI control.
- Browser layout and screenshots should be checked after significant UI changes.
