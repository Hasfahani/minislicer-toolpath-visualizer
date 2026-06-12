"""Plotly figure generation for toolpath visualization."""

from __future__ import annotations

import math
from typing import Iterable

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from shapely.geometry import LineString, Polygon


def create_toolpath_figure(
    boundary: LineString,
    perimeter_paths: list[LineString],
    infill_lines: list[LineString],
    show_travel_moves: bool = False,
    show_seam_markers: bool = False,
    show_boundary: bool = True,
    show_perimeters: bool = True,
    show_infill: bool = True,
    show_start_end_points: bool = True,
    extrusion_width_mm: float = 0.0,
    print_speed_mm_s: float = 0.0,
    line_width_scale: float = 1.0,
    color_scheme: str = "Classic",
    max_path_index: int | None = None,
    build_plate_size: tuple[float, float] | None = None,
    show_direction_arrows: bool = False,
    show_dimensions: bool = False,
) -> go.Figure:
    """Create a Plotly figure with boundary, perimeters, infill, and optional overlays.

    Args:
        show_travel_moves: Draw dashed lines for non-printing head movements.
        show_seam_markers: Draw a marker at the start (seam) of each perimeter.
        extrusion_width_mm: If > 0, render paths as filled extrusion bands.
        max_path_index: Only render the first N perimeter+infill paths (animation use).
    """
    fig = go.Figure()
    colors = _colors_for_scheme(color_scheme)
    width_scale = max(0.5, float(line_width_scale))

    # Slice paths for step animation
    if max_path_index is not None:
        n_perims = min(max_path_index, len(perimeter_paths))
        n_infill = max(0, max_path_index - len(perimeter_paths))
        perimeter_paths = perimeter_paths[:n_perims]
        infill_lines = infill_lines[:n_infill]

    use_extrusion = extrusion_width_mm > 0

    if build_plate_size is not None:
        plate_w, plate_d = build_plate_size
        fig.add_shape(
            type="rect",
            x0=0,
            y0=0,
            x1=plate_w,
            y1=plate_d,
            line=dict(color="#94a3b8", width=1, dash="dash"),
            fillcolor="rgba(148, 163, 184, 0.08)",
            layer="below",
        )
        fig.add_trace(go.Scatter(
            x=[0, plate_w, plate_w, 0, 0],
            y=[0, 0, plate_d, plate_d, 0],
            mode="lines",
            name="Build plate",
            line=dict(color="#94a3b8", width=1, dash="dash"),
            hoverinfo="skip",
        ))

    # Shape boundary
    if show_boundary and (not perimeter_paths or not _same_line(boundary, perimeter_paths[0])):
        _add_line(fig, boundary, name="Shape outline", hover_label="shape outline",
                  color=colors["boundary"], width=max(1, round(2 * width_scale)), dash="dot")

    # Perimeters
    for idx, line in enumerate(perimeter_paths if show_perimeters else [], start=1):
        if use_extrusion:
            _add_extrusion_band(fig, line, color=colors["perimeter"],
                                width_mm=extrusion_width_mm,
                                name="Perimeters" if idx == 1 else "",
                                legendgroup="Perimeters",
                                showlegend=(idx == 1))
        else:
            _add_line(fig, line, name=f"Perimeter {idx}",
                      hover_label=f"perimeter {idx}",
                      color=colors["perimeter"], width=max(1, round(2 * width_scale)),
                      extra_html=f"<br>Length: {line.length:.2f} mm",
                      showlegend=(idx == 1), legendgroup="Perimeters")

    # Seam markers
    if show_seam_markers and perimeter_paths:
        seam_x = [list(line.coords)[0][0] for line in perimeter_paths]
        seam_y = [list(line.coords)[0][1] for line in perimeter_paths]
        fig.add_trace(go.Scatter(
            x=seam_x, y=seam_y,
            mode="markers", name="Seam",
            marker=dict(size=10, color="#eab308", symbol="diamond",
                        line=dict(width=1, color="#92400e")),
            hovertemplate="<b>Seam</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm<extra></extra>",
        ))

    # Infill
    for idx, line in enumerate(infill_lines if show_infill else [], start=1):
        if use_extrusion:
            _add_extrusion_band(fig, line, color=colors["infill"],
                                width_mm=extrusion_width_mm,
                                name="Infill" if idx == 1 else "",
                                legendgroup="Infill",
                                showlegend=(idx == 1))
        else:
            _t = f"<br>~{line.length / max(print_speed_mm_s, 0.1) * 1000:.0f} ms" if print_speed_mm_s > 0 else ""
            _add_line(fig, line, name=f"Infill {idx}",
                      hover_label=f"infill line {idx}",
                      color=colors["infill"], width=max(1, round(width_scale)),
                      extra_html=f"<br>Length: {line.length:.2f} mm{_t}",
                      showlegend=(idx == 1), legendgroup="Infill")

    # Travel moves
    if show_travel_moves:
        travels = _collect_travel_moves(perimeter_paths, infill_lines)
        if travels:
            tx: list[float | None] = []
            ty: list[float | None] = []
            for (x0, y0), (x1, y1) in travels:
                tx.extend([x0, x1, None])
                ty.extend([y0, y1, None])
            fig.add_trace(go.Scatter(
                x=tx, y=ty, mode="lines", name="Travel moves",
                line=dict(color=colors["travel"], width=max(1, round(width_scale)), dash="dash"),
                hovertemplate="<b>Travel</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm<extra></extra>",
            ))

    # Start / end markers
    start_points, end_points = _collect_start_end_points([*perimeter_paths, *infill_lines])
    if show_start_end_points and start_points:
        fig.add_trace(go.Scatter(
            x=[p[0] for p in start_points], y=[p[1] for p in start_points],
            mode="markers", name="Start points",
            marker=dict(size=8, color=colors["start"], symbol="circle"),
            hovertemplate="<b>Start</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm<extra></extra>",
        ))
    if show_start_end_points and end_points:
        fig.add_trace(go.Scatter(
            x=[p[0] for p in end_points], y=[p[1] for p in end_points],
            mode="markers", name="End points",
            marker=dict(size=8, color=colors["end"], symbol="x"),
            hovertemplate="<b>End</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm<extra></extra>",
        ))

    # Direction arrows - small arrow markers at each line's midpoint
    if show_direction_arrows:
        _add_direction_arrows(fig, perimeter_paths if show_perimeters else [],
                              color=colors["perimeter"], name="Perimeter direction")
        _add_direction_arrows(fig, infill_lines if show_infill else [],
                              color=colors["infill"], name="Infill direction")

    # Bounding-box dimension annotations
    if show_dimensions:
        all_lines = ([boundary] if show_boundary else []) + perimeter_paths + infill_lines
        _add_dimension_annotations(fig, all_lines)

    _dark = color_scheme in ("Dark", "Neon")
    _grid = "#374151" if _dark else "#e5e7eb"
    fig.update_layout(
        title="MiniSlicer Toolpath View",
        xaxis_title="X (mm)",
        yaxis_title="Y (mm)",
        template="plotly_dark" if _dark else "plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        margin=dict(l=24, r=24, t=70, b=24),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=True, gridcolor=_grid, zeroline=False)
    fig.update_yaxes(scaleanchor="x", scaleratio=1,
                     showgrid=True, gridcolor=_grid, zeroline=False)
    return fig


def create_multilayer_animated_figure(
    layers: list[tuple[float, list[LineString], list[LineString]]],
    color_scheme: str = "Classic",
) -> go.Figure:
    """Build an animated 3D Plotly figure that builds up one layer at a time.

    Args:
        layers: Sequence of ``(z_height, perimeter_paths, infill_lines)`` tuples,
            one per sliced layer. Sorted by ascending Z is assumed.
        color_scheme: Name passed to ``_colors_for_scheme`` for line colors.

    Returns:
        A ``go.Figure`` with a play/pause button and a per-layer slider.
        Each animation frame reveals an additional layer of the build.
    """
    colors = _colors_for_scheme(color_scheme)

    if not layers:
        fig = go.Figure()
        fig.update_layout(title="No layers to display.", template="plotly_white")
        return fig

    # Pre-accumulate (x, y, z) coordinate lists for perimeters and infill
    # at each frame (layer 0, layers 0-1, layers 0-2, ...).
    # Using None-separated single traces keeps frame payloads small.
    acc_px: list[float | None] = []
    acc_py: list[float | None] = []
    acc_pz: list[float | None] = []
    acc_ix: list[float | None] = []
    acc_iy: list[float | None] = []
    acc_iz: list[float | None] = []

    frame_data: list[tuple[list, list, list, list, list, list]] = []

    for z, perims, infills in layers:
        for line in perims:
            xs, ys = line.xy
            acc_px.extend(list(xs) + [None])
            acc_py.extend(list(ys) + [None])
            acc_pz.extend([z] * len(xs) + [None])
        for line in infills:
            xs, ys = line.xy
            acc_ix.extend(list(xs) + [None])
            acc_iy.extend(list(ys) + [None])
            acc_iz.extend([z] * len(xs) + [None])
        frame_data.append((
            list(acc_px), list(acc_py), list(acc_pz),
            list(acc_ix), list(acc_iy), list(acc_iz),
        ))

    # Initial display = first layer only
    p0x, p0y, p0z, i0x, i0y, i0z = frame_data[0]

    initial_traces = [
        go.Scatter3d(
            x=p0x, y=p0y, z=p0z,
            mode="lines",
            line=dict(color=colors["perimeter"], width=2),
            name="Perimeters",
        ),
        go.Scatter3d(
            x=i0x, y=i0y, z=i0z,
            mode="lines",
            line=dict(color=colors["infill"], width=1),
            name="Infill",
        ),
    ]

    frames = [
        go.Frame(
            name=str(idx),
            data=[
                go.Scatter3d(x=px, y=py, z=pz, mode="lines",
                             line=dict(color=colors["perimeter"], width=2)),
                go.Scatter3d(x=ix, y=iy, z=iz, mode="lines",
                             line=dict(color=colors["infill"], width=1)),
            ],
        )
        for idx, (px, py, pz, ix, iy, iz) in enumerate(frame_data)
    ]

    fig = go.Figure(data=initial_traces, frames=frames)

    z_vals = [z for z, _, _ in layers]
    slider_steps = [
        dict(
            method="animate",
            label=f"Z={z:.2f}",
            args=[
                [str(idx)],
                dict(frame=dict(duration=0, redraw=True),
                     mode="immediate",
                     transition=dict(duration=0)),
            ],
        )
        for idx, z in enumerate(z_vals)
    ]

    fig.update_layout(
        title=f"Multi-Layer Build - {len(layers)} layer{'s' if len(layers) != 1 else ''}",
        scene=dict(
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=60, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        updatemenus=[dict(
            type="buttons",
            showactive=False,
            y=-0.12, x=0.5, xanchor="center", yanchor="top",
            buttons=[
                dict(
                    label="Play",
                    method="animate",
                    args=[None, dict(frame=dict(duration=300, redraw=True),
                                    fromcurrent=True,
                                    transition=dict(duration=0))],
                ),
                dict(
                    label="Pause",
                    method="animate",
                    args=[[None], dict(frame=dict(duration=0, redraw=False),
                                      mode="immediate",
                                      transition=dict(duration=0))],
                ),
            ],
        )],
        sliders=[dict(
            currentvalue=dict(prefix="Layer Z: ", visible=True, xanchor="center",
                              font=dict(size=12)),
            pad=dict(t=50, b=10),
            steps=slider_steps,
        )],
    )
    return fig


def create_3d_figure(
    shape: Polygon,
    layer_count: int,
    perimeter_count: int,
    perimeter_spacing: float,
    infill_spacing: float,
    layer_height_mm: float,
    infill_pattern: str = "Parallel Lines",
) -> go.Figure:
    """Build a 3D Plotly figure stacking multiple sliced layers."""
    from src.toolpaths import generate_infill, generate_inward_perimeters

    fig = go.Figure()

    for layer_idx in range(layer_count):
        z = round(layer_idx * layer_height_mm, 4)
        angle = 45.0 if layer_idx % 2 == 0 else -45.0

        perimeters = generate_inward_perimeters(shape, count=perimeter_count,
                                                spacing=perimeter_spacing)
        infills = generate_infill(shape, infill_pattern, spacing=infill_spacing, angle_deg=angle)

        first_layer = layer_idx == 0

        for pidx, line in enumerate(perimeters):
            xs, ys = line.xy
            fig.add_trace(go.Scatter3d(
                x=list(xs), y=list(ys), z=[z] * len(xs),
                mode="lines",
                line=dict(color="#2563eb", width=2),
                name="Perimeters" if (first_layer and pidx == 0) else "",
                showlegend=(first_layer and pidx == 0),
                legendgroup="Perimeters",
            ))

        for iidx, line in enumerate(infills):
            xs, ys = line.xy
            fig.add_trace(go.Scatter3d(
                x=list(xs), y=list(ys), z=[z] * len(xs),
                mode="lines",
                line=dict(color="#f97316", width=1),
                name="Infill" if (first_layer and iidx == 0) else "",
                showlegend=(first_layer and iidx == 0),
                legendgroup="Infill",
            ))

    fig.update_layout(
        title=f"3D Layer Stack - {layer_count} layer{'s' if layer_count != 1 else ''}",
        scene=dict(
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
    )
    return fig


def create_speed_map_figure(
    boundary: LineString,
    perimeter_paths: list[LineString],
    infill_lines: list[LineString],
    print_speed_mm_s: float,
    travel_speed_mm_s: float,
    line_width_scale: float = 1.0,
    build_plate_size: tuple[float, float] | None = None,
    perimeter_speed_multiplier: float = 0.8,
) -> go.Figure:
    """Render paths colored by their print speed category."""
    fig = go.Figure()
    ws = max(0.5, float(line_width_scale))
    perim_speed = print_speed_mm_s * max(0.1, float(perimeter_speed_multiplier))

    if build_plate_size is not None:
        pw, pd = build_plate_size
        fig.add_shape(type="rect", x0=0, y0=0, x1=pw, y1=pd,
                      line=dict(color="#94a3b8", width=1, dash="dash"),
                      fillcolor="rgba(148,163,184,0.08)", layer="below")

    bx, by = boundary.xy
    fig.add_trace(go.Scatter(x=list(bx), y=list(by), mode="lines", name="Outline",
                             line=dict(color="#475569", width=1, dash="dot"), hoverinfo="skip"))

    for idx, line in enumerate(perimeter_paths):
        x, y = line.xy
        fig.add_trace(go.Scatter(
            x=list(x), y=list(y), mode="lines",
            name=f"Perimeters  {perim_speed:.0f} mm/s" if idx == 0 else "",
            showlegend=(idx == 0), legendgroup="perimeters",
            line=dict(color="#2563eb", width=max(1, round(2 * ws))),
            hovertemplate=f"<b>Perimeter {idx + 1}</b><br>Speed: {perim_speed:.0f} mm/s<extra></extra>",
        ))

    for idx, line in enumerate(infill_lines):
        x, y = line.xy
        fig.add_trace(go.Scatter(
            x=list(x), y=list(y), mode="lines",
            name=f"Infill  {print_speed_mm_s:.0f} mm/s" if idx == 0 else "",
            showlegend=(idx == 0), legendgroup="infill",
            line=dict(color="#16a34a", width=max(1, round(ws))),
            hovertemplate=f"<b>Infill {idx + 1}</b><br>Speed: {print_speed_mm_s:.0f} mm/s<extra></extra>",
        ))

    travels = _collect_travel_moves(perimeter_paths, infill_lines)
    if travels:
        tx: list[float | None] = []
        ty: list[float | None] = []
        for (x0, y0), (x1, y1) in travels:
            tx.extend([x0, x1, None])
            ty.extend([y0, y1, None])
        fig.add_trace(go.Scatter(
            x=tx, y=ty, mode="lines",
            name=f"Travel  {travel_speed_mm_s:.0f} mm/s",
            line=dict(color="#ef4444", width=max(1, round(ws)), dash="dash"),
            hoverinfo="skip",
        ))

    fig.update_layout(
        title=(
            f"Speed Map - Perimeter: {perim_speed:.0f} mm/s ({perimeter_speed_multiplier:.0%}) "
            f"| Infill: {print_speed_mm_s:.0f} | Travel: {travel_speed_mm_s:.0f} mm/s"
        ),
        xaxis_title="X (mm)", yaxis_title="Y (mm)", template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        margin=dict(l=24, r=24, t=70, b=24), hovermode="closest",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    fig.update_yaxes(scaleanchor="x", scaleratio=1, showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    return fig


def create_time_map_figure(
    boundary: LineString,
    perimeter_paths: list[LineString],
    infill_lines: list[LineString],
    print_speed_mm_s: float,
    line_width_scale: float = 1.0,
    build_plate_size: tuple[float, float] | None = None,
) -> go.Figure:
    """Render infill paths colored by time contribution (blue=fast/short, red=slow/long)."""
    fig = go.Figure()
    ws = max(0.5, float(line_width_scale))

    if build_plate_size is not None:
        pw, pd = build_plate_size
        fig.add_shape(type="rect", x0=0, y0=0, x1=pw, y1=pd,
                      line=dict(color="#94a3b8", width=1, dash="dash"),
                      fillcolor="rgba(148,163,184,0.08)", layer="below")

    bx, by = boundary.xy
    fig.add_trace(go.Scatter(x=list(bx), y=list(by), mode="lines", name="Outline",
                             line=dict(color="#475569", width=1, dash="dot"), hoverinfo="skip"))

    for idx, line in enumerate(perimeter_paths):
        x, y = line.xy
        fig.add_trace(go.Scatter(
            x=list(x), y=list(y), mode="lines",
            name="Perimeters" if idx == 0 else "",
            showlegend=(idx == 0), legendgroup="perimeters",
            line=dict(color="#93c5fd", width=max(1, round(2 * ws))),
            hoverinfo="skip",
        ))

    if infill_lines:
        lengths = [line.length for line in infill_lines]
        min_l = min(lengths)
        max_l = max(lengths)
        span = max(max_l - min_l, 1e-9)

        # Bucket into 5 bands: blue -> cyan -> green -> orange -> red
        bucket_colors = ["#3b82f6", "#06b6d4", "#22c55e", "#f97316", "#ef4444"]
        bucket_labels = ["shortest (fast)", "short", "medium", "long", "longest (slow)"]
        n = len(bucket_colors)
        buckets: list[list[LineString]] = [[] for _ in range(n)]
        for line, length in zip(infill_lines, lengths, strict=True):
            b = min(int((length - min_l) / span * n), n - 1)
            buckets[b].append(line)

        for b_lines, color, label in zip(buckets, bucket_colors, bucket_labels, strict=True):
            if not b_lines:
                continue
            xs: list[float | None] = []
            ys: list[float | None] = []
            for line in b_lines:
                lx, ly = line.xy
                xs.extend(list(lx) + [None])
                ys.extend(list(ly) + [None])
            avg_t = sum(seg.length for seg in b_lines) / len(b_lines) / max(print_speed_mm_s, 0.1)
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines",
                name=f"Infill {label} (~{avg_t * 1000:.0f} ms avg)",
                line=dict(color=color, width=max(1, round(ws))),
                legendgroup="infill",
            ))

    fig.update_layout(
        title="Time Map - infill color indicates path duration (blue=fast, red=slow)",
        xaxis_title="X (mm)", yaxis_title="Y (mm)", template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        margin=dict(l=24, r=24, t=70, b=24), hovermode="closest",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    fig.update_yaxes(scaleanchor="x", scaleratio=1, showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    return fig


def create_comparison_figure(
    boundary: LineString,
    perimeters: list[LineString],
    infill_a: list[LineString],
    infill_b: list[LineString],
    label_a: str = "Pattern A",
    label_b: str = "Pattern B",
    line_width_scale: float = 1.0,
    color_scheme: str = "Classic",
) -> go.Figure:
    """Side-by-side comparison of two infill patterns in a subplot figure."""
    colors = _colors_for_scheme(color_scheme)
    ws = max(0.5, float(line_width_scale))
    dark = color_scheme in ("Dark", "Neon")
    grid_color = "#374151" if dark else "#e5e7eb"

    fig = make_subplots(rows=1, cols=2, subplot_titles=[label_a, label_b], horizontal_spacing=0.06)

    for col, infill_lines in ((1, infill_a), (2, infill_b)):
        first = col == 1
        bx, by = boundary.xy
        fig.add_trace(go.Scatter(
            x=list(bx), y=list(by), mode="lines",
            name="Outline" if first else "", showlegend=first, legendgroup="outline",
            line=dict(color=colors["boundary"], width=1, dash="dot"), hoverinfo="skip",
        ), row=1, col=col)

        for pidx, line in enumerate(perimeters):
            x, y = line.xy
            fig.add_trace(go.Scatter(
                x=list(x), y=list(y), mode="lines",
                name="Perimeters" if (first and pidx == 0) else "",
                showlegend=(first and pidx == 0), legendgroup="perimeters",
                line=dict(color=colors["perimeter"], width=max(1, round(2 * ws))),
                hoverinfo="skip",
            ), row=1, col=col)

        for iidx, line in enumerate(infill_lines):
            x, y = line.xy
            fig.add_trace(go.Scatter(
                x=list(x), y=list(y), mode="lines",
                name="Infill" if (first and iidx == 0) else "",
                showlegend=(first and iidx == 0), legendgroup="infill",
                line=dict(color=colors["infill"], width=max(1, round(ws))),
                hoverinfo="skip",
            ), row=1, col=col)

    fig.update_layout(
        title="Infill Pattern Comparison",
        template="plotly_dark" if dark else "plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0.0),
        margin=dict(l=24, r=24, t=90, b=24),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=True, gridcolor=grid_color, zeroline=False)
    fig.update_yaxes(scaleanchor="x", scaleratio=1, showgrid=True, gridcolor=grid_color, zeroline=False, row=1, col=1)
    fig.update_yaxes(scaleanchor="x2", scaleratio=1, showgrid=True, gridcolor=grid_color, zeroline=False, row=1, col=2)
    return fig


def create_metrics_figure(
    metrics: dict,
    print_speed_mm_s: float,
    travel_speed_mm_s: float,
) -> go.Figure:
    """Two-panel figure: path-length pie + motion-time bar chart."""
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=["Path Length Distribution", "Estimated Time Breakdown (s)"],
    )

    perim_len = float(metrics.get("perimeter_length_mm", 0))
    infill_len = float(metrics.get("infill_length_mm", 0))
    travel_len = float(metrics.get("travel_length_mm", 0))

    fig.add_trace(go.Pie(
        labels=["Perimeters", "Infill", "Travel"],
        values=[perim_len, infill_len, travel_len],
        marker_colors=["#2563eb", "#f97316", "#a855f7"],
        textinfo="label+percent",
        hole=0.35,
        showlegend=False,
    ), row=1, col=1)

    perim_t = perim_len / max(print_speed_mm_s * 0.8, 0.1)
    infill_t = infill_len / max(print_speed_mm_s, 0.1)
    travel_t = travel_len / max(travel_speed_mm_s, 0.1)

    fig.add_trace(go.Bar(
        x=["Perimeters", "Infill", "Travel"],
        y=[perim_t, infill_t, travel_t],
        marker_color=["#2563eb", "#f97316", "#a855f7"],
        text=[f"{v:.1f}s" for v in [perim_t, infill_t, travel_t]],
        textposition="auto",
        showlegend=False,
    ), row=1, col=2)

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=24, r=24, t=50, b=24),
        height=320,
    )
    fig.update_yaxes(title_text="seconds", row=1, col=2)
    return fig


def create_infill_length_histogram(
    infill_lines: list[LineString],
    print_speed_mm_s: float = 0.0,
) -> go.Figure:
    """Histogram of infill line lengths to show distribution uniformity."""
    lengths = [line.length for line in infill_lines if len(line.coords) >= 2]
    if not lengths:
        fig = go.Figure()
        fig.update_layout(title="No infill lines to plot.", height=220)
        return fig

    fig = go.Figure(go.Histogram(
        x=lengths, nbinsx=min(30, max(5, len(lengths) // 3)),
        marker_color="#f97316", opacity=0.85,
        hovertemplate="Length: %{x:.1f} mm<br>Count: %{y}<extra></extra>",
    ))
    subtitle = ""
    if print_speed_mm_s > 0:
        avg_t = (sum(lengths) / len(lengths)) / print_speed_mm_s * 1000
        subtitle = f" - avg {avg_t:.0f} ms per line at {print_speed_mm_s:.0f} mm/s"

    fig.update_layout(
        title=f"Infill Line Length Distribution{subtitle}",
        xaxis_title="Length (mm)",
        yaxis_title="Count",
        template="plotly_white",
        height=260,
        margin=dict(l=24, r=24, t=50, b=24),
    )
    return fig


def shape_boundary(shape: Polygon) -> LineString:
    """Convert a polygon exterior to a closed LineString."""
    return LineString(shape.exterior.coords)


# -- Internal helpers ----------------------------------------------------------

def _add_line(
    fig: go.Figure,
    line: LineString,
    name: str,
    hover_label: str,
    color: str,
    width: int,
    showlegend: bool = True,
    legendgroup: str | None = None,
    dash: str | None = None,
    extra_html: str = "",
) -> None:
    x_values, y_values = line.xy
    fig.add_trace(go.Scatter(
        x=list(x_values), y=list(y_values),
        mode="lines", name=name,
        line=dict(color=color, width=width, dash=dash),
        showlegend=showlegend, legendgroup=legendgroup,
        hovertemplate=(
            f"<b>{hover_label}</b><br>X: %{{x:.2f}} mm<br>Y: %{{y:.2f}} mm{extra_html}<extra></extra>"
        ),
    ))


def _add_extrusion_band(
    fig: go.Figure,
    line: LineString,
    color: str,
    width_mm: float,
    name: str,
    legendgroup: str,
    showlegend: bool,
) -> None:
    """Render a line as a filled polygon representing the extruded bead."""
    band = line.buffer(width_mm / 2, cap_style=2)  # flat caps
    if band.is_empty:
        return
    bx, by = band.exterior.xy
    fig.add_trace(go.Scatter(
        x=list(bx), y=list(by),
        mode="lines", fill="toself",
        fillcolor=_hex_to_rgba(color, 0.35),
        line=dict(color=color, width=0.5),
        name=name, legendgroup=legendgroup, showlegend=showlegend,
        hoverinfo="skip",
    ))


def _colors_for_scheme(name: str) -> dict[str, str]:
    schemes = {
        "Classic": {
            "boundary": "#475569",
            "perimeter": "#2563eb",
            "infill": "#f97316",
            "travel": "#a855f7",
            "start": "#16a34a",
            "end": "#dc2626",
        },
        "Colorblind": {
            "boundary": "#4b5563",
            "perimeter": "#0072b2",
            "infill": "#d55e00",
            "travel": "#cc79a7",
            "start": "#009e73",
            "end": "#e69f00",
        },
        "Dark": {
            "boundary": "#cbd5e1",
            "perimeter": "#60a5fa",
            "infill": "#fb923c",
            "travel": "#c084fc",
            "start": "#4ade80",
            "end": "#f87171",
        },
        "High Contrast": {
            "boundary": "#111827",
            "perimeter": "#1d4ed8",
            "infill": "#ea580c",
            "travel": "#7c3aed",
            "start": "#15803d",
            "end": "#b91c1c",
        },
        "Neon": {
            "boundary": "#f8fafc",
            "perimeter": "#00f5ff",
            "infill": "#ff00ff",
            "travel": "#ffff00",
            "start": "#00ff88",
            "end": "#ff4444",
        },
    }
    return schemes.get(name, schemes["Classic"])


def _hex_to_rgba(color: str, alpha: float) -> str:
    if not color.startswith("#") or len(color) != 7:
        return color
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _same_line(first: LineString, second: LineString, tolerance: float = 1e-9) -> bool:
    return (
        first.hausdorff_distance(second) <= tolerance
        and second.hausdorff_distance(first) <= tolerance
    )


def _collect_start_end_points(
    lines: Iterable[LineString],
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    starts: list[tuple[float, float]] = []
    ends: list[tuple[float, float]] = []
    for line in lines:
        coords = list(line.coords)
        if len(coords) < 2:
            continue
        starts.append((float(coords[0][0]), float(coords[0][1])))
        ends.append((float(coords[-1][0]), float(coords[-1][1])))
    return starts, ends


def _collect_travel_moves(
    perimeter_paths: list[LineString],
    infill_lines: list[LineString],
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    all_paths = [*perimeter_paths, *infill_lines]
    travels: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for i in range(len(all_paths) - 1):
        curr = list(all_paths[i].coords)
        nxt = list(all_paths[i + 1].coords)
        if not curr or not nxt:
            continue
        end = (float(curr[-1][0]), float(curr[-1][1]))
        start = (float(nxt[0][0]), float(nxt[0][1]))
        dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
        if dist > 0.01:
            travels.append((end, start))
    return travels


def _add_direction_arrows(
    fig: go.Figure,
    lines: list[LineString],
    color: str,
    name: str,
    max_arrows: int = 60,
) -> None:
    """Add small directional arrow markers at the midpoint of sampled lines."""
    if not lines:
        return
    step = max(1, len(lines) // max_arrows)
    ax: list[float] = []
    ay: list[float] = []
    angles: list[float] = []
    for i in range(0, len(lines), step):
        line = lines[i]
        coords = list(line.coords)
        if len(coords) < 2:
            continue
        mid = line.interpolate(0.5, normalized=True)
        ax.append(float(mid.x))
        ay.append(float(mid.y))
        n = len(coords)
        mi = n // 2
        x0, y0 = coords[max(0, mi - 1)]
        x1, y1 = coords[min(n - 1, mi + 1)]
        dx, dy = x1 - x0, y1 - y0
        angles.append(math.degrees(math.atan2(dx, dy)))
    if not ax:
        return
    fig.add_trace(go.Scatter(
        x=ax, y=ay, mode="markers",
        name=name,
        marker=dict(symbol="arrow", size=9, angle=angles, color=color,
                    line=dict(width=1, color=color)),
        hoverinfo="skip",
        showlegend=False,
    ))


def _add_dimension_annotations(fig: go.Figure, lines: list[LineString]) -> None:
    """Overlay bounding-box width/height dimension labels on the figure."""
    xs: list[float] = []
    ys: list[float] = []
    for line in lines:
        if line is None:
            continue
        lx, ly = line.xy
        xs.extend(lx)
        ys.extend(ly)
    if not xs or not ys:
        return
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w = max_x - min_x
    h = max_y - min_y
    pad = max(w, h) * 0.09 + 2.0
    # Width annotation below the shape
    fig.add_annotation(
        x=(min_x + max_x) / 2, y=min_y - pad,
        text=f"<- {w:.1f} mm ->",
        showarrow=False,
        font=dict(size=10, color="#64748b"),
        xref="x", yref="y",
    )
    # Height annotation to the right
    fig.add_annotation(
        x=max_x + pad, y=(min_y + max_y) / 2,
        text=f"<-> {h:.1f} mm",
        showarrow=False,
        font=dict(size=10, color="#64748b"),
        xref="x", yref="y",
        textangle=-90,
    )


def create_path_density_figure(
    perimeter_paths: list[LineString],
    infill_lines: list[LineString],
    boundary: LineString,
    sample_step_mm: float = 0.5,
    build_plate_size: tuple[float, float] | None = None,
) -> go.Figure:
    """2D density heatmap showing where paths are concentrated."""
    all_x: list[float] = []
    all_y: list[float] = []
    for line in [*perimeter_paths, *infill_lines]:
        if line.length <= 0:
            continue
        n = max(2, int(line.length / sample_step_mm) + 1)
        for i in range(n):
            pt = line.interpolate(i / (n - 1), normalized=True)
            all_x.append(float(pt.x))
            all_y.append(float(pt.y))

    fig = go.Figure()
    if not all_x:
        fig.update_layout(title="No paths to plot.", height=400)
        return fig

    fig.add_trace(go.Histogram2d(
        x=all_x, y=all_y,
        colorscale="YlOrRd",
        nbinsx=70, nbinsy=70,
        showscale=True,
        colorbar=dict(title="Samples"),
        hovertemplate="X: %{x:.1f} mm<br>Y: %{y:.1f} mm<br>Density: %{z}<extra></extra>",
    ))

    bx, by = boundary.xy
    fig.add_trace(go.Scatter(
        x=list(bx), y=list(by), mode="lines", name="Boundary",
        line=dict(color="white", width=1.5, dash="dot"),
        hoverinfo="skip",
    ))

    if build_plate_size is not None:
        pw, pd = build_plate_size
        fig.add_shape(type="rect", x0=0, y0=0, x1=pw, y1=pd,
                      line=dict(color="#94a3b8", width=1, dash="dash"),
                      fillcolor="rgba(0,0,0,0)", layer="above")

    fig.update_layout(
        title="Path Density Map - hotter = more material / more passes",
        xaxis_title="X (mm)", yaxis_title="Y (mm)",
        template="plotly_dark",
        margin=dict(l=24, r=24, t=70, b=24),
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig
