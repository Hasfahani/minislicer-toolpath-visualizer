# Purpose: Builds animated Plotly previews that replay toolpath segments like a moving nozzle.
# Reason: Animation helps explain path order and motion visually without changing backend planning logic.
"""Animated Plotly figure showing nozzle path playback segment by segment."""

from __future__ import annotations

import plotly.graph_objects as go
from shapely.geometry import LineString

from src.toolpaths import Segment

# Color per path type
_TYPE_COLOR: dict[str, str] = {
    "boundary": "#475569",
    "perimeter": "#2563eb",
    "infill": "#f97316",
}
_NOZZLE_COLOR = "#16a34a"
_MAX_FRAMES = 120


def create_animated_figure(
    boundary: LineString,
    segments: list[Segment],
) -> go.Figure:
    """Build a Plotly figure with play/pause nozzle animation.

    Animation runs entirely in the browser - no Python round-trips needed.
    Automatically sub-samples to at most _MAX_FRAMES frames for performance.
    """
    bx, by = boundary.xy

    if not segments:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=list(bx), y=list(by), mode="lines", name="Boundary",
                       line=dict(color="#475569", width=2, dash="dot"))
        )
        fig.update_layout(title="No segments to animate.", template="plotly_white")
        return fig

    # Sub-sample frame indices to keep total frames manageable
    step = max(1, len(segments) // _MAX_FRAMES)
    frame_indices = list(range(0, len(segments), step))
    if frame_indices[-1] != len(segments) - 1:
        frame_indices.append(len(segments) - 1)

    # Pre-build accumulated (x, y) arrays up to each frame index
    # Use None separators so a single Scatter trace draws all segments
    all_px: list[float | None] = []
    all_py: list[float | None] = []
    frame_px: list[list[float | None]] = []
    frame_py: list[list[float | None]] = []
    frame_nx: list[float] = []
    frame_ny: list[float] = []

    seg_iter = 0
    for fi in frame_indices:
        while seg_iter <= fi:
            seg = segments[seg_iter]
            all_px.extend([seg.x_start, seg.x_end, None])
            all_py.extend([seg.y_start, seg.y_end, None])
            seg_iter += 1
        frame_px.append(list(all_px))
        frame_py.append(list(all_py))
        frame_nx.append(float(segments[fi].x_end))
        frame_ny.append(float(segments[fi].y_end))

    # Build Plotly frames
    frames: list[go.Frame] = []
    for idx, fi in enumerate(frame_indices):
        frames.append(
            go.Frame(
                name=str(fi),
                data=[
                    go.Scatter(x=list(bx), y=list(by)),
                    go.Scatter(x=frame_px[idx], y=frame_py[idx]),
                    go.Scatter(x=[frame_nx[idx]], y=[frame_ny[idx]]),
                ],
            )
        )

    # Initial state = frame 0
    fig = go.Figure(
        data=[
            go.Scatter(
                x=list(bx), y=list(by),
                mode="lines", name="Boundary",
                line=dict(color="#475569", width=2, dash="dot"),
            ),
            go.Scatter(
                x=frame_px[0], y=frame_py[0],
                mode="lines", name="Drawn path",
                line=dict(color="#2563eb", width=2),
            ),
            go.Scatter(
                x=[frame_nx[0]], y=[frame_ny[0]],
                mode="markers", name="Nozzle",
                marker=dict(
                    size=14, color=_NOZZLE_COLOR, symbol="circle",
                    line=dict(width=2, color="white"),
                ),
            ),
        ],
        frames=frames,
    )

    slider_steps = [
        dict(
            method="animate",
            label=str(fi),
            args=[
                [str(fi)],
                dict(frame=dict(duration=0, redraw=True),
                     mode="immediate",
                     transition=dict(duration=0)),
            ],
        )
        for fi in frame_indices
    ]

    fig.update_layout(
        title="Nozzle Path Animation",
        xaxis_title="X (mm)",
        yaxis_title="Y (mm)",
        template="plotly_white",
        margin=dict(l=24, r=24, t=70, b=100),
        hovermode=False,
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                y=-0.12,
                x=0.5,
                xanchor="center",
                yanchor="top",
                buttons=[
                    dict(
                        label="Play",
                        method="animate",
                        args=[
                            None,
                            dict(frame=dict(duration=40, redraw=True),
                                 fromcurrent=True,
                                 transition=dict(duration=0)),
                        ],
                    ),
                    dict(
                        label="Pause",
                        method="animate",
                        args=[
                            [None],
                            dict(frame=dict(duration=0, redraw=False),
                                 mode="immediate",
                                 transition=dict(duration=0)),
                        ],
                    ),
                ],
            )
        ],
        sliders=[
            dict(
                currentvalue=dict(
                    prefix="Segment: ",
                    visible=True,
                    xanchor="center",
                    font=dict(size=12),
                ),
                pad=dict(t=55, b=10),
                steps=slider_steps,
            )
        ],
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig
