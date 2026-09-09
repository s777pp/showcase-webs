"""Async Profile Doctor and Smart Design APIs."""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import redis_store as rs
from smweb.core import quota_state
from smweb.profile_insights import configured
from smweb.locales import normalize_language
from steam_browser_import import _public_profile_url


router = APIRouter()
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="profile-insight")


@router.post("/api/profile-insights/start")
async def start(request: Request):
    quota = quota_state(request)
    if not quota.get("email") or not quota.get("user_id"):
        return JSONResponse({"ok": False, "msg": "Login required", "code": "auth"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    kind = str(body.get("kind") or "doctor").strip().lower()
    if kind not in {"doctor", "design"}:
        return JSONResponse({"ok": False, "msg": "Unknown analysis type"}, status_code=400)
    if kind == "design" and not quota.get("pro"):
        return JSONResponse({"ok": False, "msg": "Smart Design is available with Pro", "code": "pro"}, status_code=403)
    if not configured() and kind == "design":
        return JSONResponse({"ok": False, "msg": "AI design service is not configured", "code": "ai_config"}, status_code=503)
    try:
        url = _public_profile_url(str(body.get("url") or ""))
    except Exception:
        return JSONResponse({"ok": False, "msg": "Enter a public Steam profile URL", "code": "url"}, status_code=400)

    uid = int(quota["user_id"])
    if quota.get("pro"):
        allowed, _ = rs.rate_limit(f"profile-insight-pro:{uid}", int(os.environ.get("PROFILE_AI_PRO_DAILY", "30")), 86400)
    else:
        recent_doctor = any(item.get("kind") == "doctor" for item in rs.profile_insight_history(uid))
        if recent_doctor:
            return JSONResponse({"ok": False, "msg": "Free Profile Doctor refreshes once a week", "code": "limit"}, status_code=429)
        allowed, _ = rs.rate_limit(f"profile-doctor-start:{uid}", 1, 300)
    if not allowed:
        message = "An analysis was just started; wait a few minutes before retrying" if not quota.get("pro") else "Daily analysis safety limit reached"
        return JSONResponse({"ok": False, "msg": message, "code": "limit"}, status_code=429)

    source_key = hashlib.sha256(f"{kind}:{url}".encode()).hexdigest()[:24]
    user_key = f"insight:{uid}"
    existing = rs.job_find_active(user_key, "profile_insight", source_key)
    if existing:
        return {"ok": True, "queued": True, "job_id": existing[0]}
    jid = secrets.token_hex(12)
    external = ((os.environ.get("WORKER_MODE") or "embedded").strip().lower() == "external" and rs.redis_ok() and rs.worker_alive())
    payload = {
        "kind": "profile_insight", "insight_kind": kind, "status": "queued", "pct": 1,
        "stage": "queued", "user_key": user_key, "user_id": uid, "source_key": source_key,
        "url": url, "language": normalize_language(str(body.get("language") or "")) or "en",
        "style": str(body.get("style") or "auto")[:24], "is_pro": bool(quota.get("pro")), "created": time.time(),
    }
    rs.job_create(jid, payload, enqueue=external)
    if not external:
        from smweb.profile_insight_jobs import run
        _pool.submit(run, jid, payload)
    return {"ok": True, "queued": True, "job_id": jid}


@router.get("/api/profile-insights/status/{job_id}")
def status(job_id: str, request: Request):
    quota = quota_state(request)
    job = rs.job_get(job_id) if re.fullmatch(r"[a-f0-9]{24}", job_id or "") else None
    if not quota.get("user_id") or not job or job.get("kind") != "profile_insight" or int(job.get("user_id") or 0) != int(quota["user_id"]):
        return JSONResponse({"ok": False, "msg": "Analysis not found"}, status_code=404)
    response = {"ok": True, "status": job.get("status"), "pct": int(job.get("pct") or 0), "stage": job.get("stage")}
    if job.get("status") == "done":
        response["result"] = job.get("result") or {}
    elif job.get("status") == "error":
        response.update({"error": "Analysis temporarily unavailable", "code": job.get("error_code") or "analysis"})
    return response


@router.get("/api/profile-insights/history")
def history(request: Request):
    quota = quota_state(request)
    if not quota.get("user_id"):
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    return {"ok": True, "retention_days": 7, "items": rs.profile_insight_history(int(quota["user_id"]))}
