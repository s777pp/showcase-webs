"""Shared state and helpers for all routers.

Single source of truth for DATA (imported from auth_db), quotas, access codes,
auth and IP helpers. Routers import from here; main.py assembles the app and
mounts middleware.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

import auth_db
import redis_store as rs

LOGGER = logging.getLogger("sm")

ROOT = Path(__file__).resolve().parent.parent

# DATA is the single source of truth, shared with auth_db.
DATA = auth_db.DATA
JOBS = DATA / "jobs"
USAGE_FILE = DATA / "usage.json"
CODES_FILE_REPO = ROOT / "data" / "access_codes.json"
ACCESS_FILE = DATA / "access_codes.json"
STATIC = ROOT / "static"
TEMPLATES = ROOT / "templates"
FONTS = ROOT / "fonts"

for _d in (DATA, JOBS, STATIC):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        LOGGER.error("mkdir failed %s %s", _d, e)

# Pillow decompression-bomb guard. A malicious PNG can claim 200k x 200k pixels
# and OOM the worker. Any open() above this limit raises DecompressionBombError,
# which is translated to HTTP 400 (see main._unhandled and per-file error paths).
Image.MAX_IMAGE_PIXELS = int(os.environ.get("MAX_IMAGE_PIXELS", "100_000_000"))

FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "5"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "40"))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))
APP_VERSION = os.environ.get("APP_VERSION", "prod-opt-2")

# Stripe (optional). Without keys — access codes + unpaid accounts only.
STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
APP_URL = os.environ.get("APP_URL", f"http://{HOST}:{PORT}")
DA_CLIENT_ID = os.environ.get("DA_CLIENT_ID", "").strip()
DA_CLIENT_SECRET = os.environ.get("DA_CLIENT_SECRET", "").strip()
DA_REDIRECT_URI = os.environ.get("DA_REDIRECT_URI", "").strip()
PRO_PRICE_LABEL = os.environ.get("PRO_PRICE_LABEL", "Pro · безлимит")

# Bounded pool for heavy FFmpeg/gifski work.
MAX_JOB_WORKERS = max(1, int(os.environ.get("MAX_JOB_WORKERS") or 2))

# Daily limit for the anonymous/legacy path — uses the same counter.
SESSION_TTL_DAYS = int(os.environ.get("SESSION_TTL_DAYS", "90"))

USED_CODES_FILE = DATA / "used_codes.json"


def safe_data_path(stored: str, *, subdir: str = "") -> Path | None:
    """Resolve a DB-stored relative path inside DATA, or None if it escapes.

    Mirrors main._safe_data_path. The avatar / background readers used to build
    Path(stored) directly, so an absolute or traversing value in the row turned
    a public image URL into arbitrary file read.
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


# Profile columns a user may set. Excludes avatar_path / profile_background:
# those are written by the server after an upload, never chosen by the client.
PROFILE_EDITABLE_FIELDS = (
    "display_name", "profile_username", "profile_summary", "profile_location",
    "profile_status", "profile_visibility", "profile_level", "profile_xp",
    "profile_bg_x", "profile_bg_y", "profile_bg_scale", "profile_bg_overlay",
)


def setup_logging() -> None:
    level = (os.environ.get("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def _da_cfg() -> dict:
    """Read DA env at request time (after Railway injects vars)."""
    return {
        "id": (os.environ.get("DA_CLIENT_ID") or "").strip(),
        "secret": (os.environ.get("DA_CLIENT_SECRET") or "").strip(),
        "redirect": (os.environ.get("DA_REDIRECT_URI") or "").strip(),
    }


def _da_ready() -> tuple[bool, dict]:
    c = _da_cfg()
    return bool(c["id"] and c["secret"] and c["redirect"]), c


# ---- access codes ---------------------------------------------------------
# Sources, ascending priority:
#   ADMIN_ACCESS_CODE      — one admin key
#   data/access_codes.json — bundled list (trial codes carry {"type":"trial","hours":N})
#   ACCESS_CODES           — comma list (unlimited)
#   ACCESS_CODES_JSON      — JSON map, targeted additions
#   DATA/access_codes.json — volume file, overrides everything
DEFAULT_CODES: dict[str, dict] = {}
_admin_code = (os.environ.get("ADMIN_ACCESS_CODE") or "").strip().upper()
if _admin_code:
    DEFAULT_CODES[_admin_code] = {"type": "unlimited", "label": "Pro Admin"}


def _load_codes() -> dict:
    codes = dict(DEFAULT_CODES)
    if CODES_FILE_REPO.is_file():
        try:
            data = json.loads(CODES_FILE_REPO.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                codes.update({str(k).upper(): v for k, v in data.items()})
        except Exception as e:
            LOGGER.error("load codes %s: %s", CODES_FILE_REPO, e)
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
            LOGGER.error("load ACCESS_CODES_JSON: %s", e)
    if ACCESS_FILE.is_file():
        try:
            data = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                codes.update({str(k).upper(): v for k, v in data.items()})
        except Exception as e:
            LOGGER.error("load codes %s: %s", ACCESS_FILE, e)
    return codes


# ---- usage (legacy file fallback) ----------------------------------------
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


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _ip(req) -> str:
    """Client IP. With uvicorn --proxy-headers, request.client.host is already
    the first X-Forwarded-For hop — we deliberately do NOT re-parse XFF here,
    otherwise a client could spoof the header and reset their free quota."""
    return (req.client.host if req.client else None) or "unknown"


def _auth_user(req) -> dict | None:
    """User from X-Session-Token header or sm_session cookie."""
    tok = (req.headers.get("x-session-token") or "").strip()
    if not tok:
        tok = (req.cookies.get("sm_session") or "").strip()
    if not tok:
        return None
    return auth_db.user_by_token(tok)


def _gallery_admin_emails() -> set[str]:
    allowed = (os.environ.get("GALLERY_ADMIN_EMAILS") or "serhii.perepelytsia1510@gmail.com").lower()
    return {e.strip() for e in allowed.split(",") if e.strip()}


def is_gallery_admin(user: dict | None) -> bool:
    if not user:
        return False
    email = (user.get("email") or "").strip().lower()
    return email in _gallery_admin_emails()


def admin_ok(req) -> bool:
    """Constant-time check of the X-Admin-Secret header against ADMIN_SECRET."""
    secret = (os.environ.get("ADMIN_SECRET") or "").strip()
    got = (req.headers.get("x-admin-secret") or "").strip()
    if not secret:
        return False
    return bool(got) and secrets.compare_digest(secret, got)


def _attach_session_cookie(resp, token: str, request=None):
    """Persist login across pages. secure=True only on HTTPS."""
    secure = False
    if request is not None:
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
        secure = proto == "https"
    resp.set_cookie(
        key="sm_session",
        value=token,
        max_age=60 * 60 * 24 * SESSION_TTL_DAYS,
        path="/",
        httponly=False,
        samesite="lax",
        secure=secure,
    )
    return resp


def _clear_session_cookie(resp):
    resp.delete_cookie("sm_session", path="/")
    return resp


def quota_state(req) -> dict:
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


def quota_inc(req, n: int) -> None:
    ip = _ip(req)
    try:
        rs.quota_inc(ip, _day(), n)
    except Exception:
        pass
    user = _auth_user(req)
    if user and auth_db.effective_pro(user):
        return
    u = _usage.get(ip) or {"count": 0, "day": _day()}
    if u.get("day") != _day():
        u = {"count": 0, "day": _day()}
    u["count"] = int(u.get("count") or 0) + n
    _usage[ip] = u
    _save_usage(_usage)


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

FUNPAY_OFFER_URL = "https://funpay.com/lots/offer?id=75434891"
