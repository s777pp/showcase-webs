"""Authenticated API for the experimental Steam DNA visualizer."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import auth_db
import redis_store as rs
from smweb.core import _auth_user
from smweb.steam_dna import build_profile_dna


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
    return JSONResponse(
        {"ok": True, "dna": result},
        headers={"Cache-Control": "no-store"},
    )
