"""Private API for the owner's Telegram bot (maintenance, keys, support replies, Pro purchases, cutting files).

Every call must carry ``X-Bot-Admin-Secret`` equal to BOT_ADMIN_SECRET.  When
the variable is empty the whole API answers 404, so it is off by default.
"""
from __future__ import annotations

import html
import os
import secrets
import shutil
import time

from fastapi import APIRouter, Body, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

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


# ---------------------------------------------------------------- Pro bought in the bot (smweb/telegram_billing.py)
@router.get("/pro/account")
def pro_account(request: Request, tg_id: str = ""):
    """Which site account receives purchases of this Telegram user, and its Pro state."""
    if (denied := _denied(request)):
        return denied
    from smweb import telegram_billing
    return {"ok": True, **telegram_billing.account_info(tg_id)}


@router.get("/pro/order")
def pro_order(request: Request, token: str = ""):
    """A purchase started on the site (t.me/<bot>?start=buy_<token>): the chosen plan and the account's name."""
    if (denied := _denied(request)):
        return denied
    from smweb import telegram_billing
    info = telegram_billing.order_info(token)
    if not info:
        return JSONResponse({"ok": False, "msg": "Order not found or expired"}, status_code=404)
    return {"ok": True, **info}


@router.post("/pro/grant")
def pro_grant(request: Request, body: dict = Body(...)):
    """The bot verified a payment. Safe to repeat: one payment_id grants once."""
    if (denied := _denied(request)):
        return denied
    from smweb import telegram_billing
    try:
        result = telegram_billing.record_payment(
            str(body.get("payment_id") or ""), str(body.get("tg_id") or ""), str(body.get("plan") or ""),
            tg_username=str(body.get("tg_username") or ""), method=str(body.get("method") or ""),
            amount=str(body.get("amount") or ""), currency=str(body.get("currency") or ""),
            order_token=str(body.get("order_token") or ""), claim_only=bool(body.get("claim_only")),
        )
    except ValueError as exc:
        return JSONResponse({"ok": False, "msg": f"Bad {exc}"}, status_code=400)
    LOGGER.info("telegram pro payment: %s (%s)", result.get("status"), result.get("plan"))
    result.pop("user_id", None)
    return {"ok": True, **result}


@router.post("/pro/revoke")
def pro_revoke(request: Request, body: dict = Body(...)):
    """A refund made in the bot: take the Pro time of that payment back."""
    if (denied := _denied(request)):
        return denied
    from smweb import telegram_billing
    result = telegram_billing.revoke(str(body.get("payment_id") or ""))
    LOGGER.info("telegram pro revoke: %s", result.get("status"))
    return {"ok": True, **result}


# ---------------------------------------------------------------- cutting a file sent to the bot (smweb/telegram_cut.py)
@router.get("/cut/quota")
def cut_quota(request: Request, tg_id: str = ""):
    """Pro or how many free files are left today for this Telegram user."""
    if (denied := _denied(request)):
        return denied
    from smweb import telegram_cut
    if not telegram_cut.valid_tg(tg_id):
        return JSONResponse({"ok": False, "msg": "Bad Telegram id"}, status_code=400)
    return {"ok": True, **telegram_cut.quota(tg_id)}


@router.post("/cut/start")
async def cut_start(request: Request, tg_id: str = Form(""), mode: str = Form("workshop"),
                    frame: str = Form("none"), file: UploadFile = File(...)):
    """Queue an ordinary Process job for the file the bot downloaded from Telegram."""
    if (denied := _denied(request)):
        return denied
    from smweb import telegram_cut
    from smweb.core import MAX_UPLOAD_MB
    data = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    code, body = await run_in_threadpool(telegram_cut.start, tg_id, file.filename or "file", data, mode, frame)
    return JSONResponse(body, status_code=code)


@router.get("/cut/status/{job_id}")
def cut_status(job_id: str, request: Request, tg_id: str = ""):
    if (denied := _denied(request)):
        return denied
    from smweb import telegram_cut
    job = telegram_cut.job_for(tg_id, job_id)
    if not job:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    return {"ok": True, **telegram_cut.describe(job_id, job)}


@router.get("/cut/download/{job_id}")
def cut_download(job_id: str, request: Request, tg_id: str = ""):
    """The finished ZIP (or a short-lived R2 link when the file lives only there)."""
    if (denied := _denied(request)):
        return denied
    from pathlib import Path
    from fastapi.responses import FileResponse, RedirectResponse
    from smweb import telegram_cut
    job = telegram_cut.job_for(tg_id, job_id)
    if not job or job.get("status") != "done":
        return JSONResponse({"ok": False, "msg": "Not ready"}, status_code=409 if job else 404)
    path = Path(str(job.get("zip_path") or ""))
    if path.is_file():
        return FileResponse(str(path), media_type="application/zip", filename="showcase.zip")
    if job.get("result_key"):
        from smweb import object_store
        url = object_store.presigned_get_url(str(job["result_key"]), expires=600, download_name="showcase.zip",
                                             media_type="application/zip")
        return RedirectResponse(url, status_code=302)
    return JSONResponse({"ok": False, "msg": "Result expired"}, status_code=410)
