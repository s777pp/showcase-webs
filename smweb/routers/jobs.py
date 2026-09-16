"""Unified job center: history, status, cancellation, retry and event stream."""
from __future__ import annotations

import asyncio
import json
import re
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

import redis_store as rs
from smweb.core import _auth_user, _ip
from smweb.jobs import _job_pool, _worker_mode


router = APIRouter()
_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{20,40}$")


def _owner(request: Request) -> str:
    try:
        user = _auth_user(request)
    except Exception:
        user = None
    return str(user.get("id") or "") if user else _ip(request)


def _owned(request: Request, jid: str) -> dict | None:
    if not _JOB_ID.fullmatch(str(jid or "")):
        return None
    job = rs.job_get(jid)
    return job if job and secrets.compare_digest(str(job.get("user_key") or ""), _owner(request)) else None


def _urls(jid: str, job: dict) -> tuple[str, str]:
    kind = str(job.get("kind") or "process")
    if kind == "process":
        return f"/api/process/status/{jid}", f"/api/process/download/{jid}"
    if kind == "upscale":
        return f"/api/upscale/status/{jid}", f"/api/upscale/download/{jid}"
    if kind == "compose":
        return f"/api/compose/status/{jid}", f"/api/compose/download/{jid}"
    if kind == "seamless_loop":
        return f"/api/loop/status/{jid}", f"/api/loop/download/{jid}"
    return f"/api/jobs/{jid}", ""


def _public(jid: str, job: dict) -> dict:
    status_url, download_url = _urls(jid, job)
    status = str(job.get("status") or "queued")
    kind = str(job.get("kind") or "process")
    # Local encoders can be terminated for real. Modal exposes no cancellation
    # endpoint in the current proxy, so the UI must not promise that GPU billing
    # stops when an upscale result is no longer needed.
    cancellable = {"process", "compose", "seamless_loop", "builder_bg_remove"}
    process_sources = [Path(str(item.get("path") or "")) for item in job.get("files") or []]
    return {
        "id": jid,
        "kind": kind,
        "queue": str(job.get("queue") or rs.queue_for_kind(kind)),
        "status": status,
        "pct": int(job.get("pct") or 0),
        "stage": str(job.get("stage") or ""),
        "error": str(job.get("error") or "")[:500],
        "created": float(job.get("created") or 0),
        "updated": float(job.get("updated") or job.get("created") or 0),
        "cached": bool(job.get("cache_hit")),
        "can_cancel": kind in cancellable and status in {"queued", "running"},
        "can_retry": kind == "process" and status in {"done", "error", "cancelled"} and bool(process_sources) and all(path.is_file() for path in process_sources),
        "status_url": status_url,
        "download_url": download_url if status == "done" else "",
    }


@router.get("/api/jobs")
def list_jobs(request: Request, limit: int = 30):
    jobs = [_public(jid, job) for jid, job in rs.job_list_user(_owner(request), limit)]
    return {"ok": True, "jobs": jobs, "queues": rs.queue_depths()}


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    job = _owned(request, job_id)
    return {"ok": True, "job": _public(job_id, job)} if job else JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, request: Request):
    if not _owned(request, job_id):
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    job = rs.job_cancel(job_id)
    return {"ok": True, "job": _public(job_id, job or {})}


def _dispatch_embedded(jid: str, payload: dict) -> None:
    kind = payload.get("kind")
    if kind == "compose":
        from smweb.compose_jobs import run
    elif kind == "seamless_loop":
        from smweb.loop_jobs import run
    elif kind == "builder_bg_remove":
        from smweb.background_remove_jobs import run
    else:
        from smweb.jobs import _run_process_job_from_payload as run
    _job_pool.submit(run, jid, payload)


@router.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str, request: Request):
    old = _owned(request, job_id)
    if not old:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    kind = str(old.get("kind") or "process")
    # Modal inputs are deliberately deleted after a run, while profile jobs can
    # have external side effects. Their own screens remain the retry interface.
    if kind != "process":
        return JSONResponse({"ok": False, "msg": "Upload the source again for this job"}, status_code=409)
    paths = [Path(str(item.get("path") or "")) for item in old.get("files") or []]
    paths += [Path(str(old.get(key) or "")) for key in ("source_path", "background_path", "character_path") if old.get(key)]
    if not paths or any(not path.is_file() for path in paths):
        return JSONResponse({"ok": False, "msg": "Source files have expired"}, status_code=410)
    jid = secrets.token_hex(12 if kind == "process" else 16)
    payload = {key: value for key, value in old.items() if key not in {
        "status", "pct", "stage", "error", "updated", "result_path", "result_key", "zip_path",
        "processed", "errors", "listed", "readiness", "cancel_requested", "cache_hit",
    }}
    payload.update({"status": "queued", "pct": 1, "stage": "queued", "created": time.time(), "retry_of": job_id})
    external = _worker_mode() == "external" and rs.redis_ok() and rs.worker_alive()
    rs.job_create(jid, payload, enqueue=external)
    if not external:
        _dispatch_embedded(jid, payload)
    return JSONResponse({"ok": True, "job_id": jid}, status_code=202)


@router.get("/api/jobs/events")
async def events(request: Request):
    owner = _owner(request)

    async def stream():
        previous = ""
        for _ in range(240):
            if await request.is_disconnected():
                break
            payload = [_public(jid, job) for jid, job in rs.job_list_user(owner, 30)]
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if encoded != previous:
                yield f"event: jobs\ndata: {encoded}\n\n"
                previous = encoded
            else:
                yield ": keep-alive\n\n"
            await asyncio.sleep(1.5)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "private, no-cache", "X-Accel-Buffering": "no",
    })
