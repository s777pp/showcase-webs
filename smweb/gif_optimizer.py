"""GIF Optimizer: shrink an existing GIF (tab "GIF Optimizer", 2026-10-06, owner request after steamprofile.io).

Two ways, chosen by the owner:
* manual: palette colours + lossy percent with gifsicle (fast, frames and timing untouched). When gifsicle is
  missing (old image, local Windows) FFmpeg rebuilds the palette with the same colour limit and an ordered dither
  whose strength follows the lossy percent, so the tab keeps working.
* auto: fit under 5 MB with the same gifski search as Process (`processor.fit_frames_to_gif`), from the decoded
  frames, never by re-quantizing the GIF.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image

import processor as proc
from smweb import process_control

COLOR_CHOICES = (256, 200, 128, 64, 32, 16)
MAX_FRAMES = 2000


def find_gifsicle() -> Optional[str]:
    """System gifsicle (Linux image) first; a Windows build in bin/ only on Windows."""
    found = shutil.which("gifsicle")
    if found:
        return found
    if os.name == "nt":
        local = Path(__file__).resolve().parent.parent / "bin" / "gifsicle.exe"
        if local.is_file():
            return str(local)
    return None


def info(path: Path) -> dict:
    """Frames, size and timing of a GIF (raises ValueError for a broken file)."""
    try:
        with Image.open(path) as im:
            if im.format != "GIF":
                raise ValueError("GIF only")
            frames = getattr(im, "n_frames", 1)
            if frames > MAX_FRAMES:
                raise ValueError(f"Too many frames (max {MAX_FRAMES})")
            durations = []
            for index in range(frames):
                im.seek(index)
                durations.append(int(im.info.get("duration") or 100))
            width, height = im.size
    except ValueError:
        raise
    except Exception as exc:  # Pillow: truncated or broken file
        raise ValueError("Could not read the GIF") from exc
    total = sum(durations)
    return {"frames": frames, "width": width, "height": height, "size": path.stat().st_size,
            "duration_ms": total, "avg_delay_ms": total / max(1, frames)}


def lossy_value(percent: int) -> int:
    """UI percent (0-100) -> gifsicle --lossy (0-200; 20-80 is the usual range)."""
    return max(0, min(200, round(max(0, min(100, int(percent))) * 2)))


def _run(command: list[str], job_id: str = "") -> None:
    completed = process_control.run(command, job_id=job_id or None, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout or "encoder failed").strip()[-400:])


def manual(src: Path, dest: Path, colors: int, lossy: int, job_id: str = "") -> str:
    """Compress with the chosen palette size and lossy percent. Returns the engine used."""
    colors = max(2, min(256, int(colors)))
    lossy = max(0, min(100, int(lossy)))
    gifsicle = find_gifsicle()
    if gifsicle:
        command = [gifsicle, "--no-warnings", "-O3"]
        if lossy:
            command.append(f"--lossy={lossy_value(lossy)}")
        if colors < 256:
            command += ["--colors", str(colors)]
        _run(command + [str(src), "-o", str(dest)], job_id)
        return "gifsicle"
    ffmpeg = proc.find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("Neither gifsicle nor FFmpeg is available")
    # Dither noise is what makes a GIF heavy: a higher lossy percent means a fainter ordered pattern
    # (bayer_scale up), and no dither at all from 80 %. 0 % keeps the best-looking error diffusion.
    if lossy >= 80:
        dither = "dither=none"
    elif lossy == 0:
        dither = "dither=sierra2_4a"
    else:
        dither = f"dither=bayer:bayer_scale={min(5, 1 + lossy // 20)}"
    graph = (f"split[a][b];[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
             f"[b][p]paletteuse={dither}:diff_mode=rectangle")
    _run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
          "-filter_complex", graph, "-loop", "0", str(dest)], job_id)
    return "ffmpeg"


def auto(src: Path, dest: Path, max_mb: float = proc.MAX_STEAM_MB, job_id: str = "") -> dict:
    """Best quality that fits ``max_mb``. A GIF that already fits is returned unchanged."""
    limit = int(max_mb * 1024 * 1024)
    if src.stat().st_size <= limit:
        shutil.copyfile(src, dest)
        return {"engine": "none", "already_fits": True}
    meta = info(src)
    fps = max(1, min(50, round(1000 / max(20.0, meta["avg_delay_ms"]))))
    ffmpeg = proc.find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable")
    work = Path(tempfile.mkdtemp(prefix="sm_gifopt_"))
    try:
        frames = work / "frames"
        frames.mkdir()
        # Constant frame rate from the GIF's average delay: the encoder needs one fps.
        _run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
              "-vf", f"fps={fps}", "-start_number", "1", str(frames / "frame_%05d.png")], job_id)
        process_control.checkpoint(job_id)
        chosen = proc.fit_frames_to_gif(frames, dest, fps=fps, max_mb=max_mb)
        if chosen:
            return {"engine": "gifski", "fps": fps, **chosen}
        # gifski missing or even the lowest quality does not fit: the general fallback of Process.
        shutil.copyfile(src, dest)
        proc.ensure_under_mb(dest, max_mb=max_mb)
        return {"engine": "fallback", "fps": fps}
    finally:
        shutil.rmtree(work, ignore_errors=True)
