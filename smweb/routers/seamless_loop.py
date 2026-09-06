"""Authenticated asynchronous seamless-loop API."""
from __future__ import annotations

import os
import re
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response

import auth_db
import redis_store as rs
from smweb import object_store
from smweb.core import DATA, MAX_UPLOAD_MB, _auth_user, LOGGER
from smweb.jobs import _job_pool, _worker_mode

router = APIRouter()


def _media(raw: bytes) -> tuple[str, str] | None:
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "gif"
    if len(raw) >= 12 and raw[4:8] == b"ftyp":
        return ".mp4", "video"
    if raw[:4] == b"\x1aE\xdf\xa3":
        return ".webm", "video"
    if raw[:4] == b"RIFF" and raw[8:12] == b"AVI ":
        return ".avi", "video"
    return None


def _owner(request: Request) -> tuple[dict | None, str]:
    user = _auth_user(request)
    return user, str(int(user["id"])) if user else ""


@router.post("/api/loop/start")
async def start(request: Request, file: UploadFile = File(...), mode: str = Form("pingpong"),
                output_format: str = Form("gif"), fps: int = Form(12),
                start: float = Form(0), duration: float = Form(4)):
    user, owner = _owner(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in required", "code": "auth"}, status_code=401)
    if not auth_db.effective_pro(user):
        return JSONResponse({"ok": False, "msg": "Seamless Loop is available for Pro subscribers", "code": "pro"}, status_code=403)
    if rs.job_count_user(owner) >= int(os.environ.get("MAX_JOBS_PER_USER", "2")):
        return JSONResponse({"ok": False, "msg": "Too many active jobs"}, status_code=429)
    allowed, _ = rs.rate_limit(f"loop-start:{owner}", 12, 3600)
    if not allowed:
        return JSONResponse({"ok": False, "msg": "Too many loop requests. Try again later."}, status_code=429)
    raw = await file.read()
    if not raw or len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": f"File missing or larger than {MAX_UPLOAD_MB} MB"}, status_code=400)
    media = _media(raw)
    if not media:
        return JSONResponse({"ok": False, "msg": "Animated GIF, MP4, WebM or AVI required"}, status_code=400)
    if output_format not in {"gif", "mp4"}:
        return JSONResponse({"ok": False, "msg": "Unsupported loop settings"}, status_code=400)
    # Keep the public Steam tool predictable, including for stale cached clients.
    mode = "pingpong"
    jid = secrets.token_hex(16)
    root = Path(DATA) / "jobs" / jid
    root.mkdir(parents=True, exist_ok=False)
    source = root / f"source{media[0]}"
    source.write_bytes(raw)
    external = _worker_mode() == "external" and rs.redis_ok() and rs.worker_alive()
    payload = {"kind": "seamless_loop", "job_dir": str(root), "source_path": str(source),
               "user_key": owner, "status": "queued", "pct": 2, "stage": "queued",
               "mode": mode, "output_format": output_format, "fps": max(8, min(24, fps)),
               "start": max(0, min(29.5, start)), "duration": max(0.5, min(8, duration)),
               "created": time.time()}
    rs.job_create(jid, payload, enqueue=external)
    if not external:
        from smweb.loop_jobs import run
        _job_pool.submit(run, jid, dict(payload))
    return JSONResponse({"ok": True, "job_id": jid}, status_code=202)


def _job(request: Request, job_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id or ""):
        return None
    user, owner = _owner(request)
    job = rs.job_get(job_id)
    return job if user and job and job.get("kind") == "seamless_loop" and job.get("user_key") == owner else None


@router.get("/api/loop/status/{job_id}")
def status(request: Request, job_id: str):
    job = _job(request, job_id)
    if not job:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    return {"ok": True, "status": job.get("status"), "pct": job.get("pct", 0),
            "stage": job.get("stage", ""), "error": job.get("error", ""),
            "download_url": f"/api/loop/download/{job_id}" if job.get("status") == "done" else "",
            "preview_url": f"/api/loop/download/{job_id}?inline=1" if job.get("status") == "done" else "",
            "media_type": job.get("media_type", ""), "duration": job.get("output_duration")}


@router.get("/api/loop/download/{job_id}")
def download(request: Request, job_id: str, inline: bool = False):
    job = _job(request, job_id)
    if not job or job.get("status") != "done":
        return JSONResponse({"ok": False, "msg": "Result is not ready"}, status_code=404)
    try:
        if job.get("result_key"):
            url = object_store.presigned_get_url(str(job["result_key"]), expires=600,
                download_name=None if inline else str(job.get("filename") or "seamless-loop"),
                media_type=str(job.get("media_type") or "application/octet-stream"))
            return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, no-store"})
        data = Path(str(job["result_path"])).read_bytes()
        disposition = "inline" if inline else "attachment"
        return Response(data, media_type=job.get("media_type"), headers={"Content-Disposition": f'{disposition}; filename="{job.get("filename")}"', "Cache-Control": "private, no-store"})
    except Exception:
        LOGGER.exception("loop result unavailable jid=%s", job_id)
        return JSONResponse({"ok": False, "msg": "Result is unavailable"}, status_code=404)
