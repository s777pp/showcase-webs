"""Обработка витрин — порт логики desktop (упрощённо, но те же режимы)."""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "fonts"
BIN = ROOT / "bin"
MAX_STEAM_MB = 5.0


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
                pass
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
            pass
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
        pass



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
        parts.append(part)
        # Steam: last byte 0x21 on each workshop part
        out[f"part_{i + 1}.png"] = apply_hex21(_png_bytes(part))

    out["full_original.png"] = _png_bytes(img)

    bar = 6
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


def process_image_featured(img: Image.Image) -> dict[str, bytes]:
    img = img.convert("RGBA")
    w, h = img.size
    nh = max(1, int(h * (630 / max(1, w))))
    img = img.resize((630, nh), Image.Resampling.LANCZOS)
    return {
        "featured_630.png": apply_hex21(_png_bytes(img)),
        "full_original.png": _png_bytes(img),
    }


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
) -> dict[str, bytes]:
    img = img.convert("RGBA")
    w, h = img.size
    scale = 606 / max(1, w)
    nw, nh = 606, max(1, int(h * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    center = img.crop((0, 0, 506, nh))
    side = img.crop((506, 0, 606, nh))
    out = {
        "center_506.png": apply_hex21(_png_bytes(center)),
        "side_100.png": apply_hex21(_png_bytes(side)),
        "full_original.png": _png_bytes(img),
    }
    bar = 6
    full = Image.new("RGBA", (center.width + bar + side.width, nh), (0, 0, 0, 255))
    full.paste(center, (0, 0))
    full.paste(side, (center.width + bar, 0))
    full = apply_watermark(full, wm_text, wm_font, wm_opacity, corner=wm_corner, scale=wm_scale, color=wm_color, wx=wm_x, wy=wm_y)
    out["full_with_bars.png"] = _png_bytes(full)
    return out


def _run(cmd: list[str]) -> None:
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "ffmpeg error")[-500:])



def media_to_gif(src: Path, dest: Path, fps: int, width: int, duration: float = 12) -> None:
    """Convert image/gif/video to GIF. Robust path with fallback."""
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
    vf_palette = (
        f"fps={fps},scale={width}:-2:flags=lanczos,"
        f"split[s0][s1];[s0]palettegen=stats_mode=single[p];"
        f"[s1][p]paletteuse=dither=bayer:bayer_scale=5"
    )
    cmd = [
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-t", str(duration),
        "-an",
        "-vf", vf_palette,
        "-loop", "0",
        str(dest),
    ]
    try:
        _run(cmd)
    except Exception as e1:
        # Fallback: scale to intermediate mp4 then gif (handles odd codecs)
        mid = dest.with_suffix(".tmp.mp4")
        try:
            _run([
                ff, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(src),
                "-t", str(duration),
                "-an",
                "-vf", f"fps={fps},scale={width}:-2:flags=lanczos",
                "-pix_fmt", "yuv420p",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                str(mid),
            ])
            _run([
                ff, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(mid),
                "-an",
                "-vf", (
                    f"fps={fps},"
                    f"split[s0][s1];[s0]palettegen=stats_mode=single[p];"
                    f"[s1][p]paletteuse=dither=bayer:bayer_scale=5"
                ),
                "-loop", "0",
                str(dest),
            ])
        except Exception as e2:
            raise RuntimeError(f"video→gif failed: {e1} | fallback: {e2}") from e2
        finally:
            try:
                mid.unlink(missing_ok=True)
            except Exception:
                pass

    if not dest.is_file() or dest.stat().st_size < 50:
        raise RuntimeError("GIF conversion produced empty file")


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
        pass
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
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gif_src = out_dir / "source.gif"
    media_to_gif(src, gif_src, fps=fps, width=width, duration=duration)
    return process_gif_workshop(
        gif_src, out_dir, wm_text, wm_font, wm_opacity,
        wm_color=wm_color, wm_corner=wm_corner, wm_scale=wm_scale,
        wm_x=wm_x, wm_y=wm_y,
    )


def process_video_featured(
    src: Path,
    out_dir: Path,
    fps: int = 12,
    duration: float = 10,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "featured_630.gif"
    media_to_gif(src, out, fps=fps, width=630, duration=duration)
    ensure_under_mb(out)
    clean = out_dir / "full_original.gif"
    shutil.copy2(out, clean)
    return {out.name: out, clean.name: clean}


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
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gif_src = out_dir / "source.gif"
    media_to_gif(src, gif_src, fps=fps, width=606, duration=duration)
    return process_gif_split(
        gif_src, out_dir, fps=fps, wm_text=wm_text, wm_font=wm_font, wm_opacity=wm_opacity,
        wm_color=wm_color, wm_corner=wm_corner, wm_scale=wm_scale, wm_x=wm_x, wm_y=wm_y,
    )




def find_gifski() -> Optional[str]:
    which = shutil.which("gifski")
    if which:
        return which
    for name in ("gifski", "gifski.exe"):
        p = ROOT / name
        if p.is_file():
            return str(p)
    return None


def encode_gif_from_png_sequence(
    frames_dir: Path,
    dest: Path,
    fps: int = 12,
    encoder: str = "ffmpeg",
) -> None:
    """encoder: ffmpeg | gifski | pillow (caller may already use pillow)."""
    encoder = (encoder or "ffmpeg").strip().lower()
    pattern = str(frames_dir / "frame_*.png")
    fps = max(5, min(30, int(fps or 12)))
    if encoder == "gifski":
        gs = find_gifski()
        if not gs:
            encoder = "ffmpeg"
        else:
            # gifski --fps N -o out.gif frame_*.png
            files = sorted(frames_dir.glob("frame_*.png"))
            if not files:
                raise RuntimeError("no frames for gifski")
            cmd = [gs, "--fps", str(fps), "-o", str(dest), *[str(f) for f in files]]
            subprocess.run(cmd, check=True, capture_output=True)
            return
    if encoder == "ffmpeg":
        ff = find_ffmpeg()
        if not ff:
            raise RuntimeError("ffmpeg not found")
        vf = (
            f"fps={fps},"
            f"split[s0][s1];[s0]palettegen=stats_mode=diff[p];"
            f"[s1][p]paletteuse=dither=bayer:bayer_scale=5"
        )
        cmd = [
            ff, "-y", "-framerate", str(fps), "-i", str(frames_dir / "frame_%04d.png"),
            "-lavfi", vf, "-loop", "0", str(dest),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return
    # pillow fallback: open frames and save
    files = sorted(frames_dir.glob("frame_*.png"))
    if not files:
        raise RuntimeError("no frames")
    imgs = [Image.open(f).convert("RGBA") for f in files]
    duration = int(1000 / fps)
    imgs[0].save(
        dest, save_all=True, append_images=imgs[1:], duration=duration, loop=0, disposal=2
    )


def ensure_under_mb(path: Path, max_mb: float = MAX_STEAM_MB) -> None:
    if not path.is_file() or path.suffix.lower() != ".gif":
        return
    ff = find_ffmpeg()
    if not ff:
        return
    for fps, colors, scale in ((10, 128, 90), (8, 96, 80), (6, 64, 70)):
        mb = path.stat().st_size / (1024 * 1024)
        if mb <= max_mb:
            return
        tmp = path.with_suffix(".tmp.gif")
        vf = (
            f"fps={fps},scale=iw*{scale}/100:-1:flags=lanczos,"
            f"split[s0][s1];[s0]palettegen=max_colors={colors}:stats_mode=diff[p];"
            f"[s1][p]paletteuse=dither=bayer:bayer_scale=3"
        )
        try:
            _run([ff, "-y", "-i", str(path), "-vf", vf, "-loop", "0", str(tmp)])
            if tmp.is_file() and tmp.stat().st_size < path.stat().st_size:
                tmp.replace(path)
            elif tmp.is_file():
                tmp.unlink(missing_ok=True)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass






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
            fw, fh = frame.size
            pw = max(1, fw // 5)
            full_w = fw + bar_width * 4
            full = Image.new("RGBA", (full_w, fh), (0, 0, 0, 255))
            x = 0
            for i in range(5):
                left = i * pw
                right = (i + 1) * pw if i < 4 else fw
                part = frame.crop((left, 0, right, fh))
                if part.mode == "RGBA":
                    full.paste(part, (x, 0), part)
                else:
                    full.paste(part, (x, 0))
                x += part.width
                if i < 4:
                    x += bar_width
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
    frames_p: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(gif_path) as im:
        n = int(getattr(im, "n_frames", 1) or 1)
        max_frames = 180
        step = 1
        if n > max_frames:
            step = max(1, n // max_frames)
        for idx in range(0, n, step):
            im.seek(idx)
            frame = im.convert("RGBA")
            fw, fh = frame.size
            cut = min(506, max(1, fw - 1))
            center = frame.crop((0, 0, cut, fh))
            side = frame.crop((cut, 0, fw, fh))
            if side.width <= 0:
                side = Image.new("RGBA", (100, fh), (0, 0, 0, 255))
            full_w = center.width + bar_width + side.width
            full = Image.new("RGBA", (full_w, fh), (0, 0, 0, 255))
            if center.mode == "RGBA":
                full.paste(center, (0, 0), center)
            else:
                full.paste(center, (0, 0))
            if side.mode == "RGBA":
                full.paste(side, (center.width + bar_width, 0), side)
            else:
                full.paste(side, (center.width + bar_width, 0))
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
            del full, frame
    _save_animated_gif(frames_p, durations, out_path)



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
) -> dict[str, Path]:
    """Cut GIF into 5 Steam Workshop parts + full_with_bars.gif."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg not found")
    width, height = _probe_wh(gif_path)
    # last part takes remainder so nothing is lost
    pw = max(1, width // 5)
    result: dict[str, Path] = {}
    for i in range(5):
        out = out_dir / f"part_{i + 1}.gif"
        x = i * pw
        w = pw if i < 4 else max(1, width - x)
        # crop then re-palette for valid GIF
        vf = (
            f"crop={w}:{height}:{x}:0,"
            f"split[s0][s1];[s0]palettegen=stats_mode=single[p];"
            f"[s1][p]paletteuse"
        )
        _run([ff, "-y", "-i", str(gif_path), "-an", "-vf", vf, "-loop", "0", str(out)])
        ensure_under_mb(out)
        apply_hex21_file(out)
        result[out.name] = out
    clean = out_dir / "full_original.gif"
    shutil.copy2(gif_path, clean)
    result[clean.name] = clean
    # полная гиф с полосами + watermark
    bars = out_dir / "full_with_bars.gif"
    try:
        _gif_full_with_bars_workshop(
            gif_path, bars, wm_text, wm_font, wm_opacity,
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


def process_gif_featured(gif_path: Path, out_dir: Path, fps: int = 12) -> dict[str, Path]:
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg не найден")
    out = out_dir / "featured_630.gif"
    media_to_gif(gif_path, out, fps=fps, width=630, duration=10)
    ensure_under_mb(out)
    apply_hex21_file(out)
    clean = out_dir / "full_original.gif"
    shutil.copy2(out, clean)
    return {out.name: out, clean.name: clean}


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
) -> dict[str, Path]:
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg не найден")
    tmp = out_dir / "tmp_606.gif"
    media_to_gif(gif_path, tmp, fps=fps, width=606, duration=10)
    probe = find_ffprobe() or ff.replace("ffmpeg", "ffprobe")
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    info = subprocess.check_output(
        [probe, "-v", "quiet", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(tmp)],
        text=True, **kw,
    ).strip().split(",")
    height = int(info[1])
    center = out_dir / "center_506.gif"
    side = out_dir / "side_100.gif"
    _run([ff, "-y", "-i", str(tmp), "-filter:v", f"crop=506:{height}:0:0", "-loop", "0", str(center)])
    _run([ff, "-y", "-i", str(tmp), "-filter:v", f"crop=100:{height}:506:0", "-loop", "0", str(side)])
    ensure_under_mb(center)
    ensure_under_mb(side)
    apply_hex21_file(center)
    apply_hex21_file(side)
    clean = out_dir / "full_original.gif"
    shutil.copy2(tmp, clean)
    result = {center.name: center, side.name: side, clean.name: clean}
    bars = out_dir / "full_with_bars.gif"
    try:
        _gif_full_with_bar_split(
            tmp, bars, wm_text, wm_font, wm_opacity,
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
    try:
        tmp.unlink()
    except Exception:
        pass
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
    softness: float = 20.0,
) -> Image.Image:
    """Remove green/blue/red screen. key=auto samples corners.

    Uses classic channel-difference keying (reliable for pure #00FF00 screens)
    plus a light despill. If the image already has transparency, auto skips.
    If keying would wipe almost everything, falls back to the original frame.
    """
    img = img.convert("RGBA")
    w, h = img.size
    pixels = list(img.getdata())
    key = (key or "auto").strip().lower()
    n = len(pixels)
    if n == 0:
        return img

    # Already a cutout PNG? keep as-is in auto mode
    if key in ("auto", "a"):
        sample_n = min(n, 2500)
        step = max(1, n // sample_n)
        transparent = sum(1 for i in range(0, n, step) if pixels[i][3] < 250)
        checked = (n + step - 1) // step
        if checked and (transparent / checked) > 0.08:
            return img

    def sample_backdrop():
        """Sample border ring — chromakey usually fills the frame edge (green/blue/red)."""
        acc = []
        step_x = max(1, w // 24)
        step_y = max(1, h // 24)
        for x in range(0, w, step_x):
            for y in (1, 2, max(0, h - 2), max(0, h - 3)):
                if 0 <= x < w and 0 <= y < h:
                    r, g, b, a = pixels[y * w + x]
                    if a >= 16:
                        acc.append((r, g, b))
        for y in range(0, h, step_y):
            for x in (1, 2, max(0, w - 2), max(0, w - 3)):
                if 0 <= x < w and 0 <= y < h:
                    r, g, b, a = pixels[y * w + x]
                    if a >= 16:
                        acc.append((r, g, b))
        if not acc:
            return "green", (40, 200, 40)
        rs = sorted(c[0] for c in acc)
        gs = sorted(c[1] for c in acc)
        bs = sorted(c[2] for c in acc)
        lo, hi = len(acc) // 4, max(len(acc) // 4 + 1, 3 * len(acc) // 4)
        ar = sum(rs[lo:hi]) // max(1, hi - lo)
        ag = sum(gs[lo:hi]) // max(1, hi - lo)
        ab = sum(bs[lo:hi]) // max(1, hi - lo)
        green_votes = sum(1 for r, g, b in acc if g > r + 15 and g > b + 15)
        blue_votes = sum(1 for r, g, b in acc if b > r + 15 and b > g + 15)
        red_votes = sum(1 for r, g, b in acc if r > g + 15 and r > b + 15)
        if green_votes >= blue_votes and green_votes >= red_votes and green_votes > len(acc) * 0.2:
            return "green", (ar, ag, ab)
        if blue_votes >= green_votes and blue_votes >= red_votes and blue_votes > len(acc) * 0.2:
            return "blue", (ar, ag, ab)
        if red_votes >= green_votes and red_votes >= blue_votes and red_votes > len(acc) * 0.2:
            return "red", (ar, ag, ab)
        if ag >= ar and ag >= ab:
            return "green", (ar, ag, ab)
        if ab >= ar and ab >= ag:
            return "blue", (ar, ag, ab)
        return "red", (ar, ag, ab)

    if key in ("none", "0", "off", ""):
        return img

    if key in ("auto", "a"):
        mode, (kr, kg, kb) = sample_backdrop()
    elif key == "blue":
        mode, kr, kg, kb = "blue", 20, 40, 220
    elif key == "red":
        mode, kr, kg, kb = "red", 220, 30, 30
    elif key == "green":
        mode, kr, kg, kb = "green", 40, 200, 40
    elif key.startswith("#") or (len(key) == 6 and all(c in "0123456789abcdef" for c in key)):
        kr, kg, kb = _hex_to_rgb(key if key.startswith("#") else "#" + key)
        if kg >= kr and kg >= kb:
            mode = "green"
        elif kb >= kr and kb >= kg:
            mode = "blue"
        else:
            mode = "red"
    else:
        mode, kr, kg, kb = "green", 40, 200, 40

    # Map UI tolerance (10..120) → channel threshold
    # Higher slider = more aggressive keying
    tol_ui = max(10.0, min(120.0, float(tolerance or 55)))
    # base threshold for (key_channel - max(other two))
    base_thr = 18.0 + (tol_ui - 10.0) * (70.0 / 110.0)  # ~18..88
    soft = max(4.0, float(softness or 20.0))

    def key_score(r, g, b):
        """Higher score = more like the backdrop → more transparent."""
        if mode == "green":
            return float(g) - max(r, b)
        if mode == "blue":
            return float(b) - max(r, g)
        return float(r) - max(g, b)

    # Also kill pixels very close to sampled corner color (RGB distance)
    def rgb_dist(r, g, b):
        return ((r - kr) ** 2 + (g - kg) ** 2 + (b - kb) ** 2) ** 0.5

    rgb_thr = 28.0 + (tol_ui - 10.0) * 0.55  # ~28..88

    out_data = []
    opaque = 0
    for r, g, b, a in pixels:
        if a < 8:
            out_data.append((r, g, b, 0))
            continue
        sc = key_score(r, g, b)
        rd = rgb_dist(r, g, b)
        # transparent if either channel-diff OR close to key color
        if sc >= base_thr or rd <= rgb_thr * 0.65:
            na = 0
        elif sc > base_thr - soft:
            # soft edge on channel score
            t = (sc - (base_thr - soft)) / soft
            t = max(0.0, min(1.0, t))
            na = int(a * (1.0 - t))
        elif rd < rgb_thr:
            t = (rgb_thr - rd) / max(1.0, rgb_thr * 0.5)
            t = max(0.0, min(1.0, t))
            na = int(a * (1.0 - t * 0.85))
        else:
            na = a

        # despill: pull key channel toward the other two on semi-transparent edges
        if na > 0 and mode == "green" and g > max(r, b) + 8:
            avg = (r + b) * 0.5
            mix = 0.55 if na < 200 else 0.25
            g = int(g * (1.0 - mix) + avg * mix)
        elif na > 0 and mode == "blue" and b > max(r, g) + 8:
            avg = (r + g) * 0.5
            mix = 0.55 if na < 200 else 0.25
            b = int(b * (1.0 - mix) + avg * mix)
        elif na > 0 and mode == "red" and r > max(g, b) + 8:
            avg = (g + b) * 0.5
            mix = 0.55 if na < 200 else 0.25
            r = int(r * (1.0 - mix) + avg * mix)

        if na > 16:
            opaque += 1
        out_data.append((
            max(0, min(255, int(r))),
            max(0, min(255, int(g))),
            max(0, min(255, int(b))),
            max(0, min(255, int(na))),
        ))

    # Safety: if keying wiped the subject (< 0.4% opaque), return original
    if opaque < max(16, int(n * 0.004)):
        return img

    out = Image.new("RGBA", (w, h))
    out.putdata(out_data)
    return out



def _place_character(
    bg: Image.Image,
    char: Image.Image,
    scale: float = 1.0,
    offset_x: float = 0.5,
    offset_y: float = 1.0,
) -> Image.Image:
    """Paste character on bg. offset_x/y are anchor 0..1 (0.5,1 = bottom-center).

    Scale is relative to ~85% of background height. No max-width clamp —
    chromakey sources are often much larger than the subject, so the user
    must be able to enlarge freely (overflow is cropped to the BG).
    """
    bg = bg.convert("RGBA")
    char = char.convert("RGBA")
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
) -> Image.Image:
    did_key = False
    if chroma_key and chroma_key not in ("none", "0", "off", ""):
        char = remove_chromakey(char, key=chroma_key, tolerance=chroma_tol)
        did_key = True
    if did_key and feather and float(feather) > 0:
        char = feather_alpha(char, radius=float(feather))
    char = _crop_to_alpha(char)
    return _place_character(bg, char, scale=scale, offset_x=offset_x, offset_y=offset_y)


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
) -> tuple[list[Image.Image], list[int]]:
    """Composite each frame of GIF/WebP onto bg. Returns RGBA frames + durations ms."""
    bg = bg.convert("RGBA")
    frames: list[Image.Image] = []
    durations: list[int] = []
    do_key = bool(chroma_key and chroma_key not in ("none", "0", "off", ""))
    with Image.open(char_path) as im:
        n = int(getattr(im, "n_frames", 1) or 1)
        step = 1
        if n > max_frames:
            step = max(1, n // max_frames)
        for idx in range(0, n, step):
            im.seek(idx)
            fr = im.convert("RGBA")
            if do_key:
                fr = remove_chromakey(fr, key=chroma_key, tolerance=chroma_tol)
                if feather and float(feather) > 0:
                    fr = feather_alpha(fr, radius=float(feather))
            fr = _crop_to_alpha(fr)
            composed = _place_character(bg, fr, scale=scale, offset_x=offset_x, offset_y=offset_y)
            frames.append(composed)
            try:
                d = int(im.info.get("duration", 100) or 100)
            except Exception:
                d = 100
            durations.append(max(20, d * step))
    if not frames:
        raise RuntimeError("No frames in character file")
    return frames, durations
