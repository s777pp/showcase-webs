"""Authenticated API for the experimental Steam DNA visualizer."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

import auth_db
import redis_store as rs
from smweb.core import _auth_user
from smweb.steam_dna import build_profile_dna
from smweb import steam_dna_ai
from smweb.locales import normalize_language


router = APIRouter(prefix="/api/steam-dna", tags=["steam-dna"])


@router.post("/analyze")
async def analyze(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "code": "login", "msg": "Login required"}, status_code=401)
    allowed, remaining = rs.rate_limit(f"steam-dna:{int(user['id'])}", 12, 300)
    if not allowed:
        return JSONResponse(
            {"ok": False, "code": "rate_limit", "msg": "Try again in a few minutes", "remaining": remaining},
            status_code=429,
        )
    try:
        body = await request.json()
    except Exception:
        body = {}
    snapshot = auth_db.get_steam_profile_snapshot(int(user["id"]))
    if not snapshot:
        return JSONResponse(
            {"ok": False, "code": "steam_snapshot", "msg": "Import your Steam profile first"},
            status_code=409,
        )
    result = build_profile_dna(snapshot, user_id=int(user["id"]), mode=str(body.get("mode") or "workshop"))
    language = normalize_language(str(body.get("language") or "")) or "en"
    ai_meta = {"used": False, "available": steam_dna_ai.configured()}
    if ai_meta["available"]:
        limits = steam_dna_ai.settings()
        daily = limits["pro_daily"] if auth_db.effective_pro(user) else limits["free_daily"]
        user_allowed, user_remaining = rs.rate_limit(
            f"steam-dna-ai:user:{int(user['id'])}", daily, 86400, fail_closed=True
        )
        global_allowed, _ = rs.rate_limit(
            "steam-dna-ai:global", limits["global_daily"], 86400, fail_closed=True
        )
        ai_meta["remaining"] = user_remaining
        if user_allowed and global_allowed:
            try:
                result["interpretation"] = await run_in_threadpool(
                    steam_dna_ai.enrich_profile_dna, result, snapshot, language
                )
                ai_meta["used"] = True
            except steam_dna_ai.SteamDnaAiUnavailable:
                ai_meta["reason"] = "unavailable"
        else:
            ai_meta["reason"] = "limit"
    result["ai"] = ai_meta
    return JSONResponse(
        {"ok": True, "dna": result},
        headers={"Cache-Control": "no-store"},
    )
