"""Queued local AI background removal for Builder source layers."""
from __future__ import annotations

import io
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageSequence

import processor
import redis_store as rs
from smweb import object_store
from smweb.core import DATA, _safe_data_path


_SESSION = None


def _local_output_path(key: str) -> Path:
    base = Path(DATA).resolve()
    path = (base / key).resolve()
    if base not in path.parents:
        raise ValueError("Invalid Builder result path")
    return path


def _session():
    global _SESSION
    if _SESSION is None:
        from rembg import new_session
        _SESSION = new_session("u2netp")
    return _SESSION


def _remove(image: Image.Image) -> Image.Image:
    from rembg import remove
    result = remove(image.convert("RGBA"), session=_session())
    if isinstance(result, Image.Image):
        return result.convert("RGBA")
    return Image.open(io.BytesIO(result)).convert("RGBA")


def _source_bytes(key: str) -> bytes:
    if object_store.configured():
        return object_store.get_bytes(key, public=False)
    path = _safe_data_path(key)
    if not path or not path.is_file():
        raise FileNotFoundError("Builder source not found")
    return path.read_bytes()


def _save(key: str, data: bytes, media_type: str) -> None:
    if object_store.configured():
        object_store.put_bytes(key, data, public=False, media_type=media_type)
        return
    path = _local_output_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _static(data: bytes) -> tuple[bytes, str, str]:
    image = Image.open(io.BytesIO(data))
    out = io.BytesIO()
    _remove(image).save(out, "PNG", optimize=True)
    return out.getvalue(), ".png", "image/png"


def _gif(data: bytes, jid: str) -> tuple[bytes, str, str]:
    src = Image.open(io.BytesIO(data))
    frames, durations = [], []
    total = min(96, max(1, int(getattr(src, "n_frames", 1))))
    elapsed = 0
    for index, frame in enumerate(ImageSequence.Iterator(src)):
        if index >= total or elapsed >= 8_000:
            break
        duration = max(20, int(frame.info.get("duration") or src.info.get("duration") or 80))
        frames.append(_remove(frame))
        durations.append(duration)
        elapsed += duration
        rs.job_update(jid, pct=10 + int(70 * (index + 1) / total), stage="remove")
    out = io.BytesIO()
    frames[0].save(out, "GIF", save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, disposal=2, optimize=False, transparency=0)
    return out.getvalue(), ".gif", "image/gif"


def _video(data: bytes, suffix: str, jid: str) -> tuple[bytes, str, str]:
    ffmpeg = processor.find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable")
    with tempfile.TemporaryDirectory(prefix="sm-bgremove-") as td:
        work = Path(td)
        source = work / ("source" + suffix)
        frames = work / "frames"
        frames.mkdir()
        source.write_bytes(data)
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-t", "8", "-vf", "fps=12,scale='min(750,iw)':-2", str(frames / "%05d.png"),
        ], check=True, capture_output=True)
        paths = sorted(frames.glob("*.png"))
        if not paths:
            raise RuntimeError("No video frames decoded")
        for index, path in enumerate(paths):
            cut = _remove(Image.open(path))
            cut.save(path, "PNG")
            rs.job_update(jid, pct=10 + int(70 * (index + 1) / len(paths)), stage="remove")
        output = work / "transparent.webm"
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-framerate", "12",
            "-i", str(frames / "%05d.png"), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
            "-auto-alt-ref", "0", "-an", "-y", str(output),
        ], check=True, capture_output=True)
        return output.read_bytes(), ".webm", "video/webm"


def run(jid: str, job: dict) -> None:
    """Worker entry point. All paths come from the authenticated Builder API."""
    try:
        rs.job_update(jid, status="running", pct=3, stage="load")
        source_key = str(job["source_key"])
        data = _source_bytes(source_key)
        suffix = Path(source_key).suffix.lower()
        if suffix == ".gif":
            result, out_suffix, media_type = _gif(data, jid)
        elif suffix in {".mp4", ".webm", ".mov"}:
            result, out_suffix, media_type = _video(data, suffix, jid)
        else:
            result, out_suffix, media_type = _static(data)
        output_name = str(job["output_stem"]) + out_suffix
        output_key = f"builder/{int(job['user_id'])}/{output_name}"
        _save(output_key, result, media_type)
        rs.job_update(jid, status="done", pct=100, stage="done", result={
            "url": f"/api/builder/assets/{output_name}", "media_type": media_type,
        })
    except Exception as exc:
        rs.job_update(jid, status="error", pct=100, stage="error", error=f"{type(exc).__name__}: {exc}")
