"""Pictures for the Steam Community guide "How to design a Steam profile" (RU + EN), 2026-10-09.

Output: output/steam-guide/<lang>/images/NN-name.(png|gif) next to the guide text (docs/steam-guide/<lang>.txt is
copied there as guide.txt). Steam guides take JPG, PNG and GIF only; every file is kept under 2 MB because Valve
publishes no guide limit and forum reports vary (5-10 MB).

Only the site's own art is used (static/img/samples/sample-art.webp and the site UI): the extension-guide pictures
that show other people's art (steam-profile, steam-pick-*, presets) are left out on purpose.

    py -3.14 main.py                                    # local server, FFmpeg + gifski installed
    $env:QA_BASE_URL="http://127.0.0.1:8091"; py -3.14 scripts/build_steam_guide.py [--skip-anim]
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "output" / "steam-guide"
EXT = ROOT / "static" / "img" / "extension-guide" / "v2"
FONTS = Path(os.environ.get("GUIDE_FONTS", "C:/Windows/Fonts"))
MAX_BYTES = 2 * 1024 * 1024
LANGS = ("ru", "en")
COVER = {
    "ru": ("Оформление", "профиля Steam", "витрины · GIF · фон"),
    "en": ("Aesthetic", "Steam profile", "showcases · GIFs · backgrounds"),
}


def save_png(image: Image.Image, path: Path, width: int = 1000) -> None:
    if image.width > width:
        image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
    image.convert("RGB").save(path, "PNG", optimize=True)
    if path.stat().st_size > MAX_BYTES:            # very detailed screenshots: fall back to a JPEG of the same name
        jpg = path.with_suffix(".jpg")
        image.convert("RGB").save(jpg, "JPEG", quality=88, optimize=True, progressive=True)
        path.unlink()


def gif_from_frames(frames: list[Path], path: Path, fps: int, width: int) -> None:
    """gifski with falling quality until the file fits MAX_BYTES."""
    for quality, lossy in ((80, 80), (70, 60), (65, 40), (55, 30), (45, 20)):
        subprocess.run(["gifski", "--quiet", "--fps", str(fps), "--quality", str(quality), "--lossy-quality", str(lossy),
                        "--width", str(width), "-o", str(path), *map(str, frames)], check=True)
        if path.stat().st_size <= MAX_BYTES:
            return
    width = round(width * 0.8)
    gif_from_frames(frames, path, fps, width)


# ---------------------------------------------------------------- site screenshots
def capture(base: str, lang: str, images: Path, work: Path) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        context.add_init_script("try{localStorage.setItem('sm_analytics_consent_v1','no');"
                                "localStorage.setItem('sm_process_intro_closed','1')}catch(e){}")
        page = context.new_page()

        def shot(locator, name: str) -> None:
            raw = work / f"{lang}-{name}.png"
            locator.screenshot(path=str(raw))
            save_png(Image.open(raw), images / f"{name}.png")

        page.goto(f"{base}/{lang}/app", wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.click(".process-sample")
        page.wait_for_timeout(2500)
        page.evaluate("window.scrollTo(0,0)")
        page.screenshot(path=str(work / f"{lang}-tools.png"))
        save_png(Image.open(work / f"{lang}-tools.png"), images / "04-tools.png")

        choose = page.locator(".mode[data-mode='workshop']").locator("xpath=ancestor::*[contains(@class,'card')][1]")
        choose.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        shot(choose, "05-showcase-types")

        # A frame look ("HUD with shine", the 8th quick look) on the live preview, recorded as a short GIF.
        page.evaluate("document.querySelectorAll('#tab-process .sqfx__preset')[7].click()")
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(1500)
        preview = page.locator(".process-preview-column > .card").first
        frames = []
        for index in range(20):
            frame = work / f"{lang}-frame-{index:02d}.png"
            preview.screenshot(path=str(frame))
            frames.append(frame)
            page.wait_for_timeout(100)
        gif_from_frames(frames, images / "06-frame-preview.gif", fps=8, width=640)
        page.evaluate("document.querySelectorAll('#tab-process .sqfx__preset')[6].click()")  # "Minimalism": plain cut
        page.wait_for_timeout(800)

        page.click("#btnRun")
        page.wait_for_selector(".workspace-result-modal__dialog", timeout=120000)
        page.wait_for_timeout(2500)
        shot(page.locator(".workspace-result-modal__dialog"), "07-result-window")

        with context.expect_page() as new_page:
            page.click(".workspace-result__profile")
        mockup = new_page.value
        mockup.set_viewport_size({"width": 1440, "height": 1000})
        mockup.wait_for_load_state("networkidle")
        mockup.wait_for_timeout(2500)
        mockup.screenshot(path=str(work / f"{lang}-mockup.png"))
        save_png(Image.open(work / f"{lang}-mockup.png"), images / "03-profile-mockup.png")
        mockup.close()

        for tab, name in (("steam", "12-manual-steam-tab"), ("infobox", "13-infobox")):
            page.goto(f"{base}/{lang}/app", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.evaluate(f"document.querySelector('#nav button[data-tab=\"{tab}\"]').click()")
            page.wait_for_timeout(3500)
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path=str(work / f"{lang}-{tab}.png"))
            save_png(Image.open(work / f"{lang}-{tab}.png"), images / f"{name}.png")
        browser.close()


# ---------------------------------------------------------------- extension pictures (webp -> png / gif)
def extension(lang: str, images: Path, work: Path) -> None:
    for name, target in (("uploader-anim", "08-ext-uploader"), ("upload-anim", "09-ext-uploading")):
        source = Image.open(EXT / f"{name}-{lang}.webp")
        frames = []
        for index in range(getattr(source, "n_frames", 1)):
            source.seek(index)
            frame = work / f"{lang}-{name}-{index}.png"
            source.convert("RGB").save(frame)
            frames.append(frame)
        gif_from_frames(frames, images / f"{target}.gif", fps=1, width=720)
    save_png(Image.open(EXT / f"uploader-artwork-{lang}.webp"), images / "10-ext-artwork.png", width=900)
    save_png(Image.open(EXT / f"upload-done-{lang}.webp"), images / "11-ext-done.png", width=720)
    if lang == "ru":   # popup-en.webp is the Russian popup as well
        save_png(Image.open(EXT / "popup-ru.webp"), images / "15-ext-popup.png", width=800)


# ---------------------------------------------------------------- the animated showcase (site art + "Depth 3D")
def animation(work: Path) -> Path:
    import processor as proc
    image = Image.open(ROOT / "static" / "img" / "samples" / "sample-art.webp").convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    options = {"camera": {"motion": "sway", "strength": 1.3}, "atmosphere": "light"}
    name, raw = proc.parallax_source("sample.png", buffer.getvalue(), options, work / "depth", fps=15)
    source = work / name
    source.write_bytes(raw)
    result = proc.process_video_workshop(source, work / "workshop", fps=15, width=750, encoder="gifski", duration=4)
    frames_dir = work / "showcase-frames"
    frames_dir.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(result["full_with_bars.gif"]), "-vf",
                    "fps=8,scale=630:-1:flags=lanczos", str(frames_dir / "%03d.png")], check=True)
    gif = work / "02-result.gif"
    gif_from_frames(sorted(frames_dir.glob("*.png")), gif, fps=8, width=630)
    return gif


def cover(lang: str, images: Path) -> None:
    size = 512
    tile = Image.open(ROOT / "static" / "img" / "favicon" / "favicon-512.png").convert("RGBA").resize((size, size))
    art = Image.open(ROOT / "static" / "img" / "samples" / "sample-art-960.webp").convert("RGBA")
    art = art.crop(((art.width - art.height) // 2, 0, (art.width + art.height) // 2, art.height)).resize((size, size))
    shade = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(shade)
    for y in range(size):
        draw.line([(0, y), (size, y)], fill=(4, 8, 22, round(60 + 175 * (y / size) ** 1.4)))
    image = Image.alpha_composite(art, shade)
    mark = tile.resize((96, 96))
    image.alpha_composite(mark, (28, 28))
    draw = ImageDraw.Draw(image)
    first, second, third = COVER[lang]
    bold = ImageFont.truetype(str(FONTS / "Montserrat-Bold.ttf"), 46)
    semi = ImageFont.truetype(str(FONTS / "Montserrat-SemiBold.ttf"), 24)
    draw.text((32, 330), first, font=bold, fill=(255, 255, 255))
    draw.text((32, 384), second, font=bold, fill=(85, 217, 255))
    draw.text((34, 452), third, font=semi, fill=(214, 229, 250))
    image.convert("RGB").save(images / "01-cover.png", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-anim", action="store_true", help="reuse output/steam-guide/02-result.gif")
    args = parser.parse_args()
    base = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8091").rstrip("/")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="steam-guide-") as temp:
        work = Path(temp)
        shared = OUT / "02-result.gif"
        if not (args.skip_anim and shared.is_file()):
            shutil.copy(animation(work), shared)
        for lang in LANGS:
            images = OUT / lang / "images"
            if images.exists():
                shutil.rmtree(images)
            images.mkdir(parents=True)
            cover(lang, images)
            shutil.copy(shared, images / "02-result.gif")
            capture(base, lang, images, work)
            extension(lang, images, work)
            text = ROOT / "docs" / "steam-guide" / f"{lang}.txt"
            if text.is_file():
                shutil.copy(text, OUT / lang / "guide.txt")
            for path in sorted(images.iterdir()):
                print(lang, path.name, f"{path.stat().st_size / 1024:.0f} KB")
        readme = ROOT / "docs" / "steam-guide" / "README.txt"
        if readme.is_file():
            shutil.copy(readme, OUT / "README.txt")


if __name__ == "__main__":
    main()
