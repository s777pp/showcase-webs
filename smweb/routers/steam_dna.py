"""Authenticated, queued API for live public-profile Steam DNA analysis."""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import auth_db
import redis_store as rs
from smweb.core import _auth_user
from smweb.locales import normalize_language
from steam_browser_import import _public_profile_url


router = APIRouter(prefix="/api/steam-dna", tags=["steam-dna"])
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="steam-dna")
_MODES = {"workshop", "featured", "split"}


def _bounded_env(name: str, default: int, maximum: int) -> int:
    try:
        return max(1, min(maximum, int(os.environ.get(name, str(default)))))
    except ValueError:
        return default


@router.post("/analyze")
async def analyze(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "code": "login", "msg": "Login required"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        url = _public_profile_url(str(body.get("url") or ""))
    except Exception:
        return JSONResponse(
            {"ok": False, "code": "url", "msg": "Enter a public Steam profile URL"}, status_code=400
        )

    mode = str(body.get("mode") or "workshop").strip().lower()
    if mode not in _MODES:
        mode = "workshop"
    language = normalize_language(str(body.get("language") or "")) or "en"
    cache_key = hashlib.sha256(f"{url}|{mode}|{language}|dna-v2".encode()).hexdigest()[:32]
    cached = rs.steam_dna_cache_get(cache_key)
    if cached:
        return JSONResponse({"ok": True, "cached": True, "dna": cached}, headers={"Cache-Control": "no-store"})

    uid = int(user["id"])
    burst_allowed, _ = rs.rate_limit(f"steam-dna-start:{uid}", 3, 300)
    if not burst_allowed:
        return JSONResponse({"ok": False, "code": "rate_limit", "msg": "Try again in a few minutes"}, status_code=429)
    source_key = cache_key[:24]
    user_key = f"steam-dna:{uid}"
    existing = rs.job_find_active(user_key, "steam_dna", source_key)
    if existing:
        return {"ok": True, "queued": True, "job_id": existing[0]}
    pro = auth_db.effective_pro(user)
    daily_limit = _bounded_env("STEAM_DNA_PRO_DAILY", 20, 100) if pro else _bounded_env("STEAM_DNA_FREE_DAILY", 1, 20)
    user_allowed, remaining = rs.rate_limit(f"steam-dna-live:user:{uid}", daily_limit, 86400, fail_closed=True)
    global_allowed, _ = rs.rate_limit(
        "steam-dna-live:global", _bounded_env("STEAM_DNA_GLOBAL_DAILY", 150, 5000), 86400, fail_closed=True
    )
    if not user_allowed or not global_allowed:
        return JSONResponse(
            {"ok": False, "code": "limit", "msg": "Daily Steam DNA limit reached", "remaining": remaining},
            status_code=429,
        )

    jid = secrets.token_hex(12)
    external = (
        (os.environ.get("WORKER_MODE") or "embedded").strip().lower() == "external"
        and rs.redis_ok() and rs.worker_alive()
    )
    payload = {
        "kind": "steam_dna", "status": "queued", "pct": 1, "stage": "queued",
        "user_key": user_key, "user_id": uid, "source_key": source_key, "cache_key": cache_key,
        "url": url, "mode": mode, "language": language, "is_pro": bool(pro), "created": time.time(),
    }
    rs.job_create(jid, payload, enqueue=external)
    if not external:
        from smweb.steam_dna_jobs import run
        _pool.submit(run, jid, payload)
    return {"ok": True, "queued": True, "job_id": jid}


@router.get("/status/{job_id}")
def status(job_id: str, request: Request):
    user = _auth_user(request)
    job = rs.job_get(job_id) if re.fullmatch(r"[a-f0-9]{24}", job_id or "") else None
    if not user or not job or job.get("kind") != "steam_dna" or int(job.get("user_id") or 0) != int(user["id"]):
        return JSONResponse({"ok": False, "code": "not_found", "msg": "Analysis not found"}, status_code=404)
    response = {
        "ok": True, "status": job.get("status"), "pct": int(job.get("pct") or 0), "stage": job.get("stage"),
    }
    if job.get("status") == "done":
        response["dna"] = job.get("result") or {}
    elif job.get("status") == "error":
        response.update({
            "error": "Profile analysis temporarily unavailable", "code": job.get("code") or "profile_unavailable",
            "retry": bool(job.get("retry")),
        })
    return JSONResponse(response, headers={"Cache-Control": "no-store"})
