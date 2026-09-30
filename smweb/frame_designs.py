"""Geometry of the HUD frame designs in static/assets/frames/designs.json.

The browser preview (static/js/workshop-squares-fx.js, ``designGeometry``) reads the
same JSON and builds the same points. A design is a dark plate (even-odd filled
polygons) plus an outline that traces every plate edge except the panel border.

Roles make one design work for every showcase type: ``full`` puts ornament columns
on both sides (Featured, Workshop), ``left`` only on the left (Artwork Split 506 part)
and ``right`` only on the right (Split 100 part), so the two Split files together
look like one symmetric frame.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

DESIGNS_FILE = Path(__file__).resolve().parents[1] / "static" / "assets" / "frames" / "designs.json"
ROLES = ("full", "left", "right")
# Reference widths per role (Steam Artwork: 506 + 100; the 100 px part uses 118 so its ornament column leaves a window strip) and the
# height below which everything shrinks with the panel.
_FULL_WIDTH = 606.0
# Artwork Split: the side file is 100 Steam px wide. Its frame is the ornament column
# alone, filling the whole file; the 506 file gets the same column mirrored on its left.
SPLIT_SIDE = 100.0
_REF_HEIGHT = 260.0


@lru_cache(maxsize=1)
def _catalog() -> dict[str, dict]:
    data = json.loads(DESIGNS_FILE.read_text(encoding="utf-8"))
    return {design["id"]: design for design in data["designs"]}


def design_ids() -> tuple[str, ...]:
    return tuple(_catalog())


def unit(role: str, w: float, h: float, col: float = 70.0) -> float:
    """Design units per pixel. Split parts share one scale: the column is 100 Steam px."""
    if role == "left":
        return (w / 506.0) * SPLIT_SIDE / col
    if role == "right":
        return w / col
    return min(w / _FULL_WIDTH, h / _REF_HEIGHT)


def _coord(spec, origin: float, span: float, u: float) -> float:
    if isinstance(spec, list):
        return origin + spec[0] * span + spec[1] * u
    return origin + spec * u


def _stroke_polygon(points, thickness: float):
    """Outline polygon of a polyline with mitred joins and butt ends."""
    half = thickness / 2
    normals = []
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        length = math.hypot(bx - ax, by - ay) or 1.0
        normals.append((-(by - ay) / length, (bx - ax) / length))
    left, right = [], []
    for index, (px, py) in enumerate(points):
        if index == 0:
            nx, ny = normals[0]
            scale = half
        elif index == len(points) - 1:
            nx, ny = normals[-1]
            scale = half
        else:
            ax, ay = normals[index - 1]
            bx, by = normals[index]
            nx, ny = ax + bx, ay + by
            length = math.hypot(nx, ny) or 1.0
            nx, ny = nx / length, ny / length
            cosine = max(0.25, nx * ax + ny * ay)
            scale = half / cosine
        left.append((px + nx * scale, py + ny * scale))
        right.append((px - nx * scale, py - ny * scale))
    return left + right[::-1]


def _arc_points(cx: float, cy: float, radius: float, a0: float, a1: float):
    steps = max(6, int(abs(a1 - a0) / 6))
    return [(cx + radius * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
             cy + radius * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]


def geometry(design_id: str, rect, role: str = "full"):
    """[(kind, polygon)] of one panel: kind "poly" (even-odd) or "bar"/"arc" (union)."""
    design = _catalog()[design_id]
    x, y, w, h = rect
    u = unit(role, w, h, design["col"])
    col = design["col"] * u
    left_col = col if role in ("full", "left") else 0.0
    right_col = col if role in ("full", "right") else 0.0
    edge, gap = design.get("edge", 6) * u, design.get("gap", 0) * u
    wx0 = x + (left_col or edge) + gap
    wx1 = x + w - (right_col or edge) - gap
    boxes = {"P": (x, w), "W": (wx0, max(1.0, wx1 - wx0)), "L": (x, col)}

    def point(spec, box):
        origin, span = boxes[box]
        px = _coord(spec[0], origin, span, u)
        if box == "W" or (box == "L" and role != "full"):
            # Narrow windows squeeze their chamfers instead of overflowing, and on the
            # Split parts the ornament column never reaches into the picture.
            px = min(max(px, origin), origin + span)
        return px, _coord(spec[1], y, h, u)

    polygons = []
    has_window = wx1 - wx0 >= 2
    for item in design["items"]:
        if item["box"] == "W" and not has_window:
            continue  # the 100 px part is all frame
        copies = [False]
        if item["box"] == "L":
            copies = ([False] if left_col else []) + ([True] if right_col else [])
        for mirrored in copies:
            if item["kind"] == "arc":
                cx, cy = point(item["c"], item["box"])
                pts = _arc_points(cx, cy, item["r"] * u, *item["a"])
            else:
                pts = [point(spec, item["box"]) for spec in item["pts"]]
            if mirrored:
                pts = [(2 * x + w - px, py) for px, py in pts]
            if item["kind"] in ("bar", "arc"):
                pts = _stroke_polygon(pts, max(2.0, item.get("t", 5) * u))
            polygons.append((item["kind"], pts))
    return polygons


def geometry_parts(design_id: str, rect, role: str = "full"):
    """(even-odd polygons, unioned bar polygons, outline paths) of one panel."""
    items = geometry(design_id, rect, role)
    return ([pts for kind, pts in items if kind == "poly"],
            [pts for kind, pts in items if kind != "poly"],
            _outlines([pts for _kind, pts in items], rect))


def _on_border(a, b, rect, eps: float = 0.75) -> bool:
    x, y, w, h = rect
    for axis, value in ((0, x), (0, x + w), (1, y), (1, y + h)):
        if abs(a[axis] - value) <= eps and abs(b[axis] - value) <= eps:
            return True
    # Edges fully outside the panel are never visible either.
    return (max(a[0], b[0]) <= x + eps or min(a[0], b[0]) >= x + w - eps
            or max(a[1], b[1]) <= y + eps or min(a[1], b[1]) >= y + h - eps)


def _outlines(polygons, rect):
    paths = []
    for ring in polygons:
        count = len(ring)
        keep = [not _on_border(ring[i], ring[(i + 1) % count], rect) for i in range(count)]
        if all(keep):
            paths.append((list(ring), True))
            continue
        if not any(keep):
            continue
        start = keep.index(False)
        run = []
        for step in range(1, count + 1):
            index = (start + step) % count
            if keep[index]:
                if not run:
                    run.append(ring[index])
                run.append(ring[(index + 1) % count])
            elif run:
                paths.append((run, False))
                run = []
        if run:
            paths.append((run, False))
    return paths
