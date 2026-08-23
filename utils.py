"""Shared helpers: quota, validation, cookies, codes."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse

import auth_db
from config import (
    ACCESS_FILE, CODES_FILE_REPO, DEFAULT_CODES, FREE_LIMIT, DATA,
)
from logging_config import log

try:
    import magic
    HAS_MAGIC = True
except Exception:
    HAS_MAGIC = False

ALLOWED_EXT = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp",
    ".gif", ".mp4", ".mov", ".webm", ".avi", ".mkv",
}
# magic byte signatures (prefix)
MAGIC_MAP = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",  # need WEBP check further
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"\x00\x00\x00\x18ftyp": "video/mp4",
    b"\x00\x00\x00\x1cftyp": "video/mp4",
    b"\x00\x00\x00\x20ftyp": "video/mp4",
}


def day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def client_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


def auth_user(req: Request) -> dict | None:
    tok = (req.headers.get("x-session-token") or "").strip()
    if not tok:
        tok = (req.cookies.get("sm_session") or "").strip()
    if not tok:
        return None
    return auth_db.user_by_token(tok)


def attach_session_cookie(resp, token: str, request: Request | None = None):
    secure = False
    if request is not None:
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
        secure = proto == "https"
    resp.set_cookie(
        key="sm_session",
        value=token,
        max_age=60 * 60 * 24 * 90,
        path="/",
        httponly=False,
        samesite="lax",
        secure=secure,
    )
    return resp


def clear_session_cookie(resp):
    resp.delete_cookie("sm_session", path="/")
    return resp


def load_codes() -> dict:
    codes = dict(DEFAULT_CODES)
    for c in os.environ.get("ACCESS_CODES", "").split(","):
        c = c.strip()
        if c:
            codes[c.upper()] = {"type": "unlimited", "label": "Custom"}
    for path in (CODES_FILE_REPO, ACCESS_FILE):
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    codes.update({str(k).upper(): v for k, v in data.items()})
            except Exception as e:
                log.warning("load codes failed: %s %s", path, e)
    return codes


def quota_state(req: Request) -> dict:
    user = auth_user(req)
    if user and auth_db.effective_pro(user):
        until = user.get("pro_until")
        remaining = None
        is_trial = False
        if until is not None:
            try:
                remaining = max(0, int(float(until) - time.time()))
                is_trial = True
            except (TypeError, ValueError):
                remaining = None
        return {
            "used": 0,
            "limit": -1,
            "left": -1,
            "pro": True,
            "label": "Trial" if is_trial and remaining is not None else "Pro",
            "email": user.get("email"),
            "user_id": user.get("id"),
            "pro_until": until,
            "remaining_sec": remaining,
            "is_trial": bool(is_trial and remaining is not None),
        }
    email = user.get("email") if user else None
    uid = user.get("id") if user else None
    ip = client_ip(req)
    d = day()
    auth_db.reset_usage_if_new_day(ip, d)
    used = auth_db.get_usage(ip, d)
    return {
        "used": used,
        "limit": FREE_LIMIT,
        "left": max(0, FREE_LIMIT - used),
        "pro": False,
        "label": "Free",
        "email": email,
        "user_id": uid,
        "pro_until": None,
        "remaining_sec": None,
        "is_trial": False,
    }


def quota_inc(req: Request, n: int) -> None:
    user = auth_user(req)
    if user and auth_db.effective_pro(user):
        return
    ip = client_ip(req)
    d = day()
    auth_db.inc_usage(ip, d, n)


def validate_upload(raw: bytes, filename: str) -> tuple[bool, str]:
    """Return (ok, error_msg). Checks extension + magic bytes / libmagic."""
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        return False, f"unsupported format: {ext or 'no extension'}"
    if not raw or len(raw) < 12:
        return False, "file too small"
    # magic bytes
    ok_magic = False
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        ok_magic = True
    elif raw[:3] == b"\xff\xd8\xff":
        ok_magic = True
    elif raw[:6] in (b"GIF87a", b"GIF89a"):
        ok_magic = True
    elif raw[:4] == b"RIFF" and b"WEBP" in raw[:16]:
        ok_magic = True
    elif raw[4:8] == b"ftyp":  # mp4/mov family
        ok_magic = True
    elif raw[:4] == b"\x1a\x45\xdf\xa3":  # webm/mkv
        ok_magic = True
    elif ext in (".bmp",) and raw[:2] == b"BM":
        ok_magic = True
    if HAS_MAGIC:
        try:
            mime = magic.from_buffer(raw[:2048], mime=True)
            if mime and (mime.startswith("image/") or mime.startswith("video/")):
                ok_magic = True
            elif mime and "octet" not in mime:
                # still allow if our prefix matched
                pass
        except Exception:
            pass
    if not ok_magic and ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm"):
        return False, "content does not match image/video signature"
    return True, ""



