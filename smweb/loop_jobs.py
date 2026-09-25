"""Background, frame-based seamless-loop renderer for short GIF/video sources."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import traceback
from pathlib import Path

from PIL import Image

import processor as proc
import redis_store as rs
from smweb import job_diagnostics
from smweb import object_store
from smweb import process_control


def _run_cmd(command: list[str], jid: str = "") -> None:
    options = {"capture_output": True, "text": True}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = process_control.run(command, job_id=jid, **options)
    if completed.returncode:
        # Full encoder detail stays in worker logs; the Redis/client error is generic.
        print("[loop ffmpeg] " + (completed.stderr or completed.stdout or "FFmpeg failed")[-3000:], flush=True)
        raise RuntimeError("FFmpeg command failed")


def _metadata(path: Path) -> tuple[float, int]:
    probe = proc.find_ffprobe()
    if not probe:
        raise RuntimeError("FFprobe is unavailable")
    raw = subprocess.check_output(
        [probe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "format=duration:stream=width", "-of", "json", str(path)], text=True,
    )
    payload = json.loads(raw)
    duration = float(payload["format"]["duration"])
    if not 0.5 <= duration <= 30:
        raise ValueError("Animation duration must be between 0.5 and 30 seconds")
    width = max(2, min(1280, int(payload.get("streams", [{}])[0].get("width") or 750)))
    return duration, width - (width % 2)


def _link_or_copy(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def _build_sequence(raw_frames: list[Path], output: Path, mode: str, blend_frames: int) -> int:
    """Create an ordered PNG sequence without holding the whole animation in RAM."""
    if len(raw_frames) < 2 or mode not in {"blend", "pingpong"}:
        raise ValueError("Invalid loop sequence")
    output.mkdir(parents=True, exist_ok=True)
    order: list[Path] = []
    blends: list[tuple[Path, Path, float]] = []
    if mode == "pingpong":
        order = raw_frames + raw_frames[-2:0:-1] if len(raw_frames) > 2 else raw_frames
    else:
        count = min(max(1, blend_frames), max(1, len(raw_frames) // 3))
        order = raw_frames[count:-count] if len(raw_frames) > count * 2 else []
        for index in range(count):
            blends.append((raw_frames[-count + index], raw_frames[index], (index + 1) / count))
    index = 0
    for frame in order:
        _link_or_copy(frame, output / f"frame_{index:05d}.png")
        index += 1
    for tail, head, amount in blends:
        with Image.open(tail) as a, Image.open(head) as b:
            Image.blend(a.convert("RGBA"), b.convert("RGBA"), amount).save(
                output / f"frame_{index:05d}.png", "PNG", compress_level=1,
            )
        index += 1
    if index < 2:
        raise ValueError("Selected fragment is too short")
    return index


def run(jid: str, job: dict) -> None:
    root = Path(str(job["job_dir"])); source = Path(str(job["source_path"]))
    try:
        ffmpeg = proc.find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("FFmpeg is unavailable")
        fps = max(8, min(24, int(job.get("fps") or 12)))
        source_duration, source_width = _metadata(source)
        requested = max(0.5, min(8.0, float(job.get("duration") or 8)))
        start = max(0.0, min(float(job.get("start") or 0), max(0.0, source_duration - 0.5)))
        mode = str(job.get("mode") or "blend")
        if mode == "pingpong":
            requested = max(1.0, requested)
        available = source_duration - start
        fade = min(max(.25, min(.75, float(job.get("transition") or .5))), requested * .35)
        segment = min(available, requested / 2 if mode == "pingpong" else requested + fade)
        raw_dir, sequence_dir = root / "decoded", root / "sequence"
        raw_dir.mkdir(parents=True, exist_ok=True)
        rs.job_update(jid, status="running", pct=16, stage="decode", source_duration=round(source_duration, 3))
        process_control.checkpoint(jid)
        _run_cmd([
            ffmpeg, "-y", "-ss", f"{start:.4f}", "-t", f"{segment:.4f}", "-i", str(source),
            "-an", "-vf", f"fps={fps},scale='trunc(min(1280,iw)/2)*2':-2:flags=lanczos",
            str(raw_dir / "source_%05d.png"),
        ], jid)
        frames = sorted(raw_dir.glob("source_*.png"))
        if len(frames) < 4:
            raise ValueError("Selected fragment contains too few frames")
        rs.job_update(jid, pct=48, stage="join")
        frame_count = _build_sequence(frames, sequence_dir, mode, round(fade * fps))
        output_format = str(job.get("output_format") or "gif")
        rs.job_update(jid, pct=70, stage="encode")
        if output_format == "mp4":
            result = root / "seamless-loop.mp4"
            _run_cmd([
                ffmpeg, "-y", "-framerate", str(fps), "-i", str(sequence_dir / "frame_%05d.png"),
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
                "-movflags", "+faststart", str(result),
            ], jid)
            media_type = "video/mp4"
        else:
            result = root / "seamless-loop.gif"
            proc.encode_gif_from_png_sequence(sequence_dir, result, fps=fps, encoder="gifski")
            proc.ensure_under_mb(result)
            media_type = "image/gif"
        result_key = ""
        process_control.checkpoint(jid)
        if object_store.configured():
            rs.job_update(jid, pct=92, stage="upload")
            result_key = object_store.upload_file(result, f"jobs/{jid}/{result.name}", public=False)
        process_control.checkpoint(jid)
        rs.job_update(jid, status="done", pct=100, stage="done", result_path=str(result),
                      result_key=result_key, filename=result.name, media_type=media_type,
                      output_duration=round(frame_count / fps, 3), loop_mode=mode)
        cache_key = str(job.get("cache_key") or "")
        if cache_key:
            rs.job_cache_put(cache_key, jid)
        shutil.rmtree(raw_dir, ignore_errors=True); shutil.rmtree(sequence_dir, ignore_errors=True)
        if result_key:
            shutil.rmtree(root, ignore_errors=True)
        else:
            source.unlink(missing_ok=True)
    except process_control.JobCancelled:
        process_control.mark_cancelled(jid)
        shutil.rmtree(root, ignore_errors=True)
    except Exception as exc:
        traceback.print_exc()
        # Users see a generic message; the admin console gets the real cause. The
        # source stays in the job folder until the regular cleanup for reproduction.
        rs.job_update(jid, status="error", pct=100, stage="error", error="Loop processing failed",
                      error_detail=job_diagnostics.scrub(f"{type(exc).__name__}: {exc}", root)[:500],
                      error_traces=[job_diagnostics.trace_text(exc, root)])
        shutil.rmtree(root / "decoded", ignore_errors=True); shutil.rmtree(root / "sequence", ignore_errors=True)
