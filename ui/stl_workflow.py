# Purpose: Handles JSON config re-apply, SVG/STL import controls, and multi-layer STL previews.
# Reason: Import workflow is separated because file handling has different state and validation needs.
"""STL import and multi-layer workflow controls."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from src.plotting import create_3d_figure, create_multilayer_animated_figure
from src.scenarios import overrides_from_export
from src.stl_import import load_stl_info, slice_stl_multi_layer
from src.toolpaths import generate_infill, generate_inward_perimeters, optimize_path_order


def render_import_controls() -> dict[str, Any]:
    uploaded_config = None
    imported_config: dict[str, Any] = {}
    uploaded_svg = None
    uploaded_stl = None
    stl_bytes: bytes | None = None
    stl_info = None
    stl_slice_z = 0.0

    with st.expander("Import (SVG / STL / config)", expanded=False, icon=":material/upload_file:"):
        st.caption("Optional - upload geometry to replace the built-in shape, or a JSON export to review.")
        uploaded_config = st.file_uploader("Review JSON export", type=["json"])
        if uploaded_config is not None:
            try:
                imported = json.loads(uploaded_config.read().decode("utf-8"))
                imported_config = imported.get("parameters", {}) if isinstance(imported, dict) else {}
                if imported_config:
                    st.json(imported_config, expanded=False)
                    mapped = overrides_from_export(imported_config)
                    if mapped:
                        st.caption(f"{len(mapped)} job parameters can be re-applied to the controls.")
                        if st.button(
                            "Apply parameters to controls",
                            icon=":material/playlist_add_check:",
                            help="Re-populate shape, toolpath, print, plate, and business controls from this export.",
                        ):
                            st.session_state["_overrides"] = mapped
                            st.rerun()
                    else:
                        st.caption("No re-applicable job parameters found in this export.")
                else:
                    st.warning("No 'parameters' section found in this JSON export.")
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Could not read config: {exc}")

        st.markdown("---")
        uploaded_svg = st.file_uploader("Import SVG shape", type=["svg"])
        svg_target_width = st.number_input("SVG target width (mm)", 5.0, value=80.0, step=5.0)
        uploaded_stl = st.file_uploader("Import STL mesh", type=["stl"])
        stl_target_width = st.number_input("STL target width (mm)", 5.0, value=80.0, step=5.0)
        if uploaded_svg is not None and uploaded_stl is not None:
            st.warning("Both SVG and STL loaded - STL slice takes priority.")
        if uploaded_stl is not None:
            try:
                stl_bytes = uploaded_stl.getvalue()
                stl_info = load_stl_info(stl_bytes)
                st.info(
                    f"**Mesh:** {stl_info.width:.1f} x {stl_info.depth:.1f} x "
                    f"{stl_info.height:.1f} mm  \n"
                    f"**Faces:** {stl_info.face_count:,}"
                )
                stl_slice_z = st.slider(
                    "Slice at Z (mm)",
                    min_value=float(stl_info.min_z),
                    max_value=float(stl_info.max_z),
                    value=float((stl_info.min_z + stl_info.max_z) / 2.0),
                    step=max(float(stl_info.height) / 100.0, 0.01),
                )
            except Exception as exc:  # noqa: BLE001
                st.warning(f"Could not inspect STL: {exc}")

    return {
        "uploaded_config": uploaded_config,
        "imported_config": imported_config,
        "uploaded_svg": uploaded_svg,
        "svg_target_width": svg_target_width,
        "uploaded_stl": uploaded_stl,
        "stl_target_width": stl_target_width,
        "stl_bytes": stl_bytes,
        "stl_info": stl_info,
        "stl_slice_z": stl_slice_z,
    }


def render_stl_multilayer_view(
    stl_bytes: bytes | None,
    stl_info: Any,
    stl_target_width: float,
    layer_height: float,
    perimeter_count: int,
    perimeter_spacing: float,
    infill_pattern: str,
    effective_spacing: float,
    effective_angle: float,
    optimize_infill: bool,
    reverse_lines: bool,
    color_scheme: str,
    shape: Any,
    layer_count: int,
) -> None:
    if stl_bytes is not None and stl_info is not None:
        st.subheader("STL Multi-Layer Build Simulation")
        ml1, ml2, ml3 = st.columns(3)
        ml_z_min = ml1.number_input(
            "Z min (mm)", value=float(stl_info.min_z),
            min_value=float(stl_info.min_z), max_value=float(stl_info.max_z), step=0.1,
        )
        ml_z_max = ml2.number_input(
            "Z max (mm)", value=float(stl_info.max_z),
            min_value=float(stl_info.min_z), max_value=float(stl_info.max_z), step=0.1,
        )
        ml_step = ml3.number_input(
            "Layer step (mm)", min_value=0.01, value=float(layer_height), step=0.01,
        )
        n_slices = max(1, int((ml_z_max - ml_z_min) / max(ml_step, 0.01)) + 1)
        st.info(f"**~{n_slices} slices** will be generated. Complex meshes may take a few seconds.")

        if st.button("Generate multi-layer animation", type="primary", key="btn_multilayer"):
            with st.spinner("Slicing STL and computing toolpaths..."):
                try:
                    ml_slices = slice_stl_multi_layer(
                        stl_bytes, z_min=float(ml_z_min), z_max=float(ml_z_max),
                        z_step=float(ml_step), target_width_mm=stl_target_width,
                    )
                    st.info(
                        f"Sliced {len(ml_slices)} layers from Z={ml_z_min:.2f} mm "
                        f"to Z={ml_z_max:.2f} mm (step: {ml_step:.2f} mm)"
                    )
                    ml_layers: list[tuple[float, list, list]] = []
                    for z_value, polygon in ml_slices:
                        perimeters = generate_inward_perimeters(
                            polygon, int(perimeter_count), float(perimeter_spacing),
                        )
                        infills = generate_infill(polygon, infill_pattern, effective_spacing, effective_angle)
                        if optimize_infill:
                            infills = optimize_path_order(infills, allow_reverse=reverse_lines)
                        ml_layers.append((z_value, perimeters, infills))
                    if ml_layers:
                        fig_ml = create_multilayer_animated_figure(ml_layers, color_scheme=color_scheme)
                        st.plotly_chart(fig_ml, width="stretch")
                        st.success(
                            f"Rendered **{len(ml_layers)} layers** "
                            f"from Z={ml_z_min:.2f} to Z={ml_z_max:.2f} mm."
                        )
                    else:
                        st.warning("No valid cross-sections found in the selected Z range.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Multi-layer slicing failed: {exc}")
        else:
            st.caption("Set the Z range and layer step above, then click **Generate multi-layer animation**.")
        return

    st.subheader("Shape Layer Stack")
    st.markdown("Render multiple layers of the current 2D shape stacked into a 3D view.")
    col_3d, _ = st.columns([1, 3])
    layer_count_3d = col_3d.slider(
        "Layers to stack", 1, 30, min(layer_count, 8),
        help="More layers = slower render.",
    )
    col_3d.caption(f"Height: {layer_count_3d * float(layer_height):.2f} mm")
    if st.button("Generate 3D view", type="primary"):
        with st.spinner("Rendering..."):
            fig_3d = create_3d_figure(
                shape, layer_count_3d, perimeter_count, perimeter_spacing,
                effective_spacing, layer_height, infill_pattern,
            )
        st.plotly_chart(fig_3d, width="stretch")
    else:
        st.info("Click **Generate 3D view** to render the layer stack.")
