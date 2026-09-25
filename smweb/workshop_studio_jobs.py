"""Workshop Studio jobs.

Rows layout: one full-height Steam file per uploaded row.
Squares layout: a user-chosen 5:1 area of one source cut into five 150x150 files.
"""

from __future__ import annotations

import io
import logging
import math
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

import processor as proc
from smweb.core import JOBS
from smweb.jobs import _job_set


LOG = logging.getLogger(__name__)
STEAM_LIMIT = 5 * 1024 * 1024
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ANIMATED_EXTENSIONS = {".gif", ".mp4", ".webm"}


def _grade(image: Image.Image, settings: dict) -> Image.Image:
    alpha = image.getchannel("A") if "A" in image.getbands() else None
    rgb = image.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(settings["brightness"] / 100)
    rgb = ImageEnhance.Contrast(rgb).enhance(settings["contrast"] / 100)
    rgb = ImageEnhance.Color(rgb).enhance(settings["saturation"] / 100)
    if settings["hue"]:
        hue, saturation, value = rgb.convert("HSV").split()
        offset = round(settings["hue"] * 256 / 360)
        hue = hue.point(lambda current: (current + offset) % 256)
        rgb = Image.merge("HSV", (hue, saturation, value)).convert("RGB")
    if alpha is not None:
        rgb = rgb.convert("RGBA")
        rgb.putalpha(alpha)
    return rgb


def _png_under_limit(image: Image.Image) -> bytes:
    """Keep dimensions intact; reduce palette only when lossless PNG is too large."""
    candidates = [image]
    has_alpha = "A" in image.getbands()
    base = image.convert("RGBA" if has_alpha else "RGB")
    method = Image.Quantize.FASTOCTREE if has_alpha else Image.Quantize.MEDIANCUT
    candidates += [base.quantize(colors=colors, method=method) for colors in (256, 128, 64)]
    for candidate in candidates:
        buffer = io.BytesIO()
        candidate.save(buffer, format="PNG", optimize=True, compress_level=9)
        if buffer.tell() <= STEAM_LIMIT:
            return proc.apply_hex21(buffer.getvalue())
    raise ValueError("This image cannot fit under 5 MB without changing its dimensions")


def _free_watermark(image: Image.Image) -> Image.Image:
    original_alpha = "A" in image.getbands()
    base = image.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.text((16, max(0, image.height - 38)), "ShowcaseMaker", font=proc.load_font("Fineday", 18), fill=(255, 255, 255, 150))
    result = Image.alpha_composite(base, layer)
    return result if original_alpha else result.convert("RGB")


def render_image(path: Path, settings: dict, width: int = 750, outline: bool = False, free_watermark: bool = False) -> bytes:
    with Image.open(path) as opened:
        if getattr(opened, "n_frames", 1) != 1:
            raise ValueError("Animated image must be exported as GIF")
        image = ImageOps.exif_transpose(opened)
        image.load()
    width = max(1, min(1200, int(width)))
    height = max(1, round(image.height * width / image.width))
    if (image.width, image.height) != (width, height):
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    image = _grade(image, settings)
    if free_watermark:
        image = _free_watermark(image)
    if outline:
        ImageDraw.Draw(image).rectangle((0, 0, image.width - 1, image.height - 1), outline="#8de9ff", width=2)
    return _png_under_limit(image)


def render_animation(path: Path, output: Path, settings: dict, fps: int, duration: float, start: float, outline: bool = False, free_watermark: bool = False) -> None:
    ffmpeg = proc.find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable")
    source = path
    temporary = output.parent / (output.stem + "_graded.mp4")
    watermark_image = output.parent / (output.stem + "_watermark.png")
    # Encode once with color correction and optional trim. media_to_gif performs
    # the high-quality palette encode and Steam 5 MB fitting afterwards.
    brightness = (settings["brightness"] - 100) / 100
    contrast = settings["contrast"] / 100
    saturation = settings["saturation"] / 100
    filters = (
        f"eq=brightness={brightness:.3f}:contrast={contrast:.3f}:saturation={saturation:.3f},"
        f"hue=h={settings['hue']},scale=750:-2:flags=lanczos"
    )
    if outline:
        filters += ",drawbox=x=0:y=0:w=iw:h=ih:color=0x8de9ff:t=2"
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    if start:
        command += ["-ss", f"{start:.3f}"]
    command += ["-i", str(path)]
    if free_watermark:
        watermark = Image.new("RGBA", (750, 60), (0, 0, 0, 0))
        ImageDraw.Draw(watermark).text((16, 16), "ShowcaseMaker", font=proc.load_font("Fineday", 18), fill=(255, 255, 255, 150))
        watermark.save(watermark_image)
        command += ["-loop", "1", "-i", str(watermark_image), "-t", f"{duration:.3f}", "-an",
                    "-filter_complex", f"[0:v]{filters}[base];[base][1:v]overlay=x=0:y=H-h:shortest=1[out]", "-map", "[out]"]
    else:
        command += ["-t", f"{duration:.3f}", "-an", "-vf", filters]
    command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", str(temporary)]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=90)
        source = temporary
        proc.media_to_gif(source, output, fps=fps, width=750, duration=duration, encoder="ffmpeg")
        if not output.is_file() or not output.stat().st_size:
            raise ValueError("GIF encoding produced an empty file")
        if output.stat().st_size > STEAM_LIMIT:
            raise ValueError("This animation cannot fit under 5 MB; shorten the clip")
        proc.apply_hex21_file(output)
    finally:
        temporary.unlink(missing_ok=True)
        watermark_image.unlink(missing_ok=True)


SQUARE = 150
SQUARE_COUNT = 5
STRIP_SIZE = (SQUARE * SQUARE_COUNT, SQUARE)
SQUARE_GAP = 4


def normalize_crop(crop: dict) -> dict:
    """Clamp a crop given as fractions of the source to the source bounds."""
    x, y, width, height = (float(crop[key]) for key in ("x", "y", "w", "h"))
    if not all(math.isfinite(value) for value in (x, y, width, height)):
        raise ValueError("Crop values must be finite")
    width = max(0.001, min(1.0, width))
    height = max(0.001, min(1.0, height))
    return {
        "x": max(0.0, min(1.0 - width, x)),
        "y": max(0.0, min(1.0 - height, y)),
        "w": width,
        "h": height,
    }


def _crop_box(size: tuple[int, int], crop: dict) -> tuple[float, float, float, float]:
    """Pixel box for the crop, corrected to the exact 5:1 strip ratio."""
    source_width, source_height = size
    width, height = crop["w"] * source_width, crop["h"] * source_height
    ratio = STRIP_SIZE[0] / STRIP_SIZE[1]
    if width / height > ratio:
        width = height * ratio
    else:
        height = width / ratio
    left = max(0.0, min(source_width - width, crop["x"] * source_width))
    top = max(0.0, min(source_height - height, crop["y"] * source_height))
    return left, top, left + width, top + height


def _outline(image: Image.Image) -> None:
    ImageDraw.Draw(image).rectangle((0, 0, image.width - 1, image.height - 1), outline="#8de9ff", width=2)


def _squares_preview(parts: list[Image.Image]) -> Image.Image:
    """The five squares side by side with Steam-like gaps (reference only, no HEX 21)."""
    width = SQUARE * SQUARE_COUNT + SQUARE_GAP * (SQUARE_COUNT - 1)
    preview = Image.new("RGB", (width, SQUARE), (0, 0, 0))
    for index, part in enumerate(parts):
        tile = part.convert("RGBA")
        preview.paste(tile, (index * (SQUARE + SQUARE_GAP), 0), tile)
    return preview


def render_squares_image(path: Path, settings: dict, crop: dict, outline: bool = False,
                         free_watermark: bool = False) -> dict[str, bytes]:
    """Cut the chosen 5:1 area of a still image into five 150x150 Steam files.

    The free watermark goes on the preview only; the Steam files stay clean.
    """
    with Image.open(path) as opened:
        if getattr(opened, "n_frames", 1) != 1:
            raise ValueError("Animated image must be exported as GIF")
        image = ImageOps.exif_transpose(opened)
        image.load()
    strip = image.resize(STRIP_SIZE, Image.Resampling.LANCZOS, box=_crop_box(image.size, crop))
    strip = _grade(strip, settings)
    parts = []
    result: dict[str, bytes] = {}
    for index in range(SQUARE_COUNT):
        part = strip.crop((index * SQUARE, 0, (index + 1) * SQUARE, SQUARE))
        if outline:
            _outline(part)
        parts.append(part)
        result[f"part_{index + 1}.png"] = _png_under_limit(part)
    preview = _squares_preview(parts)
    if free_watermark:
        preview = _free_watermark(preview)
    buffer = io.BytesIO()
    preview.save(buffer, format="PNG", optimize=True)
    result["preview.png"] = buffer.getvalue()
    return result


def render_squares_animation(path: Path, work_dir: Path, settings: dict, crop: dict, fps: int,
                             duration: float, start: float, outline: bool = False,
                             free_watermark: bool = False) -> dict[str, Path]:
    """Crop an animation to the 5:1 strip, then reuse the synchronized Workshop cutter.

    The free watermark goes on the preview GIF only; the Steam files stay clean.
    """
    ffmpeg = proc.find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable")
    work_dir.mkdir(parents=True, exist_ok=True)
    strip = work_dir / "squares_strip.mp4"
    brightness = (settings["brightness"] - 100) / 100
    contrast = settings["contrast"] / 100
    saturation = settings["saturation"] / 100
    # Crop in input fractions (evaluated after autorotation), then force the exact strip size.
    filters = (
        f"crop=w='iw*{crop['w']:.6f}':h='ih*{crop['h']:.6f}'"
        f":x='min(iw*{crop['x']:.6f},iw-ow)':y='min(ih*{crop['y']:.6f},ih-oh)',"
        f"scale={STRIP_SIZE[0]}:{STRIP_SIZE[1]}:flags=lanczos,setsar=1,"
        f"eq=brightness={brightness:.3f}:contrast={contrast:.3f}:saturation={saturation:.3f},"
        f"hue=h={settings['hue']}"
    )
    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    if start:
        command += ["-ss", f"{start:.3f}"]
    command += ["-i", str(path), "-t", f"{duration:.3f}", "-an", "-vf", filters,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(strip)]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=90)
        # wm_* only affects full_with_bars.gif (the preview), never the part_N.gif files.
        outputs = proc.process_gif_workshop(
            strip, work_dir, fps=fps, width=STRIP_SIZE[0], duration=duration, encoder="ffmpeg",
            outline_width=2 if outline else 0, outline_color="#8de9ff",
            wm_text="ShowcaseMaker" if free_watermark else "", wm_font="Fineday", wm_opacity=0.5,
        )
    finally:
        strip.unlink(missing_ok=True)
    result = {}
    for index in range(1, SQUARE_COUNT + 1):
        part = outputs.get(f"part_{index}.gif")
        if not part or not part.is_file() or not part.stat().st_size:
            raise ValueError("GIF encoding produced an empty file")
        if part.stat().st_size > STEAM_LIMIT:
            raise ValueError("This animation cannot fit under 5 MB; shorten the clip")
        result[part.name] = part
    if outputs.get("full_with_bars.gif"):
        result["preview.gif"] = outputs["full_with_bars.gif"]
    return result


def _run_squares(job_dir: Path, archive: zipfile.ZipFile, item: dict, options: dict) -> None:
    path = Path(item["path"])
    suffix = path.suffix.lower()
    settings = options["rows"][0]
    crop = normalize_crop(options["crop"])
    outline = bool(options.get("outline"))
    free_watermark = bool(options.get("free_watermark"))
    if suffix in IMAGE_EXTENSIONS:
        for name, data in render_squares_image(path, settings, crop, outline, free_watermark).items():
            archive.writestr(name, data)
    elif suffix in ANIMATED_EXTENSIONS:
        work_dir = job_dir / "squares"
        try:
            outputs = render_squares_animation(path, work_dir, settings, crop, options["fps"], options["duration"],
                                               settings["start"], outline, free_watermark)
            for name, output in outputs.items():
                archive.write(output, name)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
    else:
        raise ValueError("Unsupported source format")


def run(jid: str, job: dict) -> None:
    job_dir = JOBS / jid
    job_dir.mkdir(parents=True, exist_ok=True)
    zip_path = job_dir / "result.zip"
    files = job.get("files") or []
    options = job.get("options") or {}
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
            if options.get("layout") == "squares":
                _job_set(jid, status="running", pct=10, stage="squares")
                _run_squares(job_dir, archive, files[0], options)
            row_files = [] if options.get("layout") == "squares" else files
            for index, item in enumerate(row_files, 1):
                _job_set(jid, status="running", pct=5 + round(85 * (index - 1) / len(row_files)), stage=f"row:{index}")
                path = Path(item["path"])
                suffix = path.suffix.lower()
                settings = options["rows"][index - 1]
                if suffix in IMAGE_EXTENSIONS:
                    data = render_image(path, settings, outline=bool(options.get("outline")), free_watermark=bool(options.get("free_watermark")))
                    archive.writestr(f"row_{index}.png", data)
                elif suffix in ANIMATED_EXTENSIONS:
                    output = job_dir / f"row_{index}.gif"
                    render_animation(path, output, settings, options["fps"], options["duration"], settings["start"], bool(options.get("outline")), bool(options.get("free_watermark")))
                    archive.write(output, f"row_{index}.gif")
                    output.unlink(missing_ok=True)
                else:
                    raise ValueError("Unsupported source format")
        _job_set(jid, status="done", pct=100, stage="done", zip_path=str(zip_path), processed=len(files))
    except Exception as exc:
        LOG.exception("Workshop Studio job %s failed", jid)
        detail = str(exc)[:200] if isinstance(exc, ValueError) else "Could not process one of the rows"
        _job_set(jid, status="error", pct=100, stage="error", error=detail)
        zip_path.unlink(missing_ok=True)
    finally:
        for item in files:
            Path(item["path"]).unlink(missing_ok=True)
