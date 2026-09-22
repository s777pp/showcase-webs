"""Unified job center: history, status, cancellation, retry and event stream."""
from __future__ import annotations

import asyncio
import json
import re
import secrets
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

import redis_store as rs
from smweb.core import JOBS, _auth_user, _ip, max_jobs_for_user, quota_state, quota_inc
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
    if not job:
        return None
    key = str(job.get("user_key") or "")
    if secrets.compare_digest(key, _owner(request)):
        return job
    expected = _scoped_owners(request).get(key)
    return job if expected and job.get("kind") == expected else None


def _scoped_owners(request: Request) -> dict[str, str]:
    try:
        user = _auth_user(request)
    except Exception:
        user = None
    if not user:
        return {}
    uid = int(user["id"])
    return {f"{prefix}:{uid}": kind for prefix, kind in (
        ("builder-bg", "builder_bg_remove"), ("steam", "steam_profile_import"),
        ("insight", "profile_insight"), ("steam-dna", "steam_dna"),
    )}


def _history(owner: str, scoped: dict[str, str], limit: int) -> list[dict]:
    limit = max(1, min(50, limit))
    rows = dict(rs.job_list_user(owner, limit))
    for key, kind in scoped.items():
        rows.update((jid, job) for jid, job in rs.job_list_user(key, limit)
                    if job.get("kind") == kind)
    ordered = sorted(rows.items(), key=lambda item: float(item[1].get("created") or 0), reverse=True)
    return [_public(jid, job) for jid, job in ordered[:limit]]


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
    cancellable = {"process", "compose", "seamless_loop"}
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
    jobs = _history(_owner(request), _scoped_owners(request), limit)
    return {"ok": True, "jobs": jobs, "queues": rs.queue_depths()}


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, request: Request):
    owned = _owned(request, job_id)
    if not owned:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    if not _public(job_id, owned)["can_cancel"]:
        return JSONResponse({"ok": False, "msg": "This job cannot be cancelled"}, status_code=409)
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
    if old.get("status") not in {"done", "error", "cancelled"}:
        return JSONResponse({"ok": False, "msg": "Wait for the current job to finish"}, status_code=409)
    paths = [Path(str(item.get("path") or "")) for item in old.get("files") or []]
    paths += [Path(str(old.get(key) or "")) for key in ("source_path", "background_path", "character_path") if old.get(key)]
    if not paths or any(not path.is_file() for path in paths):
        return JSONResponse({"ok": False, "msg": "Source files have expired"}, status_code=410)
    # Retry is a new processing request, not a way around current account limits.
    quota = quota_state(request)
    file_count = len(old.get("files") or [])
    if not quota.get("pro") and int(quota.get("left") or 0) < file_count:
        return JSONResponse({"ok": False, "msg": "Daily processing limit reached"}, status_code=403)
    if rs.job_count_user(_owner(request)) >= max_jobs_for_user(quota.get("user_id")):
        return JSONResponse({"ok": False, "msg": "Too many active jobs. Wait for current processing to finish."}, status_code=429)
    allowed, _ = rs.rate_limit(f"job-retry:{_owner(request)}", 1, 5, fail_closed=True)
    if not allowed:
        return JSONResponse({"ok": False, "msg": "Please wait before retrying again"}, status_code=429)
    jid = secrets.token_hex(12 if kind == "process" else 16)
    payload = {key: value for key, value in old.items() if key not in {
        "status", "pct", "stage", "error", "updated", "result_path", "result_key", "zip_path", "job_dir",
        "processed", "errors", "listed", "readiness", "cancel_requested", "cache_hit",
    }}
    payload.update({"status": "queued", "pct": 1, "stage": "queued", "created": time.time(), "retry_of": job_id})
    payload["opts"] = dict(old.get("opts") or {})
    payload["opts"]["steam_check"] = bool(quota.get("email"))
    if not quota.get("pro"):
        from smweb.routers.process import _watermark_options
        keys = ("text", "wm_font", "opacity", "corner", "scale", "color", "wm_x", "wm_y")
        payload["opts"].update(zip(keys, _watermark_options(quota, "", "", 0, "0", "bl", 1.0, "#ffffff", "", "")))
    # The previous job may expire while this one waits in the queue. Give the
    # retry its own inputs so ordinary cleanup cannot break accepted work.
    retry_dir = JOBS / jid
    retry_dir.mkdir(parents=True, exist_ok=False)
    try:
        files = []
        for index, item in enumerate(old.get("files") or []):
            source = Path(item["path"])
            target = retry_dir / f"input_{index}{source.suffix}"
            shutil.copyfile(source, target)
            files.append({**item, "path": str(target)})
        payload["files"] = files
    except OSError:
        shutil.rmtree(retry_dir, ignore_errors=True)
        return JSONResponse({"ok": False, "msg": "Source files are unavailable. Upload them again."}, status_code=410)
    external = _worker_mode() == "external" and rs.redis_ok() and rs.worker_alive()
    rs.job_create(jid, payload, enqueue=external)
    if not quota.get("pro"):
        quota_inc(request, file_count)
    if not external:
        _dispatch_embedded(jid, payload)
    return JSONResponse({"ok": True, "job_id": jid}, status_code=202)


@router.get("/api/jobs/events")
async def events(request: Request):
    owner = _owner(request)
    scoped = _scoped_owners(request)

    async def stream():
        previous = ""
        for iteration in range(240):
            if await request.is_disconnected():
                break
            # A stream may stay open for six minutes. Re-check the session so
            # logout, expiry or switching accounts cannot keep receiving the
            # previous account's job history through an already-open socket.
            if iteration and iteration % 20 == 0:
                current_owner = await run_in_threadpool(_owner, request)
                current_scoped = await run_in_threadpool(_scoped_owners, request)
                if current_owner != owner or current_scoped != scoped:
                    break
            payload = await run_in_threadpool(_history, owner, scoped, 30)
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


# Literal GET routes must precede this catch-all, including the event stream.
@router.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    job = _owned(request, job_id)
    return {"ok": True, "job": _public(job_id, job)} if job else JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
