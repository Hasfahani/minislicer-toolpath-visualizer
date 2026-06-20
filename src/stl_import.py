# Purpose: Reads STL metadata and slices meshes into horizontal 2D polygons for planning.
# Reason: STL support lets the app review real 3D geometry while keeping the planner 2D and understandable.
"""STL import and horizontal slicing helpers."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon

logger = logging.getLogger(__name__)

_SLICE_ERROR_MESSAGE = (
    "This STL slice could not be converted into a usable closed outline. "
    "Try a different slice height or repair the STL mesh."
)
_MIN_POLYGON_AREA = 1e-12


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
    if not getattr(mesh, "is_watertight", True):
        logger.warning(
            "Slicing a non-manifold or open STL mesh at Z=%.6f; attempting best-effort recovery.",
            z_height,
        )

    try:
        section = mesh.section(
            plane_origin=[0.0, 0.0, z_height],
            plane_normal=[0.0, 0.0, 1.0],
        )
    except Exception as exc:  # noqa: BLE001 - trimesh raises several geometry-specific exception types
        logger.warning("Trimesh could not intersect the STL at Z=%.6f: %s", z_height, exc)
        raise ValueError(_SLICE_ERROR_MESSAGE) from None

    if section is None:
        logger.info("STL slice at Z=%.6f is empty.", z_height)
        return None

    try:
        path_2d, _ = section.to_2D()
    except Exception as exc:  # noqa: BLE001 - edge-only and degenerate sections can fail conversion
        logger.warning("STL slice at Z=%.6f could not be projected to 2D: %s", z_height, exc)
        raise ValueError(_SLICE_ERROR_MESSAGE) from None

    polygons = _extract_slice_polygons(path_2d, z_height)
    if not polygons:
        # A plane touching only a vertex or edge has no closed area. This is a
        # valid empty slice, not an application error.
        logger.info("STL slice at Z=%.6f contains no usable closed polygons.", z_height)
        return None

    shape = max(polygons, key=lambda poly: poly.area)

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


def _extract_slice_polygons(path_2d, z_height: float) -> list[Polygon]:
    """Return valid slice polygons with graceful degradation when enclosure lookup fails."""
    full_error: Exception | None = None

    try:
        # polygons_full preserves enclosure relationships and therefore holes,
        # but trimesh may require optional rtree support to build that tree.
        polygons = _filter_polygons(path_2d.polygons_full)
        logger.info(
            "polygons_full succeeded for STL slice at Z=%.6f; %d valid polygons found.",
            z_height,
            len(polygons),
        )
        if polygons:
            return polygons
        logger.info(
            "polygons_full returned no usable polygons at Z=%.6f; trying polygons_closed.",
            z_height,
        )
    except Exception as exc:  # noqa: BLE001 - includes missing rtree and trimesh topology failures
        full_error = exc
        logger.warning(
            "polygons_full failed for STL slice at Z=%.6f (%s); using polygons_closed fallback.",
            z_height,
            exc,
        )

    try:
        # polygons_closed converts each closed path independently. It can lose
        # hole nesting, but avoids enclosure-tree computation and is a safe
        # best-effort fallback when polygons_full cannot run.
        polygons = _filter_polygons(path_2d.polygons_closed)
        logger.info(
            "polygons_closed fallback used for STL slice at Z=%.6f; %d valid polygons found.",
            z_height,
            len(polygons),
        )
        return polygons
    except Exception as closed_error:  # noqa: BLE001 - normalize trimesh internals for callers
        logger.error(
            "Both polygon extraction methods failed for STL slice at Z=%.6f "
            "(polygons_full=%s; polygons_closed=%s).",
            z_height,
            full_error or "returned no usable polygons",
            closed_error,
        )
        raise ValueError(_SLICE_ERROR_MESSAGE) from None


def _filter_polygons(candidates) -> list[Polygon]:
    """Keep only non-empty, valid polygons with meaningful positive area."""
    if candidates is None:
        return []

    polygons: list[Polygon] = []
    for polygon in candidates:
        if (
            isinstance(polygon, Polygon)
            and not polygon.is_empty
            and polygon.is_valid
            and float(polygon.area) > _MIN_POLYGON_AREA
        ):
            polygons.append(polygon)
    return polygons


def _load_mesh(stl_bytes: bytes):
    try:
        import trimesh
    except ImportError as exc:  # pragma: no cover - dependency is installed in normal app use
        raise RuntimeError("STL import requires trimesh, scipy, and networkx.") from exc

    if not stl_bytes:
        raise ValueError("The STL file did not contain a readable mesh.")

    try:
        mesh = trimesh.load_mesh(io.BytesIO(stl_bytes), file_type="stl")
    except Exception as exc:  # noqa: BLE001 - normalize parser-specific failures for the UI
        logger.warning("Trimesh could not read the uploaded STL: %s", exc)
        raise ValueError("The uploaded STL file is damaged or is not a readable STL mesh.") from None

    bounds = getattr(mesh, "bounds", None)
    if (
        mesh is None
        or getattr(mesh, "is_empty", False)
        or bounds is None
        or np.asarray(bounds).shape != (2, 3)
        or not np.isfinite(bounds).all()
    ):
        raise ValueError("The STL file did not contain a readable mesh.")
    return mesh
