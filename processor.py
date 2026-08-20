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


def find_ffmpeg() -> Optional[str]:
    for name in ("ffmpeg.exe", "ffmpeg"):
        p = BIN / name
        if p.is_file():
            return str(p)
    return shutil.which("ffmpeg")


def find_ffprobe() -> Optional[str]:
    for name in ("ffprobe.exe", "ffprobe"):
        p = BIN / name
        if p.is_file():
            return str(p)
    ff = find_ffmpeg()
    if ff:
        alt = ff.replace("ffmpeg", "ffprobe")
        if os.path.isfile(alt):
            return alt
    return shutil.which("ffprobe")


def load_font(key: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (key or "lap").strip()
    candidates = []
    for ext in (".ttf", ".otf"):
        candidates.append(FONTS / f"{key}{ext}")
        candidates.append(FONTS / f"{key.lower()}{ext}")
        candidates.append(FONTS / f"{key.capitalize()}{ext}")
    if key.lower() == "fineday":
        candidates.insert(0, FONTS / "Fineday.ttf")
    for c in candidates:
        if c.is_file():
            try:
                return ImageFont.truetype(str(c), size)
            except Exception:
                pass
    return ImageFont.load_default()


def apply_watermark(
    img: Image.Image,
    text: str,
    font_key: str,
    opacity: float,
    wx: float = 0.08,
    wy: float = 0.85,
) -> Image.Image:
    if not text or opacity <= 0:
        return img
    img = img.convert("RGBA")
    h = img.height
    font = load_font(font_key, max(18, h // 28))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x = int(img.width * wx)
    y = int(img.height * wy)
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    a = layer.getchannel("A").point(lambda p: int(p * max(0.0, min(1.0, opacity))))
    layer.putalpha(a)
    return Image.alpha_composite(img, layer)


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGBA").save(buf, format="PNG")
    return buf.getvalue()


def process_image_workshop(
    img: Image.Image,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
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
        out[f"part_{i + 1}.png"] = _png_bytes(part)

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
    full = apply_watermark(full, wm_text, wm_font, wm_opacity, wx=0.08, wy=0.85)
    out["full_with_bars.png"] = _png_bytes(full)
    return out


def process_image_featured(img: Image.Image) -> dict[str, bytes]:
    img = img.convert("RGBA")
    w, h = img.size
    nh = max(1, int(h * (630 / max(1, w))))
    img = img.resize((630, nh), Image.Resampling.LANCZOS)
    return {
        "featured_630.png": _png_bytes(img),
        "full_original.png": _png_bytes(img),
    }


def process_image_split(
    img: Image.Image,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
) -> dict[str, bytes]:
    img = img.convert("RGBA")
    w, h = img.size
    scale = 606 / max(1, w)
    nw, nh = 606, max(1, int(h * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    center = img.crop((0, 0, 506, nh))
    side = img.crop((506, 0, 606, nh))
    out = {
        "center_506.png": _png_bytes(center),
        "side_100.png": _png_bytes(side),
        "full_original.png": _png_bytes(img),
    }
    bar = 6
    full = Image.new("RGBA", (center.width + bar + side.width, nh), (0, 0, 0, 255))
    full.paste(center, (0, 0))
    full.paste(side, (center.width + bar, 0))
    full = apply_watermark(full, wm_text, wm_font, wm_opacity)
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
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg не найден (положи bin/ffmpeg.exe)")
    fps = max(5, min(30, int(fps)))
    width = max(200, min(1200, int(width)))
    vf = (
        f"fps={fps},scale={width}:-1:flags=lanczos,"
        f"split[s0][s1];[s0]palettegen=stats_mode=diff[p];"
        f"[s1][p]paletteuse=dither=bayer:bayer_scale=4"
    )
    _run([ff, "-y", "-i", str(src), "-vf", vf, "-t", str(duration), "-loop", "0", str(dest)])


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
    bar_width: int = 6,
) -> None:
    """Полный GIF: 5 частей + чёрные полосы + watermark (как desktop)."""
    frames_out = []
    durations = []
    with Image.open(gif_path) as im:
        n = getattr(im, "n_frames", 1)
        im.seek(0)
        first = im.convert("RGBA")
        font = load_font(wm_font, max(18, first.size[1] // 28))
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
                full.paste(part, (x, 0))
                x += part.width
                if i < 4:
                    x += bar_width
            if wm_text and wm_opacity > 0:
                layer = Image.new("RGBA", full.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(layer)
                draw.text(
                    (int(pw * 0.08), int(fh * 0.85)),
                    wm_text,
                    font=font,
                    fill=(255, 255, 255, 255),
                )
                a = layer.getchannel("A").point(lambda p: int(p * wm_opacity))
                layer.putalpha(a)
                full = Image.alpha_composite(full, layer)
            frames_out.append(full.convert("RGB"))
            durations.append(int(im.info.get("duration", 100) or 100))
    if not frames_out:
        return
    frames_out[0].save(
        out_path,
        save_all=True,
        append_images=frames_out[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )


def _gif_full_with_bar_split(
    gif_path: Path,
    out_path: Path,
    wm_text: str,
    wm_font: str,
    wm_opacity: float,
    bar_width: int = 6,
) -> None:
    frames_out = []
    durations = []
    with Image.open(gif_path) as im:
        n = getattr(im, "n_frames", 1)
        im.seek(0)
        first = im.convert("RGBA")
        font = load_font(wm_font, max(18, first.size[1] // 28))
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
            full.paste(center, (0, 0))
            full.paste(side, (center.width + bar_width, 0))
            if wm_text and wm_opacity > 0:
                layer = Image.new("RGBA", full.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(layer)
                draw.text(
                    (int(center.width * 0.08), int(fh * 0.85)),
                    wm_text,
                    font=font,
                    fill=(255, 255, 255, 255),
                )
                a = layer.getchannel("A").point(lambda p: int(p * wm_opacity))
                layer.putalpha(a)
                full = Image.alpha_composite(full, layer)
            frames_out.append(full.convert("RGB"))
            durations.append(int(im.info.get("duration", 100) or 100))
    if not frames_out:
        return
    frames_out[0].save(
        out_path,
        save_all=True,
        append_images=frames_out[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )


def process_gif_workshop(
    gif_path: Path,
    out_dir: Path,
    wm_text: str = "",
    wm_font: str = "lap",
    wm_opacity: float = 0.22,
) -> dict[str, Path]:
    """Режет GIF на 5 частей + hex21 + full_with_bars.gif."""
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg не найден")
    probe = find_ffprobe() or ff.replace("ffmpeg", "ffprobe")
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    info = subprocess.check_output(
        [probe, "-v", "quiet", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(gif_path)],
        text=True, **kw,
    ).strip().split(",")
    width, height = int(info[0]), int(info[1])
    pw = max(1, width // 5)
    result: dict[str, Path] = {}
    for i in range(5):
        out = out_dir / f"part_{i + 1}.gif"
        _run([ff, "-y", "-i", str(gif_path), "-filter:v",
              f"crop={pw}:{height}:{i * pw}:0", "-loop", "0", str(out)])
        try:
            with open(out, "r+b") as f:
                f.seek(-1, os.SEEK_END)
                f.write(b"\x21")
        except Exception:
            pass
        ensure_under_mb(out)
        try:
            with open(out, "r+b") as f:
                f.seek(-1, os.SEEK_END)
                f.write(b"\x21")
        except Exception:
            pass
        result[out.name] = out
    clean = out_dir / "full_original.gif"
    shutil.copy2(gif_path, clean)
    result[clean.name] = clean
    # полная гиф с полосами + watermark
    bars = out_dir / "full_with_bars.gif"
    try:
        _gif_full_with_bars_workshop(gif_path, bars, wm_text, wm_font, wm_opacity)
        if bars.is_file():
            result[bars.name] = bars
    except Exception as e:
        print("full_with_bars.gif workshop:", e)
    return result


def process_gif_featured(gif_path: Path, out_dir: Path, fps: int = 12) -> dict[str, Path]:
    ff = find_ffmpeg()
    if not ff:
        raise RuntimeError("FFmpeg не найден")
    out = out_dir / "featured_630.gif"
    media_to_gif(gif_path, out, fps=fps, width=630, duration=10)
    ensure_under_mb(out)
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
    clean = out_dir / "full_original.gif"
    shutil.copy2(tmp, clean)
    result = {center.name: center, side.name: side, clean.name: clean}
    bars = out_dir / "full_with_bars.gif"
    try:
        _gif_full_with_bar_split(tmp, bars, wm_text, wm_font, wm_opacity)
        if bars.is_file():
            result[bars.name] = bars
    except Exception as e:
        print("full_with_bars.gif split:", e)
    try:
        tmp.unlink()
    except Exception:
        pass
    return result
