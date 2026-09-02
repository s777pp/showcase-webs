"""Background Character compositor used by the external Docker worker."""
from __future__ import annotations

import io
import shutil
import time
import traceback
from pathlib import Path

from PIL import Image

import processor as proc
import redis_store as rs
from smweb import object_store


VIDEO_EXTS = (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v")


def _animated(path: Path) -> bool:
    if path.suffix.lower() in VIDEO_EXTS + (".gif",):
        return True
    if path.suffix.lower() != ".webp":
        return False
    try:
        with Image.open(path) as image:
            return int(getattr(image, "n_frames", 1) or 1) > 1
    except Exception:
        return False


def _sweep_old_jobs(jobs_root: Path, max_age: float = 3600.0) -> None:
    """Drop job directories older than the Redis job TTL.

    Without this, every render that could not be uploaded to R2 leaves its
    inputs and rendered frames on the shared volume permanently.
    """
    try:
        now = time.time()
        for entry in jobs_root.iterdir():
            if not entry.is_dir():
                continue
            try:
                if now - entry.stat().st_mtime > max_age:
                    shutil.rmtree(entry, ignore_errors=True)
            except Exception:
                continue
    except Exception:
        pass


def run(jid: str, job: dict) -> None:
    try:
        _run(jid, job)
    except Exception as exc:
        traceback.print_exc()
        rs.job_update(
            jid, status="error", pct=100, stage="error",
            error=f"{type(exc).__name__}: {exc}",
        )
        try:
            shutil.rmtree(Path(str(job.get("job_dir") or "")), ignore_errors=True)
        except Exception:
            pass


def _run(jid: str, job: dict) -> None:
    root = Path(str(job["job_dir"]))
    background = Path(str(job["background_path"]))
    character = Path(str(job["character_path"]))
    opts = dict(job.get("options") or {})
    width = max(100, min(1920, int(opts.get("width") or 750)))
    fps = max(5, min(30, int(opts.get("fps") or 12)))
    key = str(opts.get("chroma_key") or "auto")
    tol = float(opts.get("chroma_tol") or 55)
    feather = max(0.0, min(4.0, float(opts.get("feather") or 1.6)))
    scale = max(0.05, min(4.0, float(opts.get("scale") or 1.0)))
    offset_x = max(0.0, min(1.0, float(opts.get("offset_x") or 0.5)))
    offset_y = max(0.0, min(1.0, float(opts.get("offset_y") or 1.0)))
    encoder = str(opts.get("gif_encoder") or "gifski").lower()
    if encoder not in ("ffmpeg", "gifski", "pillow"):
        encoder = "gifski"

    rs.job_update(jid, status="running", pct=10, stage="decode")
    animated = _animated(background) or _animated(character)
    if animated:
        bg = background
        ch = character
        if background.suffix.lower() in VIDEO_EXTS:
            rs.job_update(jid, pct=18, stage="background")
            bg = root / "background.gif"
            proc.media_to_gif(background, bg, fps=fps, width=width, duration=8)
        if character.suffix.lower() in VIDEO_EXTS:
            rs.job_update(jid, pct=30, stage="character")
            ch = root / "character.gif"
            proc.media_to_gif(character, ch, fps=fps, width=min(width, 800), duration=8)
        rs.job_update(jid, pct=45, stage="chromakey")
        frames, durations = proc.compose_animated_layers(
            bg, ch, chroma_key=key, chroma_tol=tol, scale=scale,
            offset_x=offset_x, offset_y=offset_y, feather=feather,
            target_width=width, fps=fps, max_seconds=8,
        )
        rs.job_update(jid, pct=72, stage="encode")
        result = root / "composed.gif"
        if encoder == "pillow":
            proc._save_animated_gif([proc._quantize_rgba_for_gif(f) for f in frames], durations, result)
        else:
            frame_dir = root / "frames"
            frame_dir.mkdir(parents=True, exist_ok=True)
            for i, frame in enumerate(frames):
                frame.convert("RGBA").save(frame_dir / f"frame_{i:04d}.png")
            try:
                proc.encode_gif_from_png_sequence(frame_dir, result, fps=fps, encoder=encoder)
            except Exception:
                proc._save_animated_gif([proc._quantize_rgba_for_gif(f) for f in frames], durations, result)
        proc.ensure_under_mb(result)
        media_type = "image/gif"
    else:
        rs.job_update(jid, pct=45, stage="chromakey")
        bg_image = Image.open(background).convert("RGBA")
        if bg_image.width != width:
            height = max(1, int(bg_image.height * width / max(1, bg_image.width)))
            bg_image = bg_image.resize((width, height), Image.Resampling.LANCZOS)
        char_image = Image.open(character).convert("RGBA")
        output = proc.compose_static(
            bg_image, char_image, chroma_key=key, chroma_tol=tol,
            scale=scale, offset_x=offset_x, offset_y=offset_y, feather=feather,
        )
        result = root / "composed.png"
        output.save(result, "PNG")
        media_type = "image/png"

    result_key = ""
    if object_store.configured():
        rs.job_update(jid, pct=92, stage="upload")
        result_key = object_store.upload_file(result, f"jobs/{jid}/{result.name}", public=False)
    shutil.rmtree(root / "frames", ignore_errors=True)
    rs.job_update(
        jid, status="done", pct=100, stage="done", result_path=str(result),
        result_key=result_key, filename=result.name, media_type=media_type,
    )
    # R2 is the durable result store in production, so once the result is there
    # the whole job directory can go. Without R2 the file itself has to stay --
    # /api/compose/download reads it from disk -- but the (much larger) inputs
    # never need to survive the render.
    if result_key:
        shutil.rmtree(root, ignore_errors=True)
    else:
        for leftover in (background, character):
            try:
                if leftover.is_file() and leftover != result:
                    leftover.unlink()
            except Exception:
                pass
        for stale in (root / "background.gif", root / "character.gif"):
            try:
                if stale.is_file() and stale != result:
                    stale.unlink()
            except Exception:
                pass
    _sweep_old_jobs(root.parent)
