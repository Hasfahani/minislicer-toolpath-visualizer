"""STL import and horizontal slicing helpers."""

from __future__ import annotations

import io
from dataclasses import dataclass

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
    section = mesh.section(plane_origin=[0.0, 0.0, float(z_height)], plane_normal=[0.0, 0.0, 1.0])
    if section is None:
        return None

    path_2d, _ = section.to_2D()
    polygons = [poly for poly in path_2d.polygons_full if isinstance(poly, Polygon) and not poly.is_empty]
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
