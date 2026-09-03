"""Email/password accounts, avatars, sessions.

Moved out of main.py unchanged; see docs/STRUCTURE.md.
"""


from __future__ import annotations

import hashlib
import hmac
import html
import io
import ipaddress
import json
import logging
import os
import re
import socket
import secrets
import tempfile
import shutil
import time
import uuid
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db
from smweb import object_store


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


@router.post("/api/auth/register")
async def auth_register(request: Request):
    body = await request.json()
    email = str(body.get("email") or "")
    password = str(body.get("password") or "")
    ok, msg = auth_db.register(email, password)
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    ok2, msg2, token = auth_db.login(email, password)
    resp = JSONResponse({"ok": True, "msg": msg, "token": token})
    if token:
        _attach_session_cookie(resp, token, request)
    return resp


@router.post("/api/auth/login")
async def auth_login(request: Request):
    body = await request.json()
    email = str(body.get("email") or "")
    password = str(body.get("password") or "")
    ok, msg, token = auth_db.login(email, password)
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    user = auth_db.user_by_token(token) if token else None
    resp = JSONResponse({
        "ok": True,
        "token": token,
        "email": user.get("email") if user else None,
        "is_pro": bool(user and auth_db.effective_pro(user)),
    })
    if token:
        _attach_session_cookie(resp, token, request)
    return resp


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
            form = await request.form()
            display_name = str(form.get("display_name") or "")
            f = form.get("avatar")
            if f is not None and hasattr(f, "read"):
                raw = await f.read()
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
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"{type(e).__name__}: {e}"}, status_code=500)


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
        "profile_username": user.get("profile_username") or "",
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
