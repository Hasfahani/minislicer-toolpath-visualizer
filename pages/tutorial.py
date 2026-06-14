# Purpose: Streamlit tutorial page that explains workflows, metrics, checks, exports, and demo flow.
# Reason: Kept separate from the main app so interview/demo guidance does not clutter the planning UI.
"""Advanced tutorial and operating guide for MiniSlicer."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="MiniSlicer - Advanced Guide",
    layout="wide",
    page_icon=":material/menu_book:",
)


def tutorial_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { max-width: 1240px; padding-top: 1rem; padding-bottom: 2.5rem; }
        .guide-hero {
            background: #172033;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 1.2rem 1.35rem;
            margin-bottom: 1rem;
            box-shadow: 0 12px 30px rgba(23, 32, 51, 0.12);
        }
        .guide-hero h1 {
            color: #f8fafc;
            font-size: 1.72rem;
            line-height: 1.2;
            margin: 0 0 0.35rem 0;
            letter-spacing: 0;
        }
        .guide-hero p {
            color: #cbd5e1;
            margin: 0;
            max-width: 850px;
            font-size: 0.96rem;
        }
        .guide-card {
            border: 1px solid #d7dde8;
            border-radius: 8px;
            padding: 0.9rem 1rem;
            background: #ffffff;
            min-height: 8rem;
        }
        .guide-card strong { color: #172033; }
        .guide-kicker {
            color: #475569;
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }
        .guide-callout {
            border-left: 4px solid #0f766e;
            background: #f0fdfa;
            padding: 0.75rem 0.9rem;
            border-radius: 6px;
            margin: 0.35rem 0 0.65rem;
        }
        .guide-note {
            border-left: 4px solid #1d4ed8;
            background: #eff6ff;
            padding: 0.75rem 0.9rem;
            border-radius: 6px;
            margin: 0.35rem 0 0.65rem;
        }
        div[data-testid="stExpander"] { border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def expander(title: str, body: str, *, expanded: bool = False, icon: str | None = None) -> None:
    with st.expander(title, expanded=expanded, icon=icon):
        st.markdown(body)


def reference(title: str, intro: str, table_md: str, *, icon: str | None = None) -> None:
    """Render a collapsible control-reference block: intro text plus a table."""
    with st.expander(title, icon=icon):
        if intro:
            st.markdown(intro)
        st.markdown(table_md)


def format_mm(value: float) -> str:
    return f"{value:.2f} mm"


tutorial_css()

st.markdown(
    """
    <div class="guide-hero">
        <h1>MiniSlicer Advanced Operating Guide</h1>
        <p>
            A complete tuning manual and demo companion: learn how the app is laid out,
            what every control does, how each metric and readiness check is calculated,
            and how to drive a clean, confident walkthrough.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Open the MiniSlicer planner from the sidebar. The planner has three tabs - "
    "Design (preview and View pills), Plan (pattern comparison, animation, metrics), and "
    "Release (readiness, advisor, segment ledger, export) - driven by a numbered control sidebar. "
    "Keep this page open as a decision guide while you tune settings."
)

# Quick jump links so a presenter can reach any section fast.
st.markdown(
    "**Jump to:** "
    "[Layout map](#layout-map) | "
    "[Five-minute walkthrough](#walkthrough) | "
    "[Goal recipes](#goal-recipes) | "
    "[Control reference](#control-reference) | "
    "[View modes](#view-modes) | "
    "[Formula lab](#formula-lab) | "
    "[Metrics and scores](#metrics-scores) | "
    "[Readiness checks](#readiness-checks) | "
    "[Diagnosis](#diagnosis) | "
    "[Playbooks](#parameter-playbooks) | "
    "[Metal / DED](#metal-ded) | "
    "[Experiments](#experiments) | "
    "[Data columns](#data-columns) | "
    "[Pre-export audit](#pre-export-audit) | "
    "[Glossary](#glossary) | "
    "[Presenter notes](#presenter-notes)"
)

top_cards = st.columns(3)
with top_cards[0]:
    st.markdown(
        """
        <div class="guide-card">
            <div class="guide-kicker">Do first</div>
            <strong>Pick a measurable goal.</strong><br>
            Optimize for speed, strength, visual clarity, path efficiency, or export readiness.
        </div>
        """,
        unsafe_allow_html=True,
    )
with top_cards[1]:
    st.markdown(
        """
        <div class="guide-card">
            <div class="guide-kicker">Then change</div>
            <strong>One variable at a time.</strong><br>
            Spacing, perimeters, angle, clearance, and optimization each leave a different signature.
        </div>
        """,
        unsafe_allow_html=True,
    )
with top_cards[2]:
    st.markdown(
        """
        <div class="guide-card">
            <div class="guide-kicker">Always verify</div>
            <strong>Preview plus Advisor.</strong><br>
            The chart shows geometry; Advisor shows whether the plan is coherent enough to export.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Layout map
# ---------------------------------------------------------------------------
st.header("How MiniSlicer is organized", anchor="layout-map")
st.markdown(
    "The app has three zones: a **Quick Setup bar** at the top, a **numbered control "
    "sidebar** on the left, and **three workspace tabs** in the main area. Set the job "
    "mode in Quick Setup, refine details top-to-bottom in the sidebar, then read results "
    "in the tabs."
)

map_cols = st.columns(3)
with map_cols[0]:
    st.markdown(
        """
        **Quick Setup bar (top)**

        - Load a sample job (one click)
        - Quality profile
        - Build plate (None / 220 / 300)
        - Controls (Basic / Advanced)
        - Process (FDM / Metal)
        - Reset
        """
    )
with map_cols[1]:
    st.markdown(
        """
        **Control sidebar (left)**

        - Import (SVG / STL / config)
        - 1 - Shape
        - 2 - Toolpath
        - 3 - Print settings
        - Metal / DED process (metal mode)
        - 4 - Placement
        - 5 - Appearance and overlays
        - Quality / Export (Advanced)
        - 6 - Business / Launch
        """
    )
with map_cols[2]:
    st.markdown(
        """
        **Three workspaces (main)**

        - Design: preview, View pills, STL 3D
        - Plan: pattern comparison, all-pattern
          matrix, animation, metrics
        - Release: executive dashboard, gates,
          optimizer, quote sensitivity, advisor,
          segment ledger, export
        """
    )

st.markdown(
    """
    <div class="guide-note">
    Basic mode hides the advanced fields so a live demo stays clean. Switch
    <strong>Controls</strong> to <strong>Advanced</strong> to reveal overrides inside
    every numbered section (extra toolpath, print, placement, business, and DED fields,
    plus the Quality / Export section).
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Five-minute walkthrough
# ---------------------------------------------------------------------------
st.header("Five-minute guided walkthrough", anchor="walkthrough")
st.markdown(
    """
    1. **Quick Setup:** load a sample job for an instant starting point, or choose a
       Quality profile (Balanced is a safe default), set Build plate to 220 x 220,
       and leave Controls on Basic and Process on FDM.
    2. **Sidebar 1 - Shape:** pick Rectangle and set roughly 80 x 50 mm so the infill
       is easy to read on screen.
    3. **Sidebar 2 - Toolpath:** set Perimeters to 3, choose an infill pattern, and set
       Fill by Density to about 25 percent.
    4. **Sidebar 3 - Print settings:** set Model height to the real part height so the
       full-build time, material, and cost are meaningful.
    5. **Design tab:** use the **View** pills to flip Toolpath -> Travel only -> Speed map
       -> Density. Turn off Auto-fit axes if you want to keep one zoom while switching.
    6. **Plan tab:** open Pattern Ranking and Comparison to show the recommended pattern,
       then the head-to-head A/B, then Metrics Detail.
    7. **Release tab:** read the launch score, Release Gates, Advisor findings, and the
       quote, then export a dossier.
    """
)

st.markdown(
    """
    <div class="guide-callout">
    Demo tip: change exactly one control at a time and name the metric you expect to
    move. "Watch travel share drop when I switch to Zigzag" lands better than silently
    clicking through settings.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Goal-based recipes
# ---------------------------------------------------------------------------
st.header("Goal-based recipes", anchor="goal-recipes")
goal = st.selectbox(
    "What are you trying to improve?",
    [
        "Fast preview / teaching demo",
        "Stronger FDM part",
        "Cleaner surface / fewer artifacts",
        "Lower material use",
        "Better path efficiency",
        "Production G-code readiness",
        "DED / metal planning review",
    ],
)

recipes = {
    "Fast preview / teaching demo": {
        "settings": [
            "Quality profile: Fast Preview or Draft",
            "Shape: Rectangle, Circle, or simple SVG",
            "Perimeters: 1-2",
            "Spacing: 5-8 mm or Density: 10-20%",
            "Design tab View: Toolpath, then Animation in the Plan tab",
        ],
        "watch": "Segment count, render speed, and whether the infill pattern is readable at a glance.",
        "avoid": "Dense honeycomb on a large shape; it hides the concept behind too many lines.",
    },
    "Stronger FDM part": {
        "settings": [
            "Quality profile: Strong, then switch to Advanced",
            "Perimeters: 4-5",
            "Spacing: 1.8-2.5 mm or Density: 35-60%",
            "Alternate angle each layer: on",
            "Infill overlap: 0.05-0.15 mm",
        ],
        "watch": "Material, full build time, and the Design tab Density view for over-concentrated zones.",
        "avoid": "Layer height above roughly 75% of nozzle diameter; Advisor should flag this.",
    },
    "Cleaner surface / fewer artifacts": {
        "settings": [
            "Perimeter speed mult.: 0.6-0.85",
            "Perimeters: 3-4",
            "Line thickness display: 1.0-1.5 for inspection",
            "Show seam markers and start/end points",
            "Try Concentric for shape-following internal paths",
        ],
        "watch": "Seams, short segments, and perimeter spacing relative to nozzle diameter.",
        "avoid": "Aggressive simplification that visibly changes corners or small features.",
    },
    "Lower material use": {
        "settings": [
            "Perimeters: 2",
            "Spacing: 4-7 mm or Density: 10-25%",
            "Wall clearance: 0-0.2 mm",
            "Use the Plan tab pattern comparison to test Zigzag vs Parallel Lines",
            "Model height: set to real part height before trusting full material estimates",
        ],
        "watch": "Material, cost, full build time, and whether no-infill warnings appear.",
        "avoid": "Reducing perimeters before checking whether the part still needs shell strength.",
    },
    "Better path efficiency": {
        "settings": [
            "Advanced controls: on",
            "Optimize infill order: on",
            "Allow line reversal: on",
            "Try Zigzag or Concentric",
            "Design tab View: Travel only, then Metrics in the Plan tab",
        ],
        "watch": "Travel share, path efficiency, and optimization results in the Plan tab Metrics.",
        "avoid": "Judging only by total path length; travel can dominate motion time on fragmented paths.",
    },
    "Production G-code readiness": {
        "settings": [
            "Process: FDM",
            "Show build plate: on",
            "Center on plate or Fit inside plate",
            "Set nozzle, layer height, travel speed, and E/mm in Advanced mode",
            "Advisor status must not be Blocked",
        ],
        "watch": "Production export status, machine profile bounds, and readiness blockers.",
        "avoid": "Treating preview G-code as machine-ready; it is educational output.",
    },
    "DED / metal planning review": {
        "settings": [
            "Process: Metal (LPBF/DED)",
            "Use a metal material profile",
            "Prefer larger spacing and simpler paths for first inspection",
            "Use the Design tab Speed map and Time map views to inspect motion assumptions",
            "Export CSV/JSON/report for review rather than production FDM G-code",
        ],
        "watch": "Weight, path length, motion time, and whether the shape creates tiny unstable segments.",
        "avoid": "Using FDM production G-code export for metal workflows.",
    },
}

selected = recipes[goal]
recipe_cols = st.columns([1.25, 1, 1])
with recipe_cols[0]:
    st.markdown("**Recommended controls**")
    for item in selected["settings"]:
        st.markdown(f"- {item}")
with recipe_cols[1]:
    st.markdown("**Inspect**")
    st.markdown(selected["watch"])
with recipe_cols[2]:
    st.markdown("**Avoid**")
    st.markdown(selected["avoid"])

st.divider()

# ---------------------------------------------------------------------------
# Control reference
# ---------------------------------------------------------------------------
st.header("Control reference", anchor="control-reference")
st.caption(
    "Every control, grouped by where it lives. Fields marked (Advanced) only appear when "
    "Controls is set to Advanced in Quick Setup."
)

reference(
    "Quick Setup bar",
    "Top-of-page mode switches. These reshape the rest of the UI.",
    """
    | Control | What it does | Typical choice |
    |---|---|---|
    | Load a sample job | Populates every job control from a named demo configuration | FDM bracket to start |
    | Quality profile | Presets perimeters, layer height, speed, and spacing | Balanced for demos |
    | Build plate | Draws a 220 or 300 mm reference plate behind the part | 220 x 220 |
    | Controls | Basic hides advanced fields; Advanced reveals every override | Basic to present |
    | Process | FDM polymer printing vs Metal (LPBF/DED) planning | FDM |
    | Reset | Clears all settings and reloads defaults | Use to start clean |

    **Quality profile values**

    | Profile | Layer height | Speed | Perimeters | Spacing |
    |---|---|---|---|---|
    | Fast Preview | 0.32 mm | 90 mm/s | 1 | 6.0 mm |
    | Draft | 0.28 mm | 70 mm/s | 2 | 4.0 mm |
    | Balanced | 0.20 mm | 50 mm/s | 3 | 3.0 mm |
    | Strong | 0.20 mm | 45 mm/s | 5 | 2.2 mm |
    | Fine | 0.12 mm | 35 mm/s | 4 | 2.0 mm |
    """,
    icon=":material/tune:",
)

reference(
    "Import (SVG / STL / config)",
    "Optional. Use this to plan against real geometry instead of a built-in shape.",
    """
    | Control | What it does |
    |---|---|
    | Review JSON export | Loads a prior JSON export and re-applies its core job parameters to the controls |
    | Import SVG shape | Replaces the built-in shape with a closed SVG outline |
    | SVG target width | Scales the SVG so its width equals this many mm |
    | Import STL mesh | Loads a mesh for horizontal cross-section slicing |
    | STL target width | Scales the unitless mesh so its width equals this many mm |
    | Slice at Z | Height of the 2D cross-section taken from the mesh |

    When an SVG or STL is loaded, the Shape section is disabled and the preview uses the
    imported geometry. STL takes priority if both are present.
    """,
    icon=":material/upload_file:",
)

reference(
    "1 - Shape",
    "Parametric geometry. The dimension fields change with the selected shape.",
    """
    | Control | What it does |
    |---|---|
    | Shape type | 11 parametric built-ins plus Custom Polygon (full list in the Shape dropdown) |
    | Width / Height | Bounding dimensions for rectangle, ellipse, triangle, capsule |
    | Radius / Sides / Points | Circle, regular polygon, and star parameters |
    | Corner radius | Fillet size for the rounded rectangle |
    | Custom Polygon vertices | Points entered as "x,y; x,y; ..." separated by semicolons |

    Disabled while an SVG or STL import is active.
    """,
    icon=":material/category:",
)

reference(
    "2 - Toolpath",
    "How walls and infill are generated for the active layer.",
    """
    | Control | What it does | Range / default |
    |---|---|---|
    | Perimeters | Number of inward wall loops | 1 - 10 |
    | Perim. spacing (mm) | Gap between adjacent walls | min 0.1, default 1.0 |
    | Infill pattern | Parallel Lines, Zigzag, Grid, Triangles, Honeycomb, Concentric | Parallel Lines |
    | Fill by | Spacing sets the gap directly; Density derives it | Spacing |
    | Density (%) | Target fill; spacing = nozzle x 100 / density | 5 - 100 |
    | Infill angle (deg) (Advanced) | Rotation of the fill lines | -90 to 90 |
    | Alternate angle each layer (Advanced) | Flips angle on odd/even layers for bonding | off |
    | Wall clearance (mm) (Advanced) | Pulls infill away from the walls | 0.0 |
    | Infill overlap (mm) (Advanced) | Lets infill bond back into the walls | 0.0 |
    | Perimeter speed mult. (Advanced) | Print-speed multiplier for walls | 0.2 - 1.5, default 0.8 |
    """,
    icon=":material/route:",
)

reference(
    "3 - Print settings",
    "Process parameters that drive time, material, weight, and cost.",
    """
    | Control | What it does |
    |---|---|
    | Printer profile | Custom, plus PLA / PETG / ABS (FDM) and 316L / Ti-6Al-4V / Inconel 625 (LPBF) presets |
    | Layer # | Which single layer the preview and per-layer metrics use |
    | Model height (mm) | Real part height; sets layer count and full-build time, material, and cost |
    | Material | Density used for weight (PLA, PETG, ABS, TPU, ASA, and DED metals) |
    | Material cost ($/kg) | Feedstock price used in the quote |
    | Layer height (mm) (Advanced) | Vertical layer thickness |
    | Nozzle diameter (mm) (Advanced) | Extrusion / bead width used for volume and density |
    | Print speed (mm/s) (Advanced) | Nominal printing speed |
    | Travel speed (mm/s) (Advanced) | Non-printing move speed |
    | Filament diameter (mm) (Advanced) | 1.75 or 2.85 for filament length math |
    | Accel (mm/s^2) (Advanced) | Acceleration used by the motion-time model |
    """,
    icon=":material/print:",
)

reference(
    "4 - Placement",
    "Where the part sits on the plate and how it is transformed.",
    """
    | Control | What it does |
    |---|---|
    | Show build plate | Draws the reference plate and enables plate-fit checks |
    | Scale (%) | Uniform scale of the geometry |
    | Rotate (deg) | Rotation about the center |
    | Center on plate | Centers the part on the plate |
    | Fit inside plate (Advanced) | Scales the part to fit within the plate margin |
    | Plate margin (mm) (Advanced) | Keep-out border used by fit |
    | Plate width / depth (mm) (Advanced) | Custom plate size |
    | Mirror X / Y (Advanced) | Flips the geometry on an axis |
    | Translate X / Y (mm) (Advanced) | Manual offset on the plate |
    """,
    icon=":material/open_with:",
)

reference(
    "5 - Appearance and overlays",
    "Pure display controls. They change how the preview looks, not the toolpath.",
    """
    | Control | What it does |
    |---|---|
    | Color scheme | Classic, Colorblind, Dark, Neon, High Contrast |
    | Line thickness | Visual weight of the preview lines (0.5 - 3.0) |
    | Outline | Show the part boundary |
    | Perimeters | Show the wall paths |
    | Infill | Show the fill paths |
    | Dimensions | Annotate the bounding size |
    | Travel moves | Show non-printing moves |
    | Seam markers | Mark perimeter start/end seams |
    | Start/end points | Mark the first and last motion points |
    | Direction arrows | Show travel direction |
    | Extrusion width | Render paths at bead width instead of thin lines |
    """,
    icon=":material/palette:",
)

reference(
    "Quality / Export (Advanced)",
    "Path-ordering and G-code options. Only visible in Advanced mode.",
    """
    | Control | What it does |
    |---|---|
    | Optimize perimeter order | Nearest-neighbor ordering of wall loops to cut travel |
    | Optimize infill order | Nearest-neighbor ordering of infill lines |
    | Allow line reversal | Lets infill lines run in either direction when ordering |
    | Simplify tol. (mm) | Douglas-Peucker tolerance to drop noisy micro-segments |
    | Min seg. len (mm) | Drops segments shorter than this length |
    | Z-hop (mm) | Z lift before travel moves in exported G-code |
    | E/mm | Extrusion amount per mm for preview G-code |
    | Include E values in G-code | Adds extrusion values to the exported preview G-code |
    """,
    icon=":material/tune:",
)

reference(
    "6 - Business / Launch",
    "Job metadata and the assumptions behind the quote and launch score.",
    """
    | Control | What it does |
    |---|---|
    | Job name / Customer / Owner / Job ID | Metadata stamped onto exports and the dossier |
    | Batch qty | Parts in the batch; setup labor is amortized across it |
    | Target $/part | Price target used by Commercial fit |
    | Application | Component type used for partner-fit scoring |
    | Conventional route | Casting, forging, machining from billet, weld fabrication |
    | Delivery driver | Normal procurement, expedite, or line-down / launch critical |
    | Qualification level | Prototype, Industrial, or Aerospace / safety critical |
    | Material strategy | Single material, wear-facing / gradient, or repair overlay |
    | Quote profile | Startup, Service Bureau, or Enterprise Pilot rate presets |
    | Machine $/h, Labor $/h (Advanced) | Hourly rates in the quote |
    | Setup min, Postprocess min/part (Advanced) | Labor minutes per batch and per part |
    | Scrap allowance (%), Margin (%) (Advanced) | Multipliers applied to the cost stack |
    | Max machine time (h) (Advanced) | Lead-time guardrail for Commercial fit |
    | Finish tolerance, Annual demand (Advanced) | Intake inputs for partner fit |
    | NDT required, Redesign required (Advanced) | Qualification burden flags |
    """,
    icon=":material/payments:",
)

reference(
    "Metal / DED process (Metal mode only)",
    "Neutral wire-arc DED assumptions. Appears when Process is Metal (LPBF/DED).",
    """
    | Control | What it does |
    |---|---|
    | Process preset | Generic large-format wire DED, High-deposition steel build, or Fine-bead repair / cladding |
    | Envelope X / Y / Z (mm) | Build-cell working volume for envelope-fit checks |
    | Wire diameter (mm) | Feedstock wire size |
    | Wire feed (m/min) | Wire feed rate; drives deposited mass flow |
    | Arc current / voltage (Advanced) | Sets arc power and heat input |
    | Arc / deposition efficiency (%) (Advanced) | Energy and mass yield |
    | Robot utilization (%) (Advanced) | Duty cycle for throughput |
    | Machining allowance (%) (Advanced) | Near-net stock removed after deposition |
    | Billet buy-to-fly (Advanced) | Conventional waste baseline for material savings |
    | Conventional lead time (weeks) (Advanced) | Baseline for lead-time compression |
    | Machine hours / week (Advanced) | Capacity for scheduling |
    | Preheat, interpass, cooling rate, heat retention (Advanced) | Thermal / interpass dwell model |
    | Robot reach, positioner payload, fixture mass, torch clearance (Advanced) | Robot-cell feasibility |
    | Robot program point limit (Advanced) | Program-size guardrail |
    """,
    icon=":material/bolt:",
)

st.divider()

# ---------------------------------------------------------------------------
# View modes
# ---------------------------------------------------------------------------
st.header("View modes (Design tab)", anchor="view-modes")
st.markdown(
    "The **View** pills above the preview change how the active layer is drawn. They are "
    "display-only and never change the underlying toolpath."
)
st.markdown(
    """
    | View | Shows | Use it to |
    |---|---|---|
    | Toolpath | Walls and infill, with optional travel | Default read of the layer |
    | Extrusion | Paths drawn at nozzle / bead width | Preview real coverage and gaps |
    | Perimeters only | Walls only, infill hidden | Inspect shell count and seams |
    | Infill only | Infill only, walls hidden | Inspect the fill pattern alone |
    | Travel only | Non-printing moves | Spot travel waste and ordering jumps |
    | Speed map | Paths colored by speed | See where walls slow the print |
    | Time map | Paths colored by cumulative time | See where build time accumulates |
    | Density | Heat-style path concentration | Find over- or under-filled zones |
    """
)
st.markdown(
    """
    <div class="guide-note">
    The <strong>Auto-fit axes</strong> toggle re-frames the chart on every change. Turn it
    off to keep one zoom level while you flip between views during a demo.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Formula Lab
# ---------------------------------------------------------------------------
st.header("Formula Lab", anchor="formula-lab")
st.caption("Use these calculators to predict what a setting change will do before you touch the planner.")

calc1, calc2, calc3, calc4 = st.columns(4)
nozzle = calc1.number_input("Nozzle diameter (mm)", min_value=0.1, value=0.4, step=0.05)
layer_height = calc2.number_input("Layer height (mm)", min_value=0.05, value=0.2, step=0.01)
density = calc3.slider("Target density (%)", min_value=5, max_value=100, value=25, step=5)
path_length = calc4.number_input("Path length on layer (mm)", min_value=0.0, value=1000.0, step=50.0)

spacing_from_density = nozzle * 100.0 / density
extrusion_area = (3.141592653589793 / 4.0) * nozzle * layer_height
volume = path_length * extrusion_area
pla_weight = volume / 1000.0 * 1.24

metric_cols = st.columns(4)
metric_cols[0].metric("Spacing from density", format_mm(spacing_from_density))
metric_cols[1].metric("Extrusion area", f"{extrusion_area:.3f} mm^2")
metric_cols[2].metric("Layer volume", f"{volume:.1f} mm^3")
metric_cols[3].metric("PLA weight/layer", f"{pla_weight:.3f} g")

st.markdown(
    """
    <div class="guide-callout">
    Density mode is derived from nozzle width: spacing = nozzle diameter x 100 / density.
    For example, a 0.4 mm nozzle at 25% density gives about 1.60 mm spacing. Material uses
    an elliptical bead cross-section: area = (pi / 4) x nozzle x layer height, so a flat
    rectangular guess overestimates weight by about 21%.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Metrics and scores
# ---------------------------------------------------------------------------
st.header("Metrics and scores", anchor="metrics-scores")
st.markdown("**Layer and build metrics**")
st.markdown(
    """
    | Metric | Meaning | How it is computed |
    |---|---|---|
    | Path length | Printed motion on the active layer | Sum of perimeter and infill segment lengths |
    | Segments | Path segments on the active layer | Count of generated segments |
    | Layer time | Motion time for one layer | Trapezoidal velocity profile with acceleration and slower perimeters |
    | Full build | Time for the whole part | Layer time x layer count (model height / layer height) |
    | Material | Deposited weight | (pi / 4) x path x layer height x nozzle x density, summed over layers |
    | Path efficiency | Share of motion that prints | printed / (printed + travel) |
    | Travel share | Share of motion that is travel | travel / total motion |
    | Volumetric flow | Demand on the hotend | speed x layer height x nozzle |
    """
)

st.markdown("**Executive scores**")
st.markdown(
    """
    | Score | Range | How it is computed |
    |---|---|---|
    | Readiness | 0-100 | 100 minus penalties: blocker 35, warning 12, info 4 (status bands in Readiness checks below) |
    | Program risk | Low / Med / High / Blocked | High if flow > 14; Medium if 2+ warnings or build > 12 h; else Low |
    | Commercial fit | Fit / Review / No-bid | Unit quote vs target price and batch hours vs lead-time limit |
    | Launch score | 0-100 | Readiness - risk (Med 10, High 24, Blocked 45) - commercial (Review 10, No-bid 30) |
    | Quality scorecard | Category bands | Composite of readiness, economics, commercial fit, and motion metrics |
    """
)

st.markdown(
    """
    <div class="guide-note">
    The quote is transparent: unit quote =
    (((material + machine time + postprocess labor) x batch quantity + setup labor)
    x scrap allowance x margin) / batch quantity. Setup labor is amortized across the batch;
    material, machine time, and postprocess labor are per-part. Use
    <strong>Quote Sensitivity</strong> in the Release tab to sweep margin, machine rate,
    scrap allowance, or batch quantity and watch the unit price respond.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Readiness checks
# ---------------------------------------------------------------------------
st.header("Readiness checks (Advisor)", anchor="readiness-checks")
st.markdown(
    "The Advisor in the Release tab runs these checks every time you change a control. "
    "Blockers must be cleared before production G-code export is allowed."
)
st.markdown(
    """
    | Finding | Severity | Triggers when | Fix |
    |---|---|---|---|
    | Build plate overflow | Blocker | Geometry extends outside the plate | Center, scale down, or fit inside plate |
    | No perimeter paths | Blocker | No closed wall paths were produced | Enlarge the part or reduce perimeter spacing |
    | No infill paths | Warning | Layer would be walls only | Lower spacing, raise density, or reduce clearance |
    | Tall layer height | Warning | Layer height > 80% of nozzle | Use a layer height at or below 80% of nozzle |
    | High volumetric flow | Warning | FDM flow > 14 mm3/s | Reduce speed, layer height, or nozzle width |
    | Elevated volumetric flow | Info | FDM flow > 10 mm3/s | Confirm the hotend can sustain the flow |
    | Sparse infill | Warning | Spacing > 12x nozzle | Use density mode or reduce spacing |
    | Wide wall spacing | Info | Perimeter spacing > 1.5x nozzle | Keep wall spacing near extrusion width |
    | High travel share | Warning | Travel > 35% of motion | Try Zigzag or Concentric and keep optimization on |
    | Moderate travel share | Info | Travel > 22% of motion | Compare alternate patterns before exporting |
    | Heavy toolpath | Warning | More than 10,000 segments | Increase simplification or spacing |
    | Dense preview | Info | More than 5,000 segments | Use the segment ledger and simplification |
    | Long layer stack | Warning | More than 1,200 layers | Review layer height and model height |
    | Tall FDM build | Info | FDM model height > 220 mm | Confirm Z capacity and clearance |
    | 2D metal preview | Info | Metal mode without an STL | Import an STL to review real cross-sections |
    | Parametric sample shape | Info | No SVG or STL imported | Import customer geometry for a real package |
    """
)

st.divider()

# ---------------------------------------------------------------------------
# Diagnosis matrix
# ---------------------------------------------------------------------------
st.header("Diagnosis matrix", anchor="diagnosis")

diagnosis = [
    (
        "No infill lines",
        "Spacing too large, wall clearance too high, or shape too small.",
        "Lower spacing, increase density, reduce wall clearance, or test with a bigger rectangle.",
        "Design preview, Release Advisor",
    ),
    (
        "Many tiny segments",
        "Complex imported outline, sharp corners, or dense pattern intersection.",
        "Try Simplify tol. 0.02-0.10 mm, raise min segment length, or simplify the SVG/STL source.",
        "Release Segment Ledger, Plan Metrics",
    ),
    (
        "High travel share",
        "Disconnected paths or inefficient ordering.",
        "Turn on Optimize infill order, allow line reversal, compare Zigzag or Concentric.",
        "Design Travel view, Plan Metrics",
    ),
    (
        "Production export disabled",
        "Blocked readiness, non-FDM process, layer limit, out-of-bounds motion, or invalid E/mm.",
        "Open Advisor, center on plate, choose FDM, verify machine profile and export settings.",
        "Release Advisor + Export",
    ),
    (
        "Full build estimate looks wrong",
        "Model height or layer height does not match the intended part.",
        "Set Model height and Layer height before reading full build time, material, or cost.",
        "Sidebar Print settings, Plan Metrics",
    ),
    (
        "STL slice fails",
        "Selected Z misses the mesh or produces no closed loop.",
        "Move Slice at Z into the solid region; avoid top/bottom tangent slices for first tests.",
        "Sidebar Import, Design 3D view",
    ),
]

st.markdown("| Symptom | Likely cause | Fix | Check here |")
st.markdown("|---|---|---|---|")
for symptom, cause, fix, where in diagnosis:
    st.markdown(f"| **{symptom}** | {cause} | {fix} | {where} |")

st.divider()

# ---------------------------------------------------------------------------
# Parameter playbooks
# ---------------------------------------------------------------------------
st.header("Parameter playbooks", anchor="parameter-playbooks")

playbook_tabs = st.tabs(["Infill", "Perimeters", "Motion", "Imports", "Exports"])

with playbook_tabs[0]:
    st.markdown(
        """
        **Infill controls strength, time, and readability.**

        | Change | Expected metric shift | Visual signature |
        |---|---|---|
        | Lower spacing | Higher path length, material, and segment count | Denser internal lines |
        | Higher density | Same as lower spacing | More filled interior |
        | Alternate angle | Similar single-layer metrics | Different direction on odd/even layers |
        | Wall clearance up | Less infill near walls | Gap between shell and fill |
        | Infill overlap up | More bonding into walls | Fill touches or crosses perimeter area |

        For fair comparisons, hold shape, spacing, perimeters, and angle constant.
        Change only the pattern in the **Plan** tab comparison. To see all six
        patterns at once, open the **all-pattern preview matrix** in the Plan tab.
        """
    )

with playbook_tabs[1]:
    st.markdown(
        """
        **Perimeters are the shell budget.**

        | Goal | Starting point |
        |---|---|
        | Quick demo | 1 perimeter |
        | Normal FDM part | 2-3 perimeters |
        | Stronger shell | 4-5 perimeters |
        | Surface quality review | Slower perimeter speed multiplier |

        If perimeters collapse or disappear, the shape is too small for the count
        and spacing. Reduce count, reduce spacing, or enlarge the shape.
        """
    )

with playbook_tabs[2]:
    st.markdown(
        """
        **Motion tuning is about travel versus print distance.**

        | Control | Use when |
        |---|---|
        | Optimize infill order | Travel share is high |
        | Allow line reversal | Adjacent lines start/end on opposite sides |
        | Optimize perimeter order | Multiple disconnected loops appear |
        | Simplify tol. | Imported geometry creates noisy micro-segments |
        | Min seg. len | Tiny segments clutter the segment ledger and preview |

        Watch the **Travel** and **Speed map** views (Design tab) and **Metrics** (Plan tab) after each change.
        """
    )

with playbook_tabs[3]:
    st.markdown(
        """
        **SVG and STL import are different workflows.**

        | Import | Best use | Watch for |
        |---|---|---|
        | SVG | Clean logos, outlines, flat parts | Open paths, tiny details, multiple shapes |
        | STL | Cross-section studies | Z height, units, noisy or non-manifold meshes |

        STL files are unitless here. Use **STL target width** to map the mesh into
        millimeters, then pick a Z slice through the meaningful part of the solid.
        """
    )

with playbook_tabs[4]:
    st.markdown(
        """
        **Export is split into review output and guarded machine output.**

        | Export | Use it for | Machine-ready? |
        |---|---|---|
        | CSV | Spreadsheet or path audit | No |
        | SVG | Vector review | No |
        | JSON | Reproducible parameters and segments | No |
        | Report | Human summary | No |
        | Markdown / HTML dossier | Sign-off package | No |
        | Preview G-code | Learning G-code motion | No |
        | Production G-code | Guarded FDM profile export | Review before use |

        Production G-code can still be wrong for a real printer if temperatures,
        firmware assumptions, filament, bed prep, or start/end routines do not match.
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Metal / DED workflow
# ---------------------------------------------------------------------------
st.header("Metal / DED workflow", anchor="metal-ded")
st.markdown(
    "Set Process to **Metal (LPBF/DED)** in Quick Setup to unlock the metal review. The "
    "sidebar adds a Metal / DED process section, and the Release tab adds process, partner "
    "fit, and production handoff panels. This is a neutral feasibility screen, not a "
    "calibrated process recipe."
)

ded_cols = st.columns(3)
with ded_cols[0]:
    st.markdown(
        """
        **Process model**

        - Wire mass flow from wire size and feed
        - Deposited kg/h from deposition efficiency
        - Heat input from arc voltage, current, speed
        - Energy per kg and envelope utilization
        - Material saved vs billet buy-to-fly
        """
    )
with ded_cols[1]:
    st.markdown(
        """
        **Partner fit**

        - Lead-time compression vs conventional route
        - Material reduction and annual demand
        - Qualification burden and tolerances
        - DfAM suitability and redesign effort
        - Fit verdict with expected deliverables
        """
    )
with ded_cols[2]:
    st.markdown(
        """
        **Production handoff**

        - Thermal / interpass dwell planning
        - Robot reach, payload, fixture, clearance
        - Program-size feasibility
        - Coupons, inspections, traceability records
        - Qualification evidence checklist
        """
    )

st.markdown(
    """
    <div class="guide-callout">
    For a first metal review, import an STL so cross-sections reflect the real Z range,
    keep spacing generous, and export CSV / JSON / dossier rather than FDM production
    G-code (production G-code is FDM-only by design).
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------
st.header("Experiments that teach something", anchor="experiments")

experiments = [
    (
        "Pattern efficiency shootout",
        "Rectangle 80 x 50 mm, 3 perimeters, 3 mm spacing. Compare Parallel, Zigzag, Grid, "
        "Honeycomb, and Concentric. Record path efficiency and travel share.",
        "Which pattern gives the least travel for the same spacing?",
    ),
    (
        "Shell versus fill budget",
        "Keep spacing fixed at 3 mm. Sweep perimeters from 1 to 5. "
        "Watch path length, material, and density near the wall.",
        "At what point do perimeters dominate the layer?",
    ),
    (
        "Clearance failure test",
        "Use a 20 mm circle. Raise wall clearance in Advanced mode until infill disappears.",
        "How much interior width does your fill pattern actually need?",
    ),
    (
        "Import cleanup test",
        "Load a detailed SVG or STL slice. Compare the segment ledger and preview before and after simplification.",
        "Can you reduce segment noise without changing the visible outline?",
    ),
    (
        "Production readiness drill",
        "Move a centered shape partly outside the build plate, then use Advisor to recover a valid export state.",
        "Which checks are blockers versus warnings?",
    ),
]

for title, setup, question in experiments:
    expander(
        title,
        f"""
        **Setup:** {setup}

        **Question to answer:** {question}

        **Where to look:** Design preview, Plan comparison and metrics, Release advisor and segment ledger.
        """,
    )

st.divider()

# ---------------------------------------------------------------------------
# Data columns
# ---------------------------------------------------------------------------
st.header("Data columns", anchor="data-columns")
st.markdown(
    """
    The **Segment Ledger** (Release tab) and CSV export share a stable schema.

    | Column | Meaning | How to use it |
    |---|---|---|
    | segment_id | 1-based row id | Reference a row in a review |
    | path_type | boundary, perimeter, or infill | Filter shell versus fill |
    | order_index | Execution order | Find path-order jumps |
    | x_start, y_start | Segment start coordinate | Locate travel starts |
    | x_end, y_end | Segment end coordinate | Locate travel ends |
    | length_mm | Segment length | Sort for tiny or huge paths |
    | layer | Layer number | Audit multi-layer exports |
    """
)

st.divider()

# ---------------------------------------------------------------------------
# Pre-export audit
# ---------------------------------------------------------------------------
st.header("Pre-export audit", anchor="pre-export-audit")

audit_items = [
    "Advisor is not Blocked.",
    "Shape fits inside the active build plate.",
    "Model height and layer height are correct.",
    "Nozzle diameter matches the intended process assumption.",
    "Path efficiency is acceptable for the shape and pattern.",
    "Segment Ledger (Release tab) does not show suspicious zero-length or tiny segment clutter.",
    "Production G-code is used only for FDM and only after machine-specific review.",
]

for item in audit_items:
    st.checkbox(item, value=False)

st.warning(
    "MiniSlicer is still a planning and education tool. "
    "Treat every export as something to inspect, not something to blindly run."
)

st.divider()

# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------
st.header("Glossary", anchor="glossary")

glossary = {
    "Boundary": "The original outline of the selected or imported shape.",
    "Perimeter": "An inward shell path. Real slicers often call these walls or shells.",
    "Infill": "The internal path pattern that fills the cross-section.",
    "Travel move": "A non-printing move between print paths.",
    "Path efficiency": "Printed distance divided by total motion distance. Higher means less travel waste.",
    "Travel share": "Travel distance divided by total motion. Lower is better.",
    "Layer height": "Vertical thickness used for material and full-build estimates.",
    "Nozzle diameter": "The assumed extrusion width used for density and volume calculations.",
    "Wall clearance": "How far infill is pulled away from perimeters before overlap is applied.",
    "Volumetric flow": "Speed x layer height x nozzle width; the demand placed on the hotend.",
    "Seam": "Start/end location for a closed perimeter loop.",
    "Z-hop": "Temporary Z lift before travel moves in exported G-code.",
    "Readiness": "Automated score based on fit, paths, material, and motion checks.",
    "Launch score": "Readiness adjusted down for program risk and commercial fit.",
    "Commercial fit": "Whether the unit quote and batch hours meet the target price and lead time.",
    "Program risk": "Buyer-facing risk label from readiness, flow, and build hours.",
    "Quality scorecard": "Composite category view of technical and commercial health.",
    "Quote profile": "A preset bundle of machine rate, labor rate, scrap, and margin.",
    "Buy-to-fly": "Ratio of starting billet mass to finished part mass for conventional routes.",
    "Interpass temperature": "Temperature limit between metal deposition passes.",
    "Deposition rate": "Deposited mass per hour in the DED process model.",
    "Production export": "Guarded FDM G-code path with machine profile checks. It still requires human review.",
}

g1, g2 = st.columns(2)
items = list(glossary.items())
for term, definition in items[: len(items) // 2]:
    g1.markdown(f"**{term}**")
    g1.caption(definition)
for term, definition in items[len(items) // 2 :]:
    g2.markdown(f"**{term}**")
    g2.caption(definition)

st.divider()

# ---------------------------------------------------------------------------
# Presenter notes
# ---------------------------------------------------------------------------
st.header("Presenter notes", anchor="presenter-notes")
st.markdown(
    """
    A tight, repeatable demo flow for a stakeholder review:

    1. **Frame it** in one line: "planning, quoting, and readiness for additive parts,
       with traceable exports."
    2. **Quick Setup:** Balanced profile, 220 x 220 plate, Basic controls, FDM. Keep the
       sidebar tidy by staying in Basic.
    3. **Design:** load or pick a part, then flip the View pills - Toolpath, Travel only,
       Speed map, Density - narrating what each reveals.
    4. **Plan:** show the pattern ranking and the head-to-head A/B comparison; point at the
       decision metrics (fewest moves, lowest travel, best efficiency).
    5. **Release:** read the launch score and Release Gates, walk the Advisor findings, then
       show the quote and export a dossier.
    6. **Metal angle (optional):** switch Process to Metal to show the DED process model,
       partner fit, and production handoff.
    """
)
st.markdown(
    """
    <div class="guide-note">
    Be honest about scope: MiniSlicer is a planning and visualization tool, not a certified
    production slicer. Preview G-code is educational; production G-code is FDM-only and
    guarded by readiness checks and machine bounds, and still needs machine validation.
    Stating the limits up front builds more trust than overclaiming.
    </div>
    """,
    unsafe_allow_html=True,
)

st.success(
    "Use this page like a lab notebook: pick a goal, run one experiment, record the metrics, then change one control."
)
