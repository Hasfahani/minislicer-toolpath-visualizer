<!-- Purpose: Defines the industrial data and ML boundary for MiniSlicer. -->
<!-- Reason: Company adoption requires traceable evidence, conservative recommendations, and honest limits. -->
# Process Intelligence

MiniSlicer keeps geometry slicing, toolpath creation, hard process limits, and
machine export deterministic. Machine learning is introduced as an advisory
layer over completed and quality-reviewed builds.

## First Production Use Case

The initial model recommends a starting DED parameter window for a known
machine and material:

- travel speed
- wire-feed rate
- arc current
- arc voltage
- interpass temperature limit

It does not generate robot motion, bypass readiness gates, or release a build.

## Required Company Data

Store one `BuildRecord` for every completed build. A useful record includes:

- anonymous build, machine, material, and material-batch identifiers
- plan fingerprint and geometry family
- volume, surface area, height, maximum section, wall thickness, and overhang fraction
- wire diameter and layer height
- commanded travel speed, wire feed, current, voltage, and interpass limit
- dimensional error, porosity, roughness, deposition efficiency, interruptions
- final accepted/rejected disposition from the responsible engineer

Raw high-frequency telemetry should remain in a separate time-series or object
store and reference the same build ID. Useful signals include current, voltage,
wire feed, robot speed, torch position, interpass temperature, melt-pool camera,
thermal images, gas flow, alarms, and operator interventions.

## Safety and Validation Rules

- Train one model per compatible machine/material domain.
- Rejected builds remain available for failure models but never become parameter recipes.
- Require a minimum number of accepted builds before enabling recommendations.
- Split evaluation by complete build and chronologically. Never mix layers from
  one build across training and test sets.
- Reject requests outside the model's applicability domain.
- Clamp every recommendation to engineer-approved parameter limits.
- Display evidence build IDs, confidence, warnings, model version, and dataset version.
- Require a monitored development build before promoting a recommendation into
  a qualified procedure.

## Suggested Storage Layout

```text
data/
  build-records.jsonl        versioned build-level labels and settings
  telemetry/
    <build-id>/              raw sensor streams and images
  models/
    <machine>/<material>/    immutable model artifacts and evaluation reports
```

Open datasets such as NIST AM-Bench are appropriate for research, feature
development, and benchmarking. Final process recommendations must be validated
against the company's own machines, materials, sensors, operators, and
inspection procedures.
