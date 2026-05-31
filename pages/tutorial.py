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
        div[data-testid="stExpander"] { border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def expander(title: str, body: str, *, expanded: bool = False) -> None:
    with st.expander(title, expanded=expanded):
        st.markdown(body)


def format_mm(value: float) -> str:
    return f"{value:.2f} mm"


tutorial_css()

st.markdown(
    """
    <div class="guide-hero">
        <h1>MiniSlicer Advanced Operating Guide</h1>
        <p>
            Use this as a tuning manual: choose a goal, change the right controls,
            inspect the right tab, and understand what each warning or metric means.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Open the MiniSlicer planner from the sidebar. Keep this page open as a decision guide while you tune settings."
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

st.header("Goal-Based Recipes", anchor="goal-recipes")
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
            "Preview mode: Toolpath, then Animation",
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
        "watch": "Material, full build time, and Density view for over-concentrated zones.",
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
            "Use Compare to test Zigzag vs Parallel Lines",
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
            "Preview mode: Travel only, then Metrics",
        ],
        "watch": "Travel share, path efficiency, and optimization results in Metrics.",
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
            "Process: DED / Metal",
            "Use a metal material profile",
            "Prefer larger spacing and simpler paths for first inspection",
            "Use Speed map and Time map to inspect motion assumptions",
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

st.header("Formula Lab", anchor="formula-lab")
st.caption("Use these calculators to predict what a setting change will do before you touch the planner.")

calc1, calc2, calc3, calc4 = st.columns(4)
nozzle = calc1.number_input("Nozzle diameter (mm)", min_value=0.1, value=0.4, step=0.05)
layer_height = calc2.number_input("Layer height (mm)", min_value=0.05, value=0.2, step=0.01)
density = calc3.slider("Target density (%)", min_value=5, max_value=100, value=25, step=5)
path_length = calc4.number_input("Path length on layer (mm)", min_value=0.0, value=1000.0, step=50.0)

spacing_from_density = nozzle * 100.0 / density
extrusion_area = nozzle * layer_height
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
    For example, a 0.4 mm nozzle at 25% density gives about 1.60 mm spacing.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

st.header("Diagnosis Matrix", anchor="diagnosis")

diagnosis = [
    (
        "No infill lines",
        "Spacing too large, wall clearance too high, or shape too small.",
        "Lower spacing, increase density, reduce wall clearance, or test with a bigger rectangle.",
        "Preview, Advisor",
    ),
    (
        "Many tiny segments",
        "Complex imported outline, sharp corners, or dense pattern intersection.",
        "Try Simplify tol. 0.02-0.10 mm, raise min segment length, or simplify the SVG/STL source.",
        "Data, Metrics",
    ),
    (
        "High travel share",
        "Disconnected paths or inefficient ordering.",
        "Turn on Optimize infill order, allow line reversal, compare Zigzag or Concentric.",
        "Travel only, Metrics",
    ),
    (
        "Production export disabled",
        "Blocked readiness, non-FDM process, layer limit, out-of-bounds motion, or invalid E/mm.",
        "Open Advisor, center on plate, choose FDM, verify machine profile and export settings.",
        "Advisor, Export",
    ),
    (
        "Full build estimate looks wrong",
        "Model height or layer height does not match the intended part.",
        "Set Model height and Layer height before reading full build time, material, or cost.",
        "Print Settings, Metrics",
    ),
    (
        "STL slice fails",
        "Selected Z misses the mesh or produces no closed loop.",
        "Move Slice at Z into the solid region; avoid top/bottom tangent slices for first tests.",
        "Import, 3D",
    ),
]

st.markdown("| Symptom | Likely cause | Fix | Check here |")
st.markdown("|---|---|---|---|")
for symptom, cause, fix, where in diagnosis:
    st.markdown(f"| **{symptom}** | {cause} | {fix} | {where} |")

st.divider()

st.header("Parameter Playbooks", anchor="parameter-playbooks")

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
        Change only the pattern in **Compare**.
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
        | Min seg. len | Tiny segments clutter Data and Preview |

        Watch **Travel only**, **Speed map**, and **Metrics** after each change.
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
        | Preview G-code | Learning G-code motion | No |
        | Production G-code | Guarded FDM profile export | Review before use |

        Production G-code can still be wrong for a real printer if temperatures,
        firmware assumptions, filament, bed prep, or start/end routines do not match.
        """
    )

st.divider()

st.header("Experiments That Teach Something", anchor="experiments")

experiments = [
    (
        "Pattern efficiency shootout",
        "Rectangle 80 x 50 mm, 3 perimeters, 3 mm spacing. Compare Parallel, Zigzag, Grid, Honeycomb, and Concentric. Record path efficiency and travel share.",
        "Which pattern gives the least travel for the same spacing?",
    ),
    (
        "Shell versus fill budget",
        "Keep spacing fixed at 3 mm. Sweep perimeters from 1 to 5. Watch path length, material, and density near the wall.",
        "At what point do perimeters dominate the layer?",
    ),
    (
        "Clearance failure test",
        "Use a 20 mm circle. Raise wall clearance in Advanced mode until infill disappears.",
        "How much interior width does your fill pattern actually need?",
    ),
    (
        "Import cleanup test",
        "Load a detailed SVG or STL slice. Compare Data and Preview before and after small simplification.",
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

        **Tabs to use:** Preview, Compare, Metrics, Advisor, Data.
        """,
    )

st.divider()

st.header("Data Columns", anchor="data-columns")
st.markdown(
    """
    The **Data** tab and CSV export share a stable schema.

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

st.header("Pre-Export Audit", anchor="pre-export-audit")

audit_items = [
    "Advisor is not Blocked.",
    "Shape fits inside the active build plate.",
    "Model height and layer height are correct.",
    "Nozzle diameter matches the intended process assumption.",
    "Path efficiency is acceptable for the shape and pattern.",
    "Data tab does not show suspicious zero-length or tiny segment clutter.",
    "Production G-code is used only for FDM and only after machine-specific review.",
]

for item in audit_items:
    st.checkbox(item, value=False)

st.warning(
    "MiniSlicer is still a planning and education tool. Treat every export as something to inspect, not something to blindly run."
)

st.divider()

st.header("Glossary", anchor="glossary")

glossary = {
    "Boundary": "The original outline of the selected or imported shape.",
    "Perimeter": "An inward shell path. Real slicers often call these walls or shells.",
    "Infill": "The internal path pattern that fills the cross-section.",
    "Travel move": "A non-printing move between print paths.",
    "Path efficiency": "Printed distance divided by total motion distance. Higher means less travel waste.",
    "Layer height": "Vertical thickness used for material and full-build estimates.",
    "Nozzle diameter": "The assumed extrusion width used for density and volume calculations.",
    "Wall clearance": "How far infill is pulled away from perimeters before overlap is applied.",
    "Seam": "Start/end location for a closed perimeter loop.",
    "Z-hop": "Temporary Z lift before travel moves in exported G-code.",
    "Readiness": "The app's automated score based on fit, paths, material, and motion checks.",
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

st.success(
    "Use this page like a lab notebook: pick a goal, run one experiment, record the metrics, then change one control."
)
