"""GIF Optimizer API: start a job, poll it, get the result or the original back for the comparison."""
from __future__ import annotations

import hashlib
import re
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response

import processor as proc
import redis_store as rs
from smweb import free_limits, gif_optimizer, job_diagnostics, object_store
from smweb.core import DATA, MAX_UPLOAD_MB, LOGGER, _auth_user, max_jobs_for_user, owner_key, quota_inc, quota_state
from smweb.jobs import _job_pool, _worker_mode

router = APIRouter()
KIND = "gif_optimizer"


def _stem(name: str) -> str:
    return re.sub(r"[^\w.-]+", "_", Path(name or "").stem)[:60] or "gif"


@router.post("/api/gif-optimizer/start")
async def start(request: Request, file: UploadFile = File(...), mode: str = Form("manual"),
                colors: int = Form(256), lossy: int = Form(30)):
    if mode not in ("manual", "auto"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)
    q = quota_state(request)
    # While the tool is in beta it is Pro-only (smweb/free_limits.py, BETA_FEATURES).
    if not q["pro"] and free_limits.is_beta("gifopt"):
        return free_limits.refusal(request, "beta", "gifopt")
    # Out of beta it shares the daily allowance of Process: one optimisation = one file.
    if not q["pro"] and q["left"] < 1:
        return free_limits.refusal(request, "daily", "files", n=q.get("limit") or 0)
    user = _auth_user(request)
    owner = owner_key(request, user)
    if owner and rs.job_count_user(owner) >= max_jobs_for_user(int(user["id"]) if user else None):
        return JSONResponse({"ok": False, "msg": "Too many active jobs"}, status_code=429)
    raw = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if not raw or len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": f"File missing or larger than {MAX_UPLOAD_MB} MB"}, status_code=400)
    if raw[:6] not in (b"GIF87a", b"GIF89a"):
        return JSONResponse({"ok": False, "msg": "GIF only — convert the file first", "code": "not_gif"}, status_code=400)
    raw = proc.restore_gif_trailer(raw)  # a Steam-ready (HEX 21) GIF used as the source
    colors = max(2, min(256, int(colors)))
    lossy = max(0, min(100, int(lossy)))
    settings = f"auto:{proc.MAX_STEAM_MB}" if mode == "auto" else f"manual:{colors}:{lossy}"
    cache_key = hashlib.sha256(f"gifopt:1:{owner}:{settings}:".encode() + raw).hexdigest()
    cached_id = rs.job_cache_get(cache_key)
    cached = rs.job_get(cached_id) if cached_id else None
    if cached and cached.get("status") == "done" and (cached.get("result_key") or Path(str(cached.get("result_path") or "")).is_file()) \
            and Path(str(cached.get("source_path") or "")).is_file():
        return {"ok": True, "job_id": cached_id, "cached": True}
    jid = secrets.token_hex(16)
    root = Path(DATA) / "jobs" / jid
    root.mkdir(parents=True, exist_ok=False)
    source = root / "source.gif"
    source.write_bytes(raw)
    try:
        meta = gif_optimizer.info(source)
    except ValueError as exc:
        import shutil
        shutil.rmtree(root, ignore_errors=True)
        return JSONResponse({"ok": False, "msg": str(exc), "code": "bad_gif"}, status_code=400)
    external = _worker_mode() == "external" and rs.redis_ok() and rs.worker_alive()
    payload = {"kind": KIND, "queue": "media", "job_dir": str(root), "source_path": str(source),
               "user_key": owner, "status": "queued", "pct": 2, "stage": "queued", "created": time.time(),
               "mode": mode, "colors": colors, "lossy": lossy, "stem": _stem(file.filename),
               "size_before": len(raw), "in_width": meta["width"], "in_height": meta["height"],
               "in_frames": meta["frames"], "cache_key": cache_key}
    rs.job_create(jid, payload, enqueue=external)
    try:
        quota_inc(request, 1)
    except Exception:
        pass
    if not external:
        from smweb.gif_optimizer_jobs import run
        _job_pool.submit(run, jid, dict(payload))
    return JSONResponse({"ok": True, "job_id": jid}, status_code=202)


def _job(request: Request, job_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id or ""):
        return None
    job = rs.job_get(job_id)
    owner = owner_key(request, _auth_user(request))
    return job if job and job.get("kind") == KIND and owner and job.get("user_key") == owner else None


@router.get("/api/gif-optimizer/status/{job_id}")
def status(request: Request, job_id: str):
    job = _job(request, job_id)
    if not job:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    done = job.get("status") == "done"
    base = f"/api/gif-optimizer/file/{job_id}"
    return {"ok": True, "status": job.get("status"), "pct": job.get("pct", 0), "stage": job.get("stage", ""),
            "error": job.get("error", ""), "mode": job.get("mode"),
            "size_before": job.get("size_before"), "size_after": job.get("size_after") if done else None,
            "width": job.get("in_width"), "height": job.get("in_height"), "frames": job.get("in_frames"),
            "already_fits": bool(job.get("already_fits")),
            "download_url": base + "/result" if done else "", "result_url": base + "/result?inline=1" if done else "",
            "source_url": base + "/source",
            **(job_diagnostics.public_error(job.get("error")) if job.get("status") == "error" else {})}


@router.get("/api/gif-optimizer/file/{job_id}/{which}")
def get_file(request: Request, job_id: str, which: str, inline: bool = False):
    job = _job(request, job_id)
    if not job or which not in ("result", "source"):
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    headers = {"Cache-Control": "private, no-store"}
    try:
        if which == "source":
            return Response(Path(str(job["source_path"])).read_bytes(), media_type="image/gif", headers=headers)
        if job.get("status") != "done":
            return JSONResponse({"ok": False, "msg": "Result is not ready"}, status_code=404)
        name = str(job.get("filename") or "optimized.gif")
        if job.get("result_key"):
            url = object_store.presigned_get_url(str(job["result_key"]), expires=600,
                                                 download_name=None if inline else name, media_type="image/gif")
            return RedirectResponse(url, status_code=302, headers=headers)
        disposition = "inline" if inline else "attachment"
        return Response(Path(str(job["result_path"])).read_bytes(), media_type="image/gif",
                        headers={**headers, "Content-Disposition": f'{disposition}; filename="{name}"'})
    except Exception:
        LOGGER.exception("gif optimizer file unavailable jid=%s", job_id)
        return JSONResponse({"ok": False, "msg": "File is unavailable"}, status_code=404)
