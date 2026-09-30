"""Frames and effects for the Workshop "5 squares" layout.

The browser preview (static/js/workshop-squares-fx.js) implements the same
formulas, so the downloaded files match what the user saw. Everything is a
function of ``u`` in [0, 1): the position inside one loop. Every motion makes a
whole number of cycles per loop, so the resulting GIF loops without a jump.

Coordinates are in strip pixels: the strip is 750x150 (five 150x150 squares).
"""
from __future__ import annotations

import colorsys
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from smweb import frame_designs

W, H, SQUARE = 750, 150, 150
STATIC_FRAMES = {"none", "solid", "double", "corners", "neon"}
ANIMATED_FRAMES = {"rgb", "comet", "pulse", "dashes", "shimmer", "grain"}
FRAME_STYLES = STATIC_FRAMES | ANIMATED_FRAMES
# Outline geometry; the style above paints it. "rect" is the classic rectangle.
FRAME_SHAPES = ("rect", "bevel", "notch") + frame_designs.design_ids()
PLATE_RGB = (4, 6, 11)
TEXTURE_EFFECTS = {"petals", "snow", "rain", "lightning"}
EFFECTS = {"none", "particle", "sparks", "stars", "streaks", "matrix"} | TEXTURE_EFFECTS
TEXTURES = Path(__file__).resolve().parents[1] / "static" / "assets" / "builder" / "effects"
MATRIX_CHARS = "0123456789ABCDEF"

# Same deterministic particle table as the Builder.
PARTICLES = [((i * 79 % 101) / 100, (i * 47 % 97) / 96, 1 + i % 4, i % 3) for i in range(74)]


def _color(value, fallback: str) -> str:
    text = str(value or "").strip()
    if len(text) == 7 and text.startswith("#"):
        try:
            int(text[1:], 16)
            return text.lower()
        except ValueError:
            pass
    return fallback


def _number(value, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(low, min(high, number))


def normalize(raw: dict | None, legacy_outline: bool = False) -> dict:
    """Validate client options. ``legacy_outline`` maps the old checkbox."""
    raw = raw if isinstance(raw, dict) else {}
    frame = raw.get("frame") if isinstance(raw.get("frame"), dict) else {}
    effect = raw.get("effect") if isinstance(raw.get("effect"), dict) else {}
    style = str(frame.get("style") or ("solid" if legacy_outline else "none"))
    kind = str(effect.get("type") or "none")
    shape = str(frame.get("shape") or "rect")
    return {
        "frame": {
            "style": style if style in FRAME_STYLES else "none",
            "shape": shape if shape in FRAME_SHAPES else "rect",
            "plate": int(_number(frame.get("plate"), 0, 0, 100)),
            "color": _color(frame.get("color"), "#8de9ff"),
            "color2": _color(frame.get("color2"), "#8a62ff"),
            "width": int(_number(frame.get("width"), 2 if legacy_outline else 3, 1, 10)),
            "speed": int(_number(frame.get("speed"), 1, 1, 4)),
            "target": "strip" if frame.get("target") == "strip" else "squares",
        },
        "effect": {
            "type": kind if kind in EFFECTS else "none",
            "color": _color(effect.get("color"), "#ff9fc8"),
            "speed": _number(effect.get("speed"), 100, 50, 300),
            "density": _number(effect.get("density"), 100, 25, 200),
            "opacity": _number(effect.get("opacity"), 90, 10, 100),
        },
    }


def is_animated(fx: dict) -> bool:
    return fx["frame"]["style"] in ANIMATED_FRAMES or fx["effect"]["type"] != "none"


def is_empty(fx: dict) -> bool:
    return fx["frame"]["style"] == "none" and fx["effect"]["type"] == "none"


def _rgb(hex_color: str) -> tuple[int, int, int]:
    return int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)


def _mix(a, b, t: float) -> tuple[int, int, int]:
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


# ------------------------------------------------------------------ effects
@lru_cache(maxsize=24)
def _texture(name: str, color: str, tile_width: int) -> Image.Image:
    """Builder texture, tinted like the Builder does, scaled to one tile."""
    with Image.open(TEXTURES / f"{name}.png") as opened:
        source = opened.convert("RGBA")
    height = max(1, round(tile_width * source.height / source.width))
    source = source.resize((tile_width, height), Image.Resampling.LANCZOS)
    alpha = source.getchannel("A")
    solid = Image.new("RGBA", source.size, (*_rgb(color), 255))
    tinted = Image.blend(source, solid, 0.48)
    tinted.putalpha(alpha)
    original = source.copy()
    original.putalpha(alpha.point(lambda value: int(value * 0.42)))
    return Image.alpha_composite(tinted, original)


def _tile(layer: Image.Image, texture: Image.Image, offset_x: float, offset_y: float, alpha: float) -> None:
    if alpha <= 0:
        return
    tile = texture
    if alpha < 1:
        tile = texture.copy()
        tile.putalpha(texture.getchannel("A").point(lambda value: int(value * alpha)))
    tw, th = tile.size
    start_x = int(math.floor(offset_x % tw)) - tw
    start_y = int(math.floor(offset_y % th)) - th
    for x in range(start_x, W, tw):
        for y in range(start_y, H, th):
            # alpha_composite needs a non-negative destination: crop the source instead.
            layer.alpha_composite(tile, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))


def _effect(base: Image.Image, u: float, effect: dict) -> Image.Image:
    kind = effect["type"]
    if kind == "none":
        return base
    speed = effect["speed"] / 100
    density = effect["density"] / 100
    opacity = effect["opacity"] / 100
    color = _rgb(effect["color"])
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tau = math.tau

    if kind in {"petals", "snow", "rain"}:
        rain = kind == "rain"
        passes = 3 if density > 1.35 else (2 if density > 0.65 else 1)
        base_cycles = max(1, round(speed * (3 if rain else 1)))
        for index in range(passes):
            tile_width = round((478 if rain else 531) * (1 + index * 0.14))
            texture = _texture(kind, effect["color"], tile_width)
            th = texture.height
            offset_y = (u * (base_cycles + index) * th + index * th * 0.47) % th
            drift = -W * 0.04 if rain else (0.055 * math.sin(tau * (u + index * 0.33)) - 0.09) * W
            _tile(layer, texture, drift, offset_y, opacity * min(1.0, 0.42 + density * 0.22 - index * 0.08))
        return Image.alpha_composite(base, layer)

    if kind == "lightning":
        cycles = max(1, round(speed))
        pulse = ((u * cycles) % 1) * 3.7
        flash = 1 if pulse < 0.12 else (0.38 if pulse < 0.22 else (0.68 if 0.36 < pulse < 0.43 else 0))
        if not flash:
            return base
        texture = _texture("lightning", effect["color"], 765)
        _tile(layer, texture, W * 0.013, H * 0.017, 1.0)
        strength = opacity * flash * min(1.0, 0.48 + density * 0.34)
        glow = layer.filter(ImageFilter.GaussianBlur(3))
        light = Image.alpha_composite(glow, layer)
        light.putalpha(light.getchannel("A").point(lambda value: int(value * strength)))
        rgb = base.convert("RGB")
        lit = ImageChops.screen(rgb, Image.composite(light.convert("RGB"), Image.new("RGB", (W, H)), light.getchannel("A")))
        result = lit.convert("RGBA")
        result.putalpha(base.getchannel("A"))
        return result

    count = max(8, min(len(PARTICLES), round(len(PARTICLES) * density)))
    draw = ImageDraw.Draw(layer)
    glow_radius = 2.0
    if kind in {"particle", "sparks"}:
        direction = -1 if kind == "sparks" else 1
        for index, (px, py, radius, lane) in enumerate(PARTICLES[:count]):
            cycles = max(1, round((1 + lane) * speed))
            y = ((py + direction * cycles * u) % 1) * H
            x = (px + 0.02 * math.sin(tau * (u + py))) * W
            alpha = 1.0
            if kind == "sparks":
                alpha = 0.55 + 0.45 * (0.5 + 0.5 * math.cos(tau * (cycles * u + px * 3)))
            r = radius * (0.7 if kind == "sparks" else 0.9)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*color, int(255 * opacity * alpha)))
        glow_radius = 3.0 if kind == "sparks" else 2.0
    elif kind == "stars":
        drift = max(1, round(speed))
        for index, (px, py, radius, lane) in enumerate(PARTICLES[:count]):
            x = ((px + u * drift) % 1) * W
            y = py * H
            twinkle = 0.35 + 0.65 * (0.5 + 0.5 * math.cos(tau * (2 * u + px * 7)))
            r = radius * 0.6
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*color, int(255 * opacity * twinkle)))
        glow_radius = 3.5
    elif kind == "streaks":
        for index, (px, py, radius, lane) in enumerate(PARTICLES[:min(count, 30)]):
            cycles = max(1, round((1 + lane) * speed))
            x = ((px + cycles * u) % 1) * W
            y = py * H
            draw.line((x, y, x + 42, y - 27), fill=(*color, int(255 * opacity)), width=2)
    elif kind == "matrix":
        font = _matrix_font()
        step = int(u * 12)
        for index, (px, py, radius, lane) in enumerate(PARTICLES[:min(count, 44)]):
            cycles = max(1, round((1 + lane) * speed))
            x = px * W
            y = ((py + cycles * u) % 1) * H
            char = MATRIX_CHARS[(index * 17 + step) % len(MATRIX_CHARS)]
            draw.text((x, y), char, font=font, fill=(*color, int(255 * opacity)), anchor="mm")
    glow = layer.filter(ImageFilter.GaussianBlur(glow_radius))
    return Image.alpha_composite(Image.alpha_composite(base, glow), layer)


@lru_cache(maxsize=1)
def _matrix_font():
    try:
        return ImageFont.load_default(size=12)
    except TypeError:
        return ImageFont.load_default()


# ------------------------------------------------------------------- frames
def _rects(target: str, size: tuple[int, int] = (W, H)) -> list[tuple[int, int, int, int]]:
    """Five Workshop panels (or the whole image) of an image of any size."""
    width, height = size
    if target == "strip":
        return [(0, 0, width, height)]
    edges = [index * width // 5 for index in range(6)]
    return [(edges[index], 0, edges[index + 1] - edges[index], height) for index in range(5)]


def _perimeter(rect, width: int):
    """Clockwise path points around the rectangle, plus its total length."""
    x, y, w, h = rect
    half = width / 2
    x0, y0, x1, y1 = x + half, y + half, x + w - half, y + h - half
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 2 * ((x1 - x0) + (y1 - y0))


def _point(corners, length: float, distance: float) -> tuple[float, float]:
    distance %= length
    for index in range(4):
        (ax, ay), (bx, by) = corners[index], corners[(index + 1) % 4]
        side = abs(bx - ax) + abs(by - ay)
        if distance <= side:
            t = distance / side if side else 0
            return ax + (bx - ax) * t, ay + (by - ay) * t
        distance -= side
    return corners[0]


def _segments(draw: ImageDraw.ImageDraw, rect, width: int, color_at, step: float = 2.0) -> None:
    corners, length = _perimeter(rect, width)
    count = max(8, min(600, int(length / step)))
    for index in range(count):
        position = index / count
        color = color_at(position, position * length)
        if color is None:
            continue
        a = _point(corners, length, position * length)
        b = _point(corners, length, (index + 1) / count * length)
        draw.line((a, b), fill=color, width=width)


# ------------------------------------------------------------ shaped frames
# A shaped frame is a dark plate (even-odd polygons plus unioned bars) and an
# outline along the plate edges. "rect"/"bevel"/"notch" are simple windows; the
# other shapes are HUD designs from static/assets/frames/designs.json
# (smweb.frame_designs), placed per panel role: "full" (ornaments on both
# sides) or "left"/"right" (the two Artwork Split files).
# static/js/workshop-squares-fx.js mirrors all of this for the live preview.
def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _bevel(x0, y0, x1, y1, c):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
            (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def _window_shapes(shape: str, rect, width: int):
    """Windows of the simple shapes (rect, bevel, notch)."""
    x, y, w, h = rect
    half = width / 2
    x0, y0, x1, y1 = x + half, y + half, x + w - half, y + h - half
    bw, bh = max(1.0, x1 - x0), max(1.0, y1 - y0)
    k = min(bw, bh)
    c = _clamp(k * 0.12, 3, 60)
    if shape == "bevel":
        return [_bevel(x0, y0, x1, y1, c)]
    if shape == "notch":
        s = c * 0.5
        d = _clamp(k * 0.07, 2, 26)
        half_notch = min(bw * 0.17, k * 0.45, bw / 2 - s - d - 1)
        if half_notch < 2:
            return [_bevel(x0, y0, x1, y1, s)]
        mx = (x0 + x1) / 2
        return [[(x0 + s, y0), (mx - half_notch - d, y0), (mx - half_notch, y0 + d),
                 (mx + half_notch, y0 + d), (mx + half_notch + d, y0), (x1 - s, y0), (x1, y0 + s),
                 (x1, y1 - s), (x1 - s, y1), (mx + half_notch + d, y1), (mx + half_notch, y1 - d),
                 (mx - half_notch, y1 - d), (mx - half_notch - d, y1), (x0 + s, y1), (x0, y1 - s), (x0, y0 + s)]]
    return [[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]]


def panel_geometry(shape: str, rect, width: int, role: str = "full"):
    """(even-odd polygons, unioned bar polygons, outline paths) of one panel."""
    if shape in frame_designs.design_ids():
        return frame_designs.geometry_parts(shape, rect, role)
    windows = _window_shapes(shape, rect, width)
    x, y, w, h = rect
    return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]] + windows, [], [(win, True) for win in windows]


def shape_paths(shape: str, rect, width: int, role: str = "full"):
    """Outline paths of one panel, each (points, closed)."""
    return panel_geometry(shape, rect, width, role)[2]


def _path_metrics(points, closed: bool):
    pts = list(points) + ([points[0]] if closed else [])
    lengths = [math.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(pts, pts[1:])]
    return pts, lengths, sum(lengths)


def _path_point(points, closed: bool, distance: float):
    pts, lengths, total = _path_metrics(points, closed)
    if total <= 0:
        return pts[0]
    distance = distance % total if closed else _clamp(distance, 0, total)
    for (ax, ay), (bx, by), length in zip(pts, pts[1:], lengths):
        if distance <= length:
            t = distance / length if length else 0
            return ax + (bx - ax) * t, ay + (by - ay) * t
        distance -= length
    return pts[-1]


def _hash01(i: int, j: int) -> float:
    """Deterministic noise in [0, 1); identical integer math in the browser."""
    n = (i * 7919 + j * 104729 + 13) % 65521
    n = (n * n * 31 + n * 17) % 65521
    return n / 65521


# Outline textures measured on the reference animations (2 s loops, 24 fps):
# "shimmer" (animation 1) = soft light patches ~80-160 px that slowly morph,
# "grain" (animation 2) = fine 10-15 px grain that flickers. Value noise in
# image space and loop time; the time lattice is periodic, so u=1 equals u=0.
# Octaves: (cell x, cell y, time cells per loop); weights; contrast.
OUTLINE_TEXTURES = {
    "shimmer": (((75, 170, 3), (36, 80, 3)), (0.68, 0.32), 1.35),
    "grain": (((10, 16, 10), (4.5, 7, 10)), (0.6, 0.4), 2.2),
}


def _hash3(i, j, k):
    """numpy version of the browser's integer hash (i, j, k: int64 arrays)."""
    import numpy as np
    n = (i * 7919 + j * 104729 + k * 1299709 + 13) % 65521
    n = (n * n * 31 + n * 17) % 65521
    return n.astype(np.float64) / 65521


def _value_noise(gx, gy, gt, period: int):
    import numpy as np
    ix, iy, it = np.floor(gx).astype(np.int64), np.floor(gy).astype(np.int64), np.floor(gt).astype(np.int64)
    fx, fy, ft = gx - ix, gy - iy, gt - it
    sx, sy, st = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), ft * ft * (3 - 2 * ft)
    t0, t1 = it % period, (it + 1) % period
    result = 0.0
    for layer_t, weight in ((t0, 1 - st), (t1, st)):
        top = _hash3(ix, iy, layer_t) * (1 - sx) + _hash3(ix + 1, iy, layer_t) * sx
        bottom = _hash3(ix, iy + 1, layer_t) * (1 - sx) + _hash3(ix + 1, iy + 1, layer_t) * sx
        result = result + (top * (1 - sy) + bottom * sy) * weight
    return result


def texture_level(style: str, xs, ys, u: float, scale: float, speed: int):
    """Brightness 0..1 of the outline texture at image pixels (xs, ys)."""
    import numpy as np
    octaves, weights, contrast = OUTLINE_TEXTURES[style]
    value = 0.0
    for (cell_x, cell_y, cells), weight in zip(octaves, weights):
        period = int(cells * max(1, speed))
        value = value + weight * _value_noise(np.asarray(xs, dtype=np.float64) / (cell_x * scale),
                                              np.asarray(ys, dtype=np.float64) / (cell_y * scale),
                                              (u % 1) * period, period)
    value = np.clip((value - 0.5) * contrast + 0.5, 0, 1)
    return 0.12 + 0.8 * value * value * (3 - 2 * value)


def _style_color(style, frame, u, shift, color, color2):
    """color_at(position, distance) for the styles that paint along the path."""
    cycles = frame["speed"]
    if style == "rgb":
        def color_at(position, _distance):
            r, g, b = colorsys.hsv_to_rgb((position + shift - cycles * u) % 1, 1.0, 1.0)
            return int(r * 255), int(g * 255), int(b * 255), 255
        return color_at
    if style == "comet":
        heads = [(cycles * u + shift) % 1, (cycles * u + shift + 0.5) % 1]
        tail = 0.34

        def color_at(position, _distance):
            distance = min((head - position) % 1 for head in heads)
            if distance > tail:
                return (*_mix(color, (0, 0, 0), 0.45), 70)
            strength = (1 - distance / tail) ** 0.85
            tone = _mix(color2, color, strength)
            if distance < 0.03:
                tone = _mix(tone, (255, 255, 255), 0.7)
            return (*tone, int(90 + 165 * strength))
        return color_at
    if style == "dashes":
        offset = u * cycles * 14 * 6
        return lambda _p, distance: (*color, 255) if (distance - offset) % 14 < 8 else (*color2, 90)
    return None


def _stroke_path(draw, points, closed, width, color_at, step: float = 2.0) -> None:
    pts, lengths, total = _path_metrics(points, closed)
    if total <= 0:
        return
    walked = 0.0
    radius = width / 2
    for (ax, ay), (bx, by), length in zip(pts, pts[1:], lengths):
        count = max(1, int(math.ceil(length / step)))
        for index in range(count):
            d0 = walked + length * index / count
            fill = color_at(d0 / total, d0)
            if fill is None:
                continue
            t0, t1 = index / count, (index + 1) / count
            draw.line(((ax + (bx - ax) * t0, ay + (by - ay) * t0), (ax + (bx - ax) * t1, ay + (by - ay) * t1)),
                      fill=fill, width=width)
        # Round joint so thick lines have no notch at the corners.
        if width >= 3:
            fill = color_at(((walked + length) % total) / total if closed else min(1.0, (walked + length) / total),
                            walked + length)
            if fill is not None and (closed or walked + length < total):
                draw.ellipse((bx - radius, by - radius, bx + radius, by + radius), fill=fill)
        walked += length


def _corner_mask(points, closed, size):
    """Filter for the "corners" style: only near the vertices."""
    _pts, lengths, total = _path_metrics(points, closed)
    marks = [0.0]
    for length in lengths:
        marks.append(marks[-1] + length)

    def near(distance):
        return min(abs(distance - mark) for mark in marks) <= size or (closed and total - distance <= size)
    return near


@lru_cache(maxsize=64)
def _panel_masks(shape: str, size: tuple[int, int], width: int, role: str):
    """(plate alpha, interior) of one panel, drawn 2x for smooth diagonals.

    The interior (plate shrunk by about the line width) hides outline parts that
    run inside the plate where bars overlap, so the line follows the contour.
    """
    import numpy as np
    w, h = size
    if role == "right" and shape in frame_designs.design_ids():
        # The 100 px Split file is the left file's ornament column, flipped pixel for
        # pixel, so both sides of the pair match exactly.
        left_width = max(w, round(w * 506 / frame_designs.SPLIT_SIDE))
        plate, interior = _panel_masks(shape, (left_width, h), width, "left")
        flip = Image.Transpose.FLIP_LEFT_RIGHT
        return plate.crop((0, 0, w, h)).transpose(flip), interior.crop((0, 0, w, h)).transpose(flip)
    even_odd, bars, _paths = panel_geometry(shape, (0, 0, w, h), width, role)
    scale = 2
    parity = np.zeros((h * scale, w * scale), dtype=bool)
    for polygon in even_odd:
        layer = Image.new("1", (w * scale, h * scale), 0)
        ImageDraw.Draw(layer).polygon([(px * scale, py * scale) for px, py in polygon], fill=1)
        parity ^= np.asarray(layer, dtype=bool)
    union = Image.new("1", (w * scale, h * scale), 0)
    union_draw = ImageDraw.Draw(union)
    for polygon in bars:
        union_draw.polygon([(px * scale, py * scale) for px, py in polygon], fill=1)
    solid = parity | np.asarray(union, dtype=bool)
    big = Image.fromarray((solid * 255).astype(np.uint8), "L")
    plate = big.resize((w, h), Image.Resampling.BOX)
    grow = min(31, (int(width) * 2 + 3) * 2 + 1)
    interior = big.filter(ImageFilter.MinFilter(grow)).resize((w, h), Image.Resampling.BOX)
    if role == "full" and shape in frame_designs.design_ids():
        # Designs are symmetric: copy the left half onto the right, pixel for pixel, so
        # both ornament columns match exactly (the Split cut shows them side by side).
        plate, interior = _mirror_left_half(plate), _mirror_left_half(interior)
    return plate, interior


def _mirror_left_half(mask: Image.Image) -> Image.Image:
    import numpy as np
    data = np.asarray(mask).copy()
    half = data.shape[1] // 2
    data[:, data.shape[1] - half:] = data[:, :half][:, ::-1]
    return Image.fromarray(data, mask.mode)


def _panel_frame(panel: Image.Image, offset, u: float, frame: dict, role: str, index: int, scale: float) -> Image.Image:
    """Plate and outline on one panel crop (the outline never leaves the panel)."""
    import numpy as np
    style = frame["style"]
    width = frame["width"]
    color = _rgb(frame["color"])
    color2 = _rgb(frame["color2"])
    cycles = frame["speed"]
    w, h = panel.size
    plate_mask, interior = _panel_masks(frame["shape"], (w, h), width, role)
    level = frame.get("plate", 0) / 100
    if level > 0:
        plate = Image.new("RGBA", (w, h), (*PLATE_RGB, 0))
        plate.putalpha(plate_mask.point(lambda value: int(value * level)))
        panel = Image.alpha_composite(panel, plate)
    _even_odd, _bars, paths = panel_geometry(frame["shape"], (0, 0, w, h), width, role)
    keep = 1 - np.asarray(interior, dtype=np.float64) / 255
    shift = index * 0.2 if frame["target"] == "squares" else 0.0
    pulse = 0.5 + 0.5 * math.cos(math.tau * cycles * u) if style == "pulse" else 1.0
    if style in OUTLINE_TEXTURES or style in {"solid", "neon", "pulse", "double"}:
        # One mask for all outlines, coloured by the texture or a flat colour.
        big = Image.new("L", (w * 2, h * 2), 0)
        mask_draw = ImageDraw.Draw(big)
        for points, closed in paths:
            pts = [(px * 2, py * 2) for px, py in points]
            if closed:
                pts.append(pts[0])
            mask_draw.line(pts, fill=255, width=width * 2, joint="curve")
        mask = np.asarray(big.resize((w, h), Image.Resampling.BOX), dtype=np.float64) / 255 * keep
        rgba = np.zeros((h, w, 4), dtype=np.float64)
        if style in OUTLINE_TEXTURES:
            ys, xs = np.nonzero(mask > 0)
            light = texture_level(style, xs + offset[0], ys + offset[1], u, scale, cycles)
            base = np.array(color, dtype=np.float64)
            tone = base[None, :] * (light[:, None] * 1.25) + 255 * np.clip(light - 0.72, 0, 1)[:, None] * 1.4
            rgba[ys, xs, :3] = np.clip(tone, 0, 255)
        else:
            rgba[..., :3] = _mix(color, (255, 255, 255), 0.35) if style in {"neon", "pulse"} else color
        rgba[..., 3] = mask * 255 * (0.55 + 0.45 * pulse if style == "pulse" else 1.0)
        layer = Image.fromarray(np.round(rgba).astype(np.uint8), "RGBA")
    else:
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        heads = []
        for path_index, (points, closed) in enumerate(paths):
            total = _path_metrics(points, closed)[2]
            color_at = _style_color(style, frame, u, shift, color, color2)
            if color_at is None:  # corners
                near = _corner_mask(points, closed, min(w, h) * 0.14)
                color_at = lambda _p, distance, near=near: (*color, 255) if near(distance) else None
            _stroke_path(draw, points, closed, width, color_at)
            if style == "comet" and closed and path_index == 0:
                heads += [_path_point(points, closed, head * total)
                          for head in ((cycles * u + shift) % 1, (cycles * u + shift + 0.5) % 1)]
        radius = width * 0.9 + 1.5
        for hx, hy in heads:
            draw.ellipse((hx - radius, hy - radius, hx + radius, hy + radius), fill=(255, 255, 255, 255))
        cut = np.asarray(layer, dtype=np.float64)
        cut[..., 3] *= keep
        layer = Image.fromarray(np.round(cut).astype(np.uint8), "RGBA")
    glow = {"neon": 1.8, "pulse": 1.8, "rgb": 1.6, "comet": 1.6, "dashes": 1.0,
            "shimmer": 1.2, "grain": 1.0}.get(style, 0.0)
    if glow:
        halo = layer.filter(ImageFilter.GaussianBlur(max(1.5, width * glow)))
        strength = {"neon": 1.6, "pulse": 1.6 * (0.25 + 0.75 * pulse), "shimmer": 0.8, "grain": 0.6}.get(style, 1.0)
        if strength != 1.0:
            halo.putalpha(halo.getchannel("A").point(lambda value: min(255, int(value * strength))))
        panel = Image.alpha_composite(panel, halo)
        if style in {"rgb", "comet"}:
            panel = Image.alpha_composite(panel, halo)
    return Image.alpha_composite(panel, layer)


def _shaped_frame(image: Image.Image, u: float, frame: dict, roles=None, surface=None, origin=(0, 0)) -> Image.Image:
    rects = _rects(frame["target"], image.size)
    roles = list(roles or []) + ["full"] * len(rects)
    scale = (surface or max(image.size)) / 1000
    result = image.copy()
    for index, (x, y, w, h) in enumerate(rects):
        if w < 2 or h < 2:
            continue
        panel = result.crop((x, y, x + w, y + h))
        result.paste(_panel_frame(panel, (x + origin[0], y + origin[1]), u, frame, roles[index], index, scale), (x, y))
    return result


def _frame(image: Image.Image, u: float, frame: dict, roles=None, surface=None, origin=(0, 0)) -> Image.Image:
    style = frame["style"]
    if style == "none":
        return image
    if frame.get("shape", "rect") != "rect" or style in OUTLINE_TEXTURES or roles:
        return _shaped_frame(image, u, frame, roles, surface, origin)
    width = frame["width"]
    color = _rgb(frame["color"])
    color2 = _rgb(frame["color2"])
    cycles = frame["speed"]
    size = image.size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    rects = _rects(frame["target"], size)
    glow_radius = 0.0
    glow_strength = 1.0

    if style in {"solid", "double", "neon", "pulse"}:
        level = 1.0
        if style == "pulse":
            level = 0.5 + 0.5 * math.cos(math.tau * cycles * u)
        line_alpha = int(255 * (0.55 + 0.45 * level)) if style == "pulse" else 255
        core = _mix(color, (255, 255, 255), 0.35) if style in {"neon", "pulse"} else color
        for x, y, w, h in rects:
            draw.rectangle((x, y, x + w - 1, y + h - 1), outline=(*core, line_alpha), width=width)
            if style == "double":
                gap = width * 2 + 3
                draw.rectangle((x + gap, y + gap, x + w - 1 - gap, y + h - 1 - gap),
                               outline=(*color2, 255), width=max(1, width - 1))
        if style in {"neon", "pulse"}:
            glow_radius = max(2.0, width * 1.8)
            glow_strength = 0.25 + 0.75 * level if style == "pulse" else 1.0
            glow_color = Image.new("RGBA", size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_color)
            for x, y, w, h in rects:
                glow_draw.rectangle((x, y, x + w - 1, y + h - 1), outline=(*color, 255), width=width + 2)
            halo = glow_color.filter(ImageFilter.GaussianBlur(glow_radius))
            halo.putalpha(halo.getchannel("A").point(lambda value: min(255, int(value * 1.6 * glow_strength))))
            return Image.alpha_composite(Image.alpha_composite(image, halo), layer)
        return Image.alpha_composite(image, layer)

    if style == "corners":
        for x, y, w, h in rects:
            size = int(min(w, h) * 0.22)
            x1, y1 = x + w - 1, y + h - 1
            for (cx, cy, dx, dy) in ((x, y, 1, 1), (x1, y, -1, 1), (x, y1, 1, -1), (x1, y1, -1, -1)):
                draw.line(((cx + dx * size, cy + dy * (width // 2)), (cx, cy + dy * (width // 2))), fill=(*color, 255), width=width)
                draw.line(((cx + dx * (width // 2), cy), (cx + dx * (width // 2), cy + dy * size)), fill=(*color, 255), width=width)
        return Image.alpha_composite(image, layer)

    for index, rect in enumerate(rects):
        shift = index * 0.2 if frame["target"] == "squares" else 0.0
        if style == "rgb":
            def color_at(position, _distance, shift=shift):
                r, g, b = colorsys.hsv_to_rgb((position + shift - cycles * u) % 1, 1.0, 1.0)
                return int(r * 255), int(g * 255), int(b * 255), 255
            glow_radius = max(2.0, width * 1.5)
        elif style == "comet":
            # Two comets chase each other around every square; tails fade to color2.
            heads = [(cycles * u + shift) % 1, (cycles * u + shift + 0.5) % 1]
            tail = 0.34

            def color_at(position, _distance, heads=heads):
                distance = min((head - position) % 1 for head in heads)
                if distance > tail:
                    return (*_mix(color, (0, 0, 0), 0.45), 70)
                strength = (1 - distance / tail) ** 0.85
                tone = _mix(color2, color, strength)
                if distance < 0.03:
                    tone = _mix(tone, (255, 255, 255), 0.7)
                return (*tone, int(90 + 165 * strength))
            glow_radius = max(2.5, width * 1.8)
        else:  # dashes
            period, dash = 14, 8
            offset = u * cycles * period * 6

            def color_at(_position, distance, offset=offset):
                if (distance - offset) % period < dash:
                    return (*color, 255)
                return (*color2, 90)
            glow_radius = max(1.5, width)
        _segments(draw, rect, width, color_at)
        if style == "comet":
            corners, length = _perimeter(rect, width)
            for head in heads:
                hx, hy = _point(corners, length, head * length)
                radius = width * 0.9 + 1.5
                draw.ellipse((hx - radius, hy - radius, hx + radius, hy + radius), fill=(255, 255, 255, 255))
    halo = layer.filter(ImageFilter.GaussianBlur(glow_radius)) if glow_radius else None
    result = image
    if halo is not None:
        result = Image.alpha_composite(result, halo)
        if style in {"rgb", "comet"}:
            result = Image.alpha_composite(result, halo)
    return Image.alpha_composite(result, layer)


def normalize_frame(raw: dict | None) -> dict:
    """Frame options alone (used by Process Workshop outlines)."""
    return normalize({"frame": raw if isinstance(raw, dict) else {}})["frame"]


def draw_frame(image: Image.Image, u: float, frame: dict, role: str | None = None,
               surface: float | None = None, origin=(0, 0)) -> Image.Image:
    """Frame on an image of any size: five Workshop panels or the whole image.

    ``role`` ("left"/"right") marks an Artwork Split part, so HUD designs put
    their ornaments on the outer side of the pair. ``surface``/``origin`` place a
    part inside the whole showcase, so outline textures continue across files.
    """
    roles = [role] if role in ("left", "right") else None
    return _frame(image.convert("RGBA"), u % 1, frame, roles, surface, origin)


def apply(strip: Image.Image, u: float, fx: dict) -> Image.Image:
    """Effect below, frame on top, for loop position ``u``."""
    image = strip.convert("RGBA")
    if image.size != (W, H):
        raise ValueError("Squares strip must be 750x150")
    image = _effect(image, u % 1, fx["effect"])
    return _frame(image, u % 1, fx["frame"])
