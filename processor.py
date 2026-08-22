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
    key = (key or "lap").strip()
    candidates = []
    for ext in (".ttf", ".otf"):
        candidates.append(FONTS / f"{key}{ext}")
        candidates.append(FONTS / f"{key.lower()}{ext}")
        candidates.append(FONTS / f"{key.capitalize()}{ext}")
    if key.lower() == "fineday":
        candidates.insert(0, FONTS / "Fineday.ttf")
    # If watermark has Cyrillic, prefer fonts that actually draw it
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
    c = (corner or "bl").strip().lower()
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
    c = (color or "#ffffff").strip()
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
    full = apply_watermark(full, wm_text, wm_font, wm_opacity, corner=wm_corner, scale=wm_scale, color=wm_color)
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
    full = apply_watermark(full, wm_text, wm_font, wm_opacity, corner=wm_corner, scale=wm_scale, color=wm_color)
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
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gif_src = out_dir / "source.gif"
    media_to_gif(src, gif_src, fps=fps, width=width, duration=duration)
    return process_gif_workshop(
        gif_src, out_dir, wm_text, wm_font, wm_opacity, wm_corner, wm_scale
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
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gif_src = out_dir / "source.gif"
    media_to_gif(src, gif_src, fps=fps, width=606, duration=duration)
    return process_gif_split(
        gif_src, out_dir, fps=fps, wm_text=wm_text, wm_font=wm_font, wm_opacity=wm_opacity,
        wm_corner=wm_corner, wm_scale=wm_scale,
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
) -> None:
    """Full GIF: 5 parts + black bars + watermark (all frames)."""
    frames_out: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(gif_path) as im:
        n = int(getattr(im, "n_frames", 1) or 1)
        for idx in range(n):
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
                full.paste(part, (x, 0), part)
                x += part.width
                if i < 4:
                    x += bar_width
            if wm_text and float(wm_opacity or 0) > 0:
                full = apply_watermark(
                    full, wm_text, wm_font, float(wm_opacity),
                    corner=wm_corner, scale=wm_scale, color=wm_color,
                )
            frames_out.append(full.convert("RGBA"))
            try:
                d = int(im.info.get("duration", 100) or 100)
            except Exception:
                d = 100
            durations.append(max(20, d))
    if not frames_out:
        raise RuntimeError("GIF has no frames")
    # Pillow animated GIF: convert to P with adaptive palette per-frame is hard;
    # save RGBA via disposal=2 works on modern Pillow for many viewers / Steam tools.
    first, rest = frames_out[0], frames_out[1:]
    first.save(
        out_path,
        save_all=True,
        append_images=rest,
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )
    if not out_path.is_file() or out_path.stat().st_size < 32:
        raise RuntimeError("full_with_bars.gif not written")


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
) -> None:
    frames_out: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(gif_path) as im:
        n = int(getattr(im, "n_frames", 1) or 1)
        for idx in range(n):
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
            full.paste(center, (0, 0), center)
            full.paste(side, (center.width + bar_width, 0), side)
            if wm_text and float(wm_opacity or 0) > 0:
                full = apply_watermark(
                    full, wm_text, wm_font, float(wm_opacity),
                    corner=wm_corner, scale=wm_scale, color=wm_color,
                )
            frames_out.append(full.convert("RGBA"))
            try:
                d = int(im.info.get("duration", 100) or 100)
            except Exception:
                d = 100
            durations.append(max(20, d))
    if not frames_out:
        raise RuntimeError("GIF has no frames")
    first, rest = frames_out[0], frames_out[1:]
    first.save(
        out_path,
        save_all=True,
        append_images=rest,
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )
    if not out_path.is_file() or out_path.stat().st_size < 32:
        raise RuntimeError("full_with_bars.gif not written")


def process_gif_workshop(
    gif_path: Path,
    out_dir: Path,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
    wm_color: str = "#ffffff",
    wm_corner: str = "bl",
    wm_scale: float = 1.0,
) -> dict[str, Path]:
    """Cut GIF into 5 Steam Workshop parts + full_with_bars.gif."""
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
            gif_path, bars, wm_text, wm_font, wm_opacity, wm_corner, wm_scale, wm_color=wm_color
        )
        if bars.is_file():
            result[bars.name] = bars
        else:
            print("full_with_bars.gif workshop: file missing after save")
    except Exception as e:
        print("full_with_bars.gif workshop:", type(e).__name__, e)
        import traceback
        traceback.print_exc()
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
        _gif_full_with_bar_split(tmp, bars, wm_text, wm_font, wm_opacity, wm_corner, wm_scale, wm_color=wm_color)
        if bars.is_file():
            result[bars.name] = bars
    except Exception as e:
        print("full_with_bars.gif split:", e)
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
