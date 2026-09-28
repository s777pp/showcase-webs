"""Background, frame-based seamless-loop renderer for short GIF/video sources."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import traceback
from pathlib import Path

import numpy as np
from PIL import Image

import processor as proc
import redis_store as rs
from smweb import job_diagnostics
from smweb import object_store
from smweb import process_control
from smweb import saved_results


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


def _signatures(frames: list[Path]) -> np.ndarray:
    """Small grayscale copies of every frame, enough to compare scenes quickly."""
    rows = []
    for frame in frames:
        with Image.open(frame) as image:
            gray = image.convert("L")
            width = 96
            height = max(8, round(gray.height * width / max(1, gray.width)))
            rows.append(np.asarray(gray.resize((width, height), Image.Resampling.BILINEAR), dtype=np.float32).ravel())
    return np.stack(rows)


def find_loop(sig: np.ndarray, want: int, lo: int, hi: int, first: int, last_start: int) -> tuple[int, int, float]:
    """Pick frames (i, j) so that playing i..j-1 and jumping back to i looks continuous.

    Frame j is what would follow the loop's last frame, so the best pair is the
    one where j looks like i.  Neighbouring frames are compared too, which
    makes the speed and direction of motion match, not only the picture.  A
    penalty keeps the length close to the user's selection.  Returns
    (i, j, seam) where seam is the remaining mismatch relative to an ordinary
    step between two frames (<= ~1.3 means the jump looks like normal playback).
    """
    n = len(sig)
    steps = np.abs(np.diff(sig, axis=0)).mean(axis=1)
    step = float(np.median(steps)) + 1e-3
    best = (first, min(n - 1, first + want), float("inf"), float("inf"))
    for i in range(first, max(first, last_start) + 1):
        j0, j1 = i + lo, min(n - 1, i + hi)
        if j1 < j0:
            break
        js = np.arange(j0, j1 + 1)
        here = np.abs(sig[js] - sig[i]).mean(axis=1)
        cost = here.copy()
        weight = 1.0
        for offset in (-1, 1):
            ok = (js + offset >= 0) & (js + offset < n) & (0 <= i + offset < n)
            if ok.all():
                cost += 0.5 * np.abs(sig[js + offset] - sig[i + offset]).mean(axis=1)
                weight += 0.5
        cost = cost / weight + 0.6 * step * np.abs(js - i - want) / max(1, want)
        k = int(np.argmin(cost))
        if cost[k] < best[2]:
            best = (i, int(js[k]), float(cost[k]), float(here[k]))
    return best[0], best[1], best[3] / step


_RIFE = None


def _rife():
    """RIFE interpolator when PyTorch and the weights are installed, else None."""
    global _RIFE
    if _RIFE is None:
        weights = Path(os.environ.get("RIFE_WEIGHTS") or Path(__file__).resolve().parents[1] / "models" / "flownet_v4.25.pkl")
        try:
            import torch
            import rife_net
            if not weights.is_file():
                raise FileNotFoundError(weights)
            # All cores but one: the join is the slowest step of a loop, and one
            # core stays free for the web process and a parallel job.
            torch.set_num_threads(max(1, int(os.environ.get("RIFE_THREADS") or (os.cpu_count() or 2) - 1)))
            _RIFE = rife_net.Interpolator(str(weights))
        except Exception as exc:
            print(f"[loop] RIFE unavailable, using optical-flow morph ({type(exc).__name__})", flush=True)
            _RIFE = False
    return _RIFE or None


def _morph(tail: Path, head: Path, t: float) -> Image.Image:
    """In-between picture of two frames at 0..1 without ghosting.

    A plain crossfade shows both pictures at once.  RIFE is used when
    installed; otherwise each frame is warped part of the way towards the
    other along OpenCV optical flow before mixing, so hair, snow and hands
    travel instead of dissolving.  Last resort: a plain crossfade.
    """
    with Image.open(tail) as a_img, Image.open(head) as b_img:
        a_rgba, b_rgba = a_img.convert("RGBA"), b_img.convert("RGBA")
    rife = _rife()
    if rife and min(a_rgba.size) >= 32:
        # RIFE (a neural frame interpolator) handles occlusions and fine detail
        # such as hair and petals much better than classic optical flow.
        try:
            return rife.at(a_rgba, b_rgba, t).convert("RGBA")
        except Exception as exc:
            print(f"[loop] RIFE frame failed, using morph ({type(exc).__name__})", flush=True)
    try:
        import cv2
    except ImportError:
        return Image.blend(a_rgba, b_rgba, t)
    a, b = np.asarray(a_rgba), np.asarray(b_rgba)
    h, w = a.shape[:2]
    if min(h, w) < 16 or a.shape != b.shape:
        return Image.blend(a_rgba, b_rgba, t)
    scale = min(1.0, 480 / max(h, w))
    small = (max(8, round(w * scale)), max(8, round(h * scale)))
    ga = cv2.resize(cv2.cvtColor(a, cv2.COLOR_RGBA2GRAY), small, interpolation=cv2.INTER_AREA)
    gb = cv2.resize(cv2.cvtColor(b, cv2.COLOR_RGBA2GRAY), small, interpolation=cv2.INTER_AREA)
    try:
        dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        f_ab = cv2.resize(dis.calc(ga, gb, None), (w, h), interpolation=cv2.INTER_LINEAR) / scale
        f_ba = cv2.resize(dis.calc(gb, ga, None), (w, h), interpolation=cv2.INTER_LINEAR) / scale
    except cv2.error:
        return Image.blend(a_rgba, b_rgba, t)
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    warp_a = cv2.remap(a, gx - t * f_ab[..., 0], gy - t * f_ab[..., 1],
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    warp_b = cv2.remap(b, gx - (1 - t) * f_ba[..., 0], gy - (1 - t) * f_ba[..., 1],
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    mixed = cv2.addWeighted(warp_a, 1 - t, warp_b, t, 0)
    return Image.fromarray(mixed, "RGBA")


def _build_sequence(raw_frames: list[Path], output: Path, mode: str, blend_frames: int,
                    want: int = 0, preroll: int = 0, max_frames: int = 0) -> tuple[int, str]:
    """Create an ordered PNG sequence without holding the whole animation in RAM.

    Returns (frame count, seam) where seam is "pingpong", "exact" (the loop
    point matched on its own) or "crossfade".
    """
    if len(raw_frames) < 2 or mode not in {"blend", "pingpong"}:
        raise ValueError("Invalid loop sequence")
    output.mkdir(parents=True, exist_ok=True)
    order: list[Path] = []
    blends: list[tuple[Path, Path, float]] = []
    seam = "pingpong"
    if mode == "pingpong":
        order = raw_frames + raw_frames[-2:0:-1] if len(raw_frames) > 2 else raw_frames
    else:
        sig = _signatures(raw_frames)
        # A hard cut inside the decoded range (a new scene, or the point where a
        # re-uploaded loop starts over) must not end up inside the loop or its
        # transition: keep the cut-free run that covers most of the selection.
        steps = np.abs(np.diff(sig, axis=0)).mean(axis=1)
        cuts = [k + 1 for k in np.flatnonzero(steps > max(20.0, 6 * float(np.median(steps))))]
        bounds = [0, *cuts, len(raw_frames)]
        runs = [(a, b) for a, b in zip(bounds, bounds[1:]) if b - a >= 4]
        if not runs:
            raise ValueError("Selected fragment is too short")
        start_at, end_at = max(runs, key=lambda r: min(r[1], preroll + (want or len(raw_frames))) - max(r[0], preroll))
        raw_frames, sig = raw_frames[start_at:end_at], sig[start_at:end_at]
        preroll = max(0, preroll - start_at)
        n = len(raw_frames)
        want = max(4, min(want or n, n - 1))
        # The loop stays inside what the user selected: its length may move by
        # 15% and its start by 20% of the selection to find a better join.
        lo, hi = max(4, round(want * .85)), max(4, min(round(want * 1.15), max_frames or n))
        first = min(max(1, preroll), n - lo - 1) if n - lo - 1 >= 1 else 0
        last_start = min(n - lo - 1, first + max(1, round(want * .2)))
        i, j, mismatch = find_loop(sig, want, lo, hi, first, last_start)
        order = raw_frames[i:j]
        count = 0
        if mismatch > 1.3:
            # Very different ends need a longer morph, otherwise the motion
            # visibly speeds up during the transition.
            count = blend_frames if mismatch <= 3 else max(blend_frames, round((j - i) * .3))
            count = min(count, i, max(1, (j - i) // 3))
        seam = "exact" if count == 0 else "crossfade"
        if count:
            # Both streams keep moving forward: the loop's last frames morph into
            # the frames that come right before its first frame, so the next
            # frame played (frame i) continues the motion instead of jumping.
            order = raw_frames[i:j - count]
            for m in range(count):
                t = (m + 1) / (count + 1)
                blends.append((raw_frames[j - count + m], raw_frames[i - count + m], t * t * (3 - 2 * t)))
    index = 0
    for frame in order:
        _link_or_copy(frame, output / f"frame_{index:05d}.png")
        index += 1
    for tail, head, amount in blends:
        _morph(tail, head, amount).save(output / f"frame_{index:05d}.png", "PNG", compress_level=1)
        index += 1
    if index < 2:
        raise ValueError("Selected fragment is too short")
    return index, seam


def render_sequence(source: Path, root: Path, *, mode: str, fps: int, start: float, duration: float,
                    transition: float, max_width: int = 1280, progress=None, jid: str = "") -> tuple[int, str, Path]:
    """Decode the selected fragment and build the loop's PNG sequence.

    Shared by the full job and the quick preview, so both find the same join.
    Returns (frame count, seam kind, sequence directory).
    """
    ffmpeg = proc.find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable")
    source_duration, _width = _metadata(source)
    requested = max(0.5, min(8.0, float(duration or 8)))
    start = max(0.0, min(float(start or 0), max(0.0, source_duration - 0.5)))
    if mode == "pingpong":
        requested = max(1.0, requested)
    fade = min(max(.25, min(.75, float(transition or .5))), requested * .35)
    preroll = 0.0
    if mode == "pingpong":
        segment = min(source_duration - start, requested / 2)
    else:
        # Decode a little before the selection (frames to fade into) and past
        # its end, so the loop point can be searched for.
        preroll = min(start, max(fade, requested * .3))
        start -= preroll
        segment = min(source_duration - start, preroll + min(8.0, requested * 1.15) + requested * .2)
    raw_dir, sequence_dir = root / "decoded", root / "sequence"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if progress:
        progress("decode", 16, source_duration=round(source_duration, 3))
    _run_cmd([
        ffmpeg, "-y", "-ss", f"{start:.4f}", "-t", f"{segment:.4f}", "-i", str(source),
        "-an", "-vf", f"fps={fps},scale='trunc(min({max_width},iw)/2)*2':-2:flags={proc.SCALE_FLAGS}{proc.source_matrix(source)}",
        str(raw_dir / "source_%05d.png"),
    ], jid)
    frames = sorted(raw_dir.glob("source_*.png"))
    if len(frames) < 4:
        raise ValueError("Selected fragment contains too few frames")
    if progress:
        progress("join", 48)
    frame_count, seam = _build_sequence(frames, sequence_dir, mode, round(fade * fps),
                                        want=round(min(8.0, requested) * fps), preroll=round(preroll * fps),
                                        max_frames=8 * fps)
    return frame_count, seam, sequence_dir


def preview(source: Path, *, mode: str, start: float, duration: float, transition: float) -> bytes:
    """Small MP4 of the finished loop (360 px, 12 fps) to check the join first."""
    root = Path(tempfile.mkdtemp(prefix="sm_loop_preview_"))
    try:
        fps = 12
        count, _seam, sequence_dir = render_sequence(source, root, mode=mode, fps=fps, start=start,
                                                     duration=duration, transition=transition, max_width=360)
        out = root / "preview.mp4"
        _run_cmd([
            proc.find_ffmpeg(), "-y", "-framerate", str(fps), "-i", str(sequence_dir / "frame_%05d.png"),
            "-an", "-vf", "scale='trunc(iw/2)*2':'trunc(ih/2)*2'", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
        ])
        return out.read_bytes()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run(jid: str, job: dict) -> None:
    root = Path(str(job["job_dir"])); source = Path(str(job["source_path"]))
    try:
        ffmpeg = proc.find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("FFmpeg is unavailable")
        fps = max(8, min(24, int(job.get("fps") or 12)))

        def progress(stage: str, pct: int, **extra) -> None:
            if stage == "decode":
                rs.job_update(jid, status="running", pct=pct, stage=stage, **extra)
            else:
                rs.job_update(jid, pct=pct, stage=stage)
            process_control.checkpoint(jid)

        frame_count, seam, sequence_dir = render_sequence(
            source, root, mode=str(job.get("mode") or "blend"), fps=fps,
            start=float(job.get("start") or 0), duration=float(job.get("duration") or 8),
            transition=float(job.get("transition") or .5), progress=progress, jid=jid,
        )
        mode = str(job.get("mode") or "blend")
        raw_dir = root / "decoded"
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
            # Fit the Steam limit from the full-colour frames, not by re-quantizing the GIF.
            if not proc.fit_frames_to_gif(sequence_dir, result, fps=fps):
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
                      output_duration=round(frame_count / fps, 3), loop_mode=mode, loop_seam=seam)
        saved_results.save_job_result(jid, user_key=str(job.get("user_key") or ""), result_path=result,
                                      kind="seamless_loop", mode=str(mode or ""))
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
