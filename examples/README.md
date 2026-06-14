<!-- # Purpose: Explains the small example assets included for import, export, and dossier demos. -->
<!-- # Reason: Example documentation keeps demo fixtures understandable and avoids accidental customer data. -->
# MiniSlicer Example Assets

This folder contains small, reviewable demo assets and placeholders for future
project fixtures. Do not commit large binary fixtures unless they are truly
needed and clearly licensed.

## Included Files

| File | Purpose |
|---|---|
| `sample-bracket.svg` | Small SVG outline for import and screenshot demos |
| `demo-fdm-job.json` | Compact FDM planning packet fixture |
| `demo-ded-job.json` | Compact DED/WAAM feasibility packet fixture |
| `sample-job-dossier.md` | Small markdown dossier example |
| `sample-job-dossier.html` | Small standalone HTML dossier example |

The JSON files are intentionally compact examples. Generate fresh exports from
the app for formal reviews or regression fixtures.

## Recommended Future Files

### Sample SVG Outlines

Add more lightweight vector files that demonstrate common planning scenarios:

- simple bracket outline
- logo or nameplate outline
- coupon or test geometry
- sharp-corner geometry for readiness warnings
- thin-wall outline for manufacturability review

Suggested filenames:

```text
sample-bracket.svg
sample-nameplate.svg
thin-wall-coupon.svg
```

### Sample STL Parts

Add small STL files only when they are simple, licensed, and useful for
cross-section demos:

- block with a hole
- simple bracket
- curved surface test piece
- part with changing cross-section by Z height

Suggested filenames:

```text
sample-bracket.stl
stepped-cross-section.stl
```

### Demo FDM Job JSON

Add exported JSON from a known-good FDM planning run. It should demonstrate:

- active parameters
- segment data
- plan fingerprint
- readiness state
- production export metadata

Suggested filename:

```text
demo-fdm-job.json
```

### Demo DED Job JSON

Add exported JSON from a metal planning run. It should demonstrate:

- DED process assumptions
- wire-feed and heat-input estimates
- robot and qualification review state
- launch and commercial signals

Suggested filename:

```text
demo-ded-job.json
```

### Sample Markdown Dossier

Add additional markdown dossiers exported from the app for product or engineering review.

Suggested filename:

```text
sample-job-dossier.md
```

### Sample HTML Dossier

Add matching standalone HTML dossiers when useful for demos or screenshots.

Suggested filename:

```text
sample-job-dossier.html
```

## Notes

- Keep examples small and human-reviewable.
- Prefer generated exports from the current app so examples stay realistic.
- Do not include proprietary customer geometry.
- Document the source and license for any external asset.
