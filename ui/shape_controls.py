"""Shape parameter controls for the MiniSlicer sidebar."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_shape_controls(
    shapes: list[str],
    shape_icons: dict[str, str],
    disabled: bool,
) -> dict[str, Any]:
    with st.expander("Shape", expanded=True):
        shape_type = st.selectbox(
            "Shape type", shapes, index=0, disabled=disabled,
            format_func=lambda s: f"{shape_icons.get(s, '')} {s}",
            help="Disabled when an SVG or STL is imported above.",
        )

        settings: dict[str, Any] = {
            "shape_type": shape_type,
            "width": 50.0,
            "height": 30.0,
            "radius": 22.0,
            "corner_radius": 5.0,
            "sides": 6,
            "points": 5,
            "inner_radius": 10.0,
            "size": 42.0,
            "arm_width": 14.0,
            "length": 54.0,
            "head_width": 24.0,
            "shaft_width": 10.0,
            "coords_text": "0,0; 50,0; 40,25; 10,35",
        }

        if shape_type in ("Rectangle", "Ellipse", "Triangle", "Capsule"):
            c1, c2 = st.columns(2)
            settings["width"] = c1.number_input("Width (mm)", 1.0, value=50.0, step=1.0)
            settings["height"] = c2.number_input("Height (mm)", 1.0, value=30.0, step=1.0)

        elif shape_type == "Rounded Rectangle":
            c1, c2 = st.columns(2)
            settings["width"] = c1.number_input("Width (mm)", 1.0, value=50.0, step=1.0)
            settings["height"] = c2.number_input("Height (mm)", 1.0, value=30.0, step=1.0)
            max_radius = max(0.1, min(settings["width"], settings["height"]) / 2.0 - 0.1)
            settings["corner_radius"] = st.slider(
                "Corner radius (mm)", 0.0, float(max_radius), min(5.0, float(max_radius)), 0.5,
            )

        elif shape_type == "Circle":
            settings["radius"] = st.number_input("Radius (mm)", 1.0, value=22.0, step=1.0)

        elif shape_type == "Regular Polygon":
            c1, c2 = st.columns(2)
            settings["radius"] = c1.number_input("Radius (mm)", 1.0, value=22.0, step=1.0)
            settings["sides"] = c2.slider("Sides", 3, 16, 6)

        elif shape_type == "Star":
            c1, c2 = st.columns(2)
            settings["radius"] = c1.number_input("Outer radius (mm)", 1.0, value=22.0, step=1.0)
            settings["inner_radius"] = c2.number_input("Inner radius (mm)", 0.5, value=10.0, step=0.5)
            settings["points"] = st.slider("Points", 3, 12, 5)

        elif shape_type == "Cross":
            c1, c2 = st.columns(2)
            settings["size"] = c1.number_input("Size (mm)", 1.0, value=42.0, step=1.0)
            settings["arm_width"] = c2.number_input("Arm width (mm)", 0.5, value=14.0, step=0.5)

        elif shape_type == "Arrow":
            c1, c2 = st.columns(2)
            settings["length"] = c1.number_input("Length (mm)", 1.0, value=54.0, step=1.0)
            settings["head_width"] = c2.number_input("Head width (mm)", 1.0, value=24.0, step=1.0)
            settings["shaft_width"] = st.number_input(
                "Shaft width (mm)", 0.5, value=min(10.0, settings["head_width"] - 0.1), step=0.5,
            )

        elif shape_type == "Custom Polygon":
            settings["coords_text"] = st.text_area(
                "Vertices  (x,y; x,y; ...)",
                value="0,0; 50,0; 40,25; 10,35",
                help="Separate each point with a semicolon.",
            )

    return settings
