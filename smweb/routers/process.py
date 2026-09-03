"""The showcase pipeline: start, status, download, legacy sync route.

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


from fastapi import APIRouter


from smweb.core import (
    FREE_LIMIT,
    JOBS,
    MAX_UPLOAD_MB,
    _auth_user,
    _ip,
    quota_inc,
    quota_state,
)
from smweb.jobs import (
    _job_cleanup_old,
    _job_get,
    _job_pool,
    _job_set,
    _run_process_job,
    _worker_mode,
)



router = APIRouter()


def _watermark_options(
    quota: dict,
    wm_text: str,
    wm_font: str,
    wm_opacity: int,
    wm_enable: str,
    wm_corner: str,
    wm_scale: float,
    wm_color: str,
    wm_x: str,
    wm_y: str,
) -> tuple[str, str, float, str, float, str, float | None, float | None]:
    """Return trusted watermark settings for the processing pipeline.

    Free-tier branding is enforced here instead of only in the browser, so it
    cannot be disabled or changed by editing the form payload.
    """
    if not quota.get("pro"):
        return "ShowcaseMaker", "Fineday", 0.50, "bl", 1.0, "#ffffff", None, None

    wm_on = wm_enable not in ("0", "false", "False", "")
    opacity = (wm_opacity / 100.0) if wm_on else 0.0
    text = wm_text if wm_on else ""
    color = (wm_color or "#ffffff").strip() or "#ffffff"
    corner = (wm_corner or "bl").strip().lower()
    if corner not in ("tl", "tr", "bl", "br"):
        corner = "bl"
    try:
        scale = max(0.4, min(2.5, float(wm_scale)))
    except (TypeError, ValueError):
        scale = 1.0
    wm_x_f = wm_y_f = None
    try:
        if str(wm_x).strip() != "" and str(wm_y).strip() != "":
            wm_x_f = max(0.0, min(1.0, float(wm_x)))
            wm_y_f = max(0.0, min(1.0, float(wm_y)))
    except (TypeError, ValueError):
        wm_x_f = wm_y_f = None
    return text, wm_font, opacity, corner, scale, color, wm_x_f, wm_y_f


@router.post("/api/process/start")
async def api_process_start(
    request: Request,
    mode: str = Form("workshop"),
    fps: int = Form(12),
    size: int = Form(750),
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_enable: str = Form("1"),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    wm_x: str = Form(""),
    wm_y: str = Form(""),
    auto_contrast: str = Form("0"),
    gif_encoder: str = Form("gifski"),
    all_modes: str = Form("0"),
    files: list[UploadFile] = File(...),
):
    """Start async job; poll /api/process/status/{id} then download."""
    _job_cleanup_old()
    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Limit {FREE_LIMIT} files/day. Enter access code or buy Pro."},
            status_code=403,
        )
    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)
    do_all = str(all_modes).lower() in ("1", "true", "yes", "on")
    modes = ["workshop", "featured", "split"] if do_all else [mode]
    text, wm_font, opacity, corner, scale, color, wm_x_f, wm_y_f = _watermark_options(
        q, wm_text, wm_font, wm_opacity, wm_enable, wm_corner,
        wm_scale, wm_color, wm_x, wm_y,
    )
    do_ac = str(auto_contrast).lower() in ("1", "true", "yes", "on")
    try:
        size_i = int(size)
    except (TypeError, ValueError):
        size_i = 750
    if size_i not in (630, 640, 750, 800):
        size_i = min((630, 640, 750, 800), key=lambda s: abs(s - size_i))
    left = 999 if q["pro"] else q["left"]
    files = files[: max(1, left)]
    files_data: list[tuple[str, bytes]] = []
    for uf in files:
        name = uf.filename or "file"
        raw = await uf.read()
        files_data.append((name, raw))
    if not files_data:
        return JSONResponse({"ok": False, "msg": "No files"}, status_code=400)
    enc = (gif_encoder or "ffmpeg").strip().lower()
    if enc not in ("ffmpeg", "gifski", "pillow"):
        enc = "ffmpeg"
    jid = secrets.token_hex(12)
    opts = {
        "modes": modes,
        "text": text,
        "opacity": opacity,
        "color": color,
        "corner": corner,
        "scale": scale,
        "wm_x": wm_x_f,
        "wm_y": wm_y_f,
        "do_ac": do_ac,
        "size_i": size_i,
        "fps": fps,
        "enc": enc,
        "wm_font": wm_font,
    }
    user_key = ""
    try:
        u = _auth_user(request)
        # Anonymous callers are keyed by IP. Using request.client.host here
        # meant the proxy's address behind Railway, so every logged-out user
        # shared one MAX_JOBS_PER_USER budget and blocked each other.
        user_key = str(u.get("id") or "") if u else _ip(request)
    except Exception:
        user_key = ""
    # Check the per-user cap BEFORE registering the job or charging quota,
    # otherwise a rejected request still burns a free-tier slot.
    if user_key and rs.job_count_user(user_key) >= int(os.environ.get("MAX_JOBS_PER_USER", "2")):
        return JSONResponse(
            {"ok": False, "msg": "Too many active jobs. Wait for current processing to finish."},
            status_code=429,
        )

    # persist uploads to disk (the worker — embedded or external — reads them back)
    job_upload_dir = JOBS / jid
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    files_meta = []
    for name, raw in files_data:
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:80] or "file"
        p = job_upload_dir / safe
        p.write_bytes(raw)
        files_meta.append({"name": name, "path": str(p)})

    # Only hand the job to an external worker if one is actually alive; otherwise
    # the entry would sit in the Redis queue forever with nobody to pop it.
    mode = _worker_mode()
    external = mode == "external" and rs.redis_ok() and rs.worker_alive()
    if mode == "external" and not external:
        print(
            f"[job {jid[:8]}] WORKER_MODE=external but no live worker "
            f"(redis={rs.redis_ok()} beat={rs.worker_alive()}) — running embedded",
            flush=True,
        )

    payload = {
        "status": "queued", "pct": 1, "stage": "queued",
        "user_key": user_key, "files": files_meta, "opts": opts,
        "created": time.time(),
    }
    rs.job_create(jid, payload, enqueue=external)
    _job_set(jid, status="queued", pct=1, stage="queued", created=time.time(), user_key=user_key)
    try:
        quota_inc(request, len(files_data))
    except Exception:
        pass
    if not external:
        _job_pool.submit(_run_process_job, jid, files_data, opts)
    return {"ok": True, "job_id": jid}


@router.get("/api/process/status/{job_id}")
def api_process_status(job_id: str):
    j = _job_get(job_id)
    if not j:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    out = {
        "ok": True,
        "status": j.get("status"),
        "pct": int(j.get("pct") or 0),
        "stage": j.get("stage") or "",
        "error": j.get("error"),
        "processed": j.get("processed"),
        "errors": j.get("errors") or [],
    }
    if j.get("status") == "done":
        out["download"] = f"/api/process/download/{job_id}"
    return out


@router.get("/api/process/download/{job_id}")
def api_process_download(job_id: str):
    j = _job_get(job_id)
    if not j:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    if j.get("status") != "done" or not j.get("zip_path"):
        return JSONResponse(
            {"ok": False, "msg": f"Not ready (status={j.get('status') or 'unknown'})"},
            status_code=409,
        )
    path = Path(j["zip_path"])
    if not path.is_file():
        # Result was cleaned up, or produced on a filesystem this instance cannot see.
        return JSONResponse(
            {"ok": False, "msg": "Result expired or stored on another instance. Please run the job again."},
            status_code=410,
        )
    return FileResponse(
        path,
        media_type="application/zip",
        filename="showcase.zip",
        headers={"X-Processed": str(j.get("processed") or "")},
    )


@router.post("/api/process")
async def api_process(
    request: Request,
    mode: str = Form("workshop"),
    fps: int = Form(12),
    size: int = Form(750),
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_enable: str = Form("1"),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    wm_x: str = Form(""),
    wm_y: str = Form(""),
    auto_contrast: str = Form("0"),
    gif_encoder: str = Form("gifski"),
    all_modes: str = Form("0"),
    files: list[UploadFile] = File(...),
):
    """Process → ZIP download → delete temps."""
    import tempfile
    import time as _sm_time
    _sm_req_t0 = _sm_time.perf_counter()
    print("[API TIMING] START /api/process", flush=True)

    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Limit {FREE_LIMIT} files/day. Enter access code or buy Pro."},
            status_code=403,
        )

    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)

    do_all = str(all_modes).lower() in ("1", "true", "yes", "on")
    modes = ["workshop", "featured", "split"] if do_all else [mode]

    text, wm_font, opacity, corner, scale, color, wm_x_f, wm_y_f = _watermark_options(
        q, wm_text, wm_font, wm_opacity, wm_enable, wm_corner,
        wm_scale, wm_color, wm_x, wm_y,
    )
    do_ac = str(auto_contrast).lower() in ("1", "true", "yes", "on")
    try:
        size_i = int(size)
    except (TypeError, ValueError):
        size_i = 750
    if size_i not in (630, 640, 750, 800):
        size_i = min((630, 640, 750, 800), key=lambda s: abs(s - size_i))

    left = 999 if q["pro"] else q["left"]
    files = files[: max(1, left)]

    job_dir = Path(tempfile.mkdtemp(prefix="sm_job_"))
    zip_buf = io.BytesIO()
    processed = 0
    errors: list[str] = []
    listed: list[dict] = []

    try:
        zf = zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED)
        for uf in files:
            name = uf.filename or "file"
            try:
                raw = await uf.read()
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

                for mode in modes:
                    _sm_mode_t0 = _sm_time.perf_counter()
                    folder = f"{stem}_{mode}"
                    work = job_dir / folder
                    work.mkdir(exist_ok=True)

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
                                img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        elif mode == "featured":
                            parts = proc.process_image_featured(
                                img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        else:
                            parts = proc.process_image_split(
                                img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
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
                        enc = (gif_encoder or "ffmpeg").strip().lower()
                        if enc not in ("ffmpeg", "gifski", "pillow"):
                            enc = "ffmpeg"
                        # pillow → treat as ffmpeg for process pipeline
                        if enc == "pillow":
                            enc = "ffmpeg"
                        if is_video:
                            if not proc.find_ffmpeg():
                                raise RuntimeError("FFmpeg not available")
                            if mode == "workshop":
                                paths = proc.process_video_workshop(
                                    src, work, fps=v_fps, width=size_i,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                                    duration=v_dur, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=enc,
                                )
                            elif mode == "featured":
                                paths = proc.process_video_featured(
                                    src, work, fps=v_fps, duration=v_dur, encoder=enc,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                                    wm_corner=corner, wm_scale=scale, wm_x=wm_x_f, wm_y=wm_y_f,
                                )
                            else:
                                paths = proc.process_video_split(
                                    src, work, fps=v_fps,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                                    duration=v_dur, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=enc,
                                )
                        else:
                            if mode == "workshop":
                                paths = proc.process_gif_workshop(
                                    src, work,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=enc, fps=v_fps,
                                )
                            elif mode == "featured":
                                paths = proc.process_gif_featured(
                                    src, work, fps=v_fps, encoder=enc,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f,
                                )
                            else:
                                paths = proc.process_gif_split(
                                    src, work, fps=v_fps,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=enc,
                                )
                        for pname, pth in paths.items():
                            pth = Path(pth)
                            if not pth.is_file():
                                continue
                            data = pth.read_bytes()
                            zf.writestr(f"{folder}/{pname}", data)
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/{pname}", "size": len(data)})
                            try:
                                pth.unlink(missing_ok=True)
                            except Exception:
                                pass
                        try:
                            src.unlink(missing_ok=True)
                        except Exception:
                            pass

                    print(
                        f"[API TIMING] MODE {mode}: "
                        f"{_sm_time.perf_counter()-_sm_mode_t0:.3f}s",
                        flush=True,
                    )

                processed += 1
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {e}")
                try:
                    shutil.rmtree(work, ignore_errors=True)
                except Exception:
                    pass

        _sm_zip_t0 = _sm_time.perf_counter()
        try:
            zf.close()
        except Exception:
            pass
        print(
            f"[API TIMING] ZIP close: "
            f"{_sm_time.perf_counter()-_sm_zip_t0:.3f}s",
            flush=True,
        )

        if processed == 0:
            detail = "; ".join(errors) if errors else "unknown error"
            return JSONResponse(
                {"ok": False, "msg": f"Failed to process: {detail}", "errors": errors},
                status_code=400,
            )

        try:
            quota_inc(request, processed)
        except Exception as e:
            print("quota_inc:", e)

        zip_bytes = zip_buf.getvalue()
        zip_buf.close()
        headers_out = {
            "Content-Disposition": f'attachment; filename="showcase_{"all" if do_all else mode}.zip"',
            "X-Processed": str(processed),
            "X-Errors": str(len(errors)),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Processed, X-Errors",
        }
        print(
            f"[API TIMING] TOTAL before response: "
            f"{_sm_time.perf_counter()-_sm_req_t0:.3f}s | "
            f"ZIP={len(zip_bytes)/1024/1024:.2f}MB",
            flush=True,
        )
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers=headers_out,
        )
    finally:
        try:
            shutil.rmtree(job_dir, ignore_errors=True)
        except Exception:
            pass


@router.get("/api/download/{job_id}")
def download(job_id: str):
    """Legacy one-shot download — file is deleted after read."""
    job_id = "".join(c for c in job_id if c.isalnum())[:16]
    job_path = JOBS / job_id
    path = job_path / "result.zip"
    if not path.is_file():
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    data = path.read_bytes()
    try:
        shutil.rmtree(job_path, ignore_errors=True)
    except Exception:
        pass
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="showcase_{job_id}.zip"'},
    )


@router.get("/api/job-file/{job_id}/{name}")
def job_file(job_id: str, name: str):
    job_id = "".join(c for c in job_id if c.isalnum())[:16]
    name = Path(name).name
    path = JOBS / job_id / name
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path, filename=name)
