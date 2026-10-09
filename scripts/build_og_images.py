"""Build the link-preview pictures static/img/og/og-<lang>.jpg (1200x630, 2026-10-09).

Telegram, Discord, VK, X and search engines show this picture next to a shared link (smweb/seo.py adds the
og:image tag). One picture per site language: the landing background (the monitor already shows a Steam
profile) with the wordmark and a two-line tagline in that language on a dark fade at the left.

    py -3.14 scripts/build_og_images.py [--fonts DIR]

Needs Montserrat Bold / SemiBold (OFL). Default: the Windows fonts folder; pass --fonts for another place.
Rebuild when the background master or the copy below changes, then bump nothing: og-*.jpg are not cached
by ?v= keys, so add ?v= in smweb/seo.py og_image() if a changed picture must reach caches sooner.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = ROOT / "static" / "img" / "home" / "fon-1920.webp"
ICON = ROOT / "static" / "icon-256.png"
OUT = ROOT / "static" / "img" / "og"
W, H = 1200, 630

TAGLINE = {
    "en": ("Steam profile design", "in 5 minutes"),
    "ru": ("Оформление профиля Steam", "за 5 минут"),
    "uk": ("Оформлення профілю Steam", "за 5 хвилин"),
    "de": ("Steam-Profil gestalten", "in 5 Minuten"),
    "fr": ("Design de profil Steam", "en 5 minutes"),
    "es": ("Diseño de perfil de Steam", "en 5 minutos"),
    "pt": ("Design de perfil Steam", "em 5 minutos"),
    "tr": ("Steam profil tasarımı", "5 dakikada"),
}
CHIPS = {
    "en": ("Showcases", "GIF", "Backgrounds"),
    "ru": ("Витрины", "GIF", "Фоны"),
    "uk": ("Вітрини", "GIF", "Фони"),
    "de": ("Showcases", "GIF", "Hintergründe"),
    "fr": ("Vitrines", "GIF", "Arrière-plans"),
    "es": ("Escaparates", "GIF", "Fondos"),
    "pt": ("Vitrines", "GIF", "Fundos"),
    "tr": ("Vitrinler", "GIF", "Arka planlar"),
}


def background() -> Image.Image:
    image = Image.open(BACKGROUND).convert("RGB")
    # Keep the right part (the monitor with the Steam profile); the text sits over the left part.
    scale = H / image.height * 1.08
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = image.width - W - round(image.width * 0.02)
    top = round((image.height - H) * 0.35)
    return image.crop((left, top, left + W, top + H))


def shade(image: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", (W, H))
    pixels = overlay.load()
    for x in range(W):
        t = x / W
        alpha = 236 if t < 0.36 else max(0, round(236 * (1 - (t - 0.36) / 0.34)))
        for y in range(H):
            pixels[x, y] = (3, 7, 18, alpha)
    return Image.alpha_composite(image.convert("RGBA"), overlay)


def fit(draw: ImageDraw.ImageDraw, text: str, font_path: Path, size: int, width: int) -> ImageFont.FreeTypeFont:
    while size > 20:
        font = ImageFont.truetype(str(font_path), size)
        if draw.textlength(text, font=font) <= width:
            return font
        size -= 2
    return ImageFont.truetype(str(font_path), size)


def build(language: str, fonts: Path, base: Image.Image) -> Image.Image:
    bold, semi = fonts / "Montserrat-Bold.ttf", fonts / "Montserrat-SemiBold.ttf"
    image = base.copy()
    draw = ImageDraw.Draw(image)
    x = 64
    icon = Image.open(ICON).convert("RGBA").resize((76, 76), Image.LANCZOS)
    image.alpha_composite(icon, (x, 70))
    draw.text((x + 92, 78), "SHOWCASE", font=ImageFont.truetype(str(bold), 30), fill=(234, 249, 255))
    draw.text((x + 92, 112), "MAKER", font=ImageFont.truetype(str(bold), 30), fill=(85, 217, 255))

    first, second = TAGLINE[language]
    font = fit(draw, first, bold, 60, 600)
    draw.text((x, 232), first, font=font, fill=(255, 255, 255))
    accent = fit(draw, second, bold, font.size, 600)
    draw.text((x, 232 + font.size + 14), second, font=accent, fill=(85, 217, 255))

    chip_font = ImageFont.truetype(str(semi), 24)
    cx, cy = x, 470
    for label in CHIPS[language]:
        width = round(draw.textlength(label, font=chip_font)) + 40
        draw.rounded_rectangle((cx, cy, cx + width, cy + 50), radius=25, fill=(14, 26, 60, 230),
                               outline=(85, 217, 255, 160), width=2)
        draw.text((cx + 20, cy + 11), label, font=chip_font, fill=(234, 249, 255))
        cx += width + 14
    draw.text((x, 556), "showcasemaker.com", font=ImageFont.truetype(str(semi), 22), fill=(160, 186, 214))
    return image.convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", default="C:/Windows/Fonts", help="folder with Montserrat-Bold.ttf and -SemiBold.ttf")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    base = shade(background().filter(ImageFilter.GaussianBlur(0.6)))
    for language in TAGLINE:
        path = OUT / f"og-{language}.jpg"
        build(language, Path(args.fonts), base).save(path, "JPEG", quality=86, optimize=True, progressive=True)
        print(path.relative_to(ROOT), path.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
