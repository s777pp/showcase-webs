"""Public assistant routes. No secrets or private project docs are sent to clients."""
from __future__ import annotations
import hashlib
import json
import re
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
import auth_db
import redis_store as rs
from smweb.core import _auth_user, _ip
from smweb import admin_content, support_chat as chat

router = APIRouter()

def reply(body, status=200):
    return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})


def _same_origin(request: Request) -> bool:
    origin = request.headers.get("origin", "").rstrip("/")
    allowed = {str(request.base_url).rstrip("/"), os.environ.get("APP_URL", "").rstrip("/")}
    return bool(origin and origin in allowed and request.headers.get("sec-fetch-site") != "cross-site")

@router.get("/api/support/info")
def info():
    return reply({"ok": True, "available": chat.configured(),
                  "daily_limit": chat.settings()["visitor_daily"], "topics": chat.KNOWLEDGE})

@router.post("/api/support/chat")
async def support(request: Request):
    # Protect anonymous paid calls as well as cookie sessions.
    if not _same_origin(request):
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


@router.post("/api/support/tickets")
async def create_ticket(request: Request):
    if not _same_origin(request):
        return reply({"ok": False, "code": "origin"}, 403)
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        return reply({"ok": False, "code": "invalid"}, 415)
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 12000:
            return reply({"ok": False, "code": "too_large"}, 413)
    allowed_call, _ = rs.rate_limit("support-ticket:" + hashlib.sha256(_ip(request).encode()).hexdigest()[:24], 5, 86400)
    if not allowed_call:
        return reply({"ok": False, "code": "limit"}, 429)
    try:
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError
        try:
            user = _auth_user(request)
        except Exception:
            user = None
        email, telegram = _contact(body, user)
        if not email and not telegram:
            return reply({"ok": False, "code": "contact"}, 400)
        context = dict(body.get("context") or {}) if isinstance(body.get("context"), dict) else {}
        context["telegram"] = telegram
        result = admin_content.create_ticket(
            user_id=int(user["id"]) if user else None, email=email,
            message=body.get("message", ""), page=body.get("page", "/"), context=context,
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return reply({"ok": False, "code": "invalid"}, 400)
    from smweb import admin_notify
    admin_notify.ticket_created(result.get("ticket_id", ""), email, str(body.get("message", "")),
                                str(body.get("page", "/")), telegram=telegram)
    return reply(result, 201)


_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_TELEGRAM = re.compile(r"^(?:https?://)?(?:t\.me/|telegram\.me/)?@?([A-Za-z][A-Za-z0-9_]{4,31})/?$")


def _contact(body: dict, user: dict | None) -> tuple[str, str]:
    """(email, telegram username) the user wants the answer at.

    ``contact`` comes from the support window and may be an e-mail or a
    Telegram username / t.me link; ``email`` is the older chat form.  A
    logged-in user who gives nothing is answered at the account e-mail.
    """
    raw = str(body.get("contact") or body.get("email") or "").strip()[:254]
    if _EMAIL.match(raw):
        return raw, ""
    match = _TELEGRAM.match(raw)
    if match:
        return "", match.group(1)
    if not raw and user and user.get("email"):
        return str(user["email"])[:254], ""
    return "", ""


@router.get("/api/support/my")
def my_tickets(request: Request):
    user = _auth_user(request)
    if not user:
        return reply({"ok": False, "code": "login"}, 401)
    from smweb import support_threads
    return reply({"ok": True, "items": support_threads.user_tickets(int(user["id"]))})


@router.get("/api/support/my/{ticket_id}")
def my_ticket(ticket_id: str, request: Request):
    user = _auth_user(request)
    if not user:
        return reply({"ok": False, "code": "login"}, 401)
    from smweb import support_threads
    thread = support_threads.user_thread(ticket_id, int(user["id"]))
    if not thread:
        return reply({"ok": False, "code": "not_found"}, 404)
    try:
        connection = auth_db._conn()
        try:
            connection.execute("UPDATE notifications SET is_read=1 WHERE user_id=? AND group_key=?",
                               (int(user["id"]), f"support:{ticket_id}"))
            connection.commit()
        finally:
            connection.close()
    except Exception:
        pass
    return reply({"ok": True, "ticket": thread})


@router.post("/api/support/my/{ticket_id}")
async def my_ticket_reply(ticket_id: str, request: Request):
    if not _same_origin(request):
        return reply({"ok": False, "code": "origin"}, 403)
    user = _auth_user(request)
    if not user:
        return reply({"ok": False, "code": "login"}, 401)
    allowed_call, _ = rs.rate_limit(f"support-reply:{int(user['id'])}", 20, 3600)
    if not allowed_call:
        return reply({"ok": False, "code": "limit"}, 429)
    try:
        body = await request.json()
    except Exception:
        body = {}
    from smweb import support_threads
    try:
        support_threads.reply_from_user(ticket_id, int(user["id"]), str((body or {}).get("text") or ""))
    except LookupError:
        return reply({"ok": False, "code": "not_found"}, 404)
    except ValueError as exc:
        return reply({"ok": False, "code": "invalid", "msg": str(exc)}, 400)
    return reply({"ok": True})


@router.get("/api/announcements")
def public_announcements(request: Request):
    try:
        user = _auth_user(request)
    except Exception:
        user = None
    audience = "pro" if user and auth_db.effective_pro(user) else ("users" if user else "guests")
    items = admin_content.announcements(active_only=True, audience=audience)
    return JSONResponse({"ok": True, "items": items[:3]}, headers={"Cache-Control": "private, max-age=60"})


# ---------------------------------------------------------------- "My requests" page (2026-10-01)
from fastapi.responses import HTMLResponse  # noqa: E402

from smweb.locales import SUPPORTED_LANGUAGES  # noqa: E402


@router.get("/support", include_in_schema=False)
def support_redirect(request: Request):
    from smweb.routers import pages
    return pages._legacy_redirect(request, "/support")


def _support_page(language: str):
    def serve():
        from smweb.routers import pages
        response = pages._localized_html("support.html", language, "/support")
        response.headers["X-Robots-Tag"] = "noindex, follow"
        return response
    return serve


for _language in SUPPORTED_LANGUAGES:
    router.add_api_route(f"/{_language}/support", _support_page(_language), methods=["GET"],
                         response_class=HTMLResponse, include_in_schema=False)
