"""Tests for STL import and slicing helpers."""

import trimesh

from src.stl_import import load_stl_info, slice_stl_to_polygon


def _box_stl_bytes() -> bytes:
    mesh = trimesh.creation.box(extents=(20.0, 10.0, 6.0))
    return trimesh.exchange.stl.export_stl(mesh)


def test_load_stl_info_reads_bounds() -> None:
    info = load_stl_info(_box_stl_bytes())
    assert info.width == 20.0
    assert info.depth == 10.0
    assert info.height == 6.0
    assert info.face_count > 0


def test_slice_stl_to_polygon_returns_section() -> None:
    poly = slice_stl_to_polygon(_box_stl_bytes(), z_height=0.0)
    assert poly is not None
    assert poly.area == 200.0


def test_slice_stl_to_polygon_can_scale_to_width() -> None:
    poly = slice_stl_to_polygon(_box_stl_bytes(), z_height=0.0, target_width_mm=40.0)
    assert poly is not None
    min_x, _, max_x, _ = poly.bounds
    assert max_x - min_x == 40.0
