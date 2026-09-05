"""Background job store and the worker that runs the heavy pipelines.

Moved out of main.py unchanged; see docs/STRUCTURE.md.
"""


from __future__ import annotations

import hashlib
import hmac
import html
import io
import ipaddress
import json
import logging
import os
import re
import socket
import secrets
import tempfile
import shutil
import time
import uuid
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db


from smweb.core import JOBS, MAX_UPLOAD_MB


JOB_RESULT_TTL_SECONDS = max(120, int(os.environ.get("JOB_RESULT_TTL_SECONDS") or 900))


def _cleanup_old_jobs(max_age_sec: float | None = None) -> int:
    """Delete expired shared job folders without touching queued/running work."""
    import time as _time
    max_age_sec = float(max_age_sec or JOB_RESULT_TTL_SECONDS)
    removed = 0
    try:
        if not JOBS.is_dir():
            return 0
        now = _time.time()
        for p in list(JOBS.iterdir()):
            try:
                if not p.is_dir():
                    # orphan files
                    if now - p.stat().st_mtime > max_age_sec:
                        p.unlink(missing_ok=True)
                        removed += 1
                    continue
                job = rs.job_get(p.name)
                if job and job.get("status") in ("queued", "running"):
                    continue
                # Redis's update timestamp marks actual completion. Directory
                # mtime can be much older when a long GIF job finishes.
                updated = float((job or {}).get("updated") or 0)
                touched = max(p.stat().st_mtime, updated)
                if now - touched >= max_age_sec:
                    shutil.rmtree(p, ignore_errors=True)
                    removed += 1
            except Exception:
                continue
    except Exception as e:
        print("cleanup jobs:", e)
    return removed


def _cleanup_loop():
    import time as _time
    while True:
        try:
            n = _cleanup_old_jobs()
            if n:
                print(f"cleanup: removed {n} old job(s)")
        except Exception as e:
            print("cleanup loop:", e)
        _time.sleep(30)


# start background cleaner
try:
    import threading
    threading.Thread(target=_cleanup_loop, daemon=True, name="job-cleaner").start()
except Exception as e:
    print("cleanup thread:", e)


# ====================== Async process jobs (real progress) ======================
_process_jobs: dict[str, dict] = {}


_process_jobs_lock = __import__("threading").Lock()


# Bounded pool for heavy FFmpeg/gifski work. Raw threads let N parallel GIF
# encodes saturate the CPU and stall the API for everyone else.
MAX_JOB_WORKERS = max(1, int(os.environ.get("MAX_JOB_WORKERS") or 1))


_job_pool = ThreadPoolExecutor(max_workers=MAX_JOB_WORKERS, thread_name_prefix="job")


def _worker_mode() -> str:
    """'embedded' (default) — process in this container's pool.
    'external'  — a separate worker.py process drains the Redis queue.

    Default is embedded: on Railway there is only one service, so an enqueued
    job would otherwise sit in the queue with nobody to pop it.
    """
    m = (os.environ.get("WORKER_MODE") or "").strip().lower()
    if m in ("embedded", "external"):
        return m
    # back-compat: USE_EXTERNAL_WORKER=1 used to mean "an external worker exists"
    if (os.environ.get("USE_EXTERNAL_WORKER") or "0").lower() in ("1", "true", "yes", "on"):
        return "external"
    return "embedded"


def _job_set(jid: str, **kw) -> None:
    with _process_jobs_lock:
        j = _process_jobs.get(jid) or {}
        j.update(kw)
        j["updated"] = time.time()
        _process_jobs[jid] = j
    try:
        rs.job_update(jid, **kw)  # upsert; shared source of truth
    except Exception:
        pass


def _job_get(jid: str) -> dict | None:
    """Redis first: the job may have been produced by another uvicorn worker or by
    the external worker process, in which case this process's dict knows nothing
    about it (or is frozen at 'queued'). Local dict is the offline fallback."""
    try:
        shared = rs.job_get(jid)
    except Exception:
        shared = None
    with _process_jobs_lock:
        local = _process_jobs.get(jid)
        local = dict(local) if local else None
    if shared:
        if local:
            local.update(shared)
            return local
        return shared
    return local


def _job_cleanup_old(max_age: float = 600.0) -> None:
    now = time.time()
    with _process_jobs_lock:
        dead = [k for k, v in _process_jobs.items() if now - float(v.get("updated") or 0) > max_age]
        for k in dead:
            j = _process_jobs.pop(k, None)
            if j and j.get("zip_path"):
                try:
                    Path(j["zip_path"]).unlink(missing_ok=True)
                except Exception:
                    pass
            if j and j.get("job_dir"):
                try:
                    shutil.rmtree(j["job_dir"], ignore_errors=True)
                except Exception:
                    pass


def _run_process_job_from_payload(jid: str, job: dict) -> None:
    """Worker entry: keep file paths lazy so a batch is not all resident in RAM."""
    import redis_store as _rs
    files_data = []
    for item in job.get("files") or []:
        name = item.get("name") or "file"
        path = item.get("path")
        if path and Path(path).is_file():
            files_data.append((name, Path(path)))
    opts = job.get("opts") or {}
    if not files_data:
        _rs.job_update(jid, status="error", pct=100, stage="error", error="No files")
        return
    # Reuse existing runner if present
    try:
        _run_process_job(jid, files_data, opts)
    except TypeError:
        # if signature differs, mark error
        _rs.job_update(jid, status="error", pct=100, stage="error", error="Worker incompatible")
        raise


    # No explicit sync needed: _run_process_job writes through _job_set, which
    # upserts into Redis on every progress step.


def _run_process_job(jid: str, files_data: list[tuple[str, bytes | Path]], opts: dict) -> None:
    """Background worker: same pipeline as /api/process, updates progress."""
    import time as _sm_time
    _sm_job_t0 = _sm_time.perf_counter()
    print(f"[JOB TIMING] START jid={jid}", flush=True)
    # The API and external worker are different containers. Results must live
    # in their shared /data volume, never in the worker-only /tmp filesystem.
    job_dir = JOBS / jid
    job_dir.mkdir(parents=True, exist_ok=True)
    _job_set(jid, status="running", pct=5, stage="prepare", job_dir=str(job_dir), error=None)
    zip_path = job_dir / "result.zip"
    processed = 0
    errors: list[str] = []
    listed: list[dict] = []
    modes = opts["modes"]
    text = opts["text"]
    opacity = opts["opacity"]
    color = opts["color"]
    corner = opts["corner"]
    scale = opts["scale"]
    wm_x_f = opts["wm_x"]
    wm_y_f = opts["wm_y"]
    do_ac = opts["do_ac"]
    size_i = opts["size_i"]
    fps = opts["fps"]
    enc = opts["enc"]
    n_files = max(1, len(files_data))
    try:
        zf = zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED)
        for fi, (name, raw) in enumerate(files_data):
            if isinstance(raw, Path):
                raw = raw.read_bytes()
            base_pct = 8 + int(80 * fi / n_files)
            _job_set(jid, pct=base_pct, stage=f"file:{name}")
            try:
                if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
                    errors.append(f"{name}: >{MAX_UPLOAD_MB}MB")
                    continue
                ext = Path(name).suffix.lower()
                stem = Path(name).stem[:40]
                if ext not in (
                    ".png", ".jpg", ".jpeg", ".webp", ".bmp",
                    ".gif", ".mp4", ".mov", ".webm", ".avi", ".mkv",
                ):
                    errors.append(f"{name}: unsupported format")
                    continue
                for mi, mode in enumerate(modes):
                    folder = f"{stem}_{mode}"
                    work = job_dir / folder
                    work.mkdir(exist_ok=True)
                    stage = "image" if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp") else (
                        "video" if ext in (".mp4", ".mov", ".webm", ".avi", ".mkv") else "gif"
                    )
                    _job_set(
                        jid,
                        pct=min(90, base_pct + int(12 * (mi + 1) / max(1, len(modes)))),
                        stage=f"{stage}:{mode}:{name}",
                    )
                    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                        img = Image.open(io.BytesIO(raw))
                        img.load()
                        max_side = 4096
                        if max(img.size) > max_side:
                            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                        if do_ac:
                            from PIL import ImageOps
                            rgb = img.convert("RGB")
                            rgb = ImageOps.autocontrast(rgb, cutoff=1)
                            img = rgb
                        if mode == "workshop" and img.size[0] != size_i:
                            nh = max(1, int(img.size[1] * (size_i / max(1, img.size[0]))))
                            img = img.resize((size_i, nh), Image.Resampling.LANCZOS)
                        if mode == "workshop":
                            parts = proc.process_image_workshop(
                                img, text, opts["wm_font"], opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        elif mode == "featured":
                            parts = proc.process_image_featured(
                                img, text, opts["wm_font"], opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        else:
                            parts = proc.process_image_split(
                                img, text, opts["wm_font"], opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        for pname, data in parts.items():
                            zf.writestr(f"{folder}/{pname}", data)
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/{pname}", "size": len(data)})
                    else:
                        src = work / f"source{ext}"
                        src.write_bytes(raw)
                        is_video = ext in (".mp4", ".mov", ".webm", ".avi", ".mkv")
                        v_fps = min(int(fps), 12)
                        v_dur = 8.0
                        encoder = enc
                        if encoder == "pillow":
                            encoder = "ffmpeg"
                        if is_video:
                            if not proc.find_ffmpeg():
                                raise RuntimeError("FFmpeg not available")
                            if mode == "workshop":
                                paths = proc.process_video_workshop(
                                    src, work, fps=v_fps, width=size_i,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity, wm_color=color,
                                    duration=v_dur, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=encoder,
                                )
                            elif mode == "featured":
                                paths = proc.process_video_featured(
                                    src, work, fps=v_fps, duration=v_dur, encoder=encoder,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity, wm_color=color,
                                    wm_corner=corner, wm_scale=scale, wm_x=wm_x_f, wm_y=wm_y_f,
                                )
                            else:
                                paths = proc.process_video_split(
                                    src, work, fps=v_fps,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity, wm_color=color,
                                    duration=v_dur, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=encoder,
                                )
                        else:
                            if mode == "workshop":
                                paths = proc.process_gif_workshop(
                                    src, work,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=encoder, fps=v_fps,
                                )
                            elif mode == "featured":
                                paths = proc.process_gif_featured(
                                    src, work, fps=v_fps, encoder=encoder,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f,
                                )
                            else:
                                paths = proc.process_gif_split(
                                    src, work, fps=v_fps,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=encoder,
                                )
                        for pname, pth in paths.items():
                            pth = Path(pth)
                            if not pth.is_file():
                                continue
                            size_bytes = pth.stat().st_size
                            zf.write(pth, f"{folder}/{pname}")
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/{pname}", "size": size_bytes})
                            try:
                                pth.unlink(missing_ok=True)
                            except Exception:
                                pass
                        try:
                            src.unlink(missing_ok=True)
                        except Exception:
                            pass
                processed += 1
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {e}")
        _sm_zip_t0 = _sm_time.perf_counter()
        try:
            zf.close()
        except Exception:
            pass
        print(
            f"[JOB TIMING] ZIP close: {_sm_time.perf_counter()-_sm_zip_t0:.3f}s",
            flush=True,
        )
        if processed == 0:
            detail = "; ".join(errors) if errors else "unknown error"
            _job_set(jid, status="error", pct=100, stage="error", error=f"Failed: {detail}", errors=errors)
            shutil.rmtree(job_dir, ignore_errors=True)
            return
        print(f"[JOB TIMING] ZIP size={zip_path.stat().st_size / 1024 / 1024:.2f}MB", flush=True)
        # quota already counted on start
        _job_set(
            jid,
            status="done",
            pct=100,
            stage="done",
            zip_path=str(zip_path),
            processed=processed,
            errors=errors,
            listed=listed,
        )
        print(
            f"[JOB TIMING] TOTAL: {_sm_time.perf_counter()-_sm_job_t0:.3f}s | jid={jid}",
            flush=True,
        )
    except Exception as e:
        _job_set(jid, status="error", pct=100, stage="error", error=f"{type(e).__name__}: {e}")
        shutil.rmtree(job_dir, ignore_errors=True)
