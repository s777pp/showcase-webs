"""Обработка витрин — порт логики desktop (упрощённо, но те же режимы)."""
from __future__ import annotations
import time

import errno
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFile, ImageFont
import logging
_LOG = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "fonts"
BIN = ROOT / "bin"
MAX_STEAM_MB = 5.0

# Encode profile of the current job (user's choice in the quality dialog).
#   standard: gifski --fast, coarser size search (~2-3x faster; measured on panel
#             frames: +3 % size at equal quality, -0.06 dB PSNR, not visible)
#   max:      plain gifski probes and a final --extra pass, filled close to 5 MB
# A ContextVar does not follow work into ThreadPoolExecutor threads, so code that
# encodes in a pool reads `encode_fast()` first and passes it on explicitly.
import contextlib
import contextvars

ENCODE_PROFILES = ("standard", "max")
_ENCODE_PROFILE: contextvars.ContextVar[str] = contextvars.ContextVar("sm_encode_profile", default="max")


def normalize_encode_profile(value) -> str:
    value = str(value or "").strip().lower()
    return value if value in ENCODE_PROFILES else "standard"


@contextlib.contextmanager
def encode_profile(value):
    token = _ENCODE_PROFILE.set(normalize_encode_profile(value))
    try:
        yield
    finally:
        _ENCODE_PROFILE.reset(token)


def encode_fast() -> bool:
    return _ENCODE_PROFILE.get() == "standard"


# Extra files next to the Steam files. Direct callers (gallery, profile) get all of
# them as before; Process jobs pass only what the user ticked.
EXTRA_ORIGINAL = "original"   # full_original.* : the whole showcase without cuts
EXTRA_PREVIEW = "preview"     # full_with_bars.* / full_with_watermark.* : DeviantArt preview
ALL_EXTRAS = frozenset({EXTRA_ORIGINAL, EXTRA_PREVIEW})


def _extras(value) -> frozenset:
    return ALL_EXTRAS if value is None else frozenset(value) & ALL_EXTRAS


def _is_runnable(path: Path) -> bool:
    """File exists and is executable (skip Windows .exe on Linux, no +x, etc.)."""
    try:
        if not path.is_file():
            return False
        # never run .exe on non-Windows
        if path.suffix.lower() == ".exe" and os.name != "nt":
            return False
        if os.name == "nt":
            return True
        return os.access(str(path), os.X_OK)
    except Exception:
        return False


def find_ffmpeg() -> Optional[str]:
    # Prefer system binary on Linux/Docker (Render installs via apt)
    which = shutil.which("ffmpeg")
    if which and _is_runnable(Path(which)):
        return which
    for name in ("ffmpeg", "ffmpeg.exe"):
        cand = BIN / name
        if _is_runnable(cand):
            return str(cand)
    return which  # may still be useful


def find_ffprobe() -> Optional[str]:
    which = shutil.which("ffprobe")
    if which and _is_runnable(Path(which)):
        return which
    for name in ("ffprobe", "ffprobe.exe"):
        cand = BIN / name
        if _is_runnable(cand):
            return str(cand)
    ff = find_ffmpeg()
    if ff:
        alt = ff.replace("ffmpeg", "ffprobe")
        if _is_runnable(Path(alt)):
            return alt
    return which


def _has_cyrillic(text: str) -> bool:
    return any(chr(0x0400) <= ch <= chr(0x04FF) for ch in (text or ""))



def _cyrillic_font_candidates() -> list:
    """Fonts known to cover Russian glyphs."""
    names = (
        "NotoSans-Regular.ttf", "NotoSans.ttf", "DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf", "Roboto-Regular.ttf", "arial.ttf", "Arial.ttf",
        "liberation-sans.ttf", "LiberationSans-Regular.ttf",
    )
    paths = []
    for n in names:
        paths.append(FONTS / n)
    # system paths (Linux / Railway images often have DejaVu)
    for p in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    ):
        paths.append(p)
    return paths


def load_font(key: str, size: int, text: str = "") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = str(key or "lap").strip()
    candidates = []
    for ext in (".ttf", ".otf"):
        candidates.append(FONTS / f"{key}{ext}")
        candidates.append(FONTS / f"{key.lower()}{ext}")
        candidates.append(FONTS / f"{key.capitalize()}{ext}")
    if key.lower() == "fineday":
        candidates.insert(0, FONTS / "Fineday.ttf")
    # User fonts
    for extra in ("roboto", "gothic-rus", "Roboto", "Gothic-Rus"):
        candidates.append(FONTS / f"{extra}.ttf")
        candidates.append(FONTS / f"{extra}.otf")
    # If watermark has Cyrillic, prefer fonts that actually draw it
    # gothic-rus / roboto first when present
    if any("\u0400" <= ch <= "\u04FF" for ch in (text or "")):
        for prefer in ("gothic-rus.ttf", "gothic-rus.otf", "roboto.ttf", "Roboto-Regular.ttf"):
            candidates.insert(0, FONTS / prefer)
    if _has_cyrillic(text):
        candidates = list(_cyrillic_font_candidates()) + candidates
    for c in candidates:
        if c.is_file():
            try:
                return ImageFont.truetype(str(c), size)
            except Exception:
                _LOG.debug("ignored error", exc_info=True)
    return ImageFont.load_default()


def wm_anchor(corner: str, w: int, h: int, tw: int, th: int, margin_ratio: float = 0.04) -> tuple[int, int]:
    """Return top-left of text box for corner: tl/tr/bl/br."""
    c = str(corner or "bl").strip().lower()
    mx = max(4, int(w * margin_ratio))
    my = max(4, int(h * margin_ratio))
    if c in ("tl", "top-left", "topleft"):
        return mx, my
    if c in ("tr", "top-right", "topright"):
        return max(mx, w - tw - mx), my
    if c in ("br", "bottom-right", "bottomright"):
        return max(mx, w - tw - mx), max(my, h - th - my)
    # bl default
    return mx, max(my, h - th - my)



def _parse_rgb(color: str) -> tuple[int, int, int]:
    c = str(color or "#ffffff").strip()
    if c.startswith("#") and len(c) == 7:
        try:
            return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        except Exception:
            _LOG.debug("ignored error", exc_info=True)
    return 255, 255, 255

def apply_watermark(
    img: Image.Image,
    text: str,
    font_key: str,
    opacity: float,
    corner: str = "bl",
    scale: float = 1.0,
    wx: float | None = None,
    wy: float | None = None,
    color: str = "#ffffff",
) -> Image.Image:
    if not text or opacity <= 0:
        return img
    img = img.convert("RGBA")
    h = img.height
    scale = max(0.4, min(2.5, float(scale or 1.0)))
    font_size = max(12, int((h // 28) * scale))
    font = load_font(font_key, font_size, text=text)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = font_size * max(1, len(text)) // 2, font_size
    if wx is not None and wy is not None:
        x, y = int(img.width * wx), int(img.height * wy)
    else:
        x, y = wm_anchor(corner, img.width, img.height, tw, th)
    r, g, b = _parse_rgb(color)
    draw.text((x, y), text, font=font, fill=(r, g, b, 255))
    a = layer.getchannel("A").point(lambda p: int(p * max(0.0, min(1.0, opacity))))
    layer.putalpha(a)
    return Image.alpha_composite(img, layer)


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return buf.getvalue()


def apply_hex21(data: bytes) -> bytes:
    """Steam upload trick: force last byte to 0x21 (PNG, GIF, any binary)."""
    if not data:
        return data
    if len(data) == 1:
        return bytes([0x21])
    return data[:-1] + bytes([0x21])

def apply_hex21_file(path: Path) -> None:
    path = Path(path)
    if not path.is_file():
        return
    try:
        data = path.read_bytes()
        if data:
            path.write_bytes(apply_hex21(data))
    except Exception:
        _LOG.debug("ignored error", exc_info=True)



# Formats the pipelines handle directly; anything else that Pillow can open as a
# still picture (ICO/CUR, TIFF, AVIF, TGA, PSD, QOI, JPEG 2000, DDS, ICNS, PCX, ...)
# is converted to PNG first, so every tool accepts "any image".
NATIVE_STILL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# iPhone photos (HEIC/HEIF). Optional: without pillow-heif these stay unsupported.
try:
    from pillow_heif import register_heif_opener as _register_heif_opener
    _register_heif_opener()
    HEIF_SUPPORTED = True
except Exception:
    HEIF_SUPPORTED = False
# Decode JPEG/PNG files whose end is missing (interrupted downloads, some phone and messenger
# exports) the way browsers do: the missing rows stay grey instead of failing the whole job
# with "image file is truncated". The user already saw the same picture in the preview.
ImageFile.LOAD_TRUNCATED_IMAGES = True
MOTION_EXTENSIONS = {".gif", ".mp4", ".mov", ".webm", ".avi", ".mkv"}


def still_image_to_png(raw: bytes) -> bytes | None:
    """PNG bytes for any still image Pillow can decode, else None (icons: largest size)."""
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format in ("ICO", "ICNS") and hasattr(image, "info") and image.info.get("sizes"):
                image.size = max(image.info["sizes"], key=lambda size: size[0] * size[1])
            image.load()
            frame = image.convert("RGBA") if image.mode not in ("RGB", "RGBA") else image.copy()
    except Exception:
        return None
    out = io.BytesIO()
    frame.save(out, "PNG", optimize=False)
    return out.getvalue()


def restore_gif_trailer(raw: bytes) -> bytes:
    """Undo the HEX 21 patch on a GIF (users re-upload files this site prepared for Steam).

    Pillow raises IndexError in ``n_frames`` when the trailer byte is 0x21."""
    if raw[:6] in (b"GIF87a", b"GIF89a") and raw.endswith(b"!"):
        return raw[:-1] + b";"
    return raw


def restore_gif_trailer_file(path: Path) -> None:
    with path.open("rb") as handle:
        head = handle.read(6)
        handle.seek(-1, 2)
        last = handle.read(1)
    if head in (b"GIF87a", b"GIF89a") and last == b"!":
        with path.open("r+b") as handle:
            handle.seek(-1, 2)
            handle.write(b";")


def normalize_upload(name: str, raw: bytes) -> tuple[str, bytes]:
    """Return (name, bytes) the pipelines understand; unknown still images become PNG."""
    raw = restore_gif_trailer(raw)
    ext = Path(name).suffix.lower()
    if ext in NATIVE_STILL_EXTENSIONS or ext in MOTION_EXTENSIONS:
        return name, raw
    png = still_image_to_png(raw)
    if png is None:
        return name, raw
    return (Path(name).stem or "image") + ".png", png


GRADE_RANGES = {"brightness": (50, 150, 100), "contrast": (50, 150, 100), "saturation": (0, 200, 100), "hue": (-180, 180, 0)}


def normalize_grade(raw) -> dict | None:
    """Colour correction options (same ranges as static/js/color-grade.js); None when neutral."""
    source = raw if isinstance(raw, dict) else {}
    grade = {}
    for key, (low, high, default) in GRADE_RANGES.items():
        try:
            value = int(round(float(source.get(key, default))))
        except (TypeError, ValueError):
            value = default
        grade[key] = max(low, min(high, value))
    return None if all(grade[key] == GRADE_RANGES[key][2] for key in grade) else grade


def grade_image(image: Image.Image, grade: dict) -> Image.Image:
    """Brightness / contrast / saturation / hue, alpha kept (same maths as Workshop Studio)."""
    from PIL import ImageEnhance
    alpha = image.getchannel("A") if "A" in image.getbands() else None
    rgb = image.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(grade["brightness"] / 100)
    rgb = ImageEnhance.Contrast(rgb).enhance(grade["contrast"] / 100)
    rgb = ImageEnhance.Color(rgb).enhance(grade["saturation"] / 100)
    if grade["hue"]:
        hue, saturation, value = rgb.convert("HSV").split()
        offset = round(grade["hue"] * 256 / 360)
        hue = hue.point(lambda current: (current + offset) % 256)
        rgb = Image.merge("HSV", (hue, saturation, value)).convert("RGB")
    if alpha is not None:
        rgb = rgb.convert("RGBA")
        rgb.putalpha(alpha)
    return rgb


def graded_source(name: str, raw: bytes, grade: dict | None, work_dir: Path) -> tuple[str, bytes]:
    """Apply colour correction once, before any cutting. Stills -> PNG, motion -> lossless FFV1 clip."""
    if not grade:
        return name, raw
    ext = Path(name).suffix.lower()
    if ext in NATIVE_STILL_EXTENSIONS:
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            graded = grade_image(image, grade)
        out = io.BytesIO()
        graded.save(out, "PNG")
        return Path(name).stem + ".png", out.getvalue()
    if ext not in MOTION_EXTENSIONS:
        return name, raw
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found")
    work_dir.mkdir(parents=True, exist_ok=True)
    source = work_dir / f"grade_source{ext}"
    output = work_dir / "graded.mkv"
    source.write_bytes(raw)
    brightness = (grade["brightness"] - 100) / 100
    video_filter = (f"eq=brightness={brightness:.3f}:contrast={grade['contrast'] / 100:.3f}:"
                    f"saturation={grade['saturation'] / 100:.3f},hue=h={grade['hue']}")
    try:
        _run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), "-t", "20", "-an",
              "-vf", video_filter, "-c:v", "ffv1", "-pix_fmt", "bgra", str(output)])
        return Path(name).stem + ".mkv", output.read_bytes()
    finally:
        source.unlink(missing_ok=True)
        output.unlink(missing_ok=True)


def process_image_workshop(
    img: Image.Image,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    outline_width: int = 0,
    outline_color: str = "#ffffff",
) -> dict[str, bytes]:
    img = img.convert("RGBA")
    w, h = img.size
    pw = max(1, w // 5)
    out: dict[str, bytes] = {}
    parts = []
    for i in range(5):
        left = i * pw
        right = (i + 1) * pw if i < 4 else w
        part = img.crop((left, 0, right, h))
        if outline_width > 0:
            from PIL import ImageDraw
            stroke = max(1, min(12, int(outline_width)))
            draw = ImageDraw.Draw(part)
            for offset in range(stroke):
                draw.rectangle(
                    (offset, offset, part.width - 1 - offset, part.height - 1 - offset),
                    outline=outline_color,
                    width=1,
                )
        parts.append(part)
        # Steam: last byte 0x21 on each workshop part
        out[f"part_{i + 1}.png"] = apply_hex21(_png_bytes(part))

    out["full_original.png"] = _png_bytes(img)

    bar = steam_bar_width(w, "workshop")
    full_w = w + bar * 4
    full = Image.new("RGBA", (full_w, h), (0, 0, 0, 255))
    x = 0
    for i, part in enumerate(parts):
        full.paste(part, (x, 0))
        x += part.width
        if i < 4:
            x += bar
    full = apply_watermark(full, wm_text, wm_font, wm_opacity, corner=wm_corner, scale=wm_scale, color=wm_color, wx=wm_x, wy=wm_y)
    out["full_with_bars.png"] = _png_bytes(full)
    return out


def _active_frame(frame_fx: dict | None) -> dict | None:
    """Styled frame options (smweb.square_fx) or None when nothing is drawn."""
    return frame_fx if frame_fx and frame_fx.get("style", "none") != "none" else None


def _draw_whole_frame(image: Image.Image, u: float, frame_fx: dict, role: str | None = None,
                      surface: float | None = None, origin=(0, 0)) -> Image.Image:
    """One frame around the whole image (Featured, or one Split part: role left/right)."""
    from smweb.square_fx import draw_frame
    return draw_frame(image, u, dict(frame_fx, target="strip"), role=role, surface=surface, origin=origin)


def _split_parts(frame: Image.Image, u: float = 0.0, frame_fx: dict | None = None) -> tuple[Image.Image, Image.Image]:
    """Cut a 606 px wide frame into center 506 + side 100, optionally framed.

    ``target == "strip"`` draws one frame around both parts (the gap between
    them is Steam's); otherwise each part gets its own frame.
    """
    frame_fx = _active_frame(frame_fx)
    if frame_fx:
        from smweb.frame_designs import design_ids
        # HUD designs are drawn once around the whole 606 px showcase (same thickness
        # as on Featured), then cut: the left column sits in the 506 file, the mirrored
        # right column fits inside the 100 px file.
        if frame_fx.get("shape") in design_ids():
            frame_fx = dict(frame_fx, target="strip")
    if frame_fx and frame_fx.get("target") == "strip":
        frame = _draw_whole_frame(frame.convert("RGBA"), u, frame_fx)
    center = frame.crop((0, 0, 506, frame.height))
    side = frame.crop((506, 0, 606, frame.height))
    if frame_fx and frame_fx.get("target") != "strip":
        # HUD designs put their ornaments on the outer side of each part, so the
        # two files still read as one symmetric frame on the profile.
        surface = max(606, frame.height)
        center = _draw_whole_frame(center, u, frame_fx, role="left", surface=surface)
        side = _draw_whole_frame(side, u, frame_fx, role="right", surface=surface, origin=(506, 0))
    return center, side


def process_image_featured(
    img: Image.Image,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    frame_fx: dict | None = None,
) -> dict[str, bytes]:
    img = img.convert("RGBA")
    w, h = img.size
    nh = max(1, int(h * (630 / max(1, w))))
    img = img.resize((630, nh), Image.Resampling.LANCZOS)
    if _active_frame(frame_fx):
        img = _draw_whole_frame(img, 0.0, frame_fx)
    out = {
        "featured_630.png": apply_hex21(_png_bytes(img)),
        "full_original.png": _png_bytes(img),
    }
    # Watermarked copy (like full_with_bars for workshop/split)
    if wm_text and float(wm_opacity or 0) > 0:
        wm_img = apply_watermark(
            img, wm_text, wm_font, wm_opacity,
            corner=wm_corner, scale=wm_scale, color=wm_color, wx=wm_x, wy=wm_y,
        )
        out["full_with_watermark.png"] = _png_bytes(wm_img)
        # also alias used by gallery/process callers
        out["full_with_bars.png"] = out["full_with_watermark.png"]
    return out


def process_image_split(
    img: Image.Image,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    frame_fx: dict | None = None,
) -> dict[str, bytes]:
    img = img.convert("RGBA")
    w, h = img.size
    scale = 606 / max(1, w)
    nw, nh = 606, max(1, int(h * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    center, side = _split_parts(img, 0.0, frame_fx)
    out = {
        "center_506.png": apply_hex21(_png_bytes(center)),
        "side_100.png": apply_hex21(_png_bytes(side)),
        "full_original.png": _png_bytes(img),
    }
    bar = steam_bar_width(center.width + side.width, "split")
    full = Image.new("RGBA", (center.width + bar + side.width, nh), (0, 0, 0, 255))
    full.paste(center, (0, 0))
    full.paste(side, (center.width + bar, 0))
    full = apply_watermark(full, wm_text, wm_font, wm_opacity, corner=wm_corner, scale=wm_scale, color=wm_color, wx=wm_x, wy=wm_y)
    out["full_with_bars.png"] = _png_bytes(full)
    return out


def _run(cmd: list[str]) -> None:
    # The worker polls the persisted cancellation flag while the encoder is
    # running, so cancelling from another API container terminates FFmpeg or
    # gifski instead of merely hiding its progress in the browser.
    from smweb.process_control import run as run_cancellable
    r = run_cancellable(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "ffmpeg error")[-500:])



def _ffmpeg_palette_vf(fps: int, width: Optional[int] = None, scale_pct: Optional[int] = None,
                       max_colors: int = 256, dither: str = "sierra2_4a") -> str:
    """High-quality palette pipeline for ffmpeg GIF encode."""
    fps_i = max(5, min(30, int(fps)))
    parts = [f"fps={fps_i}"]
    if width is not None:
        w = max(200, min(1200, int(width)))
        if w % 2:
            w -= 1
        parts.append(f"scale={w}:-2:flags=lanczos")
    elif scale_pct is not None and int(scale_pct) < 100:
        pct = max(40, min(100, int(scale_pct)))
        parts.append(f"scale=iw*{pct}/100:-2:flags=lanczos")
    colors = max(32, min(256, int(max_colors)))
    # stats_mode=diff — better temporal palette; sierra2_4a — best looking dither in ffmpeg
    parts.append(
        f"split[s0][s1];[s0]palettegen=max_colors={colors}:stats_mode=diff:reserve_transparent=0[p];"
        f"[s1][p]paletteuse=dither={dither}:diff_mode=rectangle"
    )
    return ",".join(parts)


# Exact chroma upsampling and rounding when frames are read from video: the
# default blurs coloured edges, which is very visible on anime line art.
SCALE_FLAGS = "lanczos+accurate_rnd+full_chroma_int"


def source_matrix(src: Path) -> str:
    """``:in_color_matrix=bt709`` for HD video that carries no colour tag.

    FFmpeg falls back to BT.601 for untagged video, which shifts reds and
    greens in HD sources (they are almost always BT.709).  Tagged video is
    already converted correctly and gets nothing.
    """
    probe = find_ffprobe()
    if not probe:
        return ""
    try:
        raw = subprocess.check_output(
            [probe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=color_space,height,codec_name", "-of", "json", str(src)],
            text=True, timeout=20,
        )
        import json
        stream = (json.loads(raw).get("streams") or [{}])[0]
    except Exception:
        return ""
    space = str(stream.get("color_space") or "unknown").lower()
    if stream.get("codec_name") in ("gif", "png", "apng", "mjpeg", "webp") or space not in ("", "unknown"):
        return ""
    return ":in_color_matrix=bt709" if int(stream.get("height") or 0) >= 720 else ""


def _gifski_size_args(first_frame: Path) -> list[str]:
    """Pin gifski's output to the frame size.

    Without --width gifski quietly shrinks large animations ("limited to about
    800x600"): a 750x1500 row came out 375x750.
    """
    try:
        with Image.open(first_frame) as image:
            width, height = image.size
    except Exception:
        return []
    return ["--width", str(width), "--height", str(height)]


def _gifski_from_frames(frames_dir: Path, dest: Path, fps: int, quality: int = 100, extra: bool = False,
                       fast: bool | None = None) -> bool:
    """Encode PNG sequence with gifski. Returns True on success.

    ``extra`` is gifski's slower, more careful quantization (about 1.6x the
    time); used for the final encode of the "max" profile only.  ``fast``
    (default: the job's encode profile) adds ``--fast`` and drops ``extra``.
    """
    if fast is None:
        fast = encode_fast()
    if fast:
        extra = False
    gs = find_gifski()
    if not gs:
        return False
    files = sorted(frames_dir.glob("frame_*.png"))
    if not files:
        return False
    fps = max(5, min(30, int(fps)))
    quality = max(1, min(100, int(quality)))
    if len(files) == 1:
        # gifski refuses a single input ("not enough to make an animation"); a static-looking
        # source (e.g. a still with identical frames) then lost its full preview.
        files = files * 2
    try:
        cmd = [
            gs, "--fps", str(fps), "--quality", str(quality), *_gifski_size_args(files[0]),
            *(["--fast"] if fast else []), *(["--extra"] if extra else []),
            "-o", str(dest), *[str(f) for f in files],
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return dest.is_file() and dest.stat().st_size > 50
    except Exception:
        return False


def _search_band() -> tuple[float, float]:
    """(target, close enough) as fractions of the limit for the job's profile.

    "standard" accepts a file 12 % under the limit and saves one or two encodes;
    "max" keeps filling the limit to within 6 %.
    """
    return (0.95, 0.88) if encode_fast() else (0.97, 0.94)


def _best_quality(size_at, limit: int, min_quality: int = 1) -> int:
    """Highest gifski quality whose output fits ``limit`` bytes, in few encodes.

    Output size grows roughly exponentially with quality, so each probe aims
    just under the limit using ln(size) fitted between the closest fitting and
    failing probes.  The search stops once a fitting result is within 6 % of
    the limit or the fit/fail bracket is one step wide; a prediction outside
    the bracket falls back to bisection.  Typically 3-4 encodes
    instead of the 8 a plain binary search needs.  Returns 0 if nothing fits.
    """
    import math

    sizes: dict[int, int] = {}

    def probe(quality: int) -> int:
        if quality not in sizes:
            sizes[quality] = int(size_at(quality))
        return sizes[quality]

    if probe(100) <= limit:
        return 100
    target_share, close_share = _search_band()
    target = target_share * limit
    fit_q, fail_q = 0, 100
    slope = 0.0375  # typical d ln(size) / d quality for gifski
    guess = 100 - math.log(sizes[100] / target) / slope
    jump = 2
    for _ in range(14):
        low = fit_q + 1 if fit_q else max(1, min_quality)
        high = fail_q - 1
        if low > high:
            break
        quality = max(low, min(high, int(round(guess))))
        if not fit_q:
            # Nothing fits yet: move down at least `jump`, doubling each time,
            # so flat stretches of the size curve cannot stall the search.
            quality = max(low, min(quality, fail_q - jump))
            jump *= 2
        elif high - low > 4 and quality in (low, high):
            quality = (low + high) // 2
        if probe(quality) <= limit:
            fit_q = quality
            if sizes[quality] >= close_share * limit:
                break
        else:
            fail_q = quality
        # Refit the slope on the two probes closest to the target size.
        near = sorted(sizes, key=lambda q: abs(math.log(max(1, sizes[q]) / target)))[:2]
        if len(near) == 2 and near[0] != near[1] and sizes[near[0]] != sizes[near[1]]:
            fitted = math.log(max(1, sizes[near[0]]) / max(1, sizes[near[1]])) / (near[0] - near[1])
            if fitted > 0:
                slope = max(0.004, fitted)
        base = near[0]
        guess = base + math.log(target / max(1, sizes[base])) / slope
        if fit_q and not (fit_q < guess < fail_q):
            guess = (fit_q + fail_q) / 2  # prediction left the bracket: bisect
    if not fit_q and min_quality > 1 and min_quality < fail_q and probe(min_quality) <= limit:
        fit_q = min_quality
    return fit_q


def fit_frames_to_gif(frames_dir: Path, dest: Path, fps: int, max_mb: float = MAX_STEAM_MB,
                      min_quality: int = 1) -> Optional[dict]:
    """Best-looking gifski GIF from full-colour frames that fits ``max_mb``.

    Always works from the original frames: re-quantizing an already
    dithered GIF adds a second layer of noise.  The highest fitting quality
    is found by `_best_quality` with fast encodes, then the final file is made
    with ``--extra``.  Returns the chosen settings, or None when gifski is
    missing or even ``min_quality`` does not fit (the caller falls back).
    """
    if not find_gifski():
        return None
    limit = int(max_mb * 1024 * 1024)
    work = Path(tempfile.mkdtemp(prefix="sm_fit_"))
    try:
        def encode(quality: int, extra: bool = False) -> Optional[Path]:
            out = work / f"q{quality}{'x' if extra else ''}.gif"
            return out if _gifski_from_frames(frames_dir, out, fps=fps, quality=quality, extra=extra) else None

        def fits(path: Optional[Path]) -> bool:
            return bool(path) and 50 < path.stat().st_size <= limit

        paths: dict[int, Optional[Path]] = {}

        def size_at(quality: int) -> int:
            paths[quality] = encode(quality)
            return paths[quality].stat().st_size if paths[quality] else limit * 100

        best = _best_quality(size_at, limit, min_quality=max(1, min_quality))
        if not best:
            return None
        if encode_fast():
            _safe_replace(paths[best], dest)
            return {"quality": best, "extra": False, "fast": True}
        # --extra can add a few KB; step down a little if it no longer fits.
        for quality in range(best, max(min_quality, best - 4) - 1, -1):
            candidate = encode(quality, extra=True)
            if fits(candidate):
                _safe_replace(candidate, dest)
                return {"quality": quality, "extra": True}
        _safe_replace(paths[best], dest)
        return {"quality": best, "extra": False}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def normalize_rotation(value: float | int | str | None) -> float:
    """Normalise clockwise degrees to the compact -180..180 interval."""
    try:
        degrees = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    degrees = ((degrees + 180.0) % 360.0) - 180.0
    return 0.0 if abs(degrees) < 0.01 else degrees


def rotate_image(image: Image.Image, degrees: float | int | str | None) -> Image.Image:
    """Rotate a still image clockwise, expanding the canvas without stretching."""
    from PIL import ImageOps
    image = ImageOps.exif_transpose(image)
    angle = normalize_rotation(degrees)
    if angle == 0:
        return image.copy()
    if angle == 90:
        return image.transpose(Image.Transpose.ROTATE_270)
    if angle == -90:
        return image.transpose(Image.Transpose.ROTATE_90)
    if abs(angle) == 180:
        return image.transpose(Image.Transpose.ROTATE_180)
    return image.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=True)


def _ffmpeg_rotation_filter(degrees: float | int | str | None) -> str:
    """Return a lossless quarter-turn filter or an expanded arbitrary rotation."""
    angle = normalize_rotation(degrees)
    if angle == 0:
        return ""
    if angle == 90:
        return "transpose=clock"
    if angle == -90:
        return "transpose=cclock"
    if abs(angle) == 180:
        return "hflip,vflip"
    radians = angle * 3.141592653589793 / 180.0
    return f"rotate={radians:.10f}:ow=rotw({radians:.10f}):oh=roth({radians:.10f}):c=black@0"


def extract_frames(src: Path, frames_dir: Path, fps: int, width: int, duration: float = 8,
                   rotation: float = 0) -> int:
    """Decode a video into lossless ``frame_%04d.png`` files at ``fps`` and ``width``.

    For intermediate steps (Character compositing): a GIF fitted to 5 MB there
    cost a full size search and added a second layer of dithering.
    """
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found (install ffmpeg or put bin/ffmpeg)")
    fps = max(5, min(30, int(fps)))
    width = max(100, min(1920, int(width)))
    width -= width % 2
    frames_dir = Path(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    video_filter = ",".join(part for part in (
        _ffmpeg_rotation_filter(rotation),
        f"fps={fps}",
        f"scale={width}:-2:flags={SCALE_FLAGS}{source_matrix(Path(src))}",
    ) if part)
    _run([
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src), "-t", str(max(1.0, min(20.0, float(duration)))),
        "-an", "-vf", video_filter, "-compression_level", "0",
        str(frames_dir / "frame_%04d.png"),
    ])
    count = len(list(frames_dir.glob("frame_*.png")))
    if not count:
        raise RuntimeError("no frames extracted")
    return count


def media_to_gif(
    src: Path,
    dest: Path,
    fps: int,
    width: int,
    duration: float = 12,
    encoder: str = "ffmpeg",
    rotation: float = 0,
) -> None:
    """Convert image/gif/video to high-quality GIF, then fit under Steam 5 MB.

    encoder: gifski | ffmpeg — gifski preferred when binary is available.
    """
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found (install ffmpeg or put bin/ffmpeg)")
    fps = max(5, min(24, int(fps)))
    width = max(200, min(1200, int(width)))
    if width % 2:
        width -= 1
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = Path(src)
    if not src.is_file():
        raise RuntimeError(f"source missing: {src}")

    duration = max(1.0, min(20.0, float(duration)))
    encoder = (encoder or "ffmpeg").strip().lower()

    # High-quality path: rasterize frames → gifski (or ffmpeg palette)
    tmp = Path(tempfile.mkdtemp(prefix="sm_m2g_"))
    try:
        frames = tmp / "frames"
        frames.mkdir()
        # Extract scaled frames as PNG (source for both encoders)
        rotation_filter = _ffmpeg_rotation_filter(rotation)
        video_filter = ",".join(part for part in (
            rotation_filter,
            f"fps={fps}",
            f"scale={width}:-2:flags={SCALE_FLAGS}{source_matrix(src)}",
        ) if part)
        try:
            _run([
                ff, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(src),
                "-t", str(duration),
                "-an",
                "-vf", video_filter,
                "-compression_level", "0",
                str(frames / "frame_%04d.png"),
            ])
        except Exception:
            # odd codecs: intermediate mp4
            mid = tmp / "mid.mp4"
            _run([
                ff, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(src),
                "-t", str(duration),
                "-an",
                "-vf", video_filter,
                "-pix_fmt", "yuv420p",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                str(mid),
            ])
            _run([
                ff, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(mid),
                "-an",
                str(frames / "frame_%04d.png"),
            ])

        if not list(frames.glob("frame_*.png")):
            raise RuntimeError("no frames extracted for GIF")

        if encoder == "gifski":
            if not find_gifski():
                raise RuntimeError("gifski selected but binary not found")
            if not fit_frames_to_gif(frames, dest, fps=fps):
                ok = _gifski_from_frames(frames, dest, fps=fps, quality=100)
                if not ok:
                    raise RuntimeError("gifski encode failed (no fallback to ffmpeg when gifski is selected)")
        else:
            # ffmpeg palette from PNG sequence
            vf = _ffmpeg_palette_vf(fps=fps, max_colors=256)
            _run([
                ff, "-y", "-hide_banner", "-loglevel", "error",
                "-framerate", str(fps),
                "-i", str(frames / "frame_%04d.png"),
                "-lavfi", vf,
                "-loop", "0",
                str(dest),
            ])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if not dest.is_file() or dest.stat().st_size < 50:
        raise RuntimeError("GIF conversion produced empty file")
    ensure_under_mb(dest)


def _probe_wh(path: Path) -> tuple[int, int]:
    probe = find_ffprobe()
    ff = find_ffmpeg()
    if not probe and ff:
        probe = ff.replace("ffmpeg", "ffprobe")
    # Prefer Pillow for GIF/images (more reliable after palette encode)
    try:
        with Image.open(path) as im:
            return int(im.size[0]), int(im.size[1])
    except Exception:
        _LOG.debug("ignored error", exc_info=True)
    if not probe:
        raise RuntimeError("cannot probe dimensions (no ffprobe / unreadable image)")
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    out = subprocess.check_output(
        [
            probe, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(path),
        ],
        text=True, **kw,
    ).strip().replace("x", ",").split(",")
    if len(out) < 2:
        raise RuntimeError(f"ffprobe bad output: {out!r}")
    return int(out[0]), int(out[1])


def process_video_workshop(
    src: Path,
    out_dir: Path,
    fps: int = 12,
    width: int = 750,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    duration: float = 12,
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    encoder: str = "ffmpeg",
    outline_width: int = 0,
    outline_color: str = "#ffffff",
    rotation: float = 0,
    frame_fx: dict | None = None,
    extras=None,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return process_gif_workshop(
        src, out_dir, wm_text, wm_font, wm_opacity,
        wm_color=wm_color, wm_corner=wm_corner, wm_scale=wm_scale,
        wm_x=wm_x, wm_y=wm_y, encoder=encoder, fps=fps,
        outline_width=outline_width, outline_color=outline_color,
        rotation=rotation, width=width, duration=duration, frame_fx=frame_fx,
        extras=extras,
    )


def process_video_featured(
    src: Path,
    out_dir: Path,
    fps: int = 12,
    duration: float = 10,
    encoder: str = "ffmpeg",
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    rotation: float = 0,
    frame_fx: dict | None = None,
    extras=None,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Straight from the video frames to the final GIF. This used to encode an
    # intermediate GIF fitted to 5 MB first and then decode and fit it again:
    # twice the work and a second layer of dithering.
    return process_gif_featured(
        src, out_dir, fps=fps, encoder=encoder,
        wm_text=wm_text, wm_font=wm_font, wm_opacity=wm_opacity,
        wm_color=wm_color, wm_corner=wm_corner, wm_scale=wm_scale,
        wm_x=wm_x, wm_y=wm_y, rotation=rotation, frame_fx=frame_fx, duration=duration,
        extras=extras,
    )


def process_video_split(
    src: Path,
    out_dir: Path,
    fps: int = 12,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    duration: float = 12,
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    encoder: str = "ffmpeg",
    rotation: float = 0,
    frame_fx: dict | None = None,
    extras=None,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return process_gif_split(
        src, out_dir, fps=fps, wm_text=wm_text, wm_font=wm_font, wm_opacity=wm_opacity,
        wm_color=wm_color, wm_corner=wm_corner, wm_scale=wm_scale, wm_x=wm_x, wm_y=wm_y,
        encoder=encoder, rotation=rotation, duration=duration, frame_fx=frame_fx,
        extras=extras,
    )




def find_gifski() -> Optional[str]:
    """Locate gifski binary. Prefer system PATH (Railway/Linux), then bin/.

    Note: gifski.exe is Windows-only — skipped on Linux so a local .exe
    in bin/ never shadows a real system `gifski` on the server.
    """
    which = shutil.which("gifski")
    if which and _is_runnable(Path(which)):
        return which
    # also accept "gifski.exe" only on Windows
    if os.name == "nt":
        which_exe = shutil.which("gifski.exe")
        if which_exe and _is_runnable(Path(which_exe)):
            return which_exe
    for name in ("gifski", "gifski.exe"):
        if name.endswith(".exe") and os.name != "nt":
            continue
        for base in (BIN, ROOT):
            cand = base / name
            if _is_runnable(cand):
                return str(cand)
    return None


def encode_gif_from_png_sequence(
    frames_dir: Path,
    dest: Path,
    fps: int = 12,
    encoder: str = "ffmpeg",
    quality: int = 100,
) -> None:
    """encoder: ffmpeg | gifski | pillow. quality 1..100 used by gifski."""
    encoder = (encoder or "ffmpeg").strip().lower()
    fps = max(5, min(30, int(fps or 12)))
    quality = max(1, min(100, int(quality or 100)))
    files = sorted(frames_dir.glob("frame_*.png"))
    if not files:
        raise RuntimeError("no frames for gif encode")

    if encoder == "gifski":
        gs = find_gifski()
        if not gs:
            raise RuntimeError("gifski selected but binary not found")
        cmd = [
            gs, "--fps", str(fps),
            "--quality", str(quality), *_gifski_size_args(files[0]),
            *(["--fast"] if encode_fast() else []),
            "-o", str(dest),
            *[str(f) for f in files],
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except Exception as e:
            raise RuntimeError(f"gifski encode failed (no ffmpeg fallback): {e}") from e
        if dest.is_file() and dest.stat().st_size > 50:
            return
        raise RuntimeError("gifski encode produced empty file (no ffmpeg fallback)")

    if encoder == "ffmpeg":
        ff = find_ffmpeg()
        if not ff:
            raise RuntimeError("ffmpeg not found")
        vf = _ffmpeg_palette_vf(fps=fps, max_colors=256)
        cmd = [
            ff, "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%04d.png"),
            "-lavfi", vf,
            "-loop", "0",
            str(dest),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        if dest.is_file() and dest.stat().st_size > 50:
            return

    # pillow fallback
    imgs = [Image.open(f).convert("RGBA") for f in files]
    q = [_quantize_rgba_for_gif(im) for im in imgs]
    duration = int(1000 / fps)
    q[0].save(
        dest, save_all=True, append_images=q[1:], duration=duration, loop=0, disposal=2, optimize=True
    )


def _gif_mb(path: Path) -> float:
    try:
        return path.stat().st_size / (1024 * 1024)
    except Exception:
        return 999.0

def _safe_replace(src: Path, dest: Path) -> None:
    """Replace a file, including across different filesystems."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        src.replace(dest)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        shutil.copy2(src, dest)
        src.unlink()

def _try_replace(src_tmp: Path, dest: Path) -> bool:
    """Replace dest with tmp if tmp is smaller and valid."""
    if not src_tmp.is_file() or src_tmp.stat().st_size < 50:
        try:
            src_tmp.unlink(missing_ok=True)
        except Exception:
            _LOG.debug("ignored error", exc_info=True)
        return False
    if src_tmp.stat().st_size < dest.stat().st_size:
        _safe_replace(src_tmp, dest)
        return True
    try:
        src_tmp.unlink(missing_ok=True)
    except Exception:
        _LOG.debug("ignored error", exc_info=True)
    return False


def _ensure_under_mb_impl(path: Path, max_mb: float = MAX_STEAM_MB) -> None:
    """Fit GIF under Steam limit while preserving as much quality as possible.

    Strategy (in order):
      1. Already under limit → done
      2. gifski binary-search on --quality (best visual result)
      3. Gentle ffmpeg ladder: prefer keeping resolution & fps, reduce palette/dither cost
      4. Only then lower fps / slight downscale
    Target: get as close as possible to max_mb without exceeding it.
    """
    path = Path(path)
    if not path.is_file() or path.suffix.lower() != ".gif":
        return
    if _gif_mb(path) <= max_mb:
        return

    ff = find_ffmpeg()
    gs = find_gifski()
    tmp_dir = Path(tempfile.mkdtemp(prefix="sm_gif_fit_"))
    try:
        # Extract frames once for gifski / re-encode paths
        frames_dir = tmp_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        extracted = False
        if ff:
            try:
                _run([
                    ff, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(path),
                    "-compression_level", "0",
                    str(frames_dir / "frame_%04d.png"),
                ])
                extracted = bool(list(frames_dir.glob("frame_*.png")))
            except Exception:
                extracted = False

        # Probe fps roughly from frame count / duration
        src_fps = 12
        try:
            with Image.open(path) as im:
                n = int(getattr(im, "n_frames", 1) or 1)
                dur = 0
                for i in range(n):
                    im.seek(i)
                    dur += int(im.info.get("duration", 100) or 100)
                if dur > 0 and n > 1:
                    src_fps = max(5, min(24, round(n * 1000 / dur)))
        except Exception:
            _LOG.debug("ignored error", exc_info=True)

        # ── 1) gifski: highest quality that fits (binary search + --extra) ──
        if gs and extracted:
            fitted = tmp_dir / "fitted.gif"
            if fit_frames_to_gif(frames_dir, fitted, fps=src_fps, max_mb=max_mb):
                _safe_replace(fitted, path)
                return

        # ── 2) ffmpeg gentle ladder (keep res/fps as long as possible) ──
        if not ff:
            return

        # steps ordered by visual impact (lightest first)
        # (fps_factor, scale_pct, max_colors)
        steps = [
            (1.00, 100, 256),
            (1.00, 100, 224),
            (1.00, 100, 192),
            (0.90, 100, 256),
            (0.90, 100, 192),
            (1.00, 96, 256),
            (0.85, 100, 192),
            (1.00, 92, 224),
            (0.80, 100, 192),
            (1.00, 90, 192),
            (0.75, 95, 192),
            (1.00, 88, 160),
            (0.70, 90, 160),
            (0.65, 85, 128),
            (0.55, 80, 128),
            (0.50, 75, 96),
            (0.45, 70, 64),
        ]
        for fps_f, scale_pct, colors in steps:
            if _gif_mb(path) <= max_mb:
                return
            fps_i = max(5, min(24, int(round(src_fps * fps_f))))
            tmp = tmp_dir / f"ff_{fps_i}_{scale_pct}_{colors}.gif"
            vf = _ffmpeg_palette_vf(
                fps=fps_i,
                scale_pct=scale_pct if scale_pct < 100 else None,
                max_colors=colors,
                dither="sierra2_4a",
            )
            try:
                _run([
                    ff, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(path),
                    "-an",
                    "-vf", vf,
                    "-loop", "0",
                    str(tmp),
                ])
                if tmp.is_file() and tmp.stat().st_size > 50:
                    if _gif_mb(tmp) <= max_mb:
                        _safe_replace(tmp, path)
                        return
                    # still over — keep if smaller (progress toward limit)
                    if tmp.stat().st_size < path.stat().st_size:
                        _safe_replace(tmp, path)
                    else:
                        tmp.unlink(missing_ok=True)
            except Exception:
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    _LOG.debug("ignored error", exc_info=True)

        # last resort: very aggressive
        if _gif_mb(path) > max_mb and ff:
            tmp = tmp_dir / "last.gif"
            try:
                vf = _ffmpeg_palette_vf(fps=6, scale_pct=65, max_colors=48, dither="bayer")
                _run([ff, "-y", "-hide_banner", "-loglevel", "error",
                      "-i", str(path), "-vf", vf, "-loop", "0", str(tmp)])
                if tmp.is_file() and tmp.stat().st_size > 50:
                    _safe_replace(tmp, path)
            except Exception:
                _LOG.debug("ignored error", exc_info=True)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)






def ensure_under_mb(path: Path, max_mb: float = MAX_STEAM_MB) -> None:
    return _ensure_under_mb_impl(path, max_mb)



def _quantize_rgba_for_gif(im: Image.Image) -> Image.Image:
    """Composite on black and convert to 256-color palette for GIF."""
    im = im.convert("RGBA")
    bg = Image.new("RGBA", im.size, (0, 0, 0, 255))
    composed = Image.alpha_composite(bg, im)
    rgb = composed.convert("RGB")
    return rgb.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)


def _save_animated_gif(frames_p: list, durations: list, out_path: Path) -> None:
    if not frames_p:
        raise RuntimeError("no frames to save")
    durations = [max(20, int(d or 100)) for d in durations]
    while len(durations) < len(frames_p):
        durations.append(100)
    durations = durations[: len(frames_p)]
    frames_p[0].save(
        out_path,
        save_all=True,
        append_images=frames_p[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )
    if not out_path.is_file() or out_path.stat().st_size < 64:
        raise RuntimeError("GIF write failed (empty output)")


# Steam shows the panels of a Workshop row inside a 630 px column and an
# Artwork Split as 506 + 100 px; the gap between them looks about 3 px there.
# Previews scale the gap with their own width so every file looks the same
# once it is shown at one size (DeviantArt, the gallery, Steam itself).
_STEAM_ROW_WIDTH = {"workshop": 630, "split": 606}


def steam_bar_width(total_width: int, layout: str) -> int:
    return max(2, round(3 * int(total_width) / _STEAM_ROW_WIDTH[layout]))


def _compose_bars(frame: Image.Image, layout: str) -> Image.Image:
    """Full preview frame: the panels separated by black Steam-like gaps."""
    frame = frame.convert("RGBA")
    fw, fh = frame.size
    bar = steam_bar_width(fw, layout)
    if layout == "split":
        cut = min(506, max(1, fw - 1))
        parts = [frame.crop((0, 0, cut, fh)), frame.crop((cut, 0, fw, fh))]
    else:
        pw = max(1, fw // 5)
        parts = [frame.crop((i * pw, 0, (i + 1) * pw if i < 4 else fw, fh)) for i in range(5)]
    full = Image.new("RGBA", (sum(p.width for p in parts) + bar * (len(parts) - 1), fh), (0, 0, 0, 255))
    x = 0
    for part in parts:
        full.paste(part, (x, 0), part)
        x += part.width + bar
    return full


def _bars_gif_from_frames(frames_dir: Path, out_path: Path, layout: str, fps: int, wm_text: str,
                          wm_font: str, wm_opacity: float, wm_corner: str = "bl", wm_scale: float = 1.0,
                          wm_color: str = "#ffffff", wm_x: float | None = None,
                          wm_y: float | None = None) -> bool:
    """full_with_bars.gif straight from the full-colour frames, at gifski quality 100.

    Not fitted to the Steam limit on purpose: it is the owner's full-quality
    upload (DeviantArt).  Building it from the original frames avoids the
    second quantization the old path did on an already finished GIF.
    """
    files = sorted(frames_dir.glob("frame_*.png"))
    if not files or not find_gifski():
        return False
    tmp = Path(tempfile.mkdtemp(prefix="sm_bars_"))
    try:
        for index, path in enumerate(files, start=1):
            with Image.open(path) as opened:
                full = _compose_bars(opened, layout)
            if wm_text and float(wm_opacity or 0) > 0:
                full = apply_watermark(full, str(wm_text), wm_font, float(wm_opacity), corner=wm_corner,
                                       scale=float(wm_scale or 1.0), color=wm_color or "#ffffff",
                                       wx=wm_x, wy=wm_y)
            flat = Image.alpha_composite(Image.new("RGBA", full.size, (0, 0, 0, 255)), full).convert("RGB")
            flat.save(tmp / f"frame_{index:04d}.png", format="PNG", compress_level=0)
        # --extra is skipped here: at quality 100 it gave the same file size and
        # no visible gain on the VPS, for twice the encode time (6.9 -> 12.3 s).
        return _gifski_from_frames(tmp, out_path, fps=fps, quality=100)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _gif_full_with_bars_workshop(
    gif_path: Path,
    out_path: Path,
    wm_text: str,
    wm_font: str,
    wm_opacity: float,
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    bar_width: int = 6,
    wm_color: str = "#ffffff",
    wm_x: float | None = None,
    wm_y: float | None = None,
) -> None:
    """Full GIF: 5 parts + black bars + watermark. Quantizes each frame immediately."""
    frames_p: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(gif_path) as im:
        n = int(getattr(im, "n_frames", 1) or 1)
        # Cap extreme GIFs to avoid OOM on small Railway instances
        max_frames = 180
        step = 1
        if n > max_frames:
            step = max(1, n // max_frames)
        for idx in range(0, n, step):
            im.seek(idx)
            frame = im.convert("RGBA")
            full = _compose_bars(frame, "workshop")
            if wm_text and float(wm_opacity or 0) > 0:
                full = apply_watermark(
                    full,
                    str(wm_text),
                    wm_font,
                    float(wm_opacity),
                    corner=wm_corner,
                    scale=float(wm_scale or 1.0),
                    color=wm_color or "#ffffff",
                    wx=wm_x,
                    wy=wm_y,
                )
            frames_p.append(_quantize_rgba_for_gif(full))
            try:
                d = int(im.info.get("duration", 100) or 100)
            except Exception:
                d = 100
            durations.append(max(20, d * step))
            # free
            del full, frame
    _save_animated_gif(frames_p, durations, out_path)


def _gif_full_with_bar_split(
    gif_path: Path,
    out_path: Path,
    wm_text: str,
    wm_font: str,
    wm_opacity: float,
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    bar_width: int = 6,
    wm_color: str = "#ffffff",
    wm_x: float | None = None,
    wm_y: float | None = None,
) -> None:
    """Build full-color split/bar frames and let gifski do final quantization."""
    gs = find_gifski()
    if not gs:
        raise RuntimeError("gifski not found")

    tmp = Path(tempfile.mkdtemp(prefix="sm_split_bars_"))
    try:
        frames_dir = tmp / "frames"
        frames_dir.mkdir()

        durations = []
        frame_no = 0

        with Image.open(gif_path) as im:
            n = int(getattr(im, "n_frames", 1) or 1)
            max_frames = 180
            step = 1
            if n > max_frames:
                step = max(1, n // max_frames)

            for idx in range(0, n, step):
                im.seek(idx)
                frame = im.convert("RGBA")
                full = _compose_bars(frame, "split")

                if wm_text and float(wm_opacity or 0) > 0:
                    full = apply_watermark(
                        full,
                        str(wm_text),
                        wm_font,
                        float(wm_opacity),
                        corner=wm_corner,
                        scale=float(wm_scale or 1.0),
                        color=wm_color or "#ffffff",
                        wx=wm_x,
                        wy=wm_y,
                    )

                # Same black alpha composite as old quantizer,
                # but DO NOT reduce to a 256-color Pillow palette.
                bg = Image.new(
                    "RGBA", full.size, (0, 0, 0, 255)
                )
                composed = Image.alpha_composite(bg, full)
                rgb = composed.convert("RGB")

                frame_no += 1
                rgb.save(
                    frames_dir / f"frame_{frame_no:04d}.png",
                    format="PNG",
                    compress_level=0,
                )

                try:
                    d = int(im.info.get("duration", 100) or 100)
                except Exception:
                    d = 100

                durations.append(max(20, d * step))

        if frame_no == 0:
            raise RuntimeError("no frames for split bars")

        # Current Process uses fixed FPS. Keep the same fps behavior
        # used by the existing gifski pipeline.
        if durations:
            avg_ms = sum(durations) / len(durations)
            fps = max(5, min(30, round(1000.0 / avg_ms)))
        else:
            fps = 12

        ok = bool(fit_frames_to_gif(frames_dir, out_path, fps=fps)) or _gifski_from_frames(
            frames_dir,
            out_path,
            fps=fps,
            quality=100,
        )

        if not ok:
            raise RuntimeError("gifski split bars encode failed")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)



def _reencode_crop_hq(
    src_gif: Path,
    dest: Path,
    crop_vf: str,
    fps: int = 12,
    encoder: str = "ffmpeg",
) -> None:
    """Crop a GIF strip and re-encode with max quality (gifski when requested)."""
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found")
    encoder = (encoder or "ffmpeg").strip().lower()
    tmp = Path(tempfile.mkdtemp(prefix="sm_crop_"))
    try:
        frames = tmp / "f"
        frames.mkdir()
        # crop → PNG sequence
        _run([
            ff, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src_gif),
            "-an",
            "-vf", f"{crop_vf},fps={max(5, min(24, int(fps)))}",
            str(frames / "frame_%04d.png"),
        ])
        if not list(frames.glob("frame_*.png")):
            raise RuntimeError("crop produced no frames")
        if encoder == "gifski":
            if not find_gifski():
                raise RuntimeError("gifski selected but binary not found")
            ok = bool(fit_frames_to_gif(frames, dest, fps=fps)) or _gifski_from_frames(frames, dest, fps=fps, quality=100)
            if not ok:
                raise RuntimeError("gifski crop-encode failed (no ffmpeg fallback)")
        else:
            vf = _ffmpeg_palette_vf(fps=fps, max_colors=256)
            _run([
                ff, "-y", "-hide_banner", "-loglevel", "error",
                "-framerate", str(max(5, min(24, int(fps)))),
                "-i", str(frames / "frame_%04d.png"),
                "-lavfi", vf,
                "-loop", "0",
                str(dest),
            ])
        ensure_under_mb(dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class _SynchronizedGroupFitError(RuntimeError):
    """A synchronized output group needs a lower shared FPS."""


def _encode_synchronized_frame_group(
    frame_dirs: list[Path],
    destinations: list[Path],
    fps: int,
    encoder: str,
    label: str,
    max_mb: float = MAX_STEAM_MB,
) -> dict[str, int | str]:
    """Encode related panels with one shared quality setting.

    Every attempt uses the same encoder settings for every panel. The highest
    common setting for which every panel fits Steam's limit wins. This avoids
    visible seams and timing drift in Workshop and Artwork Split outputs.
    """
    if not frame_dirs or len(frame_dirs) != len(destinations):
        raise ValueError("Synchronized encoding requires matching frame sets and destinations")

    fps = max(5, min(24, int(fps)))
    encoder = (encoder or "ffmpeg").strip().lower()
    if encoder == "pillow":
        encoder = "ffmpeg"
    safe_label = "".join(char for char in str(label).lower() if char.isalnum()) or "group"
    attempts_root = Path(tempfile.mkdtemp(prefix=f"sm_{safe_label}_group_"))

    def fits(paths: list[Path]) -> bool:
        return all(path.is_file() and 50 < path.stat().st_size <= max_mb * 1024 * 1024 for path in paths)

    def install(paths: list[Path]) -> None:
        for source, destination in zip(paths, destinations):
            _safe_replace(source, destination)

    try:
        if encoder == "gifski":
            if not find_gifski():
                raise RuntimeError("gifski selected but binary not found")
            fast = encode_fast()  # read here: the pool threads below do not see the ContextVar

            def encode_quality(quality: int, extra: bool = False) -> list[Path]:
                attempt_dir = attempts_root / f"q_{quality}{'x' if extra else ''}"
                attempt_dir.mkdir()
                outputs = [attempt_dir / f"part_{index}.gif" for index in range(1, len(frame_dirs) + 1)]
                # Panels are narrow, so one gifski cannot keep every core busy;
                # encoding them side by side is several times faster.
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(len(frame_dirs), os.cpu_count() or 2)) as pool:
                    done = list(pool.map(
                        lambda pair: _gifski_from_frames(pair[0], pair[1], fps=fps, quality=quality,
                                                         extra=extra, fast=fast),
                        zip(frame_dirs, outputs),
                    ))
                for index, ok in enumerate(done, start=1):
                    if not ok:
                        raise RuntimeError(f"gifski failed for Workshop part {index}")
                _LOG.info(f"[{label.upper()} GROUP] gifski q={quality} fps={fps} sizes="
                    + ",".join(f"{_gif_mb(path):.2f}" for path in outputs))
                return outputs

            def install_best(quality: int, fast_paths: list[Path]) -> dict[str, int | str]:
                if fast:
                    install(fast_paths)
                    return {"encoder": "gifski", "quality": quality, "fps": fps, "fast": 1}
                # Final encode with gifski --extra (smoother gradients); it can
                # grow a few KB, so step down a little when it stops fitting.
                for candidate in range(quality, max(1, quality - 4) - 1, -1):
                    refined = encode_quality(candidate, extra=True)
                    if fits(refined):
                        install(refined)
                        return {"encoder": "gifski", "quality": candidate, "fps": fps, "extra": 1}
                install(fast_paths)
                return {"encoder": "gifski", "quality": quality, "fps": fps}

            attempts: dict[int, list[Path]] = {}

            def group_size(quality: int) -> int:
                # The group fits only when its largest panel fits.
                attempts[quality] = encode_quality(quality)
                return max(path.stat().st_size for path in attempts[quality])

            best_quality = _best_quality(group_size, int(max_mb * 1024 * 1024))
            best_paths = attempts.get(best_quality) if best_quality else None
            if best_paths is None:
                raise _SynchronizedGroupFitError(
                    f"{label} cannot fit all synchronized panels under 5 MB "
                    "without changing their shared FPS or dimensions"
                )
            return install_best(best_quality, best_paths)

        ff = find_ffmpeg()
        if not ff:
            raise RuntimeError("FFmpeg not found")

        def encode_colors(colors: int) -> list[Path]:
            attempt_dir = attempts_root / f"colors_{colors}"
            attempt_dir.mkdir()
            outputs: list[Path] = []
            for index, frames_dir in enumerate(frame_dirs, start=1):
                output = attempt_dir / f"part_{index}.gif"
                _run([
                    ff, "-y", "-hide_banner", "-loglevel", "error",
                    "-framerate", str(fps),
                    "-i", str(frames_dir / "frame_%04d.png"),
                    "-lavfi", _ffmpeg_palette_vf(fps=fps, max_colors=colors),
                    "-loop", "0", str(output),
                ])
                outputs.append(output)
            _LOG.info(f"[{label.upper()} GROUP] ffmpeg colors={colors} fps={fps} sizes="
                + ",".join(f"{_gif_mb(path):.2f}" for path in outputs))
            return outputs

        highest = encode_colors(256)
        if fits(highest):
            install(highest)
            return {"encoder": "ffmpeg", "quality": 256, "fps": fps}

        low, high = 32, 255
        best_colors = 0
        best_paths = None
        while low <= high:
            colors = (low + high) // 2
            outputs = encode_colors(colors)
            if fits(outputs):
                best_colors = colors
                best_paths = outputs
                low = colors + 1
            else:
                high = colors - 1
        if best_paths is None:
            raise _SynchronizedGroupFitError(
                f"{label} cannot fit all synchronized panels under 5 MB "
                "without changing their shared FPS or dimensions"
            )
        install(best_paths)
        return {"encoder": "ffmpeg", "quality": best_colors, "fps": fps}
    finally:
        shutil.rmtree(attempts_root, ignore_errors=True)


def _synchronized_fps_candidates(requested_fps: int) -> list[int]:
    requested = max(5, min(24, int(requested_fps)))
    candidates: list[int] = []
    for candidate in (requested, 20, 18, 15, 12, 10, 8, 6, 5):
        if candidate <= requested and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _select_synchronized_frame_group(
    temp: Path,
    destinations: list[Path],
    requested_fps: int,
    encoder: str,
    label: str,
    prepare,
) -> tuple[Path, dict[str, int | str], int]:
    """Prepare and fit a related panel group without per-panel divergence."""
    last_fit_error: Exception | None = None
    for candidate_fps in _synchronized_fps_candidates(requested_fps):
        candidate_dir = temp / f"fps_{candidate_fps}"
        candidate_dir.mkdir()
        full_frames, frame_dirs, frame_count = prepare(candidate_dir, candidate_fps)
        try:
            settings = _encode_synchronized_frame_group(
                frame_dirs, destinations, fps=candidate_fps,
                encoder=encoder, label=label,
            )
        except _SynchronizedGroupFitError as exc:
            last_fit_error = exc
            shutil.rmtree(candidate_dir, ignore_errors=True)
            continue
        return full_frames, settings, frame_count
    raise RuntimeError(str(last_fit_error or f"{label} group encoding failed"))


def _prepare_workshop_frame_sets(
    source: Path,
    work_dir: Path,
    fps: int,
    width: int,
    rotation: float = 0,
    duration: float | None = None,
    outline_width: int = 0,
    outline_color: str = "#ffffff",
    frame_fx: dict | None = None,
    need_full: bool = True,
) -> tuple[Path, list[Path], int]:
    """Decode once, then derive five perfectly aligned lossless frame sets.

    ``frame_fx`` (smweb.square_fx frame options) replaces the plain outline and
    is drawn on the full frame at loop position index/count, so animated
    outlines stay synchronized across the five panels and loop seamlessly.
    """
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found")
    fps = max(5, min(24, int(fps)))
    width = max(200, min(1200, int(width or 750)))
    width -= width % 5
    if width < 200:
        width = 200

    full_frames = work_dir / "full_frames"
    full_frames.mkdir()
    part_dirs = [work_dir / f"part_{index}_frames" for index in range(1, 6)]
    for part_dir in part_dirs:
        part_dir.mkdir()
    part_width = width // 5
    stroke = 0 if frame_fx else max(0, min(12, int(outline_width or 0)))
    stroke_color = _parse_rgb(outline_color)
    draw_frame = None
    if frame_fx and frame_fx.get("style", "none") != "none":
        from smweb.square_fx import draw_frame

    rotation_filter = _ffmpeg_rotation_filter(rotation)
    video_filter = ",".join(part for part in (
        rotation_filter,
        f"fps={fps}",
        f"scale={width}:-2:flags={SCALE_FLAGS}{source_matrix(source)}",
    ) if part)
    command = [
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source),
    ]
    if duration is not None:
        command.extend(["-t", str(max(1.0, min(20.0, float(duration))))])

    if not draw_frame:
        # Fast path: one FFmpeg run decodes once and writes the five panel
        # sequences (plus the full frames only when an extra file needs them).
        # Same pixels as the Pillow crop below; the plain outline is a drawbox
        # of the same thickness, drawn in RGBA so the edge keeps its colour.
        # `-t` is an output option that binds to the next output only, so every
        # output repeats it (otherwise only part 1 is cut to the duration).
        limit = command[-2:] if duration is not None else []
        del command[len(command) - len(limit):]
        outputs = 5 + (1 if need_full else 0)
        graph = [f"[0:v]{video_filter},format=rgba,split={outputs}" + "".join(f"[s{i}]" for i in range(outputs))]
        hex_color = "0x%02x%02x%02x" % stroke_color
        for index in range(5):
            box = f",drawbox=x=0:y=0:w=iw:h=ih:color={hex_color}@1:t={stroke}" if stroke else ""
            graph.append(f"[s{index}]crop={part_width}:ih:{index * part_width}:0{box}[p{index}]")
        command.extend(["-an", "-filter_complex", ";".join(graph)])
        for index, part_dir in enumerate(part_dirs):
            command.extend(["-map", f"[p{index}]", *limit, "-compression_level", "0", str(part_dir / "frame_%04d.png")])
        if need_full:
            command.extend(["-map", "[s5]", *limit, "-compression_level", "0", str(full_frames / "frame_%04d.png")])
        _run(command)
        count = len(list(part_dirs[0].glob("frame_*.png")))
        if not count:
            raise RuntimeError("Workshop source produced no frames")
        return full_frames, part_dirs, count

    command.extend([
        "-an", "-vf", video_filter, "-compression_level", "0",
        str(full_frames / "frame_%04d.png"),
    ])
    _run(command)

    frame_files = sorted(full_frames.glob("frame_*.png"))
    if not frame_files:
        raise RuntimeError("Workshop source produced no frames")

    for frame_index, frame_path in enumerate(frame_files):
        with Image.open(frame_path) as opened:
            frame = opened.convert("RGBA")
        if frame.width != width:
            raise RuntimeError(f"Workshop frame width mismatch: {frame.width} != {width}")
        if draw_frame:
            frame = draw_frame(frame, frame_index / len(frame_files), frame_fx)
        for index, part_dir in enumerate(part_dirs):
            left = index * part_width
            part = frame.crop((left, 0, left + part_width, frame.height))
            if stroke:
                draw = ImageDraw.Draw(part)
                for offset in range(stroke):
                    draw.rectangle(
                        (offset, offset, part.width - 1 - offset, part.height - 1 - offset),
                        outline=stroke_color,
                        width=1,
                    )
            part.save(part_dir / frame_path.name, format="PNG", compress_level=0)
    return full_frames, part_dirs, len(frame_files)


def process_gif_workshop(
    gif_path: Path,
    out_dir: Path,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    encoder: str = "ffmpeg",
    fps: int = 12,
    outline_width: int = 0,
    outline_color: str = "#ffffff",
    rotation: float = 0,
    width: int = 750,
    duration: float | None = None,
    frame_fx: dict | None = None,
    extras=None,
) -> dict[str, Path]:
    """Create five synchronized Workshop GIFs at one common quality.

    ``extras`` (default: all) picks the optional full-width files:
    EXTRA_ORIGINAL -> full_original.gif, EXTRA_PREVIEW -> full_with_bars.gif.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    extras = _extras(extras)
    temp = Path(tempfile.mkdtemp(prefix="sm_workshop_frames_"))
    result: dict[str, Path] = {}
    clean = out_dir / "full_original.gif"
    bars = out_dir / "full_with_bars.gif"
    bars_done = False
    try:
        destinations = [out_dir / f"part_{index}.gif" for index in range(1, 6)]
        requested_fps = max(5, min(24, int(fps)))

        def prepare(candidate_dir: Path, candidate_fps: int):
            return _prepare_workshop_frame_sets(
                Path(gif_path), candidate_dir, fps=candidate_fps, width=width,
                rotation=normalize_rotation(rotation), duration=duration,
                outline_width=outline_width, outline_color=outline_color, frame_fx=frame_fx,
                need_full=bool(extras),
            )

        full_frames, settings, frame_count = _select_synchronized_frame_group(
            temp, destinations, requested_fps=requested_fps,
            encoder=encoder, label="Workshop", prepare=prepare,
        )
        _LOG.info(f"[WORKSHOP GROUP] selected encoder={settings['encoder']} "
            f"quality={settings['quality']} fps={settings['fps']} frames={frame_count}")
        for output in destinations:
            apply_hex21_file(output)
            result[output.name] = output

        def encode_clean() -> None:
            if (encoder or "").strip().lower() == "gifski":
                if not _gifski_from_frames(full_frames, clean, fps=int(settings["fps"]), quality=100):
                    raise RuntimeError("gifski failed to create Workshop full preview")
            else:
                encode_gif_from_png_sequence(full_frames, clean, fps=int(settings["fps"]), encoder="ffmpeg")

        if EXTRA_ORIGINAL in extras:
            encode_clean()
            result[clean.name] = clean
        if EXTRA_PREVIEW in extras:
            try:
                bars_done = _bars_gif_from_frames(full_frames, bars, "workshop", int(settings["fps"]), wm_text, wm_font, wm_opacity, wm_corner=wm_corner, wm_scale=wm_scale, wm_color=wm_color, wm_x=wm_x, wm_y=wm_y)
            except Exception:
                import traceback
                traceback.print_exc()
            if not bars_done and not clean.is_file():
                encode_clean()  # the fallback below rebuilds the preview from it
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    if EXTRA_PREVIEW not in extras:
        return result
    try:
        if bars_done:
            result[bars.name] = bars
            return result
        _gif_full_with_bars_workshop(
            clean, bars, wm_text, wm_font, wm_opacity,
            wm_corner=wm_corner, wm_scale=wm_scale, wm_color=wm_color,
            wm_x=wm_x, wm_y=wm_y,
        )
        if bars.is_file():
            result[bars.name] = bars
        else:
            err = out_dir / "full_with_bars_ERROR.txt"
            err.write_text("full_with_bars.gif missing after save", encoding="utf-8")
            result[err.name] = err
    except Exception as e:
        import traceback
        traceback.print_exc()
        err = out_dir / "full_with_bars_ERROR.txt"
        err.write_text(f"{type(e).__name__}: {e}\n", encoding="utf-8")
        result[err.name] = err
    return result



def _iter_gif_frames(im: Image.Image, max_frames: int = 180):
    """Safely iterate GIF frames without relying on n_frames (can IndexError on odd GIFs)."""
    frames: list[tuple[Image.Image, int]] = []
    idx = 0
    while True:
        try:
            im.seek(idx)
        except EOFError:
            break
        except Exception:
            # broken trailer / odd GIF — stop if we already have frames
            if frames:
                break
            # first frame must work
            im.seek(0)
            frame = im.convert("RGBA")
            try:
                d = int(im.info.get("duration", 100) or 100)
            except Exception:
                d = 100
            frames.append((frame, max(20, d)))
            break
        try:
            frame = im.convert("RGBA")
        except Exception:
            if frames:
                break
            raise
        try:
            d = int(im.info.get("duration", 100) or 100)
        except Exception:
            d = 100
        frames.append((frame, max(20, d)))
        idx += 1
        if idx >= 5000:  # hard safety
            break
    if not frames:
        im.seek(0)
        frame = im.convert("RGBA")
        frames.append((frame, 100))
    # subsample if too many frames
    if len(frames) > max_frames:
        step = max(1, len(frames) // max_frames)
        frames = frames[::step]
    return frames


def _gif_watermark_gifski(gif_path: Path, out_path: Path, wm_text: str, wm_font: str, wm_opacity: float,
                          wm_corner: str, wm_scale: float, wm_color: str, wm_x, wm_y) -> bool:
    if not find_gifski():
        return False
    tmp = Path(tempfile.mkdtemp(prefix="sm_wm_"))
    try:
        with Image.open(gif_path) as im:
            raw_frames = _iter_gif_frames(im, max_frames=180)
        if not raw_frames:
            return False
        durations = sorted(max(20, int(d or 100)) for _frame, d in raw_frames)
        fps = max(5, min(30, round(1000 / durations[len(durations) // 2])))
        for index, (frame, _d) in enumerate(raw_frames, start=1):
            if wm_text and float(wm_opacity or 0) > 0:
                frame = apply_watermark(frame, str(wm_text), wm_font, float(wm_opacity), corner=wm_corner,
                                        scale=float(wm_scale or 1.0), color=wm_color or "#ffffff", wx=wm_x, wy=wm_y)
            flat = Image.alpha_composite(Image.new("RGBA", frame.size, (0, 0, 0, 255)), frame.convert("RGBA"))
            flat.convert("RGB").save(tmp / f"frame_{index:04d}.png", format="PNG", compress_level=0)
        return _gifski_from_frames(tmp, out_path, fps=fps, quality=90)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _gif_apply_watermark(
    gif_path: Path,
    out_path: Path,
    wm_text: str,
    wm_font: str,
    wm_opacity: float,
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_color: str = "#ffffff",
    wm_x: float | None = None,
    wm_y: float | None = None,
    encoder: str = "ffmpeg",
    fps: int = 12,
) -> None:
    """Apply watermark on every frame of a GIF and re-encode.

    gifski keeps the copy close to the source size (it reuses unchanged pixels
    between frames); the Pillow fallback quantized every frame on its own and
    made a 4.8 MB Featured GIF into a 29 MB one.
    """
    if _gif_watermark_gifski(gif_path, out_path, wm_text, wm_font, wm_opacity, wm_corner,
                             wm_scale, wm_color, wm_x, wm_y):
        return
    frames_p: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(gif_path) as im:
        raw_frames = _iter_gif_frames(im, max_frames=180)
    for frame, d in raw_frames:
        if wm_text and float(wm_opacity or 0) > 0:
            frame = apply_watermark(
                frame,
                str(wm_text),
                wm_font,
                float(wm_opacity),
                corner=wm_corner,
                scale=float(wm_scale or 1.0),
                color=wm_color or "#ffffff",
                wx=wm_x,
                wy=wm_y,
            )
        frames_p.append(_quantize_rgba_for_gif(frame))
        durations.append(d)
    if not frames_p:
        raise RuntimeError("no frames for watermarked GIF")
    _save_animated_gif(frames_p, durations, out_path)


def process_gif_featured(
    gif_path: Path,
    out_dir: Path,
    fps: int = 12,
    encoder: str = "ffmpeg",
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    rotation: float = 0,
    frame_fx: dict | None = None,
    duration: float | None = 10,
    extras=None,
) -> dict[str, Path]:
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg не найден")
    extras = _extras(extras)
    out = out_dir / "featured_630.gif"
    if _active_frame(frame_fx):
        # Styled frame drawn per decoded frame (loop position index/count), then
        # fitted to the Steam limit by the same encoder as the panel groups.
        temp = Path(tempfile.mkdtemp(prefix="sm_featured_frames_"))
        try:
            def prepare(candidate_dir: Path, candidate_fps: int):
                return _prepare_featured_frame_sets(
                    Path(gif_path), candidate_dir, fps=candidate_fps,
                    rotation=normalize_rotation(rotation), duration=duration, frame_fx=frame_fx,
                )
            _select_synchronized_frame_group(
                temp, [out], requested_fps=max(5, min(24, int(fps))),
                encoder=encoder, label="Featured", prepare=prepare,
            )
        finally:
            shutil.rmtree(temp, ignore_errors=True)
    else:
        media_to_gif(gif_path, out, fps=fps, width=630, duration=duration or 10, encoder=encoder, rotation=rotation)
        ensure_under_mb(out)
    apply_hex21_file(out)
    result = {out.name: out}
    if EXTRA_ORIGINAL in extras:
        clean = out_dir / "full_original.gif"
        shutil.copy2(out, clean)
        result[clean.name] = clean
    # Watermarked animated copy
    if EXTRA_PREVIEW in extras and wm_text and float(wm_opacity or 0) > 0:
        wm_out = out_dir / "full_with_watermark.gif"
        try:
            _gif_apply_watermark(
                out, wm_out, wm_text, wm_font, wm_opacity,
                wm_corner=wm_corner, wm_scale=wm_scale, wm_color=wm_color,
                wm_x=wm_x, wm_y=wm_y, encoder=encoder, fps=fps,
            )
            if wm_out.is_file() and wm_out.stat().st_size > 64:
                # Full preview is not subject to the Steam 5 MB limit.
                # Keep the original maximum-quality output.
                result[wm_out.name] = wm_out
                result["full_with_bars.gif"] = wm_out
            else:
                # fallback: static first frame with WM
                with Image.open(out) as im:
                    im.seek(0)
                    frame = im.convert("RGBA")
                wm_img = apply_watermark(
                    frame, wm_text, wm_font, wm_opacity,
                    corner=wm_corner, scale=wm_scale, color=wm_color, wx=wm_x, wy=wm_y,
                )
                static = out_dir / "full_with_watermark.png"
                static.write_bytes(_png_bytes(wm_img))
                result[static.name] = static
                result["full_with_bars.png"] = static
        except Exception as e:
            import traceback
            traceback.print_exc()
            err = out_dir / "full_with_watermark_ERROR.txt"
            err.write_text(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}", encoding="utf-8")
            result[err.name] = err
    return result



def _prepare_featured_frame_sets(
    source: Path,
    work_dir: Path,
    fps: int,
    rotation: float = 0,
    duration: float | None = 10,
    frame_fx: dict | None = None,
) -> tuple[Path, list[Path], int]:
    """Decode a Featured source at 630 px and draw the styled frame on every frame."""
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found")
    fps = max(5, min(24, int(fps)))
    frames_dir = work_dir / "featured_frames"
    frames_dir.mkdir()
    video_filter = ",".join(part for part in (
        _ffmpeg_rotation_filter(rotation),
        f"fps={fps}",
        f"scale=630:-2:flags={SCALE_FLAGS}{source_matrix(source)}",
    ) if part)
    command = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source)]
    if duration is not None:
        command.extend(["-t", str(max(1.0, min(20.0, float(duration))))])
    command.extend(["-an", "-vf", video_filter, "-compression_level", "0", str(frames_dir / "frame_%04d.png")])
    _run(command)
    frame_files = sorted(frames_dir.glob("frame_*.png"))
    if not frame_files:
        raise RuntimeError("Featured source produced no frames")
    for index, frame_path in enumerate(frame_files):
        with Image.open(frame_path) as opened:
            frame = opened.convert("RGBA")
        _draw_whole_frame(frame, index / len(frame_files), frame_fx).save(frame_path, format="PNG", compress_level=0)
    return frames_dir, [frames_dir], len(frame_files)


def _prepare_split_frame_sets(
    source: Path,
    work_dir: Path,
    fps: int,
    rotation: float = 0,
    duration: float | None = 10,
    frame_fx: dict | None = None,
    need_full: bool = True,
) -> tuple[Path, list[Path], int]:
    """Decode once and derive aligned 506 px + 100 px lossless frames.

    The optional styled frame is drawn at loop position index/count, so the two
    parts stay synchronized and loop seamlessly; ``full_frames`` stay unframed.
    """
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found")
    fps = max(5, min(24, int(fps)))
    full_frames = work_dir / "full_frames"
    center_frames = work_dir / "center_frames"
    side_frames = work_dir / "side_frames"
    full_frames.mkdir()
    center_frames.mkdir()
    side_frames.mkdir()

    rotation_filter = _ffmpeg_rotation_filter(rotation)
    video_filter = ",".join(part for part in (
        rotation_filter,
        f"fps={fps}",
        f"scale=606:-2:flags={SCALE_FLAGS}{source_matrix(source)}",
    ) if part)
    command = [
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source),
    ]
    if duration is not None:
        command.extend(["-t", str(max(1.0, min(20.0, float(duration))))])
    if not _active_frame(frame_fx):
        # Fast path without a frame: one FFmpeg run writes both parts directly
        # (same crop as _split_parts), full frames only when an extra needs them.
        # `-t` binds to the next output only, so it is repeated for each one.
        limit = command[-2:] if duration is not None else []
        del command[len(command) - len(limit):]
        outputs = 3 if need_full else 2
        graph = (f"[0:v]{video_filter},format=rgba,split={outputs}" + "".join(f"[s{i}]" for i in range(outputs))
                 + ";[s0]crop=506:ih:0:0[c];[s1]crop=100:ih:506:0[d]")
        command.extend(["-an", "-filter_complex", graph,
                        "-map", "[c]", *limit, "-compression_level", "0", str(center_frames / "frame_%04d.png"),
                        "-map", "[d]", *limit, "-compression_level", "0", str(side_frames / "frame_%04d.png")])
        if need_full:
            command.extend(["-map", "[s2]", *limit, "-compression_level", "0", str(full_frames / "frame_%04d.png")])
        _run(command)
        count = len(list(center_frames.glob("frame_*.png")))
        if not count:
            raise RuntimeError("Artwork Split source produced no frames")
        return full_frames, [center_frames, side_frames], count
    command.extend([
        "-an", "-vf", video_filter, "-compression_level", "0",
        str(full_frames / "frame_%04d.png"),
    ])
    _run(command)

    frame_files = sorted(full_frames.glob("frame_*.png"))
    if not frame_files:
        raise RuntimeError("Artwork Split source produced no frames")
    for frame_index, frame_path in enumerate(frame_files):
        with Image.open(frame_path) as opened:
            frame = opened.convert("RGBA")
        if frame.width != 606:
            raise RuntimeError(f"Artwork Split frame width mismatch: {frame.width} != 606")
        center, side = _split_parts(frame, frame_index / len(frame_files), frame_fx)
        center.save(center_frames / frame_path.name, format="PNG", compress_level=0)
        side.save(side_frames / frame_path.name, format="PNG", compress_level=0)
    return full_frames, [center_frames, side_frames], len(frame_files)



def process_gif_split(
    gif_path: Path,
    out_dir: Path,
    fps: int = 12,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
    wm_x: float | None = None,
    wm_y: float | None = None,
    encoder: str = "ffmpeg",
    rotation: float = 0,
    duration: float | None = 10,
    frame_fx: dict | None = None,
    extras=None,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    extras = _extras(extras)
    temp = Path(tempfile.mkdtemp(prefix="sm_split_frames_"))
    center = out_dir / "center_506.gif"
    side = out_dir / "side_100.gif"
    destinations = [center, side]
    result: dict[str, Path] = {}
    clean = out_dir / "full_original.gif"
    bars = out_dir / "full_with_bars.gif"
    bars_done = False
    try:
        requested_fps = max(5, min(24, int(fps)))

        def prepare(candidate_dir: Path, candidate_fps: int):
            return _prepare_split_frame_sets(
                Path(gif_path), candidate_dir, fps=candidate_fps,
                rotation=normalize_rotation(rotation), duration=duration, frame_fx=frame_fx,
                need_full=bool(extras),
            )

        full_frames, settings, frame_count = _select_synchronized_frame_group(
            temp, destinations, requested_fps=requested_fps,
            encoder=encoder, label="Split", prepare=prepare,
        )
        _LOG.info(f"[SPLIT GROUP] selected encoder={settings['encoder']} "
            f"quality={settings['quality']} fps={settings['fps']} frames={frame_count}")
        for output in destinations:
            apply_hex21_file(output)
            result[output.name] = output

        def encode_clean() -> None:
            if (encoder or "").strip().lower() == "gifski":
                if not _gifski_from_frames(full_frames, clean, fps=int(settings["fps"]), quality=100):
                    raise RuntimeError("gifski failed to create Artwork Split full preview")
            else:
                encode_gif_from_png_sequence(full_frames, clean, fps=int(settings["fps"]), encoder="ffmpeg")

        if EXTRA_ORIGINAL in extras:
            encode_clean()
            result[clean.name] = clean
        if EXTRA_PREVIEW in extras:
            try:
                bars_done = _bars_gif_from_frames(full_frames, bars, "split", int(settings["fps"]), wm_text, wm_font, wm_opacity, wm_corner=wm_corner, wm_scale=wm_scale, wm_color=wm_color, wm_x=wm_x, wm_y=wm_y)
            except Exception:
                import traceback
                traceback.print_exc()
            if not bars_done and not clean.is_file():
                encode_clean()  # the fallback below rebuilds the preview from it
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    if EXTRA_PREVIEW not in extras:
        return result
    try:
        if bars_done:
            result[bars.name] = bars
            return result
        _gif_full_with_bar_split(
            clean, bars, wm_text, wm_font, wm_opacity,
            wm_corner=wm_corner, wm_scale=wm_scale, wm_color=wm_color, wm_x=wm_x, wm_y=wm_y,
        )
        if bars.is_file() and bars.stat().st_size > 64:
            result[bars.name] = bars
        else:
            err = out_dir / "full_with_bars_ERROR.txt"
            err.write_text("full_with_bars.gif was not created (empty output)", encoding="utf-8")
            result[err.name] = err
    except Exception as e:
        import traceback
        traceback.print_exc()
        err = out_dir / "full_with_bars_ERROR.txt"
        err.write_text(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}", encoding="utf-8")
        result[err.name] = err
    return result



def convert_media(
    src: Path,
    dest: Path,
    target: str,
    fps: int = 12,
    width: int = 750,
    duration: float = 12.0,
) -> Path:
    """Convert between common formats: gif, mp4, webm, png, jpg, webp."""
    src = Path(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    target = (target or "").lower().lstrip(".")
    if target == "jpeg":
        target = "jpg"
    if not src.is_file():
        raise RuntimeError("source missing")

    img_exts = {"png", "jpg", "jpeg", "webp", "bmp"}
    vid_exts = {"mp4", "webm", "mov", "avi", "mkv", "gif"}
    src_ext = src.suffix.lower().lstrip(".")

    # Image → image via Pillow
    if target in img_exts and src_ext in img_exts | {"gif"}:
        im = Image.open(src)
        if target in ("jpg", "jpeg"):
            im = im.convert("RGB")
            im.save(dest, format="JPEG", quality=92)
        elif target == "png":
            im = im.convert("RGBA") if im.mode in ("P", "RGBA", "LA") else im.convert("RGBA")
            im.save(dest, format="PNG")
        elif target == "webp":
            im.save(dest, format="WEBP", quality=90)
        else:
            im.save(dest)
        if not dest.is_file() or dest.stat().st_size < 10:
            raise RuntimeError("image convert failed")
        return dest

    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not available")

    fps = max(5, min(30, int(fps)))
    width = max(200, min(1920, int(width)))
    if width % 2:
        width -= 1
    duration = float(duration or 0)
    if duration > 0:
        duration = max(1.0, min(120.0, duration))

    if target == "gif":
        d = duration if duration > 0 else 120.0
        w = width if width and width > 0 else 720
        media_to_gif(src, dest, fps=fps, width=w, duration=d)
        return dest

    if target in ("mp4", "webm", "mov"):
        # GIF/video → video
        vf = f"scale={width}:-2:flags=lanczos"
        def _vid_cmd(codec_args):
            cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src)]
            if duration > 0:
                cmd += ["-t", str(duration)]
            cmd += ["-vf", vf, "-an"] + codec_args + [str(dest)]
            return cmd
        if target == "mp4":
            cmd = _vid_cmd(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
        elif target == "webm":
            cmd = _vid_cmd(["-c:v", "libvpx-vp9", "-b:v", "1M"])
        else:
            cmd = _vid_cmd(["-c:v", "libx264", "-pix_fmt", "yuv420p"])
        _run(cmd)
        if not dest.is_file() or dest.stat().st_size < 50:
            raise RuntimeError("video convert failed")
        return dest

    if target in img_exts:
        # video/gif → single frame image
        cmd = [
            ff, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src), "-vf", f"scale={width}:-2",
            "-frames:v", "1",
            str(dest),
        ]
        _run(cmd)
        if not dest.is_file():
            raise RuntimeError("frame extract failed")
        return dest

    raise RuntimeError(f"unsupported target: {target}")


def hex21_bytes(data: bytes) -> bytes:
    return apply_hex21(data)



# ─── Character + background compose ─────────────────────────────────────────

def _hex_to_rgb(s: str) -> tuple[int, int, int]:
    s = (s or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return (0, 255, 0)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def remove_chromakey(
    img: Image.Image,
    key: str = "auto",
    tolerance: float = 55.0,
    softness: float = 16.0,
    holes: bool = True,
) -> Image.Image:
    """Remove a solid backdrop of any colour from one picture (smweb.chroma_matte).

    ``key``: auto | green | blue | red | white | black | #rrggbb | none. Clips should go
    through ``key_character_frames`` so the whole clip shares one backdrop model.
    """
    from smweb import chroma_matte
    keyed = chroma_matte.key_frames([img.convert("RGBA")], key, tolerance, softness, holes)[0]
    return Image.fromarray(keyed, mode="RGBA")


def key_character_frames(frames: list[Image.Image], key: str = "auto", tolerance: float = 55.0,
                         feather: float = 1.6, holes: bool = True) -> list[Image.Image]:
    """Key a character clip with ONE backdrop model and frame-to-frame smoothing, then
    crop every frame with the same box (the union of the figure over the clip).

    Per-frame keying re-measured the backdrop on every frame (flicker) and per-frame
    cropping changed the figure's size whenever an arm moved (the figure "breathed").
    """
    from smweb import chroma_matte
    frames = [frame.convert("RGBA") for frame in frames]
    if key and key not in ("none", "0", "off", ""):
        frames = [Image.fromarray(array, mode="RGBA")
                  for array in chroma_matte.key_frames(frames, key, tolerance, 16, holes)]
        if feather and float(feather) > 0:
            frames = [feather_alpha(frame, radius=float(feather)) for frame in frames]
    box = None
    for frame in frames:
        bbox = frame.getchannel("A").getbbox()
        if bbox:
            box = bbox if box is None else (min(box[0], bbox[0]), min(box[1], bbox[1]),
                                            max(box[2], bbox[2]), max(box[3], bbox[3]))
    if box is None:
        return frames
    width, height = frames[0].size
    box = (max(0, box[0] - 2), max(0, box[1] - 2), min(width, box[2] + 2), min(height, box[3] + 2))
    return [frame.crop(box) for frame in frames]


def _place_character(
    bg: Image.Image,
    char: Image.Image,
    scale: float = 1.0,
    offset_x: float = 0.5,
    offset_y: float = 1.0,
    rotation: float = 0.0,
) -> Image.Image:
    """Paste character on bg. offset_x/y are anchor 0..1 (0.5,1 = bottom-center).

    Scale is relative to ~85% of background height. No max-width clamp —
    chromakey sources are often much larger than the subject, so the user
    must be able to enlarge freely (overflow is cropped to the BG).
    """
    bg = bg.convert("RGBA")
    char = char.convert("RGBA")
    char = rotate_image(char, rotation)
    bw, bh = bg.size
    scale = max(0.05, min(4.0, float(scale or 1.0)))
    # fit character height to ~85% of bg by default when scale=1
    target_h = max(1, int(bh * 0.85 * scale))
    ratio = target_h / max(1, char.height)
    nw = max(1, int(char.width * ratio))
    nh = max(1, target_h)
    # no width clamp — allow character larger than background
    char_r = char.resize((nw, nh), Image.Resampling.LANCZOS)
    # anchor point on character: bottom-center
    ax = int(bw * max(0.0, min(1.0, offset_x)) - nw / 2)
    ay = int(bh * max(0.0, min(1.0, offset_y)) - nh)
    # soft clamp so at least 1px stays on canvas
    ax = max(-nw + 1, min(bw - 1, ax))
    ay = max(-nh + 1, min(bh - 1, ay))
    out = bg.copy()
    # Robust paste: always use intermediate layer so overflow / negative
    # offsets work on every Pillow version (alpha_composite(dest=) is flaky).
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(char_r, (ax, ay), char_r)
    out = Image.alpha_composite(out, layer)
    return out


def _crop_to_alpha(char: Image.Image, pad: int = 2) -> Image.Image:
    """Tight crop to non-transparent pixels so scale is based on the subject, not green frame."""
    char = char.convert("RGBA")
    bbox = char.split()[-1].getbbox()
    if not bbox:
        return char
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(char.width, r + pad)
    b = min(char.height, b + pad)
    return char.crop((l, t, r, b))


def feather_alpha(char: Image.Image, radius: float = 1.6) -> Image.Image:
    """Soft-edge the alpha channel after chromakey (anti-alias / de-fringe).

    Blurs alpha only so RGB stays sharp. Interior stays fully opaque;
    fully transparent stays transparent — only the cut edge softens.
    radius ~1.2–2.5 looks natural.
    """
    from PIL import ImageFilter, ImageMath

    char = char.convert("RGBA")
    if radius is None or float(radius) <= 0:
        return char
    r, g, b, a = char.split()
    a_soft = a.filter(ImageFilter.GaussianBlur(radius=max(0.4, float(radius))))
    try:
        # edge = min(original, blurred); solid interior (a>250) keeps original
        a_edge = ImageMath.eval("min(o, s)", o=a, s=a_soft).convert("L")
        # mask of solid interior
        a_solid_mask = a.point(lambda p: 255 if p > 250 else 0)
        a_final = Image.composite(a, a_edge, a_solid_mask)
        # never revive fully-transparent pixels
        a_zero_mask = a.point(lambda p: 255 if p > 0 else 0)
        a_final = Image.composite(a_final, Image.new("L", a.size, 0), a_zero_mask)
    except Exception:
        a_final = a_soft
    return Image.merge("RGBA", (r, g, b, a_final))


def compose_static(
    bg: Image.Image,
    char: Image.Image,
    *,
    chroma_key: str = "auto",
    chroma_tol: float = 40.0,
    scale: float = 1.0,
    offset_x: float = 0.5,
    offset_y: float = 1.0,
    feather: float = 1.6,
    rotation: float = 0.0,
    chroma_holes: bool = True,
) -> Image.Image:
    char = key_character_frames([char], chroma_key, chroma_tol, feather, chroma_holes)[0]
    return _place_character(
        bg, char, scale=scale, offset_x=offset_x, offset_y=offset_y,
        rotation=rotation,
    )


def compose_animated(
    bg: Image.Image,
    char_path: Path,
    *,
    chroma_key: str = "auto",
    chroma_tol: float = 40.0,
    scale: float = 1.0,
    offset_x: float = 0.5,
    offset_y: float = 1.0,
    feather: float = 1.6,
    max_frames: int = 120,
    rotation: float = 0.0,
    chroma_holes: bool = True,
) -> tuple[list[Image.Image], list[int]]:
    """Composite each frame of GIF/WebP onto bg. Returns RGBA frames + durations ms."""
    bg = bg.convert("RGBA")
    raw: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(char_path) as im:
        n = int(getattr(im, "n_frames", 1) or 1)
        step = 1
        if n > max_frames:
            step = max(1, n // max_frames)
        for idx in range(0, n, step):
            im.seek(idx)
            raw.append(im.convert("RGBA"))
            try:
                d = int(im.info.get("duration", 100) or 100)
            except Exception:
                d = 100
            durations.append(max(20, d * step))
    if not raw:
        raise RuntimeError("No frames in character file")
    keyed = key_character_frames(raw, chroma_key, chroma_tol, feather, chroma_holes)
    frames = [_place_character(bg, fr, scale=scale, offset_x=offset_x, offset_y=offset_y, rotation=rotation)
              for fr in keyed]
    return frames, durations


def compose_animated_layers(
    bg_path: Path,
    char_path: Path,
    *,
    chroma_key: str = "auto",
    chroma_tol: float = 40.0,
    scale: float = 1.0,
    offset_x: float = 0.5,
    offset_y: float = 1.0,
    feather: float = 1.6,
    target_width: int = 750,
    fps: int = 12,
    max_seconds: float = 8.0,
    rotation: float = 0.0,
    chroma_holes: bool = True,
) -> tuple[list[Image.Image], list[int]]:
    """Composite two animated/static image sources on one shared timeline."""
    fps = max(5, min(30, int(fps or 12)))
    frame_ms = max(20, round(1000 / fps))
    max_frames = max(1, min(240, round(float(max_seconds) * fps)))

    def read_frames(path: Path, resize_bg: bool = False):
        frames: list[Image.Image] = []
        durations: list[int] = []
        if Path(path).is_dir():
            # A video decoded by extract_frames(): lossless frames at this fps.
            for frame_path in sorted(Path(path).glob("frame_*.png"))[:240]:
                with Image.open(frame_path) as opened:
                    rgba = opened.convert("RGBA")
                if resize_bg and rgba.width != target_width:
                    nh = max(1, int(rgba.height * target_width / max(1, rgba.width)))
                    rgba = rgba.resize((target_width, nh), Image.Resampling.LANCZOS)
                frames.append(rgba)
                durations.append(frame_ms)
            if not frames:
                raise RuntimeError(f"No frames in {Path(path).name}")
            return frames, durations
        with Image.open(path) as im:
            try:
                count = max(1, min(240, int(getattr(im, "n_frames", 1) or 1)))
            except (EOFError, IndexError, OSError):
                count = 240
                try:
                    im.seek(0)
                except Exception:
                    _LOG.debug("ignored error", exc_info=True)
            for index in range(count):
                try:
                    im.seek(index)
                    rgba = im.convert("RGBA")
                except (EOFError, IndexError, OSError):
                    break
                if resize_bg and rgba.width != target_width:
                    nh = max(1, int(rgba.height * target_width / max(1, rgba.width)))
                    rgba = rgba.resize((target_width, nh), Image.Resampling.LANCZOS)
                frames.append(rgba.copy())
                durations.append(max(20, int(im.info.get("duration", frame_ms) or frame_ms)))
        if not frames:
            raise RuntimeError(f"No frames in {path.name}")
        return frames, durations

    bg_frames, bg_durations = read_frames(bg_path, resize_bg=True)
    char_frames, char_durations = read_frames(char_path)
    bg_total = max(frame_ms, sum(bg_durations))
    char_total = max(frame_ms, sum(char_durations))
    total_ms = min(int(max_seconds * 1000), max(bg_total, char_total))
    count = max(1, min(max_frames, (total_ms + frame_ms - 1) // frame_ms))

    def at_time(frames, durations, time_ms):
        total = max(1, sum(durations))
        cursor = time_ms % total
        acc = 0
        for frame, duration in zip(frames, durations):
            acc += duration
            if cursor < acc:
                return frame
        return frames[-1]

    import time

    # The character clip is keyed once, as a clip: one backdrop model, frame-to-frame
    # smoothing and one crop box for every frame (smweb.chroma_matte, key_character_frames).
    t0 = time.monotonic()
    keyed_chars = key_character_frames(char_frames, chroma_key, chroma_tol, feather, chroma_holes)
    keyed_by_id = {id(frame): keyed for frame, keyed in zip(char_frames, keyed_chars)}
    t_key = time.monotonic() - t0

    output: list[Image.Image] = []
    t0 = time.monotonic()
    for index in range(count):
        time_ms = index * frame_ms
        bg = at_time(bg_frames, bg_durations, time_ms)
        char = keyed_by_id[id(at_time(char_frames, char_durations, time_ms))]
        output.append(_place_character(bg, char, scale=scale, offset_x=offset_x, offset_y=offset_y, rotation=rotation))
    _LOG.info(f"[compose-detail] frames={count} key={t_key:.1f}s place={time.monotonic() - t0:.1f}s")

    return output, [frame_ms] * len(output)
