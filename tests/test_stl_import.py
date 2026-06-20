# Purpose: Tests STL metadata loading and horizontal mesh slicing into polygons.
# Reason: STL import is a high-risk dependency path, so it is checked with a generated mesh fixture.
"""Tests for STL import and slicing helpers."""

import logging

import pytest
import trimesh
from shapely.geometry import Polygon

from src.stl_import import (
    _extract_slice_polygons,
    _filter_polygons,
    _slice_mesh_at_z,
    load_stl_info,
    slice_stl_to_polygon,
)


def _box_stl_bytes() -> bytes:
    mesh = trimesh.creation.box(extents=(20.0, 10.0, 6.0))
    return trimesh.exchange.stl.export_stl(mesh)


def test_load_stl_info_reads_bounds() -> None:
    info = load_stl_info(_box_stl_bytes())
    assert info.width == 20.0
    assert info.depth == 10.0
    assert info.height == 6.0
    assert info.face_count > 0


def test_invalid_stl_raises_clean_value_error() -> None:
    with pytest.raises(ValueError, match="damaged|readable mesh") as error:
        load_stl_info(b"this is not an STL file")

    assert error.value.__cause__ is None


def test_slice_stl_to_polygon_returns_section() -> None:
    poly = slice_stl_to_polygon(_box_stl_bytes(), z_height=0.0)
    assert poly is not None
    assert poly.area == 200.0


def test_slice_stl_to_polygon_can_scale_to_width() -> None:
    poly = slice_stl_to_polygon(_box_stl_bytes(), z_height=0.0, target_width_mm=40.0)
    assert poly is not None
    min_x, _, max_x, _ = poly.bounds
    assert max_x - min_x == 40.0


def test_polygons_full_preserves_holes(caplog: pytest.LogCaptureFixture) -> None:
    polygon_with_hole = Polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10)],
        holes=[[(2, 2), (8, 2), (8, 8), (2, 8)]],
    )
    path = _FakePath(polygons_full=[polygon_with_hole], polygons_closed=[])

    with caplog.at_level(logging.INFO):
        polygons = _extract_slice_polygons(path, z_height=1.5)

    assert polygons == [polygon_with_hole]
    assert len(polygons[0].interiors) == 1
    assert "polygons_full succeeded" in caplog.text
    assert "1 valid polygons found" in caplog.text


def test_polygons_closed_is_used_when_polygons_full_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fallback_polygon = Polygon([(0, 0), (4, 0), (4, 3), (0, 3)])
    path = _FakePath(
        polygons_full=ModuleNotFoundError("No module named 'rtree'"),
        polygons_closed=[fallback_polygon],
    )

    with caplog.at_level(logging.INFO):
        polygons = _extract_slice_polygons(path, z_height=2.0)

    assert polygons == [fallback_polygon]
    assert "polygons_full failed" in caplog.text
    assert "polygons_closed fallback used" in caplog.text
    assert "1 valid polygons found" in caplog.text


def test_polygon_filter_rejects_none_empty_invalid_and_zero_area() -> None:
    valid = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
    invalid = Polygon([(0, 0), (2, 2), (0, 2), (2, 0)])
    zero_area = Polygon([(0, 0), (1, 0), (2, 0)])

    assert _filter_polygons([None, Polygon(), invalid, zero_area, valid]) == [valid]


def test_both_polygon_methods_fail_with_clean_value_error() -> None:
    path = _FakePath(
        polygons_full=RuntimeError("internal enclosure tree failure"),
        polygons_closed=RuntimeError("internal path conversion failure"),
    )

    with pytest.raises(ValueError, match="could not be converted into a usable closed outline") as error:
        _extract_slice_polygons(path, z_height=3.0)

    assert error.value.__cause__ is None
    assert "enclosure tree" not in str(error.value)


def test_empty_slice_returns_none() -> None:
    mesh = _FakeMesh(section=None)

    assert _slice_mesh_at_z(mesh, 20.0, target_width_mm=None, recenter_to_origin=True) is None


def test_edge_only_slice_returns_none() -> None:
    path = _FakePath(polygons_full=[], polygons_closed=[])
    mesh = _FakeMesh(section=_FakeSection(path))

    assert _slice_mesh_at_z(mesh, 0.0, target_width_mm=None, recenter_to_origin=True) is None


def test_non_manifold_mesh_is_sliced_best_effort(caplog: pytest.LogCaptureFixture) -> None:
    polygon = Polygon([(5, 7), (9, 7), (9, 10), (5, 10)])
    path = _FakePath(polygons_full=[polygon], polygons_closed=[])
    mesh = _FakeMesh(section=_FakeSection(path), is_watertight=False)

    with caplog.at_level(logging.WARNING):
        result = _slice_mesh_at_z(mesh, 0.0, target_width_mm=8.0, recenter_to_origin=True)

    assert result is not None
    assert result.bounds == (0.0, 0.0, 8.0, 6.0)
    assert "non-manifold or open STL mesh" in caplog.text


class _FakePath:
    def __init__(self, polygons_full, polygons_closed):
        self._polygons_full = polygons_full
        self._polygons_closed = polygons_closed

    @property
    def polygons_full(self):
        if isinstance(self._polygons_full, Exception):
            raise self._polygons_full
        return self._polygons_full

    @property
    def polygons_closed(self):
        if isinstance(self._polygons_closed, Exception):
            raise self._polygons_closed
        return self._polygons_closed


class _FakeSection:
    def __init__(self, path):
        self.path = path

    def to_2D(self):
        return self.path, None


class _FakeMesh:
    def __init__(self, section, is_watertight=True):
        self._section = section
        self.is_watertight = is_watertight

    def section(self, plane_origin, plane_normal):
        assert plane_origin[2] == pytest.approx(float(plane_origin[2]))
        assert plane_normal == [0.0, 0.0, 1.0]
        return self._section
