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

W, H, SQUARE = 750, 150, 150
STATIC_FRAMES = {"none", "solid", "double", "corners", "neon"}
ANIMATED_FRAMES = {"rgb", "comet", "pulse", "dashes"}
FRAME_STYLES = STATIC_FRAMES | ANIMATED_FRAMES
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
    return {
        "frame": {
            "style": style if style in FRAME_STYLES else "none",
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


def _frame(image: Image.Image, u: float, frame: dict) -> Image.Image:
    style = frame["style"]
    if style == "none":
        return image
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


def draw_frame(image: Image.Image, u: float, frame: dict) -> Image.Image:
    """Frame on an image of any size: five Workshop panels or the whole image."""
    return _frame(image.convert("RGBA"), u % 1, frame)


def apply(strip: Image.Image, u: float, fx: dict) -> Image.Image:
    """Effect below, frame on top, for loop position ``u``."""
    image = strip.convert("RGBA")
    if image.size != (W, H):
        raise ValueError("Squares strip must be 750x150")
    image = _effect(image, u % 1, fx["effect"])
    return _frame(image, u % 1, fx["frame"])
