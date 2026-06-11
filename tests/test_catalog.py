"""Tests for shared UI catalogs."""

from src.catalog import PATTERN_ICONS, PATTERNS, SHAPE_ICONS, SHAPES


def test_shape_catalog_has_icons_for_every_shape() -> None:
    assert SHAPES
    assert set(SHAPES) == set(SHAPE_ICONS)
    assert SHAPES[-1] == "Custom Polygon"


def test_pattern_catalog_has_icons_for_every_pattern() -> None:
    assert PATTERNS
    assert set(PATTERNS) == set(PATTERN_ICONS)
    assert "Honeycomb" in PATTERNS
