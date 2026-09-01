"""Paths, environment configuration and the helpers every router shares.

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
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db


logging.basicConfig(
    level=getattr(logging, (os.environ.get("LOG_LEVEL") or "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


LOGGER = logging.getLogger("sm")


# Pillow decompression-bomb guard. A 3 KB PNG can declare 200000x200000 pixels;
# decoding it allocates tens of GB and takes the container down. Pillow only
# WARNS above this limit and raises above 2x it, so promote the warning to an
# error and let the handler above turn it into a 400.
Image.MAX_IMAGE_PIXELS = int(os.environ.get("MAX_IMAGE_PIXELS", "100000000"))


warnings.simplefilter("error", Image.DecompressionBombWarning)


ROOT = Path(__file__).resolve().parent.parent  # smweb/ -> repo root


# Single source of truth, shared with auth_db. Previously each module resolved
# DATA on its own: main.py silently fell back to a writable directory while
# auth_db stayed on the volume, so avatar FILES were saved while the matching DB
# write failed with "attempt to write a readonly database".
DATA = auth_db.DATA


JOBS = DATA / "jobs"


USAGE_FILE = DATA / "usage.json"


# keys: bundled file (repo) -> env -> volume override. The bundled file carries
# per-code metadata (trial codes have "hours"), which a flat env list cannot express.
CODES_FILE_REPO = ROOT / "data" / "access_codes.json"


ACCESS_FILE = DATA / "access_codes.json"


STATIC = ROOT / "static"


TEMPLATES = ROOT / "templates"


FONTS = ROOT / "fonts"


for d in (DATA, JOBS, STATIC):
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print("mkdir failed", d, e)


FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "5"))


MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "40"))


HOST = os.environ.get("HOST", "127.0.0.1")


PORT = int(os.environ.get("PORT", "8080"))


# Stripe (опционально). Без ключей — только коды доступа + аккаунты без оплаты.
STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")


STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")  # price_... из Dashboard


APP_URL = os.environ.get("APP_URL", f"http://{HOST}:{PORT}")


DA_CLIENT_ID = os.environ.get("DA_CLIENT_ID", "").strip()


DA_CLIENT_SECRET = os.environ.get("DA_CLIENT_SECRET", "").strip()


DA_REDIRECT_URI = os.environ.get("DA_REDIRECT_URI", "").strip()  # e.g. https://xxx.up.railway.app/api/da/callback


def _da_cfg():
    """Read DA env at request time (after Railway injects vars)."""
    return {
        "id": (os.environ.get("DA_CLIENT_ID") or "").strip(),
        "secret": (os.environ.get("DA_CLIENT_SECRET") or "").strip(),
        "redirect": (os.environ.get("DA_REDIRECT_URI") or "").strip(),
    }


def _da_ready():
    c = _da_cfg()
    return bool(c["id"] and c["secret"] and c["redirect"]), c


PRO_PRICE_LABEL = os.environ.get("PRO_PRICE_LABEL", "Pro · безлимит")


# Коды доступа: снимают лимит. Источники, по возрастанию приоритета:
#   ADMIN_ACCESS_CODE      — один админский ключ
#   data/access_codes.json — файл в репозитории (основной список, с метаданными
#                            trial-кодов: {"type": "trial", "hours": 2})
#   ACCESS_CODES           — список через запятую: CODE1,CODE2 (только unlimited)
#   ACCESS_CODES_JSON      — JSON с метками, для точечных добавлений
#   DATA/access_codes.json — файл на томе, перекрывает всё остальное
DEFAULT_CODES: dict[str, dict] = {}


_admin_code = (os.environ.get("ADMIN_ACCESS_CODE") or "").strip().upper()


if _admin_code:
    DEFAULT_CODES[_admin_code] = {"type": "unlimited", "label": "Pro Admin"}


def _load_codes() -> dict:
    codes = dict(DEFAULT_CODES)
    # bundled list first, so env entries below can override individual codes
    if CODES_FILE_REPO.is_file():
        try:
            data = json.loads(CODES_FILE_REPO.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                codes.update({str(k).upper(): v for k, v in data.items()})
        except Exception as e:
            print("load codes", CODES_FILE_REPO, e)
    for c in os.environ.get("ACCESS_CODES", "").split(","):
        c = c.strip()
        if c:
            codes[c.upper()] = {"type": "unlimited", "label": "Custom"}
    raw = (os.environ.get("ACCESS_CODES_JSON") or "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                codes.update({str(k).upper(): v for k, v in data.items()})
        except Exception as e:
            print("load ACCESS_CODES_JSON:", e)
    if ACCESS_FILE.is_file():
        try:
            data = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                codes.update({str(k).upper(): v for k, v in data.items()})
        except Exception as e:
            print("load codes", ACCESS_FILE, e)
    return codes


def _load_usage() -> dict:
    if USAGE_FILE.is_file():
        try:
            return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_usage(u: dict) -> None:
    try:
        USAGE_FILE.write_text(json.dumps(u, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


_usage = _load_usage()


_sessions: dict[str, dict] = {}  # token -> {code, type}


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# How many proxies in front of us append to X-Forwarded-For.
#   1 — Railway edge, or the single Nginx from docker-compose (default)
#   0 — app exposed directly, no proxy: trust only the socket address
#   2 — Cloudflare in front of Nginx
TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "1"))


def _ip(req: Request) -> str:
    """Client IP used for quota and rate limits.

    X-Forwarded-For is attacker controlled on the LEFT: a client sends
    "9.9.9.9" and the proxy appends the real address, so reading entry [0]
    let anyone reset their free daily quota just by varying the header. Only
    the last TRUSTED_PROXY_HOPS entries are written by infrastructure we
    trust, so count from the RIGHT instead — the attacker can prepend junk
    but cannot remove what our own proxy appended.
    """
    hops = TRUSTED_PROXY_HOPS
    if hops > 0:
        xff = req.headers.get("x-forwarded-for") or ""
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-hops] if len(parts) >= hops else parts[0]
    return (req.client.host if req.client else None) or "unknown"


def _safe_data_path(stored: str, *, subdir: str = "") -> Optional[Path]:
    """Resolve a DB-stored relative path inside DATA, or None if it escapes.

    Guards the avatar / profile-background readers: those paths used to be
    written straight into Path(...), so an absolute value ("/data/users.db")
    or a traversal ("../../etc/passwd") stored in the row turned a public
    image endpoint into arbitrary file read.
    """
    s = (stored or "").strip().replace("\\", "/")
    if not s:
        return None
    base = Path(DATA).resolve()
    candidate = (base / subdir / s) if subdir else (base / s)
    try:
        resolved = candidate.resolve()
    except (OSError, ValueError):
        return None
    if resolved != base and base not in resolved.parents:
        return None
    return resolved if resolved.is_file() else None


# Profile columns a user may set themselves. Deliberately excludes avatar_path
# and profile_background: those are file locations the server writes after an
# upload, never values the client gets to choose.
PROFILE_EDITABLE_FIELDS = (
    "display_name", "profile_username", "profile_summary", "profile_location",
    "profile_status", "profile_visibility", "profile_level", "profile_xp",
    "profile_bg_x", "profile_bg_y", "profile_bg_scale", "profile_bg_overlay",
)


def _admin_ok(req: Request) -> bool:
    """Constant-time check of X-Admin-Secret against ADMIN_SECRET.

    Plain `got != secret` short-circuits on the first differing byte, which
    leaks the secret one character at a time to anyone who can measure response
    time. Absent/empty ADMIN_SECRET denies rather than allows.
    """
    secret = (os.environ.get("ADMIN_SECRET") or "").strip()
    got = (req.headers.get("x-admin-secret") or "").strip()
    if not secret or not got:
        return False
    return secrets.compare_digest(secret, got)


def _session(req: Request) -> dict:
    tok = (req.headers.get("x-access-token") or "").strip()
    if tok and tok in _sessions:
        return _sessions[tok]
    return {}


def _auth_user(req: Request) -> dict | None:
    """Пользователь по заголовку X-Session-Token или cookie."""
    tok = (req.headers.get("x-session-token") or "").strip()
    if not tok:
        tok = (req.cookies.get("sm_session") or "").strip()
    if not tok:
        return None
    return auth_db.user_by_token(tok)


# Moderator list. Kept in env so the deploy owns it; the address that used to be
# hardcoded here as a fallback is now just the default value of that variable.
GALLERY_ADMIN_EMAILS = os.environ.get(
    "GALLERY_ADMIN_EMAILS", "serhii.perepelytsia1510@gmail.com"
)


def _is_gallery_admin(user: dict | None) -> bool:
    if not user:
        return False
    email = (user.get("email") or "").strip().lower()
    emails = {e.strip() for e in GALLERY_ADMIN_EMAILS.lower().split(",") if e.strip()}
    return bool(email) and email in emails


def _esc_html(s) -> str:
    """Escape text before it goes into an HTML error page.

    The OAuth callbacks interpolated provider responses and exception text
    straight into markup, so anything an attacker could steer into an error
    message became script on our own origin.
    """
    return html.escape(str(s), quote=True)


def _check_public_url(url: str) -> tuple[bool, str]:
    """Allow only http(s) URLs that resolve to a public address.

    /api/download-url hands whatever the caller sends to yt-dlp and requests.
    With no check, "http://169.254.169.254/latest/meta-data/" or an address on
    the platform's internal network was fetched by the server and handed back
    through /api/job-file — a read primitive into infrastructure the client
    cannot reach directly. Every resolved address must be public: a name that
    answers with one public and one private A record is rejected too.

    Redirects are still followed by the libraries below, so this closes the
    front door rather than every path; keep egress locked down as well.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Bad URL"
    if parsed.scheme not in ("http", "https"):
        return False, "Only http(s) links are supported"
    host = parsed.hostname or ""
    if not host:
        return False, "Bad URL: no host"
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80),
                                   proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False, "Host not found"
    if not infos:
        return False, "Host not found"
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False, "Bad address"
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False, "This address is not allowed"
    return True, ""


def _attach_session_cookie(resp, token: str, request: Request | None = None):
    """Persist login across pages. secure=True only on HTTPS."""
    secure = False
    if request is not None:
        # Render/Railway terminate TLS; x-forwarded-proto or url scheme
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
        secure = proto == "https"
    resp.set_cookie(
        key="sm_session",
        value=token,
        max_age=60 * 60 * 24 * 90,
        path="/",
        # HttpOnly: script on the page cannot read this cookie, so an XSS that
        # gets code onto a page still cannot walk off with the session. Every
        # login path (password, Discord, Google, Telegram) sets the cookie
        # server-side, so nothing depends on the JS `document.cookie = ...`
        # writes in the frontend — the browser simply ignores those now.
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    return resp


def _clear_session_cookie(resp):
    resp.delete_cookie("sm_session", path="/")
    return resp


def quota_state(req: Request) -> dict:
    # 1) logged-in user (Pro is bound to account)
    user = _auth_user(req)
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
    ip = _ip(req)
    u = _usage.get(ip) or {"count": 0, "day": _day()}
    if u.get("day") != _day():
        u = {"count": 0, "day": _day()}
        _usage[ip] = u
        _save_usage(_usage)
    used = int(u.get("count") or 0)
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
    try:
        # Must match the IP that quota_state reads, or the Redis counter and
        # the file counter disagree about who spent what.
        rs.quota_inc(_ip(req), _day(), n)
    except Exception:
        pass
    # legacy file-backed path follows
    user = _auth_user(req)
    if user and auth_db.effective_pro(user):
        return
    if _session(req).get("type") == "unlimited":
        return
    ip = _ip(req)
    u = _usage.get(ip) or {"count": 0, "day": _day()}
    if u.get("day") != _day():
        u = {"count": 0, "day": _day()}
    u["count"] = int(u.get("count") or 0) + n
    _usage[ip] = u
    _save_usage(_usage)


USED_CODES_FILE = DATA / "used_codes.json"


def _load_used() -> set:
    if USED_CODES_FILE.is_file():
        try:
            return set(json.loads(USED_CODES_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def _save_used(used: set) -> None:
    try:
        USED_CODES_FILE.write_text(json.dumps(sorted(used), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


SOCIALS = [
    {"name": "Discord", "url": "https://discord.gg/me48dhgcw4", "icon": "/static/discord.png"},
    {"name": "TikTok", "url": "https://www.tiktok.com/@n1t1337", "icon": "/static/tiktok.png"},
    {"name": "YouTube", "url": "https://www.youtube.com/@n1t1337", "icon": "/static/youtube.png"},
    {"name": "Steam", "url": "https://steamcommunity.com/id/n1t1337/", "icon": "/static/steam.png"},
    {"name": "AboutMe", "url": "https://guns.lol/n1t1337", "icon": "/static/aboutme.png"},
]


STEAM_CONSOLE_CODE = r"""// Вставь в консоль Steam (F12 → Console) на странице загрузки
// После этого выбирай файлы в нужном порядке
$J('#image_upload').attr('multiple','multiple');
console.log('Showcase Maker: multiple upload enabled');"""
