"""Shared shape and toolpath catalogs for the MiniSlicer UI."""

SHAPES = [
    "Rectangle",
    "Rounded Rectangle",
    "Circle",
    "Ellipse",
    "Triangle",
    "Regular Polygon",
    "Star",
    "Cross",
    "Capsule",
    "Arrow",
    "Custom Polygon",
]

PATTERNS = [
    "Parallel Lines",
    "Zigzag",
    "Grid",
    "Triangles",
    "Honeycomb",
    "Concentric",
]

SHAPE_ICONS = {
    "Rectangle": "[]",
    "Rounded Rectangle": "()",
    "Circle": "o",
    "Ellipse": "0",
    "Triangle": "^",
    "Regular Polygon": "hex",
    "Star": "*",
    "Cross": "+",
    "Capsule": "cap",
    "Arrow": "->",
    "Custom Polygon": "pen",
}

PATTERN_ICONS = {
    "Parallel Lines": "|||",
    "Zigzag": "zig",
    "Grid": "#",
    "Triangles": "tri",
    "Honeycomb": "hex",
    "Concentric": "O",
}
