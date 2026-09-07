"""Public assistant routes. No secrets or private project docs are sent to clients."""
from __future__ import annotations
import hashlib
import json
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
import redis_store as rs
from smweb.core import _ip
from smweb import support_chat as chat

router = APIRouter()

def reply(body, status=200):
    return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})

@router.get("/api/support/info")
def info():
    return reply({"ok": True, "available": chat.configured(),
                  "daily_limit": chat.settings()["visitor_daily"], "topics": chat.KNOWLEDGE})

@router.post("/api/support/chat")
async def support(request: Request):
    # Protect anonymous paid calls as well as cookie sessions.
    origin = request.headers.get("origin", "").rstrip("/")
    allowed = {str(request.base_url).rstrip("/"), os.environ.get("APP_URL", "").rstrip("/")}
    if not origin or origin not in allowed or request.headers.get("sec-fetch-site") == "cross-site":
        return reply({"ok": False, "code": "origin"}, 403)
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        return reply({"ok": False, "code": "invalid"}, 415)
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 16000:
            return reply({"ok": False, "code": "too_large"}, 413)
    try:
        message, history, language = chat.validate_body(json.loads(raw))
    except (ValueError, TypeError):
        return reply({"ok": False, "code": "invalid"}, 400)
    if not chat.configured():
        return reply({"ok": False, "code": "not_configured"}, 503)
    # Production cost limits must remain shared across Uvicorn processes.
    if rs.configured() and not rs.redis_ok():
        return reply({"ok": False, "code": "unavailable"}, 503)
    identity = hashlib.sha256(_ip(request).encode()).hexdigest()[:32]
    cfg = chat.settings()
    for key, limit, window in (
        ("minute:" + identity, 4, 60),
        ("daily:" + identity, cfg["visitor_daily"], 86400),
        ("global", cfg["global_daily"], 86400),
    ):
        allowed_call, _ = rs.rate_limit("support:" + key, limit, window, fail_closed=True)
        if not allowed_call:
            return reply({"ok": False, "code": "limit"}, 429)
    try:
        text = await run_in_threadpool(chat.answer, message, history, language)
    except chat.SupportRateLimited:
        return reply({"ok": False, "code": "limit"}, 429)
    except chat.SupportUnavailable:
        return reply({"ok": False, "code": "unavailable"}, 503)
    return reply({"ok": True, "answer": text})
