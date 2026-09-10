"""Email/password accounts, avatars, sessions.

Moved out of main.py unchanged; see docs/STRUCTURE.md.
"""


from __future__ import annotations

import hashlib
import hmac
import html
import io
import asyncio
import ipaddress
import json
import logging
import os
import re
import socket
import tempfile
import shutil
import secrets
import time
import uuid
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs
import mailer

import auth_db
from smweb import object_store, analytics

from fastapi import APIRouter


from smweb.core import (
    DATA,
    LOGGER,
    _admin_ok,
    _attach_session_cookie,
    _auth_user,
    _clear_session_cookie,
    _is_gallery_admin,
    _safe_data_path,
)



router = APIRouter()


def _avatar_files(user_id) -> list[Path]:
    """Local avatar files for a user, newest first.

    Matches both the legacy `<id>.<ext>` layout and the versioned
    `<id>-<token>.<ext>` one written by /api/auth/profile.
    """
    av_dir = Path(DATA) / "avatars"
    if not av_dir.is_dir():
        return []
    try:
        uid = str(int(user_id))
    except (TypeError, ValueError):
        return []
    found = list(av_dir.glob(f"{uid}.*")) + list(av_dir.glob(f"{uid}-*"))
    def _mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0
    return sorted(found, key=_mtime, reverse=True)


def _request_language(request: Request) -> str:
    language = (request.headers.get("accept-language") or "en").split(",", 1)[0]
    return language.strip().lower()[:8] or "en"


def _account_media_cleanup(plan: dict) -> None:
    """Best-effort deletion of account-owned local and R2 media."""
    uid = int(plan["user_id"])
    if object_store.configured():
        try:
            object_store.delete_prefix(f"avatars/{uid}", public=True, directory=False)
        except Exception:
            LOGGER.exception("account delete: R2 avatar cleanup failed user_id=%s", uid)
        for prefix in (f"profile_assets/{uid}", f"profile_sc/{uid}", f"gallery/u{uid}"):
            try:
                object_store.delete_prefix(prefix, public=True)
            except Exception:
                LOGGER.exception("account delete: R2 public prefix cleanup failed prefix=%s", prefix)
        try:
            object_store.delete_prefix(f"builder/{uid}", public=False)
        except Exception:
            LOGGER.exception("account delete: R2 private prefix cleanup failed user_id=%s", uid)
        for stored in (plan.get("avatar_path"), plan.get("profile_background"), *(plan.get("gallery_paths") or [])):
            value = str(stored or "").strip()
            if not value or value.startswith(("http://", "https://")):
                continue
            try:
                key = object_store.key_from_stored(value)
                if key.startswith(("avatars/", "profile_assets/", "profile_sc/", "gallery/")):
                    object_store.delete(key, public=True)
            except Exception:
                LOGGER.exception("account delete: R2 object cleanup failed")

    for relative in (
        Path("profile_assets") / str(uid),
        Path("profile_sc") / str(uid),
        Path("builder") / str(uid),
        Path("projects") / str(uid),
        Path("gallery") / f"u{uid}",
    ):
        target = (Path(DATA) / relative).resolve()
        try:
            target.relative_to(Path(DATA).resolve())
            shutil.rmtree(target, ignore_errors=True)
        except (OSError, ValueError):
            LOGGER.exception("account delete: local directory cleanup failed user_id=%s", uid)
    for avatar in _avatar_files(uid):
        try:
            avatar.unlink(missing_ok=True)
        except OSError:
            LOGGER.exception("account delete: local avatar cleanup failed user_id=%s", uid)
    for stored in (plan.get("avatar_path"), plan.get("profile_background"), *(plan.get("gallery_paths") or [])):
        value = str(stored or "").strip()
        if not value or value.startswith(("http://", "https://")):
            continue
        path = _safe_data_path(value)
        if path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                LOGGER.exception("account delete: local object cleanup failed")


def _deliver_password_reset(email: str, code: str, language: str, identity: str) -> None:
    sent, mail_error = mailer.send_password_reset_code(email, code, language)
    if not sent:
        auth_db.discard_account_action_code(email, "password_reset")
        LOGGER.warning("password reset delivery failed identity=%s: %s", identity, mail_error)


@router.post("/api/auth/send-code")
async def auth_send_code(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    email = auth_db.normalize_email(str(body.get("email") or ""))
    if not email:
        return JSONResponse({"ok": False, "msg": "Invalid email", "code": "invalid_email"}, status_code=400)

    identity = hashlib.sha256(email.encode()).hexdigest()[:24]
    if not rs.rate_limit(f"auth-send-code:{identity}", 3, 300)[0]:
        return JSONResponse({"ok": False, "msg": "Too many requests. Try later.", "code": "rate_limited"}, status_code=429)

    # Always give the browser the same answer for registered and new addresses.
    # This prevents the registration form from becoming an account-enumeration API.
    generic = "If this address can be registered, a code has been sent"
    if auth_db.user_exists(email):
        return JSONResponse({"ok": True, "msg": generic, "code": "code_sent"})

    created, create_msg, code = auth_db.create_email_code(email, ttl_sec=900)
    if not created:
        status = 429 if "60 seconds" in create_msg else 503
        reason = "rate_limited" if status == 429 else "verification_unavailable"
        return JSONResponse({"ok": False, "msg": create_msg, "code": reason}, status_code=status)

    lang = (request.headers.get("accept-language") or "en")
    ok, msg = mailer.send_verify_code(email, code, lang)
    if not ok:
        auth_db.discard_email_code(email)
        LOGGER.warning("send_verify_code failed for %s: %s", email, msg)
        return JSONResponse({"ok": False, "msg": "Failed to send email", "code": "delivery_failed"}, status_code=503)

    return JSONResponse({"ok": True, "msg": generic, "code": "code_sent"})


@router.post("/api/auth/register")
async def auth_register(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    email = str(body.get("email") or "")
    password = str(body.get("password") or "")
    code = str(body.get("code") or "").strip()
    
    identity = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:24]
    if not rs.rate_limit(f"auth-register-email:{identity}", 3, 3600)[0]:
        return JSONResponse({"ok": False, "msg": "Too many requests. Try later.", "code": "rate_limited"}, status_code=429)
        
    ok, msg, reason = auth_db.register_with_email_code(email, password, code)
    if not ok:
        LOGGER.warning("auth register rejected identity=%s ip=%s", identity, request.client.host if request.client else "-")
        return JSONResponse({"ok": False, "msg": msg, "code": reason}, status_code=400)
    ok2, msg2, token = auth_db.login(email, password)
    resp = JSONResponse({"ok": True, "msg": msg, "session": bool(token)})
    if token:
        _attach_session_cookie(resp, token, request)
        created_user = auth_db.user_by_token(token)
        analytics.record(
            "registration_success", request=request,
            user_id=created_user.get("id") if created_user else None,
            properties={"method": "email"},
        )
    return resp


@router.post("/api/auth/login")
async def auth_login(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    email = str(body.get("email") or "")
    password = str(body.get("password") or "")
    identity = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:24]
    if not rs.rate_limit(f"auth-login-email:{identity}", 8, 300)[0]:
        return JSONResponse({"ok": False, "msg": "Too many requests. Try later."}, status_code=429)
    ok, msg, token = auth_db.login(email, password)
    if not ok:
        LOGGER.warning("auth login failed identity=%s ip=%s", identity, request.client.host if request.client else "-")
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    user = auth_db.user_by_token(token) if token else None
    resp = JSONResponse({
        "ok": True,
        "session": bool(token),
        "email": user.get("email") if user else None,
        "is_pro": bool(user and auth_db.effective_pro(user)),
    })
    if token:
        _attach_session_cookie(resp, token, request)
    LOGGER.info("auth login success user_id=%s", user.get("id") if user else "-")
    return resp


@router.post("/api/auth/change-password")
async def auth_change_password(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    current_password = str(body.get("current_password") or "")
    new_password = str(body.get("new_password") or "")
    token = (request.headers.get("x-session-token") or request.cookies.get("sm_session") or "").strip()
    if not rs.rate_limit(f"auth-change-password:{int(user['id'])}", 5, 900)[0]:
        return JSONResponse({"ok": False, "msg": "Too many requests. Try later."}, status_code=429)
    ok, msg = auth_db.change_password(int(user["id"]), current_password, new_password, token)
    LOGGER.info("auth password_change user_id=%s ok=%s", user["id"], ok)
    return JSONResponse({"ok": ok, "msg": msg}, status_code=200 if ok else 400)


@router.post("/api/auth/password-reset/request")
async def auth_password_reset_request(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.json()
    except Exception:
        body = {}
    email = auth_db.normalize_email(str(body.get("email") or ""))
    if not email:
        return JSONResponse({"ok": False, "msg": "Invalid email", "code": "invalid_email"}, status_code=400)
    identity = hashlib.sha256(email.encode()).hexdigest()[:24]
    if not rs.rate_limit(f"auth-password-reset:{identity}", 3, 900)[0]:
        return JSONResponse({"ok": False, "msg": "Too many requests. Try later.", "code": "rate_limited"}, status_code=429)

    # The same answer is returned whether the account exists or not. This
    # prevents password recovery from becoming an account enumeration endpoint.
    generic = "If an account exists for this address, a recovery code has been sent"
    account_exists = auth_db.user_exists(email)
    created, message, code = auth_db.create_account_action_code(email, "password_reset", ttl_sec=900)
    if not created:
        if "60 seconds" not in message:
            LOGGER.warning("password reset code unavailable identity=%s: %s", identity, message)
        return {"ok": True, "msg": generic, "code": "code_sent"}
    if account_exists:
        # Delivery happens after the generic response has been sent so response
        # timing cannot reveal whether the address belongs to an account.
        background_tasks.add_task(
            _deliver_password_reset, email, code, _request_language(request), identity
        )
    else:
        auth_db.discard_account_action_code(email, "password_reset")
    return {"ok": True, "msg": generic, "code": "code_sent"}


@router.post("/api/auth/password-reset/confirm")
async def auth_password_reset_confirm(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    email = auth_db.normalize_email(str(body.get("email") or ""))
    code = str(body.get("code") or "").strip()
    new_password = str(body.get("new_password") or "")
    identity = hashlib.sha256(email.encode()).hexdigest()[:24] if email else "invalid"
    if not rs.rate_limit(f"auth-password-reset-confirm:{identity}", 8, 900)[0]:
        return JSONResponse({"ok": False, "msg": "Too many requests. Try later.", "code": "rate_limited"}, status_code=429)
    ok, message, reason = auth_db.reset_password_with_code(email, code, new_password)
    LOGGER.info("auth password_reset identity=%s ok=%s", identity, ok)
    return JSONResponse({"ok": ok, "msg": message, "code": reason}, status_code=200 if ok else 400)


@router.get("/api/auth/account-export")
def auth_account_export(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    uid = int(user["id"])
    payload = auth_db.account_export_data(uid, analytics.user_hash(uid))
    encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return StreamingResponse(
        io.BytesIO(encoded),
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="showcase-maker-account-{stamp}.json"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/api/auth/account-delete")
async def auth_account_delete(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    uid = int(user["id"])
    expected_email = auth_db.normalize_email(str(user.get("email") or ""))
    confirmation_email = auth_db.normalize_email(str(body.get("confirm_email") or ""))
    if confirmation_email != expected_email or str(body.get("confirm") or "") != "DELETE":
        return JSONResponse({"ok": False, "msg": "Account deletion confirmation does not match"}, status_code=400)
    if rs.job_count_user(str(uid)):
        return JSONResponse(
            {"ok": False, "msg": "Wait for active processing jobs to finish before deleting the account"},
            status_code=409,
        )
    plan = auth_db.delete_account_data(uid, analytics.user_hash(uid))
    await asyncio.to_thread(_account_media_cleanup, plan)
    LOGGER.info("auth account_deleted user_id=%s", uid)
    response = JSONResponse({"ok": True, "msg": "Account deleted"})
    _clear_session_cookie(response)
    return response


@router.post("/api/admin/wipe-users")
async def admin_wipe_users(request: Request):
    """Delete all accounts. Requires header X-Admin-Secret = ADMIN_SECRET env."""
    if not _admin_ok(request):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    n = auth_db.wipe_all_users()
    return JSONResponse({"ok": True, "deleted": n})


@router.post("/api/auth/profile")
async def auth_profile(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    ct = (request.headers.get("content-type") or "").lower()
    display_name = None
    avatar_saved = None
    try:
        if "multipart/form-data" in ct:
            form = await request.form(max_files=1, max_fields=4, max_part_size=3_000_000)
            display_name = str(form.get("display_name") or "")
            f = form.get("avatar")
            if f is not None and hasattr(f, "read"):
                raw = await f.read()
                if len(raw) >= 3_000_000:
                    return JSONResponse(
                        {"ok": False, "msg": "Avatar must be under 3 MB"},
                        status_code=413,
                    )
                if raw and len(raw) < 3_000_000:
                    name = getattr(f, "filename", "") or "a.png"
                    ext = Path(name).suffix.lower()
                    # sniff magic if extension missing/wrong
                    head = raw[:12]
                    if head[:6] in (b"GIF87a", b"GIF89a"):
                        ext = ".gif"
                    elif head[:8] == b"\x89PNG\r\n\x1a\n":
                        ext = ".png"
                    elif head[:3] == b"\xff\xd8\xff":
                        ext = ".jpg"
                    elif head[:4] == b"RIFF" and raw[8:12] == b"WEBP":
                        ext = ".webp"
                    elif ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                        ext = ".png"
                    try:
                        Image.open(io.BytesIO(raw)).verify()
                    except Exception:
                        return JSONResponse(
                            {"ok": False, "msg": "Avatar must be a valid PNG, JPG, WEBP or GIF"},
                            status_code=400,
                        )
                    # A fresh key per upload. The header shows a stable
                    # /api/auth/avatar/{id} URL that redirects to this object, so
                    # reusing one key left browsers and R2 edges serving the
                    # previous picture until their copy expired -- the "avatar
                    # does not change in the header circle" report. A unique key
                    # changes the redirect target, so the new image appears at
                    # once and can still be cached hard.
                    avatar_saved = f"avatars/{user['id']}-{secrets.token_hex(4)}{ext}"
                    old_key = str(user.get("avatar_path") or "").strip()
                    if object_store.configured():
                        # Upload before deleting: a failed upload must not leave
                        # the account with no avatar at all.
                        object_store.put_bytes(
                            avatar_saved, raw,
                            media_type=object_store.content_type(avatar_saved),
                            immutable=True,
                        )
                        if old_key:
                            try: object_store.delete(object_store.key_from_stored(old_key))
                            except Exception: pass
                    else:
                        path = Path(DATA) / avatar_saved
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(raw)
                        old_local = _safe_data_path(old_key) if old_key else None
                        if old_local is not None and old_local != path:
                            try: old_local.unlink()
                            except Exception: pass
        else:
            body = await request.json()
            display_name = str(body.get("display_name") or "")
        auth_db.update_profile(
            int(user["id"]),
            display_name=display_name,
            avatar_path=avatar_saved,
        )
        av_url = f"/api/auth/avatar/{user['id']}" if (avatar_saved or user.get("avatar_path")) else ""
        if not av_url and _avatar_files(user["id"]):
            av_url = f"/api/auth/avatar/{user['id']}"
        return {
            "ok": True,
            "msg": "Profile updated",
            "display_name": (display_name or "").strip()[:40],
            "avatar_url": av_url,
        }
    except Exception:
        rid = getattr(request.state, "request_id", "-")
        LOGGER.exception("profile update failed rid=%s user_id=%s", rid, user["id"])
        return JSONResponse({"ok": False, "msg": "Profile update failed", "request_id": rid}, status_code=500)


@router.get("/api/auth/avatar/{user_id}")
def auth_avatar(user_id: int):
    c = auth_db._conn()
    row = c.execute("SELECT avatar_path FROM users WHERE id=?", (user_id,)).fetchone()
    c.close()
    stored = ""
    if row and row["avatar_path"]:
        stored = str(row["avatar_path"]).strip()
    if stored and object_store.configured():
        try:
            url = object_store.public_url(object_store.key_from_stored(stored))
            if url:
                return RedirectResponse(url, status_code=307, headers={"Cache-Control": "no-cache"})
        except Exception:
            LOGGER.exception("R2 avatar lookup failed")
    # Always resolve INSIDE DATA. The stored value was once used as an absolute
    # path, which made this public endpoint read any file on the box.
    path = _safe_data_path(stored) if stored else None
    if path is None:
        matches = _avatar_files(user_id)
        # prefer image extensions
        matches = [m for m in matches if m.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")] or matches
        path = matches[0] if matches else None
    if path is None or not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    from fastapi.responses import FileResponse
    media = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path,
        media_type=media,
        headers={"Cache-Control": "no-cache, max-age=0", "Access-Control-Allow-Origin": "*"},
    )


@router.post("/api/auth/logout")
async def auth_logout(request: Request):
    tok = (request.headers.get("x-session-token") or "").strip()
    if not tok:
        tok = (request.cookies.get("sm_session") or "").strip()
    if tok:
        auth_db.logout(tok)
    resp = JSONResponse({"ok": True})
    _clear_session_cookie(resp)
    return resp


def _me_payload(user: Optional[dict]) -> dict:
    """The /api/auth/me body, built from an already-resolved user.

    Shared with /api/bootstrap so the two can never drift, and takes the user as
    an argument rather than the request so the caller resolves the session once.
    """
    if not user:
        return {"ok": False, "logged_in": False}
    # Always have a public handle so the header nick can link to /profile/{username}
    try:
        un = auth_db.ensure_profile_username(int(user["id"]), user.get("display_name") or (user.get("email") or "").split("@")[0])
    except Exception:
        un = (user.get("profile_username") or "").strip()
    av = user.get("avatar_path") or ""
    av_url = ""
    if av:
        av_url = f"/api/auth/avatar/{user['id']}"
    elif _avatar_files(user["id"]):
        # fallback if path was lost but file remains on disk
        av_url = f"/api/auth/avatar/{user['id']}"
    return {
        "ok": True,
        "logged_in": True,
        "email": user["email"],
        "is_pro": auth_db.effective_pro(user),
        "pro_until": user.get("pro_until"),
        "pro_code": user.get("pro_code") or "",
        "display_name": user.get("display_name") or "",
        "profile_username": un or (user.get("profile_username") or ""),
        "avatar_url": av_url,
        "is_gallery_admin": _is_gallery_admin(user),
    }


@router.get("/api/auth/me")
def auth_me(request: Request):
    return _me_payload(_auth_user(request))


@router.get("/api/bootstrap")
def api_bootstrap(request: Request):
    """Everything a page shell needs on load, in one request.

    Every page loads ss-shell.js, which called /api/auth/me on load. On the
    homepage index.js called the same endpoint a second time for the nav pill,
    then asked /api/notifications/unread for the bell badge: three requests and
    three session lookups to paint one page.

    This is the union of those, resolving the session exactly once. The body is a
    strict superset of /api/auth/me - both are built by _me_payload() - so a
    caller can move to this endpoint without changing how it reads the response.
    Both original endpoints are left exactly as they were; anything still calling
    them keeps working.
    """
    user = _auth_user(request)
    me = _me_payload(user)
    unread = 0
    if user:
        try:
            unread = auth_db.notifications_unread_count(int(user["id"]))
        except Exception:
            # A missing notifications table must not take down the whole shell.
            LOGGER.exception("bootstrap: unread count failed")
    me["unread"] = unread
    return me
