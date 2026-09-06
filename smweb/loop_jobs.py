"""Background seamless-loop renderer for short GIF/video sources."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import traceback
from pathlib import Path

import processor as proc
import redis_store as rs
from smweb import object_store


def _run_cmd(command: list[str]) -> None:
    options = {"capture_output": True, "text": True}
    if os.name == "nt":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(command, **options)
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout or "FFmpeg failed")[-400:])


def _metadata(path: Path) -> tuple[float, int]:
    probe = proc.find_ffprobe()
    if not probe:
        raise RuntimeError("FFprobe is unavailable")
    raw = subprocess.check_output(
        [probe, "-v", "error", "-select_streams", "v:0", "-show_entries", "format=duration:stream=width", "-of", "json", str(path)],
        text=True,
    )
    payload = json.loads(raw)
    value = float(payload["format"]["duration"])
    if not 0.5 <= value <= 30:
        raise ValueError("Animation duration must be between 0.5 and 30 seconds")
    width = max(2, min(1280, int(payload.get("streams", [{}])[0].get("width") or 750)))
    return value, width


def run(jid: str, job: dict) -> None:
    root = Path(str(job["job_dir"]))
    source = Path(str(job["source_path"]))
    try:
        ffmpeg = proc.find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("FFmpeg is unavailable")
        fps = max(8, min(24, int(job.get("fps") or 12)))
        source_duration, source_width = _metadata(source)
        requested = max(0.5, min(8.0, float(job.get("duration") or 8)))
        start = max(0.0, min(float(job.get("start") or 0), max(0.0, source_duration - 0.5)))
        mode = str(job.get("mode") or "blend")
        available = source_duration - start
        fade = min(0.7, max(0.18, requested * 0.14), requested * 0.35)
        duration = min(available, requested / 2.0 if mode == "pingpong" else requested + fade)
        output_format = str(job.get("output_format") or "gif")
        intermediate = root / "loop.mp4"
        rs.job_update(jid, status="running", pct=18, stage="analyze", source_duration=round(source_duration, 3))

        common = f"fps={fps},scale='trunc(min(1280,iw)/2)*2':-2:flags=lanczos,settb=AVTB,setpts=PTS-STARTPTS"
        if mode == "pingpong":
            graph = f"[0:v]{common},split[forward][back];[back]reverse[reverse];[forward][reverse]concat=n=2:v=1:a=0,format=yuv420p[out]"
        else:
            fade = min(fade, duration * 0.35)
            offset = max(0.05, duration - (2 * fade))
            graph = (
                f"[0:v]{common},split[body][head];"
                f"[body]trim=start={fade:.4f}:end={duration:.4f},setpts=PTS-STARTPTS[body2];"
                f"[head]trim=start=0:end={fade:.4f},setpts=PTS-STARTPTS[head2];"
                f"[body2][head2]xfade=transition=fade:duration={fade:.4f}:offset={offset:.4f},format=yuv420p[out]"
            )
        rs.job_update(jid, pct=35, stage="render")
        _run_cmd([
            ffmpeg, "-y", "-ss", f"{start:.4f}", "-t", f"{duration:.4f}", "-i", str(source),
            "-filter_complex", graph, "-map", "[out]", "-an", "-c:v", "libx264",
            "-preset", "medium", "-crf", "20", "-movflags", "+faststart", str(intermediate),
        ])

        rs.job_update(jid, pct=76, stage="encode")
        if output_format == "mp4":
            result = root / "seamless-loop.mp4"
            intermediate.replace(result)
            media_type = "video/mp4"
        else:
            result = root / "seamless-loop.gif"
            proc.media_to_gif(intermediate, result, fps=fps, width=source_width, duration=20, encoder="gifski")
            media_type = "image/gif"
            intermediate.unlink(missing_ok=True)

        result_key = ""
        if object_store.configured():
            rs.job_update(jid, pct=92, stage="upload")
            result_key = object_store.upload_file(result, f"jobs/{jid}/{result.name}", public=False)
        rs.job_update(
            jid, status="done", pct=100, stage="done", result_path=str(result),
            result_key=result_key, filename=result.name, media_type=media_type,
            output_duration=round(min(8.0, duration * 2 if mode == "pingpong" else duration - fade), 3),
        )
        if result_key:
            shutil.rmtree(root, ignore_errors=True)
        else:
            source.unlink(missing_ok=True)
    except Exception as exc:
        traceback.print_exc()
        rs.job_update(jid, status="error", pct=100, stage="error", error="Loop processing failed")
        try:
            source.unlink(missing_ok=True)
        except Exception:
            pass
