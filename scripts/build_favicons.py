"""Favicons with a dark background (2026-10-09).

static/icon-256.png is a white "S" on a transparent background: Google shows site icons in a white circle, so in
its results the icon vanished. These files put the mark on the site's navy (full square: Google crops it to a
circle itself, browsers show the square). Google wants a multiple of 48 px and a stable URL; /favicon.ico is
served by pages.py.

    py -3.14 scripts/build_favicons.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MARK = ROOT / "static" / "icon-256.png"
OUT = ROOT / "static" / "img" / "favicon"


def tile(size: int) -> Image.Image:
    base = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(base)
    top, bottom = (24, 40, 92), (5, 10, 28)          # site navy, as on panels (#0e1a3c -> #050a1c, a little lighter)
    for y in range(size):
        t = y / max(1, size - 1)
        draw.line([(0, y), (size, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,))
    # Thin cyan line at the bottom edge, the accent of the site's panels.
    draw.rectangle([0, size - max(1, size // 24), size, size], fill=(31, 201, 241, 255))
    mark = Image.open(MARK).convert("RGBA")
    box = mark.getbbox() or (0, 0, mark.width, mark.height)
    mark = mark.crop(box)
    target = round(size * 0.68)
    scale = target / max(mark.size)
    mark = mark.resize((max(1, round(mark.width * scale)), max(1, round(mark.height * scale))), Image.LANCZOS)
    base.alpha_composite(mark, ((size - mark.width) // 2, (size - mark.height) // 2 - max(0, size // 64)))
    return base


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (48, 96, 192, 512):
        tile(size).save(OUT / f"favicon-{size}.png", optimize=True)
    tile(180).convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)
    big = tile(256)
    big.save(ROOT / "static" / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    for path in sorted(OUT.iterdir()) + [ROOT / "static" / "favicon.ico"]:
        print(path.relative_to(ROOT), path.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
