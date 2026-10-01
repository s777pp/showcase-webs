"""Private API for the owner's Telegram bot (maintenance, keys, support replies).

Every call must carry ``X-Bot-Admin-Secret`` equal to BOT_ADMIN_SECRET.  When
the variable is empty the whole API answers 404, so it is off by default.
"""
from __future__ import annotations

import html
import os
import secrets
import shutil
import time

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

import redis_store as rs
from smweb import admin_content, maintenance
from smweb.core import JOBS, LOGGER

router = APIRouter(prefix="/api/bot-admin")


def _denied(request: Request) -> JSONResponse | None:
    secret = (os.environ.get("BOT_ADMIN_SECRET") or "").strip()
    if not secret:
        return JSONResponse({"ok": False}, status_code=404)
    given = (request.headers.get("x-bot-admin-secret") or "").strip()
    if not given or not secrets.compare_digest(given, secret):
        return JSONResponse({"ok": False, "msg": "forbidden"}, status_code=403)
    return None


@router.get("/status")
def status(request: Request):
    if (denied := _denied(request)):
        return denied
    usage = shutil.disk_usage(str(JOBS))
    return {"ok": True, "maintenance": maintenance.get_state(), "queues": rs.queue_depths(),
            "worker_alive": bool(rs.worker_alive()), "disk_free_gb": round(usage.free / 1024 ** 3, 1),
            "open_tickets": len(admin_content.tickets(status="open", limit=100))}


@router.post("/maintenance")
def set_maintenance(request: Request, body: dict = Body(...)):
    if (denied := _denied(request)):
        return denied
    enabled = bool(body.get("enabled"))
    hours = float(body.get("hours") or 0)
    ends_at = time.time() + hours * 3600 if enabled and hours > 0 else None
    state = maintenance.set_state(enabled, str(body.get("message") or ""), ends_at=ends_at)
    LOGGER.info("maintenance set from bot: %s", state.get("enabled"))
    return {"ok": True, "maintenance": state}


@router.post("/codes")
def generate(request: Request, body: dict = Body(...)):
    if (denied := _denied(request)):
        return denied
    from smweb import admin_control
    count = max(1, min(100, int(body.get("count") or 1)))
    result = admin_control.generate_codes(
        count, int(body.get("days") or 0), label=str(body.get("label") or "Pro"),
        campaign=str(body.get("campaign") or "telegram-bot"), duration_hours=float(body.get("hours") or 0),
    )
    return {"ok": True, "codes": result.get("codes") or []}


@router.get("/tickets")
def open_tickets(request: Request):
    if (denied := _denied(request)):
        return denied
    items = admin_content.tickets(status="open", limit=10)
    return {"ok": True, "items": [{**{k: t.get(k) for k in ("id", "email", "message", "page", "status", "created_at")},
                                   "telegram": (t.get("context") or {}).get("telegram") or ""} for t in items]}


@router.post("/tickets/{ticket_id}/reply")
def reply_ticket(ticket_id: str, request: Request, body: dict = Body(...)):
    if (denied := _denied(request)):
        return denied
    text = str(body.get("text") or "").strip()
    if not 2 <= len(text) <= 2000:
        return JSONResponse({"ok": False, "msg": "Reply must be 2-2000 characters"}, status_code=400)
    # Same path as the admin console: thread on the site, bell notification, e-mail.
    from smweb import support_threads
    try:
        result = support_threads.reply_from_support(ticket_id, text, "resolved")
    except LookupError:
        return JSONResponse({"ok": False, "msg": "Ticket not found"}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)
    return {"ok": True, "emailed": result["emailed"], "has_email": result["has_email"], "notified": result["notified"]}


@router.post("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: str, request: Request):
    if (denied := _denied(request)):
        return denied
    try:
        admin_content.update_ticket(ticket_id, "closed")
    except LookupError:
        return JSONResponse({"ok": False, "msg": "Ticket not found"}, status_code=404)
    return {"ok": True}
