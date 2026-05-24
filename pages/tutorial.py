"""Interactive tutorial page for MiniSlicer."""

import streamlit as st

st.set_page_config(
    page_title="MiniSlicer — Tutorial",
    layout="wide",
    page_icon="📖",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📖 MiniSlicer — Complete Tutorial")
st.caption(
    "Everything you need to go from zero to a fully understood toolpath plan. "
    "Read top-to-bottom for the first time, or jump to any section."
)

st.info(
    "**New here?** Start at Step 1 and follow along in the main app "
    "(open it from the sidebar). Each step is short and takes about 1–2 minutes.",
    icon="👋",
)

# ── Table of contents ─────────────────────────────────────────────────────────
with st.expander("Table of Contents", expanded=False):
    st.markdown("""
1. [What is MiniSlicer?](#what-is-minislicer)
2. [Quick Start in 7 steps](#quick-start-in-5-steps)
3. [The Sidebar — your control panel](#the-sidebar-your-control-panel)
   - Shape
   - Perimeters
   - Infill
   - Process
   - Material
   - Display
   - Path Planning
   - Quality
   - Transform
   - Motion / Export
4. [Infill Patterns — deep dive](#infill-patterns-deep-dive)
5. [The Tabs — what each one does](#the-tabs-what-each-one-does)
   - Visualization
   - Compare
   - Animation
   - 3D View
   - Metrics
   - Advisor
   - Segment Data
   - Export
6. [Quick Profiles](#quick-profiles)
7. [Importing & Exporting Configs](#importing-exporting-configs)
8. [Tips, Tricks & Common Mistakes](#tips-tricks-common-mistakes)
9. [Glossary](#glossary)
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — What is MiniSlicer
# ═══════════════════════════════════════════════════════════════════════════════
st.header("1 · What is MiniSlicer?", anchor="what-is-minislicer")

col_left, col_right = st.columns([3, 2])
with col_left:
    st.markdown("""
MiniSlicer is an **interactive 2D toolpath visualizer** for additive manufacturing.
It lets you experiment with how a 3D printer — FDM plastic or DED metal — plans
the movement of its nozzle to build up a single cross-section layer.

**What it IS:**
- An educational planning and visualization tool
- A way to upload SVG outlines or STL meshes and turn one slice into a 2D toolpath
- A fast way to compare infill patterns, perimeter counts, and spacing
- A metrics calculator for path length, travel distance, print time, and material use
- An exporter for CSV, G-code (educational), SVG, and JSON

**What it is NOT:**
- A production slicer (STL slicing is simplified, and there is no support generation)
- Machine-ready output — never send the G-code directly to a printer
""")
with col_right:
    st.markdown("""
```
A typical toolpath plan:

┌─────────────────────────┐
│  Outline (boundary)     │
│  ┌───────────────────┐  │
│  │  Perimeter 1      │  │
│  │  ┌─────────────┐  │  │
│  │  │ Infill ///  │  │  │
│  │  │ lines  ///  │  │  │
│  │  └─────────────┘  │  │
│  └───────────────────┘  │
└─────────────────────────┘
```
""")
    st.caption("The nozzle traces the outer outline, then perimeter rings, then infill lines to fill the interior.")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Quick Start
# ═══════════════════════════════════════════════════════════════════════════════
st.header("2 · Quick Start in 7 Steps", anchor="quick-start-in-5-steps")

st.markdown("Open the **main app** from the sidebar, then follow these steps:")

steps = [
    (
        "Use Basic mode first",
        "At the top of the main app, leave **Controls** set to **Basic** while learning. "
        "Switch to **Advanced** when you want placement, preview, and quality controls.",
    ),
    (
        "Pick a shape",
        "In the sidebar under **Shape**, choose **Rectangle** (it's the simplest). "
        "Leave the width at 40 mm and height at 25 mm. The visualization updates instantly.",
    ),
    (
        "Choose an infill pattern",
        "Under **Infill**, change the pattern to **Zigzag**. "
        "Watch the diagonal lines in the Visualization tab flip direction alternately — "
        "that's what zigzag does to cut travel time.",
    ),
    (
        "Adjust infill spacing",
        "Set **Infill spacing** to **2.0 mm** for dense fill, then try **6.0 mm** for sparse fill. "
        "Notice how the Metrics tab updates the path length and estimated print time.",
    ),
    (
        "Try a quick profile",
        "Open the **Quick Profiles** expander at the top of the page and select **Balanced**. "
        "This sets a sensible layer height, speed, and perimeter count all at once.",
    ),
    (
        "Try STL slicing",
        "Open **Import**, upload an `.stl`, then move the **STL slice Z** slider. "
        "MiniSlicer extracts that horizontal cross-section and generates perimeters and infill from it.",
    ),
    (
        "Read the Metrics",
        "Click the **Metrics** tab. You'll see path length, travel distance, efficiency, "
        "and a visual pie chart of how the print time is split. "
        "Try the **Advisor** tab to check whether your settings look coherent.",
    ),
]

for idx, (title, body) in enumerate(steps, 1):
    with st.expander(f"Step {idx} — {title}", expanded=idx == 1):
        st.markdown(body)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Sidebar
# ═══════════════════════════════════════════════════════════════════════════════
st.header("3 · The Sidebar — your control panel", anchor="the-sidebar-your-control-panel")

st.markdown(
    "The sidebar is always visible on the left. Every control there "
    "immediately regenerates the toolpath and updates all tabs."
)

st.info(
    "**Basic vs Advanced:** Basic mode keeps the common workflow visible. "
    "Advanced mode opens placement, preview, and quality controls for deeper experiments.",
    icon=":material/tune:",
)

# ── Shape ─────────────────────────────────────────────────────────────────────
st.subheader("Shape")

shape_cols = st.columns(2)
with shape_cols[0]:
    st.markdown("""
**Built-in shapes:**
| Shape | Parameters |
|---|---|
| Rectangle | Width, Height |
| Rounded Rectangle | Width, Height, Corner radius |
| Circle | Radius |
| **Ellipse** | Width, Height |
| Triangle | Base, Height |
| Regular Polygon | Outer radius, Number of sides (3–16) |
| Star | Outer radius, Inner radius, Points |
| **Cross** | Overall size, Arm width |
| **Capsule** | Width, Height (semicircles on longer side) |
| **Arrow** | Length, Head width, Shaft width |
| Custom Polygon | Comma/semicolon coordinate list |
""")
with shape_cols[1]:
    st.markdown("""
**SVG Import** (via expander at top of sidebar):

Upload any `.svg` file and MiniSlicer will extract the largest polygon from it.
Use the **Scale to width** field to set its printed size in mm.

Supported SVG elements: `polygon`, `polyline`, `rect`,
and simple `path` elements using M/L/Z commands.

**STL Import** (same Import expander):

Upload an `.stl` mesh, choose a target slice width, then move the
**STL slice Z** slider. MiniSlicer cuts a horizontal section through the mesh,
uses the largest closed loop, and generates perimeters/infill from that 2D slice.

STL files are unitless, so the **STL slice target width** field controls the
displayed/printed size in millimeters.

**Custom Polygon format:**
```
0,0; 50,0; 40,25; 10,35
```
At least 3 coordinate pairs, separated by semicolons.
Decimal points and negative values are allowed.
""")

# ── Perimeters ────────────────────────────────────────────────────────────────
st.subheader("Perimeters")
st.markdown("""
Perimeters are the **outer shell rings** of the cross-section. Real slicers call them
*walls* or *shells*. MiniSlicer generates them by repeatedly offsetting the shape boundary inward.

| Parameter | Effect |
|---|---|
| **Number of perimeters** | More rings = thicker shell, stronger part, longer print |
| **Perimeter spacing (mm)** | Distance between rings — typically match your nozzle diameter (0.4 mm) |
| **Perimeter speed (%)** | Perimeters print slower than infill for better surface quality. 80% is the typical default. Visible in the Speed Map preview mode. |

**Rule of thumb:** 2–3 perimeters for normal parts, 4–5 for mechanical strength.
Setting spacing significantly larger than your nozzle diameter leaves visible gaps.
""")

# ── Infill ────────────────────────────────────────────────────────────────────
st.subheader("Infill")
st.markdown("""
Infill fills the interior area with a repeating pattern of lines or cells.

| Parameter | What it does |
|---|---|
| **Infill pattern** | The geometric pattern of the fill (see Section 4 for a full breakdown) |
| **Infill control** | Switch between direct spacing (mm) or percentage density |
| **Infill spacing (mm)** | Gap between consecutive lines — smaller = denser = stronger |
| **Infill density (%)** | Derived from nozzle width; 100% = no gaps, 25% = typical |
| **Infill wall clearance (mm)** | Shrinks the fill region away from the perimeters to avoid overprinting |
| **Infill-perimeter overlap (mm)** | Grows the infill region back toward perimeters for better bonding. Reduces effective clearance. |
| **Infill angle (deg)** | Rotates the pattern; −90° to +90° |
| **Alternating angle** | Odd layers use +45°, even layers use −45° for cross-hatching across layers |

**Tip:** Enable alternating angle when using the 3D View tab — you'll see the
cross-layer pattern that gives FDM parts their isotropy.
""")

# ── Process ───────────────────────────────────────────────────────────────────
st.subheader("Process")
st.markdown("""
| Parameter | What it does |
|---|---|
| **Layer number** | Which layer to show; affects alternating angle |
| **Layer height (mm)** | Thickness of one deposited layer — affects volume and weight calculations |
| **Model height for estimate (mm)** | Total part height used to extrapolate single-layer metrics to a full part |
| **Print speed (mm/s)** | Nozzle movement speed during extrusion — used to estimate print time |

**Layer height guidance (FDM):**
- 0.10–0.15 mm — fine quality, slow
- 0.20 mm — standard balanced
- 0.28–0.32 mm — fast/draft
- Never exceed ~75% of your nozzle diameter
""")

# ── Material ──────────────────────────────────────────────────────────────────
st.subheader("Material")
st.markdown("""
| Parameter | What it does |
|---|---|
| **Material** | Sets density for weight calculations. FDM plastics and DED metals available |
| **Nozzle diameter (mm)** | Controls extrusion cross-section area for volume estimates |
| **Filament diameter (mm)** | 1.75 mm or 2.85 mm — affects back-calculated filament length |
| **Material cost ($/kg)** | Used to estimate cost of a full print in the Metrics / Advisor tabs |

**Available materials:**

*FDM Polymers:* PLA (1.24 g/cm³), PETG (1.27), ABS (1.04), TPU (1.21), ASA (1.07)

*DED Metals:* Steel 316L (7.99), Steel H13 (7.76), Titanium Ti-6Al-4V (4.43),
Inconel 625 (8.44), Aluminum AlSi10Mg (2.67), Copper CuCr1Zr (8.90)
""")

# ── Display ───────────────────────────────────────────────────────────────────
st.subheader("Display")
st.markdown("""
These only affect what you see — they never change the generated geometry.

| Option | Effect |
|---|---|
| **Color scheme** | Classic, Colorblind-safe, Dark (navy), **High Contrast** (bold, presentation-ready), **Neon** (bright on black — eye-catching) |
| **Line thickness** | Scale factor for rendering line width |
| **Show outline** | The raw shape boundary (thin grey line) |
| **Show perimeters** | The inward offset rings (green/teal) |
| **Show infill** | The fill lines (orange/yellow) |
| **Show travel moves** | Purple dashed lines for non-printing head moves |
| **Show seam markers** | Yellow diamond at the start point of each loop |
| **Show start/end points** | Green (start) and red (end) dots for each path |
| **Show direction arrows** | Small arrow markers at path midpoints showing which way the nozzle is moving |
| **Show dimension labels** | Annotates the bounding box with width and height in mm |
| **Show extrusion width** | Renders paths as thick filled bands to simulate bead width |
| **Show build plate** | Reference rectangle showing the print bed |
""")

# ── Path Planning ─────────────────────────────────────────────────────────────
st.subheader("Path Planning")
st.markdown("""
These toggle post-processing of the generated paths to reduce travel distance.

| Option | Effect |
|---|---|
| **Optimize perimeter order** | Reorders multiple perimeter loops to minimize hops between them |
| **Optimize infill order** | Nearest-neighbor sort — picks the closest next line to reduce travel |
| **Allow reversing infill lines** | If the end of a line is closer than its start, flip it |

**When to enable:** For dense infill or complex shapes, enabling both optimization options
and line reversal can cut travel distance by 30–50%.

**Trade-off:** Optimization runs an O(n²) nearest-neighbor search. For very dense
patterns (>200 lines), expect a fraction-of-a-second delay.
""")

# ── Quality ───────────────────────────────────────────────────────────────────
st.subheader("Quality")
st.markdown("""
| Parameter | Effect |
|---|---|
| **Geometry simplify tolerance (mm)** | Removes micro-wiggles from intersection math. Set 0.01–0.05 mm for clean lines without visible quality loss. 0 = disabled |
| **Minimum segment length (mm)** | Drops extremely short path segments that a real printer wouldn't execute cleanly |

**Tip:** Leave both at 0 unless your infill has odd short stubs or the segment count
is very high. Start with simplify = 0.01 and minimum length = 0.1 for cleaner exports.
""")

# ── Transform ─────────────────────────────────────────────────────────────────
st.subheader("Transform")
st.markdown("""
Transforms are applied in this order: scale → mirror → rotate → translate → fit/center.

| Option | Effect |
|---|---|
| **Scale shape (%)** | Shrink or grow the shape without changing the sidebar dimensions |
| **Mirror X / Mirror Y** | Flip the shape horizontally or vertically around its centroid |
| **Rotate shape (deg)** | Rotate −180° to +180° |
| **Translate X/Y (mm)** | Shift the shape on the build plate |
| **Center on build plate** | Moves the centroid to the center of the plate (requires build plate shown) |
| **Fit inside build plate** | Scales down only if shape is too large; never scales up |
| **Plate margin (mm)** | Clearance from the plate edge when fitting |
""")

# ── Motion / Export ───────────────────────────────────────────────────────────
st.subheader("Motion / Export")
st.markdown("""
| Parameter | Effect |
|---|---|
| **Travel speed (mm/s)** | Head movement speed when not extruding — used in motion time estimates |
| **Z-hop during travel (mm)** | Lifts Z before travel moves in G-code export (educational annotation only) |
| **Include E values in G-code** | Adds a cumulative extrusion value model to G1 commands |
| **Extrusion per mm (E/mm)** | Scale factor for E value calculation |
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Infill Patterns
# ═══════════════════════════════════════════════════════════════════════════════
st.header("4 · Infill Patterns — Deep Dive", anchor="infill-patterns-deep-dive")

st.markdown("Each pattern has different trade-offs in strength, print time, and travel distance.")

patterns = {
    "Parallel Lines": {
        "icon": "〰️",
        "description": "The simplest pattern. One family of parallel lines at a constant angle.",
        "visual": """
  ///////////
  ///////////
  ///////////
  ///////////
""",
        "strengths": "Fastest to generate and print. Minimal path complexity.",
        "weaknesses": "Anisotropic — strong in one direction only. High travel between lines if unoptimized.",
        "best_for": "Quick previews, very fast prints, or base layers.",
    },
    "Zigzag": {
        "icon": "⚡",
        "description": "Same lines as Parallel, but alternating direction: odd lines go left→right, even lines go right→left.",
        "visual": """
  →→→→→→→→→→
  ←←←←←←←←←
  →→→→→→→→→→
  ←←←←←←←←←
""",
        "strengths": "Cuts travel distance between lines. Same print time as Parallel but fewer travel moves.",
        "weaknesses": "Slight reversals at ends can create corner bulge artifacts on a real printer.",
        "best_for": "Default everyday infill. Upgrade from Parallel Lines with almost no cost.",
    },
    "Grid": {
        "icon": "▦",
        "description": "Two perpendicular families of parallel lines (angle and angle+90°). Creates a cross-hatch.",
        "visual": """
  ╪╪╪╪╪╪╪╪╪╪
  ╪╪╪╪╪╪╪╪╪╪
  ╪╪╪╪╪╪╪╪╪╪
""",
        "strengths": "Isotropic in the layer plane — equal strength in X and Y. Very common default.",
        "weaknesses": "~2× more lines than Parallel. Intersections may cause slight over-extrusion on real printers.",
        "best_for": "General purpose parts, functional components requiring balanced strength.",
    },
    "Triangles": {
        "icon": "△",
        "description": "Three families of lines at 0°, 60°, and 120°. Creates a triangulated mesh.",
        "visual": """
  /\\/\\/\\/\\
  \\/\\/\\/\\/
  /\\/\\/\\/\\
""",
        "strengths": "Excellent isotropy — equal strength in all planar directions. Good for structural parts.",
        "weaknesses": "~3× lines vs Parallel; longer print time. More complex travel pattern.",
        "best_for": "Structural parts, load-bearing surfaces where direction is unknown.",
    },
    "Honeycomb": {
        "icon": "⬡",
        "description": "Hexagonal cell walls. Each cell is a regular hexagon; lines form the shared walls.",
        "visual": """
   ___   ___
  /   \\ /   \\
  \\   / \\   /
   ---   ---
""",
        "strengths": "Excellent strength-to-weight ratio. Hexagons distribute load efficiently.",
        "weaknesses": "Most complex to generate. More travel hops between individual wall segments.",
        "best_for": "Lightweight structural parts, aerospace, anything where weight matters.",
    },
    "Concentric": {
        "icon": "◎",
        "description": "Rings that offset inward from the shape boundary, like topographic contours.",
        "visual": """
  ┌──────────┐
  │ ┌──────┐ │
  │ │ ┌──┐ │ │
  │ │ └──┘ │ │
  │ └──────┘ │
  └──────────┘
""",
        "strengths": "Follows the shape perfectly. Good surface finish. No sharp direction changes.",
        "weaknesses": "For non-circular shapes, inner rings get small quickly — low density near the center.",
        "best_for": "Round parts, aesthetic surfaces, vases, flexible/elastic parts (TPU).",
    },
}

for name, info in patterns.items():
    with st.expander(f"{info['icon']} {name}", expanded=False):
        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"**{info['description']}**")
            st.markdown(f"**Strengths:** {info['strengths']}")
            st.markdown(f"**Weaknesses:** {info['weaknesses']}")
            st.markdown(f"**Best for:** {info['best_for']}")
        with right:
            st.code(info["visual"], language=None)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Tabs
# ═══════════════════════════════════════════════════════════════════════════════
st.header("5 · The Tabs — what each one does", anchor="the-tabs-what-each-one-does")

tab_info = {
    "Visualization": {
        "icon": "🗺️",
        "summary": "The main canvas. Your toolpath rendered as an interactive Plotly chart.",
        "details": """
**Layer preview slider** — Scrub through layers up to 20 deep.
Infill angle alternates automatically when *Alternating angle* is enabled.

**Preview modes:**
| Mode | Shows |
|---|---|
| Toolpath | Everything visible in sidebar Display settings |
| Perimeters only | Only the shell rings |
| Infill only | Only the fill lines |
| Travel only | Only the non-printing head moves (purple dashes) |
| Extrusion width | Paths rendered as filled bands |
| Speed map | Color gradient: slower zones darker, faster zones brighter |
| Time map | Each segment colored by cumulative time |
| **Path Density** | 2D heatmap showing where material is most concentrated — hot zones = heavy coverage |

**Hover tips:** Hover over any line in the chart to see its exact coordinates,
length in mm, and estimated time to print.

**Metrics bar** below the chart shows a quick summary without needing to switch tabs.
""",
    },
    "Compare": {
        "icon": "⚖️",
        "summary": "Side-by-side comparison of two infill patterns with the same shape and spacing.",
        "details": """
1. Pick **Pattern A** (defaults to your current sidebar selection).
2. Pick **Pattern B** (defaults to Grid).
3. Click **Compare** — the app generates both patterns and renders them side by side.

Below the chart, a metric table shows:
- Number of infill lines
- Total infill length
- Estimated print time
- Travel between paths

Pattern B metrics show **delta** vs Pattern A (e.g., `+12.5 mm` or `−3 lines`)
so you can instantly see what you gain or lose.

**Tip:** Compare Zigzag vs Parallel to see how much travel is saved for free.
""",
    },
    "Animation": {
        "icon": "▶️",
        "summary": "Watch the nozzle trace every single segment in order.",
        "details": """
Press **▶ Play** inside the Plotly chart, or drag the frame slider manually.

Each frame adds one segment to the canvas — you can watch the nozzle build
the perimeter shells and then fill the interior.

Sub-sampled to a maximum of **120 frames** for performance.
Dense infill with 400+ segments will skip some to keep it responsive.

**Use this to:** understand the order segments are visited and spot
long travel moves between distant paths.
""",
    },
    "3D View": {
        "icon": "🧊",
        "summary": "Stack multiple layers into a 3D build-up visualization.",
        "details": """
Set how many layers to stack (1–20) then click **Generate 3D View**.

Each layer is offset upward by the layer height. Infill angle alternates ±45°
per layer automatically, showing the classic cross-hatching that FDM parts use.

The view is a 3D Plotly scatter plot — rotate, zoom, and pan with the mouse.

**Note:** This can be slow for large shapes with many infill lines across 20 layers.
Start with 5 layers and a simple shape to get a feel for it.
""",
    },
    "Metrics": {
        "icon": "📊",
        "summary": "Detailed numeric and visual breakdown of the toolpath statistics.",
        "details": """
**Geometry section:** Cross-section area, bounding box, segment count.

**Path Lengths section:** Total, perimeter, and infill lengths.

**Motion Efficiency section:** Travel length, total motion, path efficiency %.
*Path efficiency = printing moves / (printing + travel moves).*
Higher is better — 90%+ means very little wasted movement.

**Material Estimate section:** Volume deposited, filament consumed, weight.
Uses a rectangular extrusion cross-section model:
`volume = path_length × layer_height × nozzle_diameter`

**Full-Part Estimate section:** Extrapolates the single layer to a full part
using the *Model height* parameter. Shows total layers, time, weight, and cost.

**Visual Breakdown:** Pie chart of how path length is split between
perimeters / infill / travel. Bar chart of estimated time breakdown.

**Infill Line Length Distribution:** Histogram showing how uniform or varied
the individual infill line lengths are. Narrow histogram = uniform pattern.
""",
    },
    "Advisor": {
        "icon": "💡",
        "summary": "Automatic checks and recommendations based on your current settings.",
        "details": """
MiniSlicer checks several conditions and shows a plain-language tip for each problem found:

- Shape doesn't fit the build plate
- No infill generated (spacing too large or clearance too tight)
- High travel ratio (> 25% of motion is non-printing)
- Low path efficiency (< 80%)
- Layer height too large for nozzle diameter
- Missing material cost input
- Wall clearance too large

If everything looks fine, it says so. No false alarms.

**Quick Stats** at the bottom shows four summary numbers at a glance.
""",
    },
    "Segment Data": {
        "icon": "🗃️",
        "summary": "A sortable table of every segment in the toolpath.",
        "details": """
Columns:
| Column | Description |
|---|---|
| path_type | `perimeter` or `infill` |
| order_index | Execution order (0 = first) |
| x_start, y_start | Segment start coordinate (mm) |
| x_end, y_end | Segment end coordinate (mm) |
| length_mm | Euclidean length |
| layer | Layer number |

Click any column header to sort. Use this to audit path order,
spot unexpectedly short segments, or understand the data before exporting.
""",
    },
    "Export": {
        "icon": "💾",
        "summary": "Download your toolpath in five different formats.",
        "details": """
| Format | Use case |
|---|---|
| **PNG** | Static raster image of the toolpath (requires `kaleido`: `pip install kaleido`) |
| **CSV** | Spreadsheet analysis, further processing in Python/Excel |
| **G-code (educational)** | Study what real G-code looks like. Never send to a real printer |
| **SVG** | Vector drawing — open in Inkscape or Illustrator |
| **JSON** | Full session export including all parameters — re-import to reproduce results |
| **Report (.txt)** | Human-readable summary for documentation or sharing |

**Config Import:** Use the *Config Import (JSON)* expander at the top of the
sidebar to load a previously exported JSON and restore all settings exactly.

**G-code notes:**
- Uses simplified G1 linear moves
- All moves are at the same Z height (2D slice only)
- E values are approximate if enabled
- No homing, no temperature, no fan commands
""",
    },
}

for tab_name, info in tab_info.items():
    with st.expander(f"{info['icon']} {tab_name}", expanded=False):
        st.markdown(f"**{info['summary']}**")
        st.markdown(info["details"])

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Quick Profiles
# ═══════════════════════════════════════════════════════════════════════════════
st.header("6 · Quick Profiles", anchor="quick-profiles")

st.markdown(
    "The **Quick Profiles** expander (just below the page title) sets a bundle of "
    "recommended parameters in one click. You can still override any value after applying one."
)

profile_table = {
    "Fast Preview": ("0.32 mm", "90 mm/s", "1", "6.0 mm", "Rough overview only. Large lines, fast."),
    "Draft": ("0.28 mm", "70 mm/s", "2", "4.0 mm", "Visible layer lines but fast. Good for iteration."),
    "Balanced": ("0.20 mm", "50 mm/s", "3", "3.0 mm", "The everyday default. Good balance of quality and speed."),
    "Strong": ("0.20 mm", "45 mm/s", "5", "2.2 mm", "Dense fill and more shells. Heavier, stronger part."),
    "Fine": ("0.12 mm", "35 mm/s", "4", "2.0 mm", "Thin layers, high detail, slow print."),
}

st.markdown("| Profile | Layer height | Speed | Perimeters | Infill spacing | Notes |")
st.markdown("|---|---|---|---|---|---|")
for name, (lh, spd, perim, spacing, note) in profile_table.items():
    st.markdown(f"| **{name}** | {lh} | {spd} | {perim} | {spacing} | {note} |")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Import / Export
# ═══════════════════════════════════════════════════════════════════════════════
st.header("7 · Importing & Exporting Configs", anchor="importing-exporting-configs")

st.markdown("""
MiniSlicer can save and restore **all your sidebar parameters** as a single JSON file.

**To save a session:**
1. Go to the **Export** tab.
2. Click **Download JSON**.
3. The file contains a `parameters` object with every setting.

**To restore a session:**
1. Open the **Config Import (JSON)** expander at the top of the sidebar.
2. Upload the JSON file.
3. Tick **Apply imported config overrides**.
4. All parameters are restored instantly.

**Useful for:**
- Reproducing the exact same plan later
- Sharing settings with a colleague
- A/B testing two setups side-by-side (open two browser tabs, load each JSON)

**SVG Import:**
- Open the **Import SVG Shape** expander in the sidebar
- Upload a `.svg` file
- Set the target width in mm — MiniSlicer scales the shape proportionally
- Complex SVGs with multiple paths use only the largest detected polygon

**STL Import:**
- Open the **Import** expander in the sidebar
- Upload a `.stl` mesh
- Set **STL slice target width** to scale the unitless mesh into millimeters
- Move **STL slice Z** to choose the horizontal cross-section
- MiniSlicer turns that slice into the active 2D shape and runs the normal toolpath workflow

If the selected Z height misses the mesh or creates no closed loop, choose a
different Z height inside the solid part of the model.
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Tips & Common Mistakes
# ═══════════════════════════════════════════════════════════════════════════════
st.header("8 · Tips, Tricks & Common Mistakes", anchor="tips-tricks-common-mistakes")

tips_col, mistakes_col = st.columns(2)

with tips_col:
    st.subheader("Tips & Tricks")
    st.markdown("""
**Get more from the Compare tab:**
Compare Zigzag vs Parallel at the same spacing to instantly see
how much travel you save with no change to print quality.

**Use the layer slider:**
In the Visualization tab, scrub the layer slider to watch the infill
angle alternate. Enable *Alternating angle* first for the full effect.

**Hover over paths:**
In any Plotly chart, hover over a line to see its exact length and
estimated time. Useful for finding unexpectedly short or long paths.

**Use Transform to test placement:**
Set *Show build plate* on, then try *Center on build plate* and
*Fit inside build plate* to quickly simulate how a part fits.

**Export the report for documentation:**
The `.txt` report is a quick summary suitable for pasting into
project notes or sharing with teammates.

**Chain Quick Profiles:**
Start with Balanced, then manually tighten infill spacing to Strong levels
to get 5 perimeters with custom density.
""")

with mistakes_col:
    st.subheader("Common Mistakes")
    st.markdown("""
**Infill spacing too large:**
If you see "No infill lines generated", reduce spacing.
For a small shape (e.g. 10 mm circle), spacing of 3 mm may leave no room.

**Wall clearance too aggressive:**
Setting infill wall clearance larger than half the shape width
eliminates the fill region entirely. Start at 0 and increase slowly.

**Layer height > nozzle diameter:**
E.g. layer height 0.5 mm with a 0.4 mm nozzle. The Advisor will flag this.
A realistic max is ~75% of nozzle diameter.

**Forgetting the build plate:**
Build plate fit/center options only work when *Show build plate* is checked.
The options are greyed out when the plate is hidden.

**Taking the G-code export to a real printer:**
The G-code is for education only. It has no temperature, homing,
or calibration commands. Never run it on real hardware.

**Comparing patterns at different spacings:**
The Compare tab uses the same spacing for both patterns.
If you want a fair comparison, leave spacing unchanged between tests.
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Glossary
# ═══════════════════════════════════════════════════════════════════════════════
st.header("9 · Glossary", anchor="glossary")

glossary = {
    "Perimeter (Wall / Shell)": "An offset ring of the shape outline. Multiple perimeters form the outer shell of a printed part.",
    "Infill": "Lines or patterns that fill the solid interior area of a cross-section.",
    "Toolpath": "The complete ordered sequence of movements (printing and travel) the nozzle makes on one layer.",
    "Segment": "One straight line between two adjacent toolpath points. A path is made of many segments.",
    "Travel move": "A non-printing head movement — nozzle moves to the start of the next path without extruding material.",
    "Path efficiency": "Ratio of printing distance to total motion distance. Higher = less wasted travel.",
    "Layer height": "Thickness of one deposited material layer. Controls vertical resolution and print speed.",
    "Nozzle diameter": "Opening diameter of the extrusion nozzle. Controls minimum feature size and extrusion width.",
    "FDM": "Fused Deposition Modelling — melts and extrudes thermoplastic filament layer by layer.",
    "DED": "Directed Energy Deposition — melts metal wire or powder using a high-energy source (laser or arc). Used for metal printing.",
    "Bounding Box": "The smallest axis-aligned rectangle that contains the entire shape.",
    "Seam": "The point where a closed perimeter loop starts and ends. Often visible as a small mark on real prints.",
    "Z-hop": "A small upward lift before a travel move to avoid scraping previously deposited material.",
    "Path order optimization": "Reordering paths using nearest-neighbor heuristics to minimize total travel distance.",
    "Geometry simplification": "Removing micro-vertices from intersection-generated paths to reduce data size.",
    "Extrusion cross-section": "The shape of deposited material (approximately rectangular: nozzle_diameter × layer_height).",
}

gcol1, gcol2 = st.columns(2)
items = list(glossary.items())
half = len(items) // 2

with gcol1:
    for term, definition in items[:half]:
        st.markdown(f"**{term}**")
        st.caption(definition)

with gcol2:
    for term, definition in items[half:]:
        st.markdown(f"**{term}**")
        st.caption(definition)

st.divider()

st.success(
    "You've read the full tutorial. Head back to **MiniSlicer — Toolpath Planner** "
    "from the sidebar and start experimenting. "
    "There is no better way to learn than adjusting parameters and watching what changes.",
    icon="🎓",
)
st.caption("MiniSlicer — Educational toolpath visualizer · Not machine-ready output")
