"""STL import and horizontal slicing helpers."""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon


@dataclass(frozen=True)
class StlInfo:
    """Basic mesh metadata used by the UI."""

    width: float
    depth: float
    height: float
    min_z: float
    max_z: float
    face_count: int


def load_stl_info(stl_bytes: bytes) -> StlInfo:
    """Return simple bounds and face-count metadata for an STL mesh."""
    mesh = _load_mesh(stl_bytes)
    min_x, min_y, min_z = mesh.bounds[0]
    max_x, max_y, max_z = mesh.bounds[1]
    return StlInfo(
        width=float(max_x - min_x),
        depth=float(max_y - min_y),
        height=float(max_z - min_z),
        min_z=float(min_z),
        max_z=float(max_z),
        face_count=int(len(mesh.faces)),
    )


def slice_stl_to_polygon(
    stl_bytes: bytes,
    z_height: float,
    target_width_mm: float | None = None,
    recenter_to_origin: bool = True,
) -> Polygon | None:
    """Slice an STL at a horizontal Z height and return the largest closed polygon.

    STL files are unitless. If ``target_width_mm`` is provided, the resulting
    2D section is scaled so its width matches that value.
    """
    mesh = _load_mesh(stl_bytes)
    return _slice_mesh_at_z(mesh, float(z_height), target_width_mm, recenter_to_origin)


def slice_stl_multi_layer(
    stl_bytes: bytes,
    z_min: float,
    z_max: float,
    z_step: float,
    target_width_mm: float | None = None,
    recenter_to_origin: bool = True,
) -> list[tuple[float, Polygon]]:
    """Slice an STL mesh at evenly-spaced Z heights and return ``(z, polygon)`` pairs.

    The mesh is loaded once and reused across all slices for efficiency.
    Only layers that yield a valid polygon cross-section are included.
    The returned list is sorted by ascending Z height.

    Args:
        stl_bytes: Raw STL file bytes.
        z_min: Lowest slice Z coordinate (inclusive).
        z_max: Highest slice Z coordinate (inclusive within one step).
        z_step: Distance between consecutive slice planes in mm.
        target_width_mm: If provided, scale each slice so its X width equals this value.
        recenter_to_origin: Translate each slice so its lower-left corner is at (0, 0).

    Raises:
        ValueError: if ``z_step`` is not positive.
    """
    if z_step <= 0:
        raise ValueError(f"z_step must be positive (got {z_step=})")

    mesh = _load_mesh(stl_bytes)
    z_heights = list(np.arange(float(z_min), float(z_max) + z_step * 0.5, float(z_step)))

    results: list[tuple[float, Polygon]] = []
    for z in z_heights:
        poly = _slice_mesh_at_z(mesh, z, target_width_mm, recenter_to_origin)
        if poly is not None:
            results.append((round(float(z), 6), poly))

    return results


# -- Internal helpers ----------------------------------------------------------

def _slice_mesh_at_z(
    mesh,
    z_height: float,
    target_width_mm: float | None,
    recenter_to_origin: bool,
) -> Polygon | None:
    """Slice a pre-loaded trimesh at ``z_height`` and return the largest polygon."""
    section = mesh.section(
        plane_origin=[0.0, 0.0, z_height],
        plane_normal=[0.0, 0.0, 1.0],
    )
    if section is None:
        return None

    path_2d, _ = section.to_2D()
    polygons = [
        poly for poly in path_2d.polygons_full
        if isinstance(poly, Polygon) and not poly.is_empty
    ]
    if not polygons:
        return None

    shape = max(polygons, key=lambda poly: poly.area)
    if not shape.is_valid:
        shape = shape.buffer(0)
    if shape.is_empty or not isinstance(shape, Polygon):
        return None

    if target_width_mm is not None and target_width_mm > 0:
        min_x, _, max_x, _ = shape.bounds
        current_width = max_x - min_x
        if current_width > 0:
            scale = float(target_width_mm) / current_width
            shape = affinity.scale(shape, xfact=scale, yfact=scale, origin=(min_x, 0.0))

    if recenter_to_origin:
        min_x, min_y, _, _ = shape.bounds
        shape = affinity.translate(shape, xoff=-min_x, yoff=-min_y)

    return shape


def _load_mesh(stl_bytes: bytes):
    try:
        import trimesh
    except ImportError as exc:  # pragma: no cover - dependency is installed in normal app use
        raise RuntimeError("STL import requires trimesh, scipy, and networkx.") from exc

    mesh = trimesh.load_mesh(io.BytesIO(stl_bytes), file_type="stl")
    if mesh is None or getattr(mesh, "is_empty", False):
        raise ValueError("The STL file did not contain a readable mesh.")
    return mesh
