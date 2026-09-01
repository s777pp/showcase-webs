#!/usr/bin/env python3
"""
Showcase Maker WEB — локальный / серверный прототип
Запуск:  python main.py
URL:     http://127.0.0.1:8080
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

ROOT = Path(__file__).resolve().parent
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


def _cleanup_old_jobs(max_age_sec: float = 120.0) -> int:
    """Delete job folders older than max_age_sec (default 2 minutes)."""
    import time as _time
    removed = 0
    try:
        if not JOBS.is_dir():
            return 0
        now = _time.time()
        for p in list(JOBS.iterdir()):
            try:
                if not p.is_dir():
                    # orphan files
                    if now - p.stat().st_mtime > max_age_sec:
                        p.unlink(missing_ok=True)
                        removed += 1
                    continue
                mtime = p.stat().st_mtime
                if now - mtime >= max_age_sec:
                    shutil.rmtree(p, ignore_errors=True)
                    removed += 1
            except Exception:
                continue
    except Exception as e:
        print("cleanup jobs:", e)
    return removed


def _cleanup_loop():
    import time as _time
    while True:
        try:
            n = _cleanup_old_jobs(120.0)
            if n:
                print(f"cleanup: removed {n} old job(s)")
        except Exception as e:
            print("cleanup loop:", e)
        _time.sleep(30)


# start background cleaner
try:
    import threading
    threading.Thread(target=_cleanup_loop, daemon=True, name="job-cleaner").start()
except Exception as e:
    print("cleanup thread:", e)


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



# ---- production middleware: request id + rate limits ----
import uuid as _uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("X-Request-ID") or _uuid.uuid4().hex[:16]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline security headers.

    docker-compose sets these in Nginx, but Railway runs the app with nothing
    in front of it, so in production nobody was sending them at all.

    The CSP is deliberately loose on inline script/style — the pages are HTML
    monoliths with inline handlers everywhere, and a strict policy would blank
    the whole UI. It still pins where scripts, frames and connections may come
    from, which is what stops an injected <script src> from calling out.
    """
    CSP = "; ".join((
        "default-src 'self'",
        # 'unsafe-inline'/'unsafe-eval' are required by the current inline JS.
        # telegram.org is the login widget, injected at runtime by sm-auth.js.
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://telegram.org",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob: https:",
        "media-src 'self' data: blob: https:",
        "connect-src 'self' https:",
        "frame-src https://telegram.org https://oauth.telegram.org",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'self'",
    ))

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "SAMEORIGIN")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        h.setdefault("Content-Security-Policy", self.CSP)
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
        if proto == "https":
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Light Redis/local rate limits on sensitive paths."""
    RULES = (
        ("/api/auth/login", 20, 60),
        ("/api/auth/register", 10, 60),
        # Guessing an access code was unlimited before: /api/unlock was simply
        # not on this list, so a script could try codes as fast as it liked.
        ("/api/unlock", 10, 60),
        # Wiping every account should not be reachable at machine speed even
        # with a leaked secret.
        ("/api/admin/", 5, 60),
        ("/api/process", 8, 60),
        ("/api/process/start", 8, 60),
        ("/api/gallery/", 60, 60),
        ("/api/download-url", 5, 60),
    )
    async def dispatch(self, request, call_next):
        path = request.url.path
        # Same IP source as the quota. This used to read request.client.host
        # directly, which behind a proxy is the PROXY's address — so every user
        # shared one bucket and a single client could lock login for everyone.
        client = _ip(request)
        for prefix, limit, window in self.RULES:
            if path.startswith(prefix) and request.method in ("POST", "PUT", "DELETE", "PATCH"):
                ok, _left = rs.rate_limit(f"{prefix}:{client}", limit, window)
                if not ok:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        {"ok": False, "msg": "Too many requests. Slow down."},
                        status_code=429,
                    )
                break
        return await call_next(request)


app = FastAPI(title="Showcase Maker Web")

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIdMiddleware)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
try:
    app.mount("/fonts", StaticFiles(directory=str(FONTS)), name="fonts")
except Exception:
    pass

@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    # Full detail to the logs, nothing to the client. Echoing str(exc) leaked
    # filesystem paths, SQL fragments and library internals to anyone who could
    # trigger an error. The request id ties a user report to the log line.
    rid = getattr(request.state, "request_id", "-")
    LOGGER.exception("unhandled error rid=%s path=%s", rid, request.url.path)
    # A too-large image is a client mistake, not a server fault — keep the 400
    # so the UI can still explain it.
    if isinstance(exc, (Image.DecompressionBombError, Image.DecompressionBombWarning)):
        return JSONResponse(
            {"ok": False, "msg": "Image is too large", "request_id": rid},
            status_code=400,
        )
    return JSONResponse(
        {"ok": False, "msg": "Internal error", "request_id": rid},
        status_code=500,
    )



@app.get("/", response_class=HTMLResponse)
def index():
    """Лендинг (как kant.tools)."""
    path = STATIC / "index.html"
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/app", response_class=HTMLResponse)
def app_page():
    """Рабочая панель инструментов."""
    path = STATIC / "app.html"
    if not path.is_file():
        path = STATIC / "index.html"
    return HTMLResponse(path.read_text(encoding="utf-8"))





@app.get("/profile", response_class=HTMLResponse)
@app.get("/profile/", response_class=HTMLResponse)
async def profile_me(request: Request):
    """Owner shortcut → /profile/{username} or login prompt page."""
    user = _auth_user(request)
    p = Path(__file__).parent / "static" / "profile.html"
    if not p.is_file():
        return HTMLResponse("profile.html missing", status_code=404)
    html = p.read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/profile/{username}", response_class=HTMLResponse)
async def profile_public(username: str, request: Request):
    """Public full-page profile (not the editor)."""
    p = Path(__file__).parent / "static" / "profile-view.html"
    if not p.is_file():
        p = Path(__file__).parent / "static" / "profile.html"
    if not p.is_file():
        return HTMLResponse("profile page missing", status_code=404)
    return HTMLResponse(p.read_text(encoding="utf-8"))


@app.get("/api/profile/me")
def api_profile_me(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    un = auth_db.ensure_profile_username(int(user["id"]), user.get("display_name"))
    prof = auth_db.get_public_profile(un)
    if not prof:
        return JSONResponse({"ok": False, "msg": "Profile not found"}, status_code=404)
    av = prof.get("avatar_path") or ""
    av_url = f"/api/auth/avatar/{prof['id']}" if av else ""
    bg = prof.get("profile_background") or ""
    bg_url = f"/api/profile/bg/{prof['id']}" if bg else ""
    return {
        "ok": True,
        "is_owner": True,
        "profile": {
            **{k: v for k, v in prof.items() if k != "email"},
            "avatar_url": av_url,
            "background_url": bg_url,
            "username": un,
        },
    }


@app.get("/api/profile/{username}")
def api_profile_get(username: str, request: Request):
    prof = auth_db.get_public_profile(username)
    if not prof:
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    viewer = _auth_user(request)
    is_owner = bool(viewer and int(viewer["id"]) == int(prof["id"]))
    vis = (prof.get("profile_visibility") or "public").lower()
    if vis == "private" and not is_owner:
        return JSONResponse({"ok": False, "msg": "Private profile"}, status_code=403)
    av = prof.get("avatar_path") or ""
    av_url = f"/api/auth/avatar/{prof['id']}" if av else ""
    bg = prof.get("profile_background") or ""
    bg_url = f"/api/profile/bg/{prof['id']}" if bg else ""
    steam_snap = None
    try:
        steam_snap = auth_db.get_steam_profile_snapshot(int(prof["id"]))
    except Exception:
        steam_snap = None
    showcases = []
    try:
        showcases = auth_db.profile_showcase_list(int(prof["id"]))
    except Exception:
        showcases = []
    return {
        "ok": True,
        "is_owner": is_owner,
        "profile": {
            **{k: v for k, v in prof.items() if k != "email"},
            "avatar_url": av_url,
            "background_url": bg_url,
            "username": prof.get("profile_username"),
            "steam": steam_snap,
            "showcases": showcases,
        },
    }


@app.post("/api/profile/update")
async def api_profile_update(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    auth_db.ensure_profile_username(int(user["id"]), user.get("display_name"))
    ct = (request.headers.get("content-type") or "").lower()
    fields: dict = {}
    try:
        if "multipart/form-data" in ct:
            form = await request.form()
            for key in PROFILE_EDITABLE_FIELDS:
                if key in form and form.get(key) is not None:
                    fields[key] = form.get(key)
            bgf = form.get("background")
            if bgf is not None and hasattr(bgf, "read"):
                raw = await bgf.read()
                if raw and len(raw) < 12_000_000:
                    name = getattr(bgf, "filename", "") or "bg.png"
                    ext = Path(str(name)).suffix.lower()
                    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                        ext = ".png"
                    bg_dir = Path(DATA) / "profile_bg"
                    bg_dir.mkdir(parents=True, exist_ok=True)
                    # clean old
                    for old in bg_dir.glob(f"{user['id']}.*"):
                        try: old.unlink()
                        except Exception: pass
                    dest = bg_dir / f"{user['id']}{ext}"
                    dest.write_bytes(raw)
                    fields["profile_background"] = f"profile_bg/{user['id']}{ext}"
        else:
            body = await request.json()
            if isinstance(body, dict):
                # Same whitelist as the multipart branch. This used to be
                # `fields = body`, which handed the caller every column
                # update_steam_profile accepts — including avatar_path and
                # profile_background, i.e. arbitrary file read via the image
                # endpoints that serve them.
                fields = {k: body[k] for k in PROFILE_EDITABLE_FIELDS if k in body}
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=400)
    ok, msg = auth_db.update_steam_profile(int(user["id"]), **fields)
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    un = auth_db.ensure_profile_username(int(user["id"]))
    return {"ok": True, "msg": msg, "username": un}


@app.get("/api/profile/bg/{user_id}")
def api_profile_bg(user_id: int):
    c = auth_db._conn()
    row = c.execute("SELECT profile_background FROM users WHERE id=?", (user_id,)).fetchone()
    c.close()
    if not row or not row["profile_background"]:
        return JSONResponse({"ok": False}, status_code=404)
    stored = str(row["profile_background"])
    # Containment check: "../../etc/passwd" stored here used to escape DATA.
    path = _safe_data_path(stored)
    if path is None:
        path = _safe_data_path(Path(stored).name, subdir="profile_bg")
    if path is None:
        return JSONResponse({"ok": False}, status_code=404)
    media = "image/png"
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"): media = "image/jpeg"
    elif s == ".webp": media = "image/webp"
    elif s == ".gif": media = "image/gif"
    elif s == ".mp4": media = "video/mp4"
    elif s == ".webm": media = "video/webm"
    elif s == ".mov": media = "video/quicktime"
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type=media)


@app.get("/api/profile/{username}/showcases")
def api_profile_showcases(username: str, request: Request):
    prof = auth_db.get_public_profile(username)
    if not prof:
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    viewer = _auth_user(request)
    is_owner = bool(viewer and int(viewer["id"]) == int(prof["id"]))
    vis = (prof.get("profile_visibility") or "public").lower()
    if vis == "private" and not is_owner:
        return JSONResponse({"ok": False, "msg": "Private"}, status_code=403)
    items = auth_db.profile_showcase_list(int(prof["id"]))
    # resolve file URLs
    for it in items:
        files = (it.get("data") or {}).get("files") or []
        urls = []
        for f in files:
            urls.append(f"/api/profile/file/{prof['id']}/{Path(str(f)).name}")
        it["urls"] = urls
    return {"ok": True, "showcases": items, "is_owner": is_owner}


@app.get("/api/profile/my-library")
def api_profile_library(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    items = auth_db.gallery_list_for_user(int(user["id"]), 80)
    out = []
    for g in items:
        out.append({
            "id": g["id"],
            "title": g.get("title") or "",
            "mode": g.get("mode") or "",
            "status": g.get("status") or "",
            "url": f"/api/gallery/image/{g['id']}" if g.get("image_path") else "",
        })
    return {"ok": True, "items": out}


@app.post("/api/profile/showcase/add")
async def api_profile_showcase_add(request: Request):
    """Add showcase: type=featured|artwork|workshop|split, optional file upload or gallery_id.
    Workshop/Split: one image is auto-sliced via processor.
    """
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    uid = int(user["id"])
    auth_db.ensure_profile_username(uid, user.get("display_name"))
    form = await request.form()
    sc_type = str(form.get("type") or "featured").strip().lower()
    if sc_type not in ("featured", "artwork", "workshop", "split"):
        return JSONResponse({"ok": False, "msg": "Invalid type"}, status_code=400)
    if sc_type == "workshop":
        existing = [s for s in auth_db.profile_showcase_list(uid) if s.get("type") == "workshop"]
        # one Workshop block on profile; it holds up to 3 rows (3 source images)
        if len(existing) >= 1:
            return JSONResponse({"ok": False, "msg": "Workshop showcase already exists — remove it to upload a new set (up to 3 images)"}, status_code=400)
    title = str(form.get("title") or sc_type)[:80]
    out_dir = Path(DATA) / "profile_sc" / str(uid)
    out_dir.mkdir(parents=True, exist_ok=True)
    import tempfile
    import shutil
    import processor as proc

    files_saved: list[str] = []
    # collect uploaded files
    uploads = []
    for k, v in form.multi_items():
        if str(k) in ("file", "files") or str(k).startswith("file"):
            if v is not None and hasattr(v, "read"):
                uploads.append(v)

    gallery_id = form.get("gallery_id")
    if gallery_id and not uploads:
        try:
            gid = int(gallery_id)
            g = auth_db.gallery_get(gid)
            if g and int(g.get("user_id") or 0) == uid and g.get("image_path"):
                src = Path(DATA) / str(g["image_path"])
                if src.is_file():
                    class _F:
                        filename = src.name
                        async def read(self, _p=src):
                            return _p.read_bytes()
                    uploads.append(_F())
        except Exception as e:
            print("gallery pull", e)

    if not uploads:
        return JSONResponse({"ok": False, "msg": "Upload a file or pick from library"}, status_code=400)

    try:
        raw0 = await uploads[0].read()
        name0 = getattr(uploads[0], "filename", None) or "img.png"
        tmp = Path(tempfile.mkdtemp(prefix="psc_"))
        src_path = tmp / Path(str(name0)).name
        src_path.write_bytes(raw0)
        ts = str(int(time.time()))
        work = tmp / "out"
        work.mkdir()

        from PIL import Image as PILImage

        def _save_dict(out_map: dict):
            for fname, blob in out_map.items():
                if not isinstance(blob, (bytes, bytearray)):
                    continue
                if not str(fname).lower().endswith((".png", ".gif", ".jpg", ".jpeg", ".webp")):
                    continue
                dest = out_dir / f"{ts}_{Path(str(fname)).name}"
                dest.write_bytes(bytes(blob))
                files_saved.append(dest.name)

        VID_EXT = {".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"}
        GIF_EXT = {".gif"}
        IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

        def _ext_of(nm: str) -> str:
            return Path(str(nm)).suffix.lower() or ".png"

        def _copy_named(src: Path, row_i: int, part_name: str) -> str:
            """Copy processor output into profile_sc with stable name …_rN_pM.ext"""
            # part_1.gif → p1
            m = None
            import re as _re
            m = _re.match(r"part_(\d+)\.", part_name, _re.I)
            if m:
                fname = f"{ts}_r{row_i}_p{m.group(1)}{src.suffix.lower()}"
            elif "center" in part_name.lower():
                fname = f"{ts}_r{row_i}_center{src.suffix.lower()}"
            elif "side" in part_name.lower():
                fname = f"{ts}_r{row_i}_side{src.suffix.lower()}"
            elif "featured" in part_name.lower():
                fname = f"{ts}_r{row_i}_featured{src.suffix.lower()}"
            else:
                fname = f"{ts}_r{row_i}_{src.name}"
            dest = out_dir / fname
            dest.write_bytes(src.read_bytes())
            return fname

        if sc_type == "workshop":
            # Up to 3 sources → each becomes a row of 5 parts (PNG or GIF)
            try:
                sources = [(name0, raw0)]
                for extra in uploads[1:3]:
                    try:
                        raw = await extra.read()
                        nm = getattr(extra, "filename", None) or "img.png"
                        if raw:
                            sources.append((nm, raw))
                    except Exception:
                        pass
                row_i = 0
                for nm, raw in sources[:3]:
                    row_i += 1
                    ext = _ext_of(nm)
                    sp = tmp / f"src_{row_i}{ext}"
                    sp.write_bytes(raw)
                    work = tmp / f"work_{row_i}"
                    work.mkdir(exist_ok=True)

                    if ext in VID_EXT:
                        if not proc.find_ffmpeg():
                            raise RuntimeError("FFmpeg required for video")
                        paths = proc.process_video_workshop(
                            sp, work, fps=12, width=750, wm_text="", wm_opacity=0.0, duration=12,
                        )
                        for pname, ppath in paths.items():
                            if not str(pname).startswith("part_"):
                                continue
                            if Path(ppath).is_file():
                                files_saved.append(_copy_named(Path(ppath), row_i, pname))
                    elif ext in GIF_EXT:
                        if proc.find_ffmpeg():
                            paths = proc.process_gif_workshop(
                                sp, work, wm_text="", wm_opacity=0.0,
                            )
                            for pname, ppath in paths.items():
                                if not str(pname).startswith("part_"):
                                    continue
                                if Path(ppath).is_file():
                                    files_saved.append(_copy_named(Path(ppath), row_i, pname))
                        else:
                            # fallback: first frame PNG crop
                            from PIL import Image as _PIL
                            import io as _io
                            im = _PIL.open(_io.BytesIO(raw))
                            im.seek(0)
                            frame = im.convert("RGBA")
                            w, h = frame.size
                            pw = max(1, w // 5)
                            for pi in range(5):
                                left = pi * pw
                                right = (pi + 1) * pw if pi < 4 else w
                                part = frame.crop((left, 0, right, h))
                                buf = _io.BytesIO()
                                part.save(buf, format="PNG")
                                fname = f"{ts}_r{row_i}_p{pi+1}.png"
                                (out_dir / fname).write_bytes(buf.getvalue())
                                files_saved.append(fname)
                    else:
                        # static image — pure PIL 5-crop PNG
                        from PIL import Image as _PIL
                        import io as _io
                        im = _PIL.open(_io.BytesIO(raw)).convert("RGBA")
                        w, h = im.size
                        if w < 5:
                            continue
                        pw = w // 5
                        for pi in range(5):
                            left = pi * pw
                            right = (pi + 1) * pw if pi < 4 else w
                            part = im.crop((left, 0, right, h))
                            buf = _io.BytesIO()
                            part.save(buf, format="PNG", optimize=True)
                            fname = f"{ts}_r{row_i}_p{pi+1}.png"
                            (out_dir / fname).write_bytes(buf.getvalue())
                            files_saved.append(fname)
                if not files_saved:
                    shutil.rmtree(tmp, ignore_errors=True)
                    return JSONResponse({"ok": False, "msg": "Workshop produced no files"}, status_code=500)
            except Exception as e:
                shutil.rmtree(tmp, ignore_errors=True)
                return JSONResponse({"ok": False, "msg": f"Workshop process failed: {e}"}, status_code=500)

        elif sc_type == "split":
            try:
                ext = _ext_of(name0)
                work = tmp / "work_split"
                work.mkdir(exist_ok=True)
                if ext in VID_EXT:
                    if not proc.find_ffmpeg():
                        raise RuntimeError("FFmpeg required for video")
                    paths = proc.process_video_split(src_path, work, fps=12, wm_text="", wm_opacity=0.0)
                    for pname, ppath in paths.items():
                        if Path(ppath).is_file() and ("center" in pname or "side" in pname or pname.startswith("part")):
                            files_saved.append(_copy_named(Path(ppath), 1, pname))
                elif ext in GIF_EXT and proc.find_ffmpeg():
                    paths = proc.process_gif_split(src_path, work, fps=12, wm_text="", wm_opacity=0.0)
                    for pname, ppath in paths.items():
                        if Path(ppath).is_file() and ("center" in pname or "side" in pname):
                            files_saved.append(_copy_named(Path(ppath), 1, pname))
                else:
                    im = PILImage.open(src_path).convert("RGBA")
                    _save_dict(proc.process_image_split(im, wm_text="", wm_opacity=0))
                    # rename saved to center/side labels if needed
                    # _save_dict already used ts_ prefix
            except Exception as e:
                shutil.rmtree(tmp, ignore_errors=True)
                return JSONResponse({"ok": False, "msg": f"Split process failed: {e}"}, status_code=500)

        elif sc_type == "featured":
            try:
                ext = _ext_of(name0)
                work = tmp / "work_feat"
                work.mkdir(exist_ok=True)
                if ext in VID_EXT:
                    if not proc.find_ffmpeg():
                        raise RuntimeError("FFmpeg required for video")
                    paths = proc.process_video_featured(src_path, work, fps=12, wm_text="", wm_opacity=0.0)
                    for pname, ppath in paths.items():
                        if Path(ppath).is_file() and ("featured" in pname or "full_original" in pname):
                            files_saved.append(_copy_named(Path(ppath), 1, pname))
                elif ext in GIF_EXT and proc.find_ffmpeg():
                    paths = proc.process_gif_featured(src_path, work, fps=12, wm_text="", wm_opacity=0.0)
                    for pname, ppath in paths.items():
                        if Path(ppath).is_file() and ("featured" in pname or "full_original" in pname):
                            files_saved.append(_copy_named(Path(ppath), 1, pname))
                else:
                    im = PILImage.open(src_path).convert("RGBA")
                    _save_dict(proc.process_image_featured(im, wm_text="", wm_opacity=0))
            except Exception as e:
                print("featured process", e)
                dest = out_dir / f"{ts}_featured{src_path.suffix or '.png'}"
                dest.write_bytes(raw0)
                files_saved.append(dest.name)

        else:  # artwork — store as-is (image/gif/video file)
            dest = out_dir / f"{ts}_art{Path(str(name0)).suffix or '.png'}"
            dest.write_bytes(raw0)
            files_saved.append(dest.name)
            for extra in uploads[1:]:
                try:
                    raw = await extra.read()
                    nm = getattr(extra, "filename", None) or "extra.png"
                    d2 = out_dir / f"{ts}_{Path(str(nm)).name}"
                    d2.write_bytes(raw)
                    files_saved.append(d2.name)
                except Exception:
                    pass

        shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

    if not files_saved:
        return JSONResponse({"ok": False, "msg": "No output files"}, status_code=500)

    sid = auth_db.profile_showcase_add(uid, sc_type, title, {"files": files_saved})
    return {"ok": True, "id": sid, "files": files_saved, "type": sc_type}


@app.post("/api/profile/showcase/delete")
async def api_profile_showcase_delete(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    body = await request.json()
    sid = int(body.get("id") or 0)
    ok = auth_db.profile_showcase_delete(int(user["id"]), sid)
    return {"ok": ok}


@app.get("/api/profile/file/{user_id}/{name}")
def api_profile_file(user_id: int, name: str):
    name = Path(name).name
    path = Path(DATA) / "profile_sc" / str(user_id) / name
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    media = "image/png"
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"): media = "image/jpeg"
    elif s == ".webp": media = "image/webp"
    elif s == ".gif": media = "image/gif"
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type=media)


@app.post("/api/auth/register")
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


@app.post("/api/auth/login")
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


@app.post("/api/admin/wipe-users")
async def admin_wipe_users(request: Request):
    """Delete all accounts. Requires header X-Admin-Secret = ADMIN_SECRET env."""
    if not _admin_ok(request):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    n = auth_db.wipe_all_users()
    return JSONResponse({"ok": True, "deleted": n})



@app.post("/api/auth/profile")
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
                    av_dir = Path(DATA) / "avatars"
                    av_dir.mkdir(parents=True, exist_ok=True)
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
                    # remove old avatar files for this user
                    for old in av_dir.glob(f"{user['id']}.*"):
                        try:
                            old.unlink(missing_ok=True)
                        except Exception:
                            pass
                    path = av_dir / f"{user['id']}{ext}"
                    path.write_bytes(raw)
                    # store relative path so it survives DATA absolute path changes
                    avatar_saved = f"avatars/{user['id']}{ext}"
        else:
            body = await request.json()
            display_name = str(body.get("display_name") or "")
        auth_db.update_profile(
            int(user["id"]),
            display_name=display_name,
            avatar_path=avatar_saved,
        )
        av_url = f"/api/auth/avatar/{user['id']}" if (avatar_saved or user.get("avatar_path")) else ""
        if not av_url:
            av_dir = Path(DATA) / "avatars"
            if av_dir.is_dir() and list(av_dir.glob(f"{user['id']}.*")):
                av_url = f"/api/auth/avatar/{user['id']}"
        return {
            "ok": True,
            "msg": "Profile updated",
            "display_name": (display_name or "").strip()[:40],
            "avatar_url": av_url,
        }
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"{type(e).__name__}: {e}"}, status_code=500)


@app.get("/api/auth/avatar/{user_id}")
def auth_avatar(user_id: int):
    c = auth_db._conn()
    row = c.execute("SELECT avatar_path FROM users WHERE id=?", (user_id,)).fetchone()
    c.close()
    stored = ""
    if row and row["avatar_path"]:
        stored = str(row["avatar_path"]).strip()
    # Always resolve INSIDE DATA. The stored value was once used as an absolute
    # path, which made this public endpoint read any file on the box.
    path = _safe_data_path(stored) if stored else None
    if path is None:
        av_dir = Path(DATA) / "avatars"
        matches = sorted(av_dir.glob(f"{int(user_id)}.*")) if av_dir.is_dir() else []
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


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    tok = (request.headers.get("x-session-token") or "").strip()
    if not tok:
        tok = (request.cookies.get("sm_session") or "").strip()
    if tok:
        auth_db.logout(tok)
    resp = JSONResponse({"ok": True})
    _clear_session_cookie(resp)
    return resp


@app.get("/api/auth/me")
def auth_me(request: Request):
    user = _auth_user(request)
    if not user:
        return {"ok": False, "logged_in": False}
    av = user.get("avatar_path") or ""
    av_url = ""
    if av:
        av_url = f"/api/auth/avatar/{user['id']}"
    else:
        # fallback if path was lost but file remains on disk
        av_dir = Path(DATA) / "avatars"
        if av_dir.is_dir() and list(av_dir.glob(f"{user['id']}.*")):
            av_url = f"/api/auth/avatar/{user['id']}"
    return {
        "ok": True,
        "logged_in": True,
        "email": user["email"],
        "is_pro": auth_db.effective_pro(user),
        "pro_until": user.get("pro_until"),
        "pro_code": user.get("pro_code") or "",
        "display_name": user.get("display_name") or "",
        "avatar_url": av_url,
        "is_gallery_admin": _is_gallery_admin(user),
    }


@app.post("/api/billing/checkout")
async def billing_checkout(request: Request):
    """Покупка Pro — редирект на FunPay (ключ активируется на сайте)."""
    # не требуем логин: можно купить и потом ввести код
    return {
        "ok": True,
        "url": "https://funpay.com/lots/offer?id=75434891",
        "msg": "FunPay",
    }


@app.post("/api/billing/webhook")
async def billing_webhook(request: Request):
    """Stripe webhook: checkout.session.completed → is_pro=1."""
    if not STRIPE_SECRET:
        return JSONResponse({"ok": False}, status_code=503)
    # No signing secret means no way to tell Stripe from anyone else. The old
    # fallback parsed the body unverified, so a hand-written POST claiming
    # checkout.session.completed granted Pro to any user_id. Fail closed.
    if not STRIPE_WEBHOOK_SECRET:
        LOGGER.error("billing webhook: STRIPE_WEBHOOK_SECRET unset, refusing unverified event")
        return JSONResponse(
            {"ok": False, "msg": "Webhook not configured"}, status_code=503
        )
    import stripe
    stripe.api_key = STRIPE_SECRET
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        LOGGER.warning("billing webhook rejected: %s", e)
        return JSONResponse({"ok": False, "msg": "Invalid signature"}, status_code=400)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        uid = (session.get("metadata") or {}).get("user_id")
        if uid:
            try:
                auth_db.set_pro(int(uid), True)
            except Exception:
                pass
    return {"ok": True}


@app.get("/api/ready")
def api_ready():
    """Readiness: DB must answer."""
    try:
        auth_db._conn().execute("SELECT 1")
        return {"ok": True}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse({"ok": False}, status_code=503)

@app.get("/api/health")
def api_health_prod():
    db_ok = True
    try:
        auth_db._conn().execute("SELECT 1")
    except Exception:
        db_ok = False
    try:
        redis_ok = rs.redis_ok()
    except Exception:
        redis_ok = False
    mode = _worker_mode()
    # writability, not just readability: a readonly volume still answers SELECT 1,
    # which is why the old db:true hid the "readonly database" failure entirely.
    db_writable = False
    db_write_error = None
    try:
        c = auth_db._conn()
        c.execute("CREATE TABLE IF NOT EXISTS _health_probe (id INTEGER PRIMARY KEY)")
        c.commit()
        c.close()
        db_writable = True
    except Exception as e:
        db_write_error = f"{type(e).__name__}: {e}"
    ff = None
    gs = None
    try:
        ff = proc.find_ffmpeg()
    except Exception:
        ff = None
    try:
        gs = proc.find_gifski() if hasattr(proc, "find_gifski") else None
    except Exception:
        gs = None
    return {
        "ok": True,
        "db": db_ok,
        "storage": {
            "dir": str(DATA),
            "writable": auth_db.DATA_WRITABLE,
            "error": auth_db.DATA_ERROR,
            "db_path": str(auth_db.DB),
            "db_writable": db_writable,
            "db_write_error": db_write_error,
        },
        "redis": redis_ok,
        # why Redis is down — the old endpoint only ever said "false"
        "redis_detail": {
            "configured": rs.configured(),
            "ok": redis_ok,
            "host": rs.redis_host(),
            "error": rs.last_error(),
        },
        "worker": {
            "mode": mode,
            "external_alive": rs.worker_alive() if redis_ok else False,
            "max_concurrent": MAX_JOB_WORKERS,
            "queue": rs.queue_depth() if redis_ok else 0,
        },
        "ffmpeg": bool(ff),
        "gifski": bool(gs),
        "ffmpeg_path": ff or None,
        "gifski_path": gs or None,
        "version": "prod-opt-2",
    }

@app.get("/api/health_legacy")

def health():
    ff = proc.find_ffmpeg()
    gs = proc.find_gifski() if hasattr(proc, "find_gifski") else None
    return {
        "ok": True,
        "ffmpeg": bool(ff),
        "gifski": bool(gs),
        "ffmpeg_path": ff or None,
        "gifski_path": gs or None,
        "fonts": [f.name for f in FONTS.glob("*.ttf")] if FONTS.is_dir() else [],
        "templates": [f.name for f in TEMPLATES.glob("*.png")] if TEMPLATES.is_dir() else [],
    }


@app.get("/api/quota")
def api_quota(request: Request):
    return quota_state(request)


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


@app.post("/api/unlock")
async def unlock(request: Request):
    """Activate Pro code — must be logged in. Key is bound to the account."""
    body = await request.json()
    code = str(body.get("code") or "").strip().upper().replace(" ", "")
    user = _auth_user(request)
    if not user or not user.get("id"):
        return JSONResponse(
            {"ok": False, "msg": "Log in first, then activate the code on your account"},
            status_code=401,
        )
    codes = _load_codes()
    if code not in codes:
        return JSONResponse({"ok": False, "msg": "Invalid access code"}, status_code=400)
    # already Pro on this account
    if user.get("is_pro"):
        return {"ok": True, "label": "Pro", "msg": "Already Pro on this account"}
    # one-time codes
    used_uid = auth_db.code_used(code)
    if used_uid is not None:
        return JSONResponse({"ok": False, "msg": "Code already used"}, status_code=400)
    # legacy file used_codes.json
    used = _load_used()
    if code.startswith("SM-WEB-") and code in used:
        return JSONResponse({"ok": False, "msg": "Code already used"}, status_code=400)

    meta = codes[code] if isinstance(codes.get(code), dict) else {"type": "unlimited", "label": "Pro"}
    ctype = str(meta.get("type") or "unlimited")
    hours = float(meta.get("hours") or 0)
    label = str(meta.get("label") or "Pro")
    until = None
    if ctype == "trial" and hours > 0:
        until = time.time() + hours * 3600
    auth_db.set_pro(int(user["id"]), True, code=code, until=until)
    auth_db.mark_code_used(code, int(user["id"]))
    if code.startswith("SM-WEB-") or code.startswith("SM-TRIAL-"):
        used.add(code)
        _save_used(used)
    msg = "Pro activated on your account"
    if until:
        msg = f"Trial activated for {int(hours)} hours"
    return {"ok": True, "label": label, "msg": msg, "until": until}


SOCIALS = [
    {"name": "Discord", "url": "https://discord.gg/me48dhgcw4", "icon": "/static/discord.png"},
    {"name": "TikTok", "url": "https://www.tiktok.com/@n1t1337", "icon": "/static/tiktok.png"},
    {"name": "YouTube", "url": "https://www.youtube.com/@n1t1337", "icon": "/static/youtube.png"},
    {"name": "Steam", "url": "https://steamcommunity.com/id/n1t1337/", "icon": "/static/steam.png"},
    {"name": "AboutMe", "url": "https://guns.lol/n1t1337", "icon": "/static/aboutme.png"},
]


@app.get("/api/meta")
def meta():
    return {
        "socials": SOCIALS,
        "buy_url": "https://funpay.com/lots/offer?id=75434891",
        "stripe_enabled": bool(STRIPE_SECRET and STRIPE_PRICE_ID),
        "pro_label": PRO_PRICE_LABEL,
        "modes": [
            {"id": "workshop", "title": "Workshop", "desc": "5 частей для витрины мастерской"},
            {"id": "featured", "title": "Featured", "desc": "630 px Featured Artwork"},
            {"id": "split", "title": "Artwork Split", "desc": "Центр 506 + бок 100"},
        ],
        "fonts": ["rob", "lap", "caratte", "Fineday", "roboto", "gothic-rus"],
        "steam_code": STEAM_CONSOLE_CODE,
    }


STEAM_CONSOLE_CODE = r"""// Вставь в консоль Steam (F12 → Console) на странице загрузки
// После этого выбирай файлы в нужном порядке
$J('#image_upload').attr('multiple','multiple');
console.log('Showcase Maker: multiple upload enabled');"""



# ====================== Async process jobs (real progress) ======================
_process_jobs: dict[str, dict] = {}
_process_jobs_lock = __import__("threading").Lock()

# Bounded pool for heavy FFmpeg/gifski work. Raw threads let N parallel GIF
# encodes saturate the CPU and stall the API for everyone else.
MAX_JOB_WORKERS = max(1, int(os.environ.get("MAX_JOB_WORKERS") or 2))
_job_pool = ThreadPoolExecutor(max_workers=MAX_JOB_WORKERS, thread_name_prefix="job")


def _worker_mode() -> str:
    """'embedded' (default) — process in this container's pool.
    'external'  — a separate worker.py process drains the Redis queue.

    Default is embedded: on Railway there is only one service, so an enqueued
    job would otherwise sit in the queue with nobody to pop it.
    """
    m = (os.environ.get("WORKER_MODE") or "").strip().lower()
    if m in ("embedded", "external"):
        return m
    # back-compat: USE_EXTERNAL_WORKER=1 used to mean "an external worker exists"
    if (os.environ.get("USE_EXTERNAL_WORKER") or "0").lower() in ("1", "true", "yes", "on"):
        return "external"
    return "embedded"


def _job_set(jid: str, **kw) -> None:
    with _process_jobs_lock:
        j = _process_jobs.get(jid) or {}
        j.update(kw)
        j["updated"] = time.time()
        _process_jobs[jid] = j
    try:
        rs.job_update(jid, **kw)  # upsert; shared source of truth
    except Exception:
        pass


def _job_get(jid: str) -> dict | None:
    """Redis first: the job may have been produced by another uvicorn worker or by
    the external worker process, in which case this process's dict knows nothing
    about it (or is frozen at 'queued'). Local dict is the offline fallback."""
    try:
        shared = rs.job_get(jid)
    except Exception:
        shared = None
    with _process_jobs_lock:
        local = _process_jobs.get(jid)
        local = dict(local) if local else None
    if shared:
        if local:
            local.update(shared)
            return local
        return shared
    return local


def _job_cleanup_old(max_age: float = 600.0) -> None:
    now = time.time()
    with _process_jobs_lock:
        dead = [k for k, v in _process_jobs.items() if now - float(v.get("updated") or 0) > max_age]
        for k in dead:
            j = _process_jobs.pop(k, None)
            if j and j.get("zip_path"):
                try:
                    Path(j["zip_path"]).unlink(missing_ok=True)
                except Exception:
                    pass
            if j and j.get("job_dir"):
                try:
                    shutil.rmtree(j["job_dir"], ignore_errors=True)
                except Exception:
                    pass




def _run_process_job_from_payload(jid: str, job: dict) -> None:
    """Worker entry: job must contain files_data (list of [name, path]) and opts."""
    import redis_store as _rs
    files_data = []
    for item in job.get("files") or []:
        name = item.get("name") or "file"
        path = item.get("path")
        if path and Path(path).is_file():
            files_data.append((name, Path(path).read_bytes()))
    opts = job.get("opts") or {}
    if not files_data:
        _rs.job_update(jid, status="error", pct=100, stage="error", error="No files")
        return
    # Reuse existing runner if present
    try:
        _run_process_job(jid, files_data, opts)
    except TypeError:
        # if signature differs, mark error
        _rs.job_update(jid, status="error", pct=100, stage="error", error="Worker incompatible")
        raise
    # No explicit sync needed: _run_process_job writes through _job_set, which
    # upserts into Redis on every progress step.


def _run_process_job(jid: str, files_data: list[tuple[str, bytes]], opts: dict) -> None:
    """Background worker: same pipeline as /api/process, updates progress."""
    import tempfile
    job_dir = Path(tempfile.mkdtemp(prefix="sm_job_"))
    _job_set(jid, status="running", pct=5, stage="prepare", job_dir=str(job_dir), error=None)
    zip_buf = io.BytesIO()
    processed = 0
    errors: list[str] = []
    listed: list[dict] = []
    modes = opts["modes"]
    text = opts["text"]
    opacity = opts["opacity"]
    color = opts["color"]
    corner = opts["corner"]
    scale = opts["scale"]
    wm_x_f = opts["wm_x"]
    wm_y_f = opts["wm_y"]
    do_ac = opts["do_ac"]
    size_i = opts["size_i"]
    fps = opts["fps"]
    enc = opts["enc"]
    n_files = max(1, len(files_data))
    try:
        zf = zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED)
        for fi, (name, raw) in enumerate(files_data):
            base_pct = 8 + int(80 * fi / n_files)
            _job_set(jid, pct=base_pct, stage=f"file:{name}")
            try:
                if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
                    errors.append(f"{name}: >{MAX_UPLOAD_MB}MB")
                    continue
                ext = Path(name).suffix.lower()
                stem = Path(name).stem[:40]
                if ext not in (
                    ".png", ".jpg", ".jpeg", ".webp", ".bmp",
                    ".gif", ".mp4", ".mov", ".webm", ".avi", ".mkv",
                ):
                    errors.append(f"{name}: unsupported format")
                    continue
                for mi, mode in enumerate(modes):
                    folder = f"{stem}_{mode}"
                    work = job_dir / folder
                    work.mkdir(exist_ok=True)
                    stage = "image" if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp") else (
                        "video" if ext in (".mp4", ".mov", ".webm", ".avi", ".mkv") else "gif"
                    )
                    _job_set(
                        jid,
                        pct=min(90, base_pct + int(12 * (mi + 1) / max(1, len(modes)))),
                        stage=f"{stage}:{mode}:{name}",
                    )
                    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                        img = Image.open(io.BytesIO(raw))
                        img.load()
                        max_side = 4096
                        if max(img.size) > max_side:
                            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                        if do_ac:
                            from PIL import ImageOps
                            rgb = img.convert("RGB")
                            rgb = ImageOps.autocontrast(rgb, cutoff=1)
                            img = rgb
                        if mode == "workshop" and img.size[0] != size_i:
                            nh = max(1, int(img.size[1] * (size_i / max(1, img.size[0]))))
                            img = img.resize((size_i, nh), Image.Resampling.LANCZOS)
                        if mode == "workshop":
                            parts = proc.process_image_workshop(
                                img, text, opts["wm_font"], opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        elif mode == "featured":
                            parts = proc.process_image_featured(
                                img, text, opts["wm_font"], opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        else:
                            parts = proc.process_image_split(
                                img, text, opts["wm_font"], opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        for pname, data in parts.items():
                            zf.writestr(f"{folder}/{pname}", data)
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/{pname}", "size": len(data)})
                    else:
                        src = work / f"source{ext}"
                        src.write_bytes(raw)
                        is_video = ext in (".mp4", ".mov", ".webm", ".avi", ".mkv")
                        v_fps = min(int(fps), 12)
                        v_dur = 8.0
                        encoder = enc
                        if encoder == "pillow":
                            encoder = "ffmpeg"
                        if is_video:
                            if not proc.find_ffmpeg():
                                raise RuntimeError("FFmpeg not available")
                            if mode == "workshop":
                                paths = proc.process_video_workshop(
                                    src, work, fps=v_fps, width=size_i,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity, wm_color=color,
                                    duration=v_dur, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=encoder,
                                )
                            elif mode == "featured":
                                paths = proc.process_video_featured(
                                    src, work, fps=v_fps, duration=v_dur, encoder=encoder,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity, wm_color=color,
                                    wm_corner=corner, wm_scale=scale, wm_x=wm_x_f, wm_y=wm_y_f,
                                )
                            else:
                                paths = proc.process_video_split(
                                    src, work, fps=v_fps,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity, wm_color=color,
                                    duration=v_dur, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=encoder,
                                )
                        else:
                            if mode == "workshop":
                                paths = proc.process_gif_workshop(
                                    src, work,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=encoder, fps=v_fps,
                                )
                            elif mode == "featured":
                                paths = proc.process_gif_featured(
                                    src, work, fps=v_fps, encoder=encoder,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f,
                                )
                            else:
                                paths = proc.process_gif_split(
                                    src, work, fps=v_fps,
                                    wm_text=text, wm_font=opts["wm_font"], wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=encoder,
                                )
                        for pname, pth in paths.items():
                            pth = Path(pth)
                            if not pth.is_file():
                                continue
                            data = pth.read_bytes()
                            zf.writestr(f"{folder}/{pname}", data)
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/{pname}", "size": len(data)})
                            try:
                                pth.unlink(missing_ok=True)
                            except Exception:
                                pass
                        try:
                            src.unlink(missing_ok=True)
                        except Exception:
                            pass
                processed += 1
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {e}")
        try:
            zf.close()
        except Exception:
            pass
        if processed == 0:
            detail = "; ".join(errors) if errors else "unknown error"
            _job_set(jid, status="error", pct=100, stage="error", error=f"Failed: {detail}", errors=errors)
            shutil.rmtree(job_dir, ignore_errors=True)
            return
        zip_path = job_dir / "result.zip"
        zip_path.write_bytes(zip_buf.getvalue())
        # quota already counted on start
        _job_set(
            jid,
            status="done",
            pct=100,
            stage="done",
            zip_path=str(zip_path),
            processed=processed,
            errors=errors,
            listed=listed,
        )
    except Exception as e:
        _job_set(jid, status="error", pct=100, stage="error", error=f"{type(e).__name__}: {e}")
        shutil.rmtree(job_dir, ignore_errors=True)


@app.post("/api/process/start")
async def api_process_start(
    request: Request,
    mode: str = Form("workshop"),
    fps: int = Form(12),
    size: int = Form(750),
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_enable: str = Form("1"),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    wm_x: str = Form(""),
    wm_y: str = Form(""),
    auto_contrast: str = Form("0"),
    gif_encoder: str = Form("gifski"),
    all_modes: str = Form("0"),
    files: list[UploadFile] = File(...),
):
    """Start async job; poll /api/process/status/{id} then download."""
    _job_cleanup_old()
    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Limit {FREE_LIMIT} files/day. Enter access code or buy Pro."},
            status_code=403,
        )
    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)
    do_all = str(all_modes).lower() in ("1", "true", "yes", "on")
    modes = ["workshop", "featured", "split"] if do_all else [mode]
    wm_on = wm_enable not in ("0", "false", "False", "")
    opacity = (wm_opacity / 100.0) if wm_on else 0.0
    text = wm_text if wm_on else ""
    color = (wm_color or "#ffffff").strip() or "#ffffff"
    corner = (wm_corner or "bl").strip().lower()
    if corner not in ("tl", "tr", "bl", "br"):
        corner = "bl"
    try:
        scale = max(0.4, min(2.5, float(wm_scale)))
    except (TypeError, ValueError):
        scale = 1.0
    wm_x_f = wm_y_f = None
    try:
        if str(wm_x).strip() != "" and str(wm_y).strip() != "":
            wm_x_f = max(0.0, min(1.0, float(wm_x)))
            wm_y_f = max(0.0, min(1.0, float(wm_y)))
    except (TypeError, ValueError):
        wm_x_f = wm_y_f = None
    do_ac = str(auto_contrast).lower() in ("1", "true", "yes", "on")
    try:
        size_i = int(size)
    except (TypeError, ValueError):
        size_i = 750
    if size_i not in (630, 640, 750, 800):
        size_i = min((630, 640, 750, 800), key=lambda s: abs(s - size_i))
    left = 999 if q["pro"] else q["left"]
    files = files[: max(1, left)]
    files_data: list[tuple[str, bytes]] = []
    for uf in files:
        name = uf.filename or "file"
        raw = await uf.read()
        files_data.append((name, raw))
    if not files_data:
        return JSONResponse({"ok": False, "msg": "No files"}, status_code=400)
    enc = (gif_encoder or "ffmpeg").strip().lower()
    if enc not in ("ffmpeg", "gifski", "pillow"):
        enc = "ffmpeg"
    jid = secrets.token_hex(12)
    opts = {
        "modes": modes,
        "text": text,
        "opacity": opacity,
        "color": color,
        "corner": corner,
        "scale": scale,
        "wm_x": wm_x_f,
        "wm_y": wm_y_f,
        "do_ac": do_ac,
        "size_i": size_i,
        "fps": fps,
        "enc": enc,
        "wm_font": wm_font,
    }
    user_key = ""
    try:
        u = _auth_user(request)
        # Anonymous callers are keyed by IP. Using request.client.host here
        # meant the proxy's address behind Railway, so every logged-out user
        # shared one MAX_JOBS_PER_USER budget and blocked each other.
        user_key = str(u.get("id") or "") if u else _ip(request)
    except Exception:
        user_key = ""
    # Check the per-user cap BEFORE registering the job or charging quota,
    # otherwise a rejected request still burns a free-tier slot.
    if user_key and rs.job_count_user(user_key) >= int(os.environ.get("MAX_JOBS_PER_USER", "2")):
        return JSONResponse(
            {"ok": False, "msg": "Too many active jobs. Wait for current processing to finish."},
            status_code=429,
        )

    # persist uploads to disk (the worker — embedded or external — reads them back)
    job_upload_dir = JOBS / jid
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    files_meta = []
    for name, raw in files_data:
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:80] or "file"
        p = job_upload_dir / safe
        p.write_bytes(raw)
        files_meta.append({"name": name, "path": str(p)})

    # Only hand the job to an external worker if one is actually alive; otherwise
    # the entry would sit in the Redis queue forever with nobody to pop it.
    mode = _worker_mode()
    external = mode == "external" and rs.redis_ok() and rs.worker_alive()
    if mode == "external" and not external:
        print(
            f"[job {jid[:8]}] WORKER_MODE=external but no live worker "
            f"(redis={rs.redis_ok()} beat={rs.worker_alive()}) — running embedded",
            flush=True,
        )

    payload = {
        "status": "queued", "pct": 1, "stage": "queued",
        "user_key": user_key, "files": files_meta, "opts": opts,
        "created": time.time(),
    }
    rs.job_create(jid, payload, enqueue=external)
    _job_set(jid, status="queued", pct=1, stage="queued", created=time.time(), user_key=user_key)
    try:
        quota_inc(request, len(files_data))
    except Exception:
        pass
    if not external:
        _job_pool.submit(_run_process_job, jid, files_data, opts)
    return {"ok": True, "job_id": jid}


@app.get("/api/process/status/{job_id}")
def api_process_status(job_id: str):
    j = _job_get(job_id)
    if not j:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    out = {
        "ok": True,
        "status": j.get("status"),
        "pct": int(j.get("pct") or 0),
        "stage": j.get("stage") or "",
        "error": j.get("error"),
        "processed": j.get("processed"),
        "errors": j.get("errors") or [],
    }
    if j.get("status") == "done":
        out["download"] = f"/api/process/download/{job_id}"
    return out


@app.get("/api/process/download/{job_id}")
def api_process_download(job_id: str):
    j = _job_get(job_id)
    if not j:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    if j.get("status") != "done" or not j.get("zip_path"):
        return JSONResponse(
            {"ok": False, "msg": f"Not ready (status={j.get('status') or 'unknown'})"},
            status_code=409,
        )
    path = Path(j["zip_path"])
    if not path.is_file():
        # Result was cleaned up, or produced on a filesystem this instance cannot see.
        return JSONResponse(
            {"ok": False, "msg": "Result expired or stored on another instance. Please run the job again."},
            status_code=410,
        )
    return FileResponse(
        path,
        media_type="application/zip",
        filename="showcase.zip",
        headers={"X-Processed": str(j.get("processed") or "")},
    )



@app.post("/api/process")
async def api_process(
    request: Request,
    mode: str = Form("workshop"),
    fps: int = Form(12),
    size: int = Form(750),
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_enable: str = Form("1"),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    wm_x: str = Form(""),
    wm_y: str = Form(""),
    auto_contrast: str = Form("0"),
    gif_encoder: str = Form("gifski"),
    all_modes: str = Form("0"),
    files: list[UploadFile] = File(...),
):
    """Process → ZIP download → delete temps."""
    import tempfile

    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Limit {FREE_LIMIT} files/day. Enter access code or buy Pro."},
            status_code=403,
        )

    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)

    do_all = str(all_modes).lower() in ("1", "true", "yes", "on")
    modes = ["workshop", "featured", "split"] if do_all else [mode]

    wm_on = wm_enable not in ("0", "false", "False", "")
    opacity = (wm_opacity / 100.0) if wm_on else 0.0
    text = wm_text if wm_on else ""
    color = (wm_color or "#ffffff").strip() or "#ffffff"
    corner = (wm_corner or "bl").strip().lower()
    if corner not in ("tl", "tr", "bl", "br"):
        corner = "bl"
    try:
        scale = max(0.4, min(2.5, float(wm_scale)))
    except (TypeError, ValueError):
        scale = 1.0
    wm_x_f = wm_y_f = None
    try:
        if str(wm_x).strip() != "" and str(wm_y).strip() != "":
            wm_x_f = max(0.0, min(1.0, float(wm_x)))
            wm_y_f = max(0.0, min(1.0, float(wm_y)))
    except (TypeError, ValueError):
        wm_x_f = wm_y_f = None
    do_ac = str(auto_contrast).lower() in ("1", "true", "yes", "on")
    try:
        size_i = int(size)
    except (TypeError, ValueError):
        size_i = 750
    if size_i not in (630, 640, 750, 800):
        size_i = min((630, 640, 750, 800), key=lambda s: abs(s - size_i))

    left = 999 if q["pro"] else q["left"]
    files = files[: max(1, left)]

    job_dir = Path(tempfile.mkdtemp(prefix="sm_job_"))
    zip_buf = io.BytesIO()
    processed = 0
    errors: list[str] = []
    listed: list[dict] = []

    try:
        zf = zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED)
        for uf in files:
            name = uf.filename or "file"
            try:
                raw = await uf.read()
                if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
                    errors.append(f"{name}: >{MAX_UPLOAD_MB}MB")
                    continue
                ext = Path(name).suffix.lower()
                stem = Path(name).stem[:40]
                if ext not in (
                    ".png", ".jpg", ".jpeg", ".webp", ".bmp",
                    ".gif", ".mp4", ".mov", ".webm", ".avi", ".mkv",
                ):
                    errors.append(f"{name}: unsupported format")
                    continue

                for mode in modes:
                    folder = f"{stem}_{mode}"
                    work = job_dir / folder
                    work.mkdir(exist_ok=True)

                    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                        img = Image.open(io.BytesIO(raw))
                        img.load()
                        max_side = 4096
                        if max(img.size) > max_side:
                            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                        if do_ac:
                            from PIL import ImageOps
                            rgb = img.convert("RGB")
                            rgb = ImageOps.autocontrast(rgb, cutoff=1)
                            img = rgb
                        if mode == "workshop" and img.size[0] != size_i:
                            nh = max(1, int(img.size[1] * (size_i / max(1, img.size[0]))))
                            img = img.resize((size_i, nh), Image.Resampling.LANCZOS)
                        if mode == "workshop":
                            parts = proc.process_image_workshop(
                                img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        elif mode == "featured":
                            parts = proc.process_image_featured(
                                img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        else:
                            parts = proc.process_image_split(
                                img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                            )
                        for pname, data in parts.items():
                            zf.writestr(f"{folder}/{pname}", data)
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/{pname}", "size": len(data)})
                    else:
                        src = work / f"source{ext}"
                        src.write_bytes(raw)
                        is_video = ext in (".mp4", ".mov", ".webm", ".avi", ".mkv")
                        v_fps = min(int(fps), 12)
                        v_dur = 8.0
                        enc = (gif_encoder or "ffmpeg").strip().lower()
                        if enc not in ("ffmpeg", "gifski", "pillow"):
                            enc = "ffmpeg"
                        # pillow → treat as ffmpeg for process pipeline
                        if enc == "pillow":
                            enc = "ffmpeg"
                        if is_video:
                            if not proc.find_ffmpeg():
                                raise RuntimeError("FFmpeg not available")
                            if mode == "workshop":
                                paths = proc.process_video_workshop(
                                    src, work, fps=v_fps, width=size_i,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                                    duration=v_dur, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=enc,
                                )
                            elif mode == "featured":
                                paths = proc.process_video_featured(
                                    src, work, fps=v_fps, duration=v_dur, encoder=enc,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                                    wm_corner=corner, wm_scale=scale, wm_x=wm_x_f, wm_y=wm_y_f,
                                )
                            else:
                                paths = proc.process_video_split(
                                    src, work, fps=v_fps,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                                    duration=v_dur, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=enc,
                                )
                        else:
                            if mode == "workshop":
                                paths = proc.process_gif_workshop(
                                    src, work,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=enc, fps=v_fps,
                                )
                            elif mode == "featured":
                                paths = proc.process_gif_featured(
                                    src, work, fps=v_fps, encoder=enc,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f,
                                )
                            else:
                                paths = proc.process_gif_split(
                                    src, work, fps=v_fps,
                                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                                    wm_color=color, wm_corner=corner, wm_scale=scale,
                                    wm_x=wm_x_f, wm_y=wm_y_f, encoder=enc,
                                )
                        for pname, pth in paths.items():
                            pth = Path(pth)
                            if not pth.is_file():
                                continue
                            data = pth.read_bytes()
                            zf.writestr(f"{folder}/{pname}", data)
                            if len(listed) < 20:
                                listed.append({"name": f"{folder}/{pname}", "size": len(data)})
                            try:
                                pth.unlink(missing_ok=True)
                            except Exception:
                                pass
                        try:
                            src.unlink(missing_ok=True)
                        except Exception:
                            pass

                processed += 1
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {e}")
                try:
                    shutil.rmtree(work, ignore_errors=True)
                except Exception:
                    pass

        try:
            zf.close()
        except Exception:
            pass

        if processed == 0:
            detail = "; ".join(errors) if errors else "unknown error"
            return JSONResponse(
                {"ok": False, "msg": f"Failed to process: {detail}", "errors": errors},
                status_code=400,
            )

        try:
            quota_inc(request, processed)
        except Exception as e:
            print("quota_inc:", e)

        zip_bytes = zip_buf.getvalue()
        zip_buf.close()
        headers_out = {
            "Content-Disposition": f'attachment; filename="showcase_{"all" if do_all else mode}.zip"',
            "X-Processed": str(processed),
            "X-Errors": str(len(errors)),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Processed, X-Errors",
        }
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers=headers_out,
        )
    finally:
        try:
            shutil.rmtree(job_dir, ignore_errors=True)
        except Exception:
            pass


@app.get("/api/download/{job_id}")
def download(job_id: str):
    """Legacy one-shot download — file is deleted after read."""
    job_id = "".join(c for c in job_id if c.isalnum())[:16]
    job_path = JOBS / job_id
    path = job_path / "result.zip"
    if not path.is_file():
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    data = path.read_bytes()
    try:
        shutil.rmtree(job_path, ignore_errors=True)
    except Exception:
        pass
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="showcase_{job_id}.zip"'},
    )


def _dl_session():
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s




def _download_pinterest(url: str, out_dir: Path) -> Path:
    """Картинки Pinterest — чистим URL и качаем с нормальными заголовками."""
    import re
    from urllib.parse import urlparse, unquote

    def clean_img_url(u: str) -> str:
        u = unquote(u).replace("&amp;", "&").replace("\\/", "/").strip()
        # обрезать CSS/мусор после расширения
        m = re.search(
            r"(https?://[^\s\"'<>]+?\.(?:jpg|jpeg|png|webp|gif))",
            u,
            re.I,
        )
        if m:
            return m.group(1)
        # pinimg path without query garbage
        m = re.search(r"(https?://i\.pinimg\.com/[^\s\"'<>]+)", u, re.I)
        if m:
            return re.split(r"[\"'\s<>{]", m.group(1))[0]
        return u.split()[0] if u else u

    s = _dl_session()
    s.headers.update({
        "Referer": "https://www.pinterest.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
    })
    html = s.get(url, timeout=30).text

    candidates = []
    for pat in (
        r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
        r'"url"\s*:\s*"(https://i\.pinimg\.com[^"]+)"',
        r"(https://i\.pinimg\.com/[^\s\"'<>]+)",
    ):
        for m in re.finditer(pat, html, re.I):
            candidates.append(clean_img_url(m.group(1)))

    def score(u: str) -> int:
        ul = u.lower()
        sc = 0
        if "originals" in ul:
            sc += 80
        if "/1200x" in ul or "1200x" in ul:
            sc += 40
        if "736x" in ul:
            sc += 20
        if any(x in ul for x in ("236x", "474x", "60x60", "75x75")):
            sc -= 20
        if ul.endswith((".png", ".jpg", ".jpeg", ".webp")):
            sc += 5
        return sc

    seen, ordered = set(), []
    for u in candidates:
        u = clean_img_url(u)
        if not u.startswith("http") or u in seen:
            continue
        seen.add(u)
        ordered.append(u)
    ordered.sort(key=score, reverse=True)
    if not ordered:
        raise RuntimeError("не найдено изображение на странице")

    last_err = None
    for img_url in ordered[:8]:
        try:
            # originals часто 403 → пробуем 1200x
            tries = [img_url]
            if "originals" in img_url:
                tries.append(
                    re.sub(r"/originals/", "/1200x/", img_url, count=1, flags=re.I)
                )
                tries.append(
                    re.sub(r"/originals/", "/736x/", img_url, count=1, flags=re.I)
                )
            for turl in tries:
                turl = clean_img_url(turl)
                rr = s.get(
                    turl,
                    timeout=60,
                    stream=True,
                    headers={
                        **s.headers,
                        "Referer": "https://www.pinterest.com/",
                        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        "Sec-Fetch-Dest": "image",
                        "Sec-Fetch-Mode": "no-cors",
                    },
                )
                if rr.status_code == 403:
                    last_err = f"403 {turl[:80]}"
                    continue
                rr.raise_for_status()
                ct = (rr.headers.get("Content-Type") or "").lower()
                if "html" in ct:
                    last_err = "got html"
                    continue
                ext = ".jpg"
                if "png" in ct or turl.lower().endswith(".png"):
                    ext = ".png"
                elif "webp" in ct or turl.lower().endswith(".webp"):
                    ext = ".webp"
                elif "gif" in ct or turl.lower().endswith(".gif"):
                    ext = ".gif"
                dest = out_dir / f"pinterest_{uuid.uuid4().hex[:8]}{ext}"
                with open(dest, "wb") as f:
                    for chunk in rr.iter_content(64 * 1024):
                        if chunk:
                            f.write(chunk)
                if dest.stat().st_size < 800:
                    dest.unlink(missing_ok=True)
                    last_err = "too small"
                    continue
                return dest
        except Exception as e:
            last_err = str(e)
            continue
    raise RuntimeError(last_err or "download failed")




@app.post("/api/convert")
async def api_convert(
    request: Request,
    target: str = Form("gif"),
    fps: int = Form(12),
    width: int = Form(0),
    duration: float = Form(0),
    file: UploadFile = File(...),
):
    """Convert media: video↔gif, image formats."""
    import tempfile

    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Limit {FREE_LIMIT} files/day."},
            status_code=403,
        )
    target = (target or "gif").lower().lstrip(".")
    if target == "jpeg":
        target = "jpg"
    allowed = {"gif", "mp4", "webm", "png", "jpg", "webp"}
    if target not in allowed:
        return JSONResponse({"ok": False, "msg": f"Unsupported target: {target}"}, status_code=400)

    name = file.filename or "file"
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": f"File >{MAX_UPLOAD_MB}MB"}, status_code=400)

    work = Path(tempfile.mkdtemp(prefix="sm_conv_"))
    try:
        ext = Path(name).suffix.lower() or ".bin"
        src = work / f"src{ext}"
        src.write_bytes(raw)
        out_name = f"{Path(name).stem[:40]}.{target}"
        dest = work / out_name
        proc.convert_media(src, dest, target, fps=fps, width=width, duration=duration)
        data = dest.read_bytes()
        quota_inc(request, 1)
        media = {
            "gif": "image/gif",
            "mp4": "video/mp4",
            "webm": "video/webm",
            "png": "image/png",
            "jpg": "image/jpeg",
            "webp": "image/webp",
        }.get(target, "application/octet-stream")
        return StreamingResponse(
            io.BytesIO(data),
            media_type=media,
            headers={
                "Content-Disposition": f'attachment; filename="{out_name}"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"{type(e).__name__}: {e}"[:400]}, status_code=400)
    finally:
        try:
            shutil.rmtree(work, ignore_errors=True)
        except Exception:
            pass


@app.post("/api/hex21")
async def api_hex21(
    request: Request,
    files: list[UploadFile] = File(...),
):
    """Apply Steam hex 0x21 to PNG/GIF/any binary. ZIP uses STORE (no recompress)."""
    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Limit {FREE_LIMIT} files/day."},
            status_code=403,
        )
    left = 999 if q["pro"] else q["left"]
    files = files[: max(1, min(40, left))]

    zip_buf = io.BytesIO()
    done = 0
    errors: list[str] = []
    png_magic = b"\x89PNG\r\n\x1a\n"
    try:
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_STORED) as zf:
            for uf in files:
                name = uf.filename or f"file_{done}"
                try:
                    raw = await uf.read()
                    if len(raw) < 2:
                        errors.append(f"{name}: empty")
                        continue
                    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
                        errors.append(f"{name}: too large")
                        continue
                    out = proc.apply_hex21(raw)
                    if not out or out[-1] != 0x21:
                        errors.append(f"{name}: hex21 failed")
                        continue
                    stem = Path(name).stem[:50] or "file"
                    ext = Path(name).suffix.lower() or ".bin"
                    if raw[:6] in (b"GIF87a", b"GIF89a"):
                        ext = ".gif"
                    elif len(raw) >= 8 and raw[0] == 0x89 and raw[1:4] == b"PNG":
                        ext = ".png"
                    zf.writestr(f"{stem}_hex21{ext}", out)
                    done += 1
                except Exception as e:
                    errors.append(f"{name}: {e}")
        if done == 0:
            return JSONResponse(
                {"ok": False, "msg": "Nothing processed: " + ("; ".join(errors[:5]) or "no files")},
                status_code=400,
            )
        try:
            quota_inc(request, done)
        except Exception:
            pass
        return StreamingResponse(
            io.BytesIO(zip_buf.getvalue()),
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="hex21.zip"',
                "X-Processed": str(done),
                "Access-Control-Expose-Headers": "Content-Disposition, X-Processed",
            },
        )
    finally:
        try:
            zip_buf.close()
        except Exception:
            pass


@app.post("/api/download-url")
async def download_url(request: Request):
    """Скачать с YouTube / TikTok / X / Reddit / Pinterest / прямая ссылка."""
    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse({"ok": False, "msg": "Лимит исчерпан"}, status_code=403)
    body = await request.json()
    url = str(body.get("url") or "").strip()
    quality = str(body.get("quality") or "best")
    if not url.startswith("http"):
        return JSONResponse({"ok": False, "msg": "Нужна ссылка http(s)"}, status_code=400)
    url_ok, url_err = _check_public_url(url)
    if not url_ok:
        LOGGER.warning("download-url rejected %s: %s", url[:200], url_err)
        return JSONResponse({"ok": False, "msg": url_err}, status_code=400)

    job_id = uuid.uuid4().hex[:12]
    out_dir = JOBS / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Pinterest (video first, then image) ---
    if "pinterest." in url.lower() or "pin.it" in url.lower():
        try:
            import re as _re
            import requests as _req

            # 1) yt-dlp with broader format + merge
            try:
                import yt_dlp
                ydl_opts = {
                    "outtmpl": str(out_dir / "pin_%(id)s.%(ext)s"),
                    "quiet": True,
                    "noplaylist": True,
                    "format": "bv*+ba/b/best",
                    "merge_output_format": "mp4",
                    "http_headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://www.pinterest.com/",
                    },
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                files = sorted(
                    [p for p in out_dir.iterdir() if p.is_file() and p.suffix.lower() in
                     (".mp4", ".webm", ".mkv", ".mov", ".gif", ".jpg", ".jpeg", ".png", ".webp")],
                    key=lambda p: (0 if p.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov") else 1, -p.stat().st_size),
                )
                if files and files[0].suffix.lower() in (".mp4", ".webm", ".mkv", ".mov", ".gif"):
                    f = files[0]
                    quota_inc(request, 1)
                    return {
                        "ok": True,
                        "name": f.name,
                        "download": f"/api/job-file/{job_id}/{f.name}",
                        **quota_state(request),
                    }
                # if only image from yt-dlp, keep trying video extract below
            except Exception as _ye:
                print("pinterest yt-dlp:", _ye)

            # 2) scrape page for video urls (v.pinimg / videos)
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                page = _req.get(url, headers=headers, timeout=30, allow_redirects=True)
                html = page.text or ""
                candidates = []
                for pat in (
                    r'https://v\.pinimg\.com/[^"\s<>]+\.mp4',
                    r'https://[^"\s<>]*pinimg[^"\s<>]+\.mp4',
                    r'"video_url"\s*:\s*"(https:[^"]+)"',
                    r'"url"\s*:\s*"(https://v\.pinimg\.com[^"]+)"',
                    r'contentUrl"\s*:\s*"(https:[^"]+\.mp4[^"]*)"',
                ):
                    for mobj in _re.finditer(pat, html, _re.I):
                        u = mobj.group(1) if mobj.lastindex else mobj.group(0)
                        u = u.replace(r"\/", "/").replace(r"\u002F", "/")
                        if u.startswith("http") and u not in candidates:
                            candidates.append(u)
                for vu in candidates[:8]:
                    try:
                        # Candidates are scraped out of a remote page, so they
                        # are attacker-influenced just like the original input.
                        cand_ok, _cand_err = _check_public_url(vu)
                        if not cand_ok:
                            continue
                        rr = _req.get(
                            vu, headers={**headers, "Referer": "https://www.pinterest.com/"},
                            timeout=60, stream=True,
                        )
                        if rr.status_code != 200:
                            continue
                        ct = (rr.headers.get("Content-Type") or "").lower()
                        if "html" in ct:
                            continue
                        ext = ".mp4"
                        if "webm" in ct or vu.lower().endswith(".webm"):
                            ext = ".webm"
                        dest = out_dir / f"pinterest_vid_{uuid.uuid4().hex[:8]}{ext}"
                        with open(dest, "wb") as fh:
                            for chunk in rr.iter_content(64 * 1024):
                                if chunk:
                                    fh.write(chunk)
                        if dest.stat().st_size > 50_000:
                            quota_inc(request, 1)
                            return {
                                "ok": True,
                                "name": dest.name,
                                "download": f"/api/job-file/{job_id}/{dest.name}",
                                **quota_state(request),
                            }
                        dest.unlink(missing_ok=True)
                    except Exception as ve:
                        print("pin video cand:", ve)
            except Exception as se:
                print("pinterest scrape:", se)

            # 3) image fallback
            f = _download_pinterest(url, out_dir)
            quota_inc(request, 1)
            return {
                "ok": True,
                "name": f.name,
                "download": f"/api/job-file/{job_id}/{f.name}",
                **quota_state(request),
            }
        except Exception as e:
            return JSONResponse({"ok": False, "msg": f"Pinterest: {e}"[:400]}, status_code=400)

    try:
        import yt_dlp
    except ImportError:
        return JSONResponse({"ok": False, "msg": "yt-dlp не установлен: pip install yt-dlp"}, status_code=500)

    outtmpl = str(out_dir / "%(title).80s.%(ext)s")
    ydl_opts = {
        "outtmpl": outtmpl,
        "quiet": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
    }
    if quality == "best":
        ydl_opts["format"] = "bv*+ba/b"
    elif quality == "audio":
        ydl_opts["format"] = "ba/b"
        ydl_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    else:
        ydl_opts["format"] = "best[height<=720]/best"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        files = [p for p in out_dir.iterdir() if p.is_file()]
        if not files:
            return JSONResponse({"ok": False, "msg": "Файл не скачался"}, status_code=400)
        if len(files) == 1:
            f = files[0]
            quota_inc(request, 1)
            return {
                "ok": True,
                "name": f.name,
                "download": f"/api/job-file/{job_id}/{f.name}",
                **quota_state(request),
            }
        zpath = out_dir / "download.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            for f in files:
                zf.write(f, f.name)
        quota_inc(request, 1)
        return {
            "ok": True,
            "name": "download.zip",
            "download": f"/api/job-file/{job_id}/download.zip",
            **quota_state(request),
        }
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)[:400]}, status_code=400)


@app.get("/api/job-file/{job_id}/{name}")
def job_file(job_id: str, name: str):
    job_id = "".join(c for c in job_id if c.isalnum())[:16]
    name = Path(name).name
    path = JOBS / job_id / name
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path, filename=name)


@app.get("/api/preview-template/{mode}")
def preview_template(mode: str):
    names = {
        "workshop": "steam_preview_workshop.png",
        "featured": "steam_preview_featured.png",
        "split": "steam_preview_split.png",
    }
    fname = names.get(mode, names["workshop"])
    path = TEMPLATES / fname
    if not path.is_file():
        return JSONResponse(
            {"ok": False, "msg": f"Нет шаблона {fname} в папке templates/"},
            status_code=404,
        )
    return FileResponse(path, media_type="image/png")



# === Profile preview (desktop 1:1 coordinates, template 1983×9978) ===


# === Profile preview — desktop 1:1 (эталон 1983×9978), масштаб один раз ===
PV_XS = [535, 661, 787, 914, 1040]
PV_WS = [122, 122, 123, 122, 122]
PV_REF_W, PV_REF_H = 1983, 9978


def _pv_slot_defs(mode: str) -> list:
    xs, ws = PV_XS, PV_WS

    def row5(y, h):
        return [(xs[i], y, ws[i], h) for i in range(5)]

    m = (mode or "workshop").strip().lower()
    if m in ("workshop",):
        return [
            {"id": "ws_main", "label": "1. Workshop (main)", "type": "workshop5",
             "boxes": row5(484, 1051)},
            {"id": "feat", "label": "2. Featured", "type": "single",
             "boxes": [(534, 2637, 630, 878)]},
            {"id": "split", "label": "3. Split", "type": "split",
             "boxes": [(533, 3974, 508, 821), (1049, 3974, 101, 821)]},
            {"id": "ws2", "label": "4. Workshop #2", "type": "workshop5",
             "boxes": row5(5706, 868)},
            {"id": "ws3", "label": "5. Workshop #3", "type": "workshop5",
             "boxes": row5(6583, 868)},
            {"id": "ws4", "label": "6. Workshop #4", "type": "workshop5",
             "boxes": row5(7453, 313)},
        ]
    if m in ("featured", "featured artwork"):
        return [
            {"id": "feat_main", "label": "1. Featured (main)", "type": "single",
             "boxes": [(534, 359, 630, 878)]},
            {"id": "ws1", "label": "2. Workshop #1", "type": "workshop5",
             "boxes": row5(1424, 344)},
            {"id": "ws2", "label": "3. Workshop #2", "type": "workshop5",
             "boxes": row5(1777, 345)},
            {"id": "ws3", "label": "4. Workshop #3", "type": "workshop5",
             "boxes": row5(2131, 344)},
            {"id": "split", "label": "5. Split", "type": "split",
             "boxes": [(533, 3974, 508, 821), (1049, 3974, 101, 821)]},
            {"id": "ws4", "label": "6. Workshop #4", "type": "workshop5",
             "boxes": row5(5706, 868)},
            {"id": "ws5", "label": "7. Workshop #5", "type": "workshop5",
             "boxes": row5(6583, 868)},
            {"id": "ws6", "label": "8. Workshop #6", "type": "workshop5",
             "boxes": row5(7453, 313)},
        ]
    # split / artwork split
    return [
        {"id": "split_main", "label": "1. Split (main)", "type": "split",
         "boxes": [(532, 359, 508, 821), (1048, 359, 101, 821)]},
        {"id": "ws1", "label": "2. Workshop #1", "type": "workshop5",
         "boxes": row5(1423, 344)},
        {"id": "ws2", "label": "3. Workshop #2", "type": "workshop5",
         "boxes": row5(1776, 345)},
        {"id": "ws3", "label": "4. Workshop #3", "type": "workshop5",
         "boxes": row5(2130, 344)},
        {"id": "feat", "label": "5. Featured", "type": "single",
         "boxes": [(534, 3576, 630, 878)]},
        {"id": "ws4", "label": "6. Workshop #4", "type": "workshop5",
         "boxes": row5(5706, 868)},
        {"id": "ws5", "label": "7. Workshop #5", "type": "workshop5",
         "boxes": row5(6583, 868)},
        {"id": "ws6", "label": "8. Workshop #6", "type": "workshop5",
         "boxes": row5(7453, 313)},
    ]


def _pv_template_name(mode: str) -> str:
    m = (mode or "workshop").strip().lower()
    if m in ("featured", "featured artwork"):
        return "steam_preview_featured.png"
    if m in ("split", "artwork split"):
        return "steam_preview_split.png"
    return "steam_preview_workshop.png"


def _pv_scale_box(box, sx: float, sy: float, max_w: int, max_h: int):
    x, y, w, h = [float(v) for v in box]
    x, y = int(round(x * sx)), int(round(y * sy))
    w, h = int(round(w * sx)), int(round(h * sy))
    if w < 1 or h < 1:
        return None
    if x >= max_w or y >= max_h:
        return None
    if x < 0:
        w += x
        x = 0
    if y < 0:
        h += y
        y = 0
    if x + w > max_w:
        w = max_w - x
    if y + h > max_h:
        h = max_h - y
    if w < 1 or h < 1:
        return None
    return (x, y, w, h)


def _pv_scaled_defs(mode: str, tw: int, th: int) -> list:
    """Hardcode desktop coords → один масштаб под размер шаблона."""
    sx, sy = tw / PV_REF_W, th / PV_REF_H
    out = []
    for d in _pv_slot_defs(mode):
        boxes = []
        for b in d["boxes"]:
            sb = _pv_scale_box(b, sx, sy, tw, th)
            if sb:
                boxes.append(sb)
        if not boxes:
            print(f"[pv] slot {d['id']} all boxes out of bounds")
            continue
        nd = dict(d)
        nd["boxes"] = boxes
        out.append(nd)
    return out


def _pv_place(canvas: Image.Image, box, img: Image.Image) -> None:
    bx, by, bw, bh = [int(v) for v in box]
    if img is None or bw < 1 or bh < 1:
        return
    try:
        src = img.convert("RGBA")
    except Exception:
        return
    fit_w = bw / max(1, src.width)
    fit_h = bh / max(1, src.height)
    base = max(fit_w, fit_h)
    nw = max(1, int(src.width * base + 0.5))
    nh = max(1, int(src.height * base + 0.5))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    ox = max(0, (nw - bw) // 2)
    oy = max(0, (nh - bh) // 2)
    crop = resized.crop((ox, oy, min(ox + bw, nw), min(oy + bh, nh)))
    if crop.size != (bw, bh):
        layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 255))
        layer.paste(crop, (0, 0))
        crop = layer
    try:
        canvas.paste(crop.convert("RGB"), (bx, by))
    except Exception as e:
        print("pv paste:", e, box)


def _pv_place_slot_abs(canvas, slot_def, img) -> bool:
    """boxes уже в пикселях шаблона — без повторного scale."""
    if img is None:
        return False
    st = slot_def["type"]
    boxes = slot_def.get("boxes") or []
    if not boxes:
        return False
    if st == "workshop5" and len(boxes) >= 5:
        for i, box in enumerate(boxes[:5]):
            left = int(img.width * i / 5)
            right = int(img.width * (i + 1) / 5)
            if right <= left:
                right = left + 1
            part = img.crop((left, 0, right, img.height))
            _pv_place(canvas, box, part)
        return True
    if st == "split" and len(boxes) >= 2:
        w = img.width
        cut = int(w * 506 / 606) if w > 10 else max(1, w // 2)
        cut = max(1, min(w - 1, cut))
        main = img.crop((0, 0, cut, img.height))
        side = img.crop((cut, 0, w, img.height))
        _pv_place(canvas, boxes[0], main)
        _pv_place(canvas, boxes[1], side)
        return True
    _pv_place(canvas, boxes[0], img)
    return True


@app.get("/api/preview-slots")
def preview_slots(mode: str = "workshop"):
    defs = _pv_slot_defs(mode)
    return {
        "ok": True,
        "mode": mode,
        "slots": [{"id": d["id"], "label": d["label"], "type": d["type"]} for d in defs],
        "count": len(defs),
    }



def _pv_slice_media(src: Path, dest: Path, x0: float, x1: float) -> bool:
    """Вырезает полосу [x0..x1] по ширине. GIF — все кадры; video — ffmpeg; image — 1 кадр."""
    import subprocess
    if not src.is_file():
        return False
    x0 = max(0.0, min(1.0, float(x0)))
    x1 = max(0.0, min(1.0, float(x1)))
    if x1 <= x0:
        x1 = min(1.0, x0 + 0.01)
    ext = src.suffix.lower()
    dest.parent.mkdir(parents=True, exist_ok=True)

    # video
    if ext in (".mp4", ".webm", ".mov", ".mkv", ".avi"):
        ff = proc.find_ffmpeg()
        if not ff:
            return False
        wf = x1 - x0
        vf = f"crop=iw*{wf:.6f}:ih:iw*{x0:.6f}:0"
        dst = dest if dest.suffix.lower() in (".mp4", ".webm") else dest.with_suffix(".mp4")
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            r = subprocess.run(
                [ff, "-y", "-i", str(src), "-vf", vf, "-an",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)],
                capture_output=True, text=True, **kw,
            )
            if r.returncode == 0 and dst.is_file() and dst.stat().st_size > 64:
                if dst != dest:
                    try:
                        dst.replace(dest)
                    except Exception:
                        pass
                return dest.is_file() or dst.is_file()
        except Exception as e:
            print("pv slice video:", e)
        return False

    # image / gif / webp
    try:
        with Image.open(src) as im:
            w, h = im.size
            left = max(0, min(w - 1, int(round(w * x0))))
            right = max(left + 1, min(w, int(round(w * x1))))
            n_frames = getattr(im, "n_frames", 1) or 1
            animated = n_frames > 1 or ext in (".gif", ".webp")

            if not animated:
                frame = im.convert("RGBA").crop((left, 0, right, h))
                out = dest.with_suffix(".png") if dest.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif") else dest
                if out.suffix.lower() == ".gif":
                    frame.convert("RGB").save(out, "GIF")
                else:
                    frame.save(out)
                return out.is_file()

            frames, durations = [], []
            for i in range(n_frames):
                im.seek(i)
                fr = im.convert("RGBA").crop((left, 0, right, h)).convert("RGB")
                frames.append(fr)
                durations.append(int(im.info.get("duration", 100) or 100))
            out = dest if dest.suffix.lower() == ".gif" else dest.with_suffix(".gif")
            frames[0].save(
                out, save_all=True, append_images=frames[1:],
                duration=durations, loop=0, disposal=2, optimize=False,
            )
            return out.is_file()
    except Exception as e:
        print("pv slice img:", e)
        return False


@app.post("/api/preview-build")
async def preview_build(request: Request):
    """
    Как desktop _pv_open_browser:
    HTML-оверлей поверх шаблона, GIF анимированные, MP4 как <video>.
    """
    form = await request.form()
    mode = str(form.get("mode") or "workshop").strip()
    fname = _pv_template_name(mode)
    tpl_path = TEMPLATES / fname
    if not tpl_path.is_file() and (ROOT / fname).is_file():
        tpl_path = ROOT / fname
    if not tpl_path.is_file():
        return JSONResponse(
            {"ok": False, "msg": f"Нет шаблона templates/{fname}"},
            status_code=404,
        )

    job_id = uuid.uuid4().hex[:12]
    job_dir = JOBS / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # template size + scale
    with Image.open(tpl_path) as im:
        tw, th = im.size
    sx, sy = tw / PV_REF_W, th / PV_REF_H

    # copy template into job
    tpl_dst = job_dir / "template.png"
    try:
        import shutil
        shutil.copy2(tpl_path, tpl_dst)
    except Exception:
        Image.open(tpl_path).convert("RGB").save(tpl_dst, "PNG")

    defs = _pv_slot_defs(mode)
    # scale boxes once
    for d in defs:
        boxes = []
        for b in d["boxes"]:
            sb = _pv_scale_box(b, sx, sy, tw, th)
            if sb:
                boxes.append(sb)
        d["boxes"] = boxes
    defs_by_id = {d["id"]: d for d in defs if d.get("boxes")}

    layers = []
    applied = []
    errors = []

    def media_tag(url: str, kind: str) -> str:
        if kind == "video":
            return (
                f'<video src="{url}" autoplay muted loop playsinline '
                f'style="width:100%;height:100%;object-fit:cover;display:block;"></video>'
            )
        return (
            f'<img src="{url}" alt="" '
            f'style="display:block;width:100%;height:100%;object-fit:cover;"/>'
        )

    def slot_box(bx, by, bw, bh, url, kind) -> str:
        return (
            f'<div class="slot" style="left:{bx}px;top:{by}px;'
            f'width:{bw}px;height:{bh}px;">{media_tag(url, kind)}</div>'
        )

    # avatar
    av_file = form.get("avatar")
    if av_file is not None and hasattr(av_file, "read") and not isinstance(av_file, (str, bytes)):
        try:
            raw = await av_file.read()
            if raw:
                av_path = job_dir / "av_avatar.png"
                Image.open(io.BytesIO(raw)).convert("RGBA").save(av_path, "PNG")
                box = _pv_scale_box((535, 139, 164, 164), sx, sy, tw, th)
                if box:
                    ax, ay, aw, ah = box
                    layers.append(slot_box(ax, ay, aw, ah, f"/api/job-file/{job_id}/av_avatar.png", "image"))
        except Exception as e:
            print("[pv] avatar", e)

    # collect slot files to disk first
    slot_files: dict[str, Path] = {}
    items = form.multi_items() if hasattr(form, "multi_items") else list(form.items())
    for key, f in items:
        key = str(key)
        if not key.startswith("slot_"):
            continue
        sid = key[5:]
        if sid not in defs_by_id:
            errors.append(f"{sid}: unknown")
            continue
        if f is None or isinstance(f, (str, bytes)) or not hasattr(f, "read"):
            continue
        try:
            if hasattr(f, "file") and hasattr(f.file, "seek"):
                try:
                    f.file.seek(0)
                except Exception:
                    pass
            raw = await f.read()
            if not raw:
                continue
            name = getattr(f, "filename", None) or "file.png"
            ext = Path(name).suffix.lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".mp4", ".webm", ".mov", ".mkv", ".avi"):
                # sniff
                if raw[:6] in (b"GIF87a", b"GIF89a"):
                    ext = ".gif"
                elif raw[:8] == b"\x89PNG\r\n\x1a\n":
                    ext = ".png"
                elif raw[4:8] == b"ftyp":
                    ext = ".mp4"
                else:
                    ext = ".png"
            path = job_dir / f"src_{sid}{ext}"
            path.write_bytes(raw)
            slot_files[sid] = path
        except Exception as e:
            errors.append(f"{sid}: {e}")

    for sid, src in slot_files.items():
        d = defs_by_id[sid]
        st = d["type"]
        boxes = d["boxes"]
        ext = src.suffix.lower()
        is_vid = ext in (".mp4", ".webm", ".mov", ".mkv", ".avi")
        is_gif = ext in (".gif", ".webp")

        try:
            if st == "workshop5" and len(boxes) >= 5:
                n = min(5, len(boxes))
                for i, (bx, by, bw, bh) in enumerate(boxes[:n]):
                    x0, x1 = i / n, (i + 1) / n
                    part_ext = ".mp4" if is_vid else (".gif" if is_gif else ".png")
                    part_path = job_dir / f"part_{sid}_{i}{part_ext}"
                    ok = _pv_slice_media(src, part_path, x0, x1)
                    if not ok:
                        # fallback full
                        part_path = job_dir / f"part_{sid}_{i}_full{ext}"
                        import shutil
                        shutil.copy2(src, part_path)
                    kind = "video" if (is_vid or part_path.suffix.lower() in (".mp4", ".webm", ".mov")) else "image"
                    # resolve actual file
                    real = part_path if part_path.is_file() else next(job_dir.glob(f"part_{sid}_{i}*"), None)
                    if real and real.is_file():
                        layers.append(slot_box(bx, by, bw, bh, f"/api/job-file/{job_id}/{real.name}", kind))
                applied.append(sid)
                continue

            if st == "split" and len(boxes) >= 2:
                (mx, my, mw, mh), (sx_, sy_, sw, sh) = boxes[0], boxes[1]
                cut = 506.0 / 606.0
                part_ext = ".mp4" if is_vid else (".gif" if is_gif else ".png")
                main_path = job_dir / f"part_{sid}_main{part_ext}"
                side_path = job_dir / f"part_{sid}_side{part_ext}"
                ok_m = _pv_slice_media(src, main_path, 0.0, cut)
                ok_s = _pv_slice_media(src, side_path, cut, 1.0)
                kind = "video" if is_vid else "image"
                if ok_m or main_path.is_file():
                    real = main_path if main_path.is_file() else main_path.with_suffix(".gif")
                    if real.is_file():
                        layers.append(slot_box(mx, my, mw, mh, f"/api/job-file/{job_id}/{real.name}", kind))
                if ok_s or side_path.is_file():
                    real = side_path if side_path.is_file() else side_path.with_suffix(".gif")
                    if real.is_file():
                        layers.append(slot_box(sx_, sy_, sw, sh, f"/api/job-file/{job_id}/{real.name}", kind))
                applied.append(sid)
                continue

            # single / featured — whole file
            bx, by, bw, bh = boxes[0]
            kind = "video" if is_vid else "image"
            layers.append(slot_box(bx, by, bw, bh, f"/api/job-file/{job_id}/{src.name}", kind))
            applied.append(sid)
        except Exception as e:
            errors.append(f"{sid}: {e}")
            print("[pv] place", sid, e)

    layers_html = "\n".join(layers)
    # page width = template width
    html = f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Showcase Maker — Preview</title>
<style>
  html, body {{ margin:0; padding:0; background:#0b0b12; }}
  .page {{ position:relative; width:{tw}px; margin:0 auto; }}
  .page > .bg {{ display:block; width:{tw}px; height:auto; }}
  .slot {{
    position:absolute; overflow:hidden; z-index:2;
    background-color:#1b2838;
  }}
  .slot img, .slot video {{
    display:block; width:100%; height:100%;
    object-fit:cover; object-position:center;
  }}
  .hint {{
    position:fixed; top:8px; left:8px; z-index:99;
    background:rgba(0,0,0,.75); color:#eee; padding:8px 12px;
    border-radius:8px; font:13px/1.4 system-ui,sans-serif;
  }}
</style>
</head>
<body>
  <div class="hint">Preview · {mode} · slots: {", ".join(applied) or "none"}</div>
  <div class="page">
    <img class="bg" src="/api/job-file/{job_id}/template.png" alt="template"/>
    {layers_html}
  </div>
</body>
</html>
"""
    (job_dir / "preview.html").write_text(html, encoding="utf-8")
    return {
        "ok": True,
        "open": f"/preview/{job_id}",
        "applied": applied,
        "errors": errors,
        "template_size": [tw, th],
    }


@app.get("/preview/{job_id}", response_class=HTMLResponse)
def preview_page(job_id: str):
    job_id = "".join(c for c in job_id if c.isalnum())[:16]
    path = JOBS / job_id / "preview.html"
    if not path.is_file():
        return HTMLResponse("<h3>Preview not found</h3>", status_code=404)
    return HTMLResponse(path.read_text(encoding="utf-8"))





@app.post("/api/da/logout")
async def da_logout(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)
    auth_db.set_da_tokens(int(user["id"]), None, None)
    return {"ok": True}



def _da_guess_mime(name: str) -> str:
    ext = Path(name or "").suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
    }.get(ext, "application/octet-stream")


def _da_refresh_token(user: dict) -> str | None:
    """Try refresh DA access token. Returns new access token or None."""
    refresh = (user.get("da_refresh_token") or "").strip()
    if not refresh:
        return None
    cid = (user.get("da_client_id") or "").strip() or (os.environ.get("DA_CLIENT_ID") or "").strip()
    sec = (user.get("da_client_secret") or "").strip() or (os.environ.get("DA_CLIENT_SECRET") or "").strip()
    if not cid or not sec:
        return None
    try:
        import requests as rq
        r = rq.post(
            "https://www.deviantart.com/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": cid,
                "client_secret": sec,
                "refresh_token": refresh,
            },
            timeout=30,
        )
        if r.status_code != 200:
            print("da refresh fail", r.status_code, r.text[:200])
            return None
        data = r.json()
        access = data.get("access_token")
        new_refresh = data.get("refresh_token") or refresh
        if access:
            auth_db.set_da_tokens(int(user["id"]), access, new_refresh)
            return access
    except Exception as e:
        print("da refresh error", e)
    return None


@app.post("/api/da/upload")
async def da_upload(request: Request):
    """Upload files to DeviantArt Sta.sh."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    token = (user.get("da_access_token") or "").strip().strip('"').strip("'")
    if not token:
        return JSONResponse({"ok": False, "msg": "Connect DeviantArt first"}, status_code=401)
    # debug length only (never log full token)
    print(f"da_upload: user={user.get('id')} token_len={len(token)} files incoming")

    form = await request.form()
    items = form.multi_items() if hasattr(form, "multi_items") else list(form.items())

    titles: dict[str, str] = {}
    for k, v in items:
        ks = str(k)
        if ks.startswith("title_"):
            titles[ks[6:]] = str(v or "")

    files: list[tuple[str, bytes, str]] = []
    idx = 0
    for k, f in items:
        ks = str(k)
        # accept file, file_0, files, etc.
        if not (ks == "file" or ks.startswith("file_") or ks.startswith("files")):
            continue
        if f is None or isinstance(f, (str, bytes, int, float)):
            continue
        if not hasattr(f, "read"):
            continue
        try:
            raw = await f.read()
        except Exception:
            raw = f.file.read() if hasattr(f, "file") else b""
        if not raw:
            continue
        name = getattr(f, "filename", None) or f"file_{idx}.png"
        name = Path(str(name)).name  # strip path
        title = titles.get(name) or titles.get(str(idx)) or Path(name).stem
        files.append((name, raw, (title or Path(name).stem)[:50]))
        idx += 1

    if not files:
        return JSONResponse({"ok": False, "msg": "No files received"}, status_code=400)

    import requests as rq

    def submit_one(access: str, name: str, raw: bytes, title: str):
        """DA Sta.sh: access_token must be in form body for multipart uploads."""
        access = (access or "").strip()
        if not access:
            raise ValueError("empty access_token")
        mime = _da_guess_mime(name)
        # Token in form field + query + Bearer — DA is picky with multipart
        return rq.post(
            "https://www.deviantart.com/api/v1/oauth2/stash/submit",
            params={"access_token": access},
            headers={"Authorization": f"Bearer {access}"},
            data={
                "access_token": access,
                "title": title or Path(name).stem,
                "artist_comments": "",
                "is_mature": "0",
            },
            files={"file": (name, raw, mime)},
            timeout=180,
        )

    ok_n = 0
    errors: list[str] = []
    access = token

    for name, raw, title in files:
        try:
            r = submit_one(access, name, raw, title)
            # expired token → refresh once and retry
            if r.status_code in (401, 403):
                new_tok = _da_refresh_token(user)
                if new_tok:
                    access = new_tok
                    user = {**user, "da_access_token": new_tok}
                    r = submit_one(access, name, raw, title)
                else:
                    auth_db.set_da_tokens(int(user["id"]), None, None)
                    errors.append(f"{name}: session expired — reconnect DeviantArt")
                    break
            if r.status_code == 200:
                try:
                    body = r.json()
                except Exception:
                    body = {}
                # DA returns {"status":"success", ...} or error object with status error
                if isinstance(body, dict) and body.get("status") == "error":
                    err_desc = body.get("error_description") or body.get("error") or r.text[:160]
                    errors.append(f"{name}: {err_desc}")
                else:
                    ok_n += 1
            else:
                snippet = (r.text or "")[:180].replace("\n", " ")
                errors.append(f"{name}: HTTP {r.status_code} {snippet}")
                if r.status_code in (401, 403):
                    auth_db.set_da_tokens(int(user["id"]), None, None)
                    break
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")

    return {
        "ok": ok_n > 0,
        "uploaded": ok_n,
        "total": len(files),
        "errors": errors,
        "msg": None if ok_n > 0 else (errors[0] if errors else "Upload failed"),
    }




# ====================== DeviantArt OAuth + Sta.sh (per-user keys, like desktop) ======================
_da_pending: dict[str, dict] = {}  # state -> {verifier, user_id, client_id, client_secret, ts}



@app.get("/api/da/debug")
def da_debug(request: Request):
    """Safe debug: no secrets, helps fix OAuth."""
    user = _auth_user(request)
    redirect = (os.environ.get("DA_REDIRECT_URI") or "").strip()
    if not redirect:
        redirect = (os.environ.get("APP_URL") or "").rstrip("/") + "/api/da/callback"
    cid = ""
    if user:
        cid = (user.get("da_client_id") or "")[:12]
    return {
        "logged_in": bool(user),
        "has_keys": bool(user and user.get("da_client_id") and user.get("da_client_secret")),
        "client_id_prefix": cid,
        "redirect_uri": redirect,
        "authorize_base": "https://www.deviantart.com/oauth2/authorize",
        "hint": "In DA app settings, Redirect URI must match redirect_uri EXACTLY. OAuth page URL contains /oauth2/authorize — not the DA home feed.",
    }

@app.get("/api/da/status")
def da_status(request: Request):
    user = _auth_user(request)
    if not user:
        return {"ok": False, "logged_in": False, "da": False, "has_keys": False}
    return {
        "ok": True,
        "logged_in": True,
        "da": bool(user.get("da_access_token")),
        "has_keys": bool(user.get("da_client_id") and user.get("da_client_secret")),
        "client_id": (user.get("da_client_id") or "")[:8] + "…" if user.get("da_client_id") else "",
        "email": user.get("email"),
        "redirect_hint": (os.environ.get("APP_URL") or "").rstrip("/") + "/api/da/callback",
    }


@app.post("/api/da/keys")
async def da_save_keys(request: Request):
    """Save user's own DeviantArt app Client ID / Secret (desktop-style)."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    body = await request.json()
    cid = str(body.get("client_id") or "").strip().split()[0] if str(body.get("client_id") or "").strip() else ""
    sec = str(body.get("client_secret") or "").strip().split()[0] if str(body.get("client_secret") or "").strip() else ""
    if not cid or not sec:
        return JSONResponse({"ok": False, "msg": "Enter Client ID and Client Secret"}, status_code=400)
    auth_db.set_da_keys(int(user["id"]), cid, sec)
    return {"ok": True, "msg": "Keys saved"}


@app.get("/api/da/login")
def da_login_start(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to Showcase account first"}, status_code=401)
    # Prefer user's own keys; fallback to server env
    cid = (user.get("da_client_id") or "").strip() or (os.environ.get("DA_CLIENT_ID") or "").strip()
    sec = (user.get("da_client_secret") or "").strip() or (os.environ.get("DA_CLIENT_SECRET") or "").strip()
    redirect = (os.environ.get("DA_REDIRECT_URI") or "").strip()
    if not redirect:
        redirect = (os.environ.get("APP_URL") or "").rstrip("/") + "/api/da/callback"
    if not cid or not sec:
        return JSONResponse(
            {
                "ok": False,
                "msg": "Enter your DeviantArt Client ID & Secret (create app at deviantart.com/developers). Redirect URI must be: " + redirect,
            },
            status_code=400,
        )
    import base64
    import hashlib
    from urllib.parse import urlencode

    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_hex(16)
    _da_pending[state] = {
        "verifier": verifier,
        "user_id": int(user["id"]),
        "client_id": cid,
        "client_secret": sec,
        "redirect": redirect,
        "ts": time.time(),
    }
    q = urlencode(
        {
            "response_type": "code",
            "client_id": cid,
            "redirect_uri": redirect,
            "scope": "stash publish browse",
            "duration": "permanent",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
    )
    return {"ok": True, "url": f"https://www.deviantart.com/oauth2/authorize?{q}"}


@app.get("/api/da/callback")
async def da_callback(request: Request, code: str = "", state: str = ""):
    pend = _da_pending.pop(state, None)
    if not pend or not code:
        return HTMLResponse("<h3>DeviantArt auth failed</h3><p>Close this tab and try again.</p>", status_code=400)
    try:
        import requests as rq

        r = rq.post(
            "https://www.deviantart.com/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": pend["client_id"],
                "client_secret": pend["client_secret"],
                "code": code,
                "redirect_uri": pend["redirect"],
                "code_verifier": pend["verifier"],
            },
            timeout=30,
        )
        if r.status_code != 200:
            return HTMLResponse(f"<h3>Token error</h3><pre>{_esc_html(r.text[:500])}</pre>", status_code=400)
        data = r.json()
        auth_db.set_da_tokens(
            int(pend["user_id"]),
            data.get("access_token"),
            data.get("refresh_token"),
        )
    except Exception:
        LOGGER.exception("oauth callback failed")
        return HTMLResponse("<h3>Error</h3><p>Sign-in failed. Please try again.</p>", status_code=500)
    app_url = (os.environ.get("APP_URL") or "/").rstrip("/")
    # Same idea as desktop localhost page: "Success! You can close this window."
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Success</title></head>
<body style="font-family:system-ui,sans-serif;background:#0b0b12;color:#e8e8f0;display:grid;place-items:center;min-height:100vh;margin:0">
  <div style="text-align:center;padding:32px">
    <h1 style="font-size:1.6rem;margin:0 0 12px">Success!</h1>
    <p style="opacity:.8;margin:0 0 20px">You can close this window.</p>
    <p style="font-size:13px;opacity:.55">DeviantArt access granted · Showcase Maker</p>
    <p style="margin-top:24px"><a href="{app_url}/app#da" style="color:#7b5cff">Back to tools</a></p>
  </div>
  <script>
    try {{ if (window.opener) window.opener.postMessage({{type:'da_connected'}}, '*'); }} catch(e) {{}}
    setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1500);
  </script>
</body></html>"""
    )


# ====================== Watermark live preview ======================

@app.post("/api/preview_wm")
async def preview_wm(
    request: Request,
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    wm_x: str = Form(""),
    wm_y: str = Form(""),
    auto_contrast: str = Form("0"),
    file: UploadFile = File(...),
):
    """PNG preview of watermark (supports drag position wx/wy 0..1)."""
    from PIL import ImageOps
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "File too large"}, status_code=400)
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        if max(img.size) > 1200:
            img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        suggestion = None
        if str(auto_contrast).lower() in ("1", "true", "yes", "on"):
            rgb = ImageOps.autocontrast(img.convert("RGB"), cutoff=1)
            img = rgb.convert("RGBA")
            suggestion = "Auto-contrast applied — details are clearer under the watermark."
        opacity = max(0.0, min(1.0, float(wm_opacity) / 100.0))
        corner = (wm_corner or "bl").strip().lower()
        if corner not in ("tl", "tr", "bl", "br"):
            corner = "bl"
        try:
            scale = max(0.4, min(2.5, float(wm_scale)))
        except Exception:
            scale = 1.0
        color = (wm_color or "#ffffff").strip() or "#ffffff"
        wx = wy = None
        try:
            if str(wm_x).strip() != "" and str(wm_y).strip() != "":
                wx = max(0.0, min(1.0, float(wm_x)))
                wy = max(0.0, min(1.0, float(wm_y)))
        except Exception:
            pass
        out = proc.apply_watermark(
            img, wm_text, wm_font, opacity, corner=corner, scale=scale, color=color, wx=wx, wy=wy
        )
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        if opacity > 0.45 and not suggestion:
            suggestion = "Opacity is high — try 15–25% so the watermark is less noticeable."
        headers = {}
        if suggestion:
            headers["X-WM-Suggestion"] = suggestion.encode("latin-1", "replace").decode("latin-1")
        from fastapi.responses import Response
        return Response(content=buf.getvalue(), media_type="image/png", headers=headers)
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)



# ====================== Public gallery (test) ======================



# ====================== Image Upscale (Hugging Face Space via gradio_client) ======================
# Uses public Space: https://huggingface.co/spaces/Phips/Upscaler
# Caveats: queue / cold start / rate limits on free ZeroGPU — not for production-critical path.

# Labels are UI-facing; keys must match Space dropdown values.
_UPSCALE_MODELS = [
    # Faster / illustration-friendly first
    "4xBHI_dat2_real",
    "4xNomosWebPhoto_RealPLKSR",
    "4xNomos2_hq_drct-l",
    "4xRealWebPhoto_v4_dat2",
    "4xNomosUni_rgt_multijpg",
    "4xLSDIRDAT",
    "4xNomos8kHAT-L_otf",
    "4xNomosUniDAT_otf",
]
_UPSCALE_MODEL_META = {
    "4xBHI_dat2_real": {"label": "Anime / art · fast", "group": "anime"},
    "4xNomosWebPhoto_RealPLKSR": {"label": "Photo · balanced", "group": "photo"},
    "4xNomos2_hq_drct-l": {"label": "General HQ", "group": "general"},
    "4xRealWebPhoto_v4_dat2": {"label": "Photo v4", "group": "photo"},
    "4xNomosUni_rgt_multijpg": {"label": "Universal / jpg", "group": "general"},
    "4xLSDIRDAT": {"label": "Detail (slower)", "group": "general"},
    "4xNomos8kHAT-L_otf": {"label": "8k HAT (slow)", "group": "slow"},
    "4xNomosUniDAT_otf": {"label": "Uni DAT (slow)", "group": "slow"},
}


def _run_hf_upscale(src_path: Path, model: str) -> Path:
    """Blocking call — run inside a threadpool."""
    from gradio_client import Client, handle_file

    model = model if model in _UPSCALE_MODELS else _UPSCALE_MODELS[0]
    client = Client("Phips/Upscaler")
    # API docs: /upscale_image(image, model_selection) -> (slider tuple, filepath)
    result = client.predict(
        handle_file(str(src_path)),
        model,
        api_name="/upscale_image",
    )
    out = None
    if isinstance(result, (list, tuple)):
        # prefer last filepath-like element (full-quality PNG)
        for item in reversed(result):
            if isinstance(item, str) and Path(item).is_file():
                out = Path(item)
                break
            if isinstance(item, dict) and item.get("path"):
                cand = Path(item["path"])
                if cand.is_file():
                    out = cand
                    break
            if isinstance(item, (list, tuple)):
                for sub in reversed(item):
                    if isinstance(sub, str) and Path(sub).is_file():
                        out = Path(sub)
                        break
    elif isinstance(result, str) and Path(result).is_file():
        out = Path(result)
    if out is None or not out.is_file():
        raise RuntimeError(f"Upscaler returned no file: {type(result)} {result!r}"[:300])
    return out


@app.get("/api/upscale/models")
def upscale_models():
    return {
        "ok": True,
        "models": [
            {"id": m, "label": (_UPSCALE_MODEL_META.get(m) or {}).get("label") or m,
             "group": (_UPSCALE_MODEL_META.get(m) or {}).get("group") or "general"}
            for m in _UPSCALE_MODELS
        ],
        "default": _UPSCALE_MODELS[0],
    }


@app.post("/api/upscale")
async def api_upscale(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form("4xBHI_dat2_real"),
):
    """Upscale image via external Space (Pro only)."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in required", "code": "auth"}, status_code=401)
    if not auth_db.effective_pro(user):
        return JSONResponse(
            {"ok": False, "msg": "Upscale is available for Pro subscribers", "code": "pro"},
            status_code=403,
        )
    raw = await file.read()
    if not raw:
        return JSONResponse({"ok": False, "msg": "Empty file"}, status_code=400)
    if len(raw) > min(MAX_UPLOAD_MB, 15) * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "File too large for upscale (max 15MB)"}, status_code=400)
    head = raw[:16]
    if not (
        head[:8] == b"\x89PNG\r\n\x1a\n"
        or head[:3] == b"\xff\xd8\xff"
        or (head[:4] == b"RIFF" and raw[8:12] == b"WEBP")
        or head[:6] in (b"GIF87a", b"GIF89a")
    ):
        return JSONResponse({"ok": False, "msg": "PNG/JPG/WEBP/GIF only"}, status_code=400)

    work = Path(tempfile.mkdtemp(prefix="upscale_"))
    try:
        ext = Path(file.filename or "in.png").suffix.lower() or ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            ext = ".png"
        src = work / f"in{ext}"
        src.write_bytes(raw)
        # GIF: take first frame as PNG for upscaler
        if ext == ".gif":
            try:
                im = Image.open(src)
                im.seek(0)
                src = work / "in.png"
                im.convert("RGBA").save(src, "PNG")
            except Exception as e:
                return JSONResponse({"ok": False, "msg": f"GIF read failed: {e}"}, status_code=400)

        import asyncio
        loop = asyncio.get_event_loop()
        try:
            out_path = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: _run_hf_upscale(src, (model or "").strip())),
                timeout=300.0,
            )
        except asyncio.TimeoutError:
            return JSONResponse({"ok": False, "msg": "Upscale timed out (Space busy / cold start). Try again."}, status_code=504)
        except Exception as e:
            return JSONResponse({"ok": False, "msg": f"Upscale failed: {type(e).__name__}: {e}"}, status_code=502)

        out_dir = Path(DATA) / "upscale"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{int(time.time())}_{secrets.token_hex(4)}_up.png"
        shutil.copy2(out_path, dest)
        # serve via short-lived job-like path
        return FileResponse(
            dest,
            media_type="image/png",
            filename=dest.name,
            headers={"X-Upscale-Model": (model or _UPSCALE_MODELS[0])[:64]},
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)



@app.get("/api/gallery/list")
def gallery_list(request: Request, status: str = "approved", limit: int = 40, offset: int = 0):
    viewer = _auth_user(request)
    viewer_id = int(viewer["id"]) if viewer else None
    # `status` arrives from the query string. Letting anyone pass
    # status=pending published the un-moderated queue to the whole internet and
    # made the admin-only /api/gallery/pending pointless. Only a moderator may
    # ask for anything other than the approved feed.
    if status != "approved" and not (_admin_ok(request) or _is_gallery_admin(viewer)):
        status = "approved"
    items = auth_db.gallery_list(status=status, limit=min(int(limit), 100), offset=max(0, int(offset)))
    # filter + collect ids
    filtered = []
    for it in items:
        st = str(it.get("status") or "").lower()
        if st in ("deleted", "rejected", "removed"):
            continue
        img_path = it.get("image_path") or ""
        if img_path and not Path(img_path).is_file():
            # also try relative to DATA
            if not (Path(DATA) / img_path).is_file():
                continue
        filtered.append(it)
    ids = [int(it["id"]) for it in filtered]
    likes_map = auth_db.gallery_like_counts(ids)
    comments_map = auth_db.gallery_comment_counts(ids)
    liked_set = auth_db.gallery_user_liked(viewer_id, ids) if viewer_id else set()
    out = []
    for it in filtered:
        author = it.get("display_name") or it.get("discord_username") or (it.get("email") or "anon")
        if isinstance(author, str) and "@" in author:
            author = author.split("@")[0]
        uid = it.get("user_id") or it.get("uid") or it.get("author_id")
        try:
            uid = int(uid) if uid is not None else None
        except Exception:
            uid = None
        iid = int(it["id"])
        # Always ensure public profile username for registered authors
        # so gallery → /profile/{username} works even if they never opened profile
        un = (it.get("profile_username") or "").strip()
        if uid:
            try:
                un = auth_db.ensure_profile_username(int(uid), author) or un
            except Exception:
                if not un:
                    un = f"user{uid}"
        out.append({
            "id": iid,
            "title": it.get("title") or "",
            "mode": it.get("mode") or "",
            "author": str(author)[:40],
            "user_id": uid,
            "username": un,
            "profile_url": f"/profile/{un}" if un else "",
            "avatar_url": f"/api/auth/avatar/{uid}" if uid else "",
            "url": f"/api/gallery/image/{iid}",
            "created_at": it.get("created_at"),
            "likes": likes_map.get(iid, 0),
            "comments": comments_map.get(iid, 0),
            "liked": iid in liked_set,
        })
    return {"ok": True, "items": out, "logged_in": bool(viewer)}

@app.get("/api/gallery/image/{item_id}")
def gallery_image(item_id: int):
    item = auth_db.gallery_get(item_id)
    if not item or item.get("status") != "approved":
        return JSONResponse({"ok": False}, status_code=404)
    path = Path(item["image_path"])
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path)


@app.post("/api/gallery/submit")
async def gallery_submit(
    request: Request,
    title: str = Form(""),
    mode: str = Form("workshop"),
    file: UploadFile = File(...),
):
    # Was anonymous (uid 0), so anyone could fill the disk and the public feed
    # without an account. /api/gallery/publish — the endpoint the UI actually
    # uses — has always required login; this one was the way around it.
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to publish"}, status_code=401)
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "Too large"}, status_code=400)
    ext = Path(file.filename or "x.png").suffix.lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return JSONResponse({"ok": False, "msg": "Images only"}, status_code=400)
    # Trust the bytes, not the filename: verify() parses the header, so a
    # renamed archive or script no longer lands in the gallery directory.
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Not a valid image"}, status_code=400)
    gdir = Path(DATA) / "gallery"
    gdir.mkdir(parents=True, exist_ok=True)
    uid = int(user["id"])
    sub = gdir / f"u{uid}"
    sub.mkdir(parents=True, exist_ok=True)
    name = f"{int(time.time())}_{secrets.token_hex(4)}{ext}"
    path = sub / name
    path.write_bytes(raw)
    thumb = None
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        im.thumbnail((400, 400))
        tp = path.with_suffix(".thumb.png")
        im.save(tp, "PNG")
        thumb = str(tp)
    except Exception:
        pass
    gid = auth_db.gallery_add(uid, title, mode, str(path), thumb, status="approved")
    return {"ok": True, "id": gid, "msg": "Published"}



@app.post("/api/gallery/publish")
async def gallery_publish(
    request: Request,
    mode: str = Form("workshop"),
    size: int = Form(750),
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_enable: str = Form("1"),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    wm_x: str = Form(""),
    wm_y: str = Form(""),
    auto_contrast: str = Form("0"),
    title: str = Form(""),
    file: UploadFile = File(...),
):
    """Build showcase preview (with/without WM) and submit to gallery as pending."""
    from PIL import ImageOps
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to publish"}, status_code=401)
    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "Too large"}, status_code=400)
    fname = (file.filename or "x.png").lower()
    ext = Path(fname).suffix.lower()
    # Sniff real format by magic bytes (fixes missing/wrong extension)
    head = raw[:16] if raw else b""
    is_gif = ext == ".gif" or head[:6] in (b"GIF87a", b"GIF89a")
    is_png = ext == ".png" or head[:8] == b"\x89PNG\r\n\x1a\n"
    is_jpg = ext in (".jpg", ".jpeg") or head[:3] == b"\xff\xd8\xff"
    is_webp = ext == ".webp" or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    is_bmp = ext == ".bmp" or head[:2] == b"BM"
    is_video = ext in (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v") or head[4:8] == b"ftyp"
    is_image = is_gif or is_png or is_jpg or is_webp or is_bmp
    if not is_image and not is_video:
        return JSONResponse(
            {"ok": False, "msg": "Images and GIF only (PNG/JPG/WEBP/GIF)"},
            status_code=400,
        )
    # normalize extension from sniffed type when missing/wrong
    if not ext or ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".mp4", ".webm", ".mov", ".avi", ".mkv"):
        if is_gif:
            ext = ".gif"
        elif is_png:
            ext = ".png"
        elif is_jpg:
            ext = ".jpg"
        elif is_webp:
            ext = ".webp"
        elif is_bmp:
            ext = ".bmp"
        elif is_video:
            ext = ".mp4"

    wm_on = wm_enable not in ("0", "false", "False", "")
    opacity = (wm_opacity / 100.0) if wm_on else 0.0
    text = wm_text if wm_on else ""
    color = (wm_color or "#ffffff").strip() or "#ffffff"
    corner = (wm_corner or "bl").strip().lower()
    if corner not in ("tl", "tr", "bl", "br"):
        corner = "bl"
    try:
        scale = max(0.4, min(2.5, float(wm_scale)))
    except Exception:
        scale = 1.0
    if scale > 2.5:
        scale = max(0.4, min(2.5, scale / 100.0))
    wm_x_f = wm_y_f = None
    try:
        if str(wm_x).strip() != "" and str(wm_y).strip() != "":
            wm_x_f = max(0.0, min(1.0, float(wm_x)))
            wm_y_f = max(0.0, min(1.0, float(wm_y)))
    except Exception:
        pass
    try:
        size_i = int(size)
    except Exception:
        size_i = 750
    if size_i not in (630, 640, 750, 800):
        size_i = 750

    import tempfile
    work = Path(tempfile.mkdtemp(prefix="sm_gal_"))
    try:
        data = None
        out_ext = ".png"

        if is_gif or is_video:
            # Animated / video: process full pipeline, keep animation in gallery
            src_ext = ext if ext else (".gif" if is_gif else ".mp4")
            if is_gif and raw[:6] in (b"GIF87a", b"GIF89a"):
                src_ext = ".gif"
            src = work / f"source{src_ext}"
            src.write_bytes(raw)
            use_video = is_video or src_ext in (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v")
            if use_video:
                if mode == "workshop":
                    paths = proc.process_video_workshop(
                        src, work, fps=12, width=size_i,
                        wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                        duration=8.0, wm_corner=corner, wm_scale=scale,
                        wm_x=wm_x_f, wm_y=wm_y_f, encoder="gifski",
                    )
                    pick = paths.get("full_with_bars.gif") or paths.get("full_original.gif")
                elif mode == "featured":
                    paths = proc.process_video_featured(
                        src, work, fps=12, duration=8.0, encoder="gifski",
                        wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                        wm_corner=corner, wm_scale=scale, wm_x=wm_x_f, wm_y=wm_y_f,
                    )
                    pick = (
                        paths.get("full_with_watermark.gif")
                        or paths.get("full_with_bars.gif")
                        or paths.get("featured_630.gif")
                        or paths.get("full_original.gif")
                    )
                else:
                    paths = proc.process_video_split(
                        src, work, fps=12,
                        wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                        duration=8.0, wm_corner=corner, wm_scale=scale,
                        wm_x=wm_x_f, wm_y=wm_y_f, encoder="gifski",
                    )
                    pick = paths.get("full_with_bars.gif") or paths.get("full_original.gif") or paths.get("center_506.gif")
            elif mode == "workshop":
                paths = proc.process_gif_workshop(
                    src, work,
                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                    wm_color=color, wm_corner=corner, wm_scale=scale,
                    wm_x=wm_x_f, wm_y=wm_y_f, encoder="gifski", fps=12,
                )
                pick = paths.get("full_with_bars.gif") or paths.get("full_original.gif")
            elif mode == "featured":
                paths = proc.process_gif_featured(
                    src, work, fps=12, encoder="gifski",
                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                    wm_color=color, wm_corner=corner, wm_scale=scale,
                    wm_x=wm_x_f, wm_y=wm_y_f,
                )
                pick = (
                    paths.get("full_with_watermark.gif")
                    or paths.get("full_with_bars.gif")
                    or paths.get("featured_630.gif")
                    or paths.get("full_original.gif")
                )
            else:
                paths = proc.process_gif_split(
                    src, work, fps=12,
                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                    wm_color=color, wm_corner=corner, wm_scale=scale,
                    wm_x=wm_x_f, wm_y=wm_y_f, encoder="gifski",
                )
                pick = paths.get("full_with_bars.gif") or paths.get("full_original.gif") or paths.get("center_506.gif")
            if pick and Path(pick).is_file():
                data = Path(pick).read_bytes()
                out_ext = ".gif"
            else:
                # fallback: first frame as static
                im = Image.open(io.BytesIO(raw))
                im.seek(0)
                img = im.convert("RGBA")
                is_gif = False  # fall through to static path below using img
                # handled in static block
                buf = io.BytesIO()
                if mode == "workshop":
                    if img.size[0] != size_i:
                        nh = max(1, int(img.size[1] * (size_i / max(1, img.size[0]))))
                        img = img.resize((size_i, nh), Image.Resampling.LANCZOS)
                    parts = proc.process_image_workshop(
                        img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                    )
                    data = parts.get("full_with_bars.png") or parts.get("full_original.png")
                elif mode == "featured":
                    parts = proc.process_image_featured(
                        img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                    )
                    data = (
                        parts.get("full_with_watermark.png")
                        or parts.get("full_with_bars.png")
                        or parts.get("featured_630.png")
                        or parts.get("full_original.png")
                    )
                else:
                    parts = proc.process_image_split(
                        img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                    )
                    data = parts.get("full_with_bars.png") or parts.get("full_original.png")
                out_ext = ".png"
        else:
            img = Image.open(io.BytesIO(raw))
            img.load()
            if max(img.size) > 4096:
                img.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
            if str(auto_contrast).lower() in ("1", "true", "yes", "on"):
                img = ImageOps.autocontrast(img.convert("RGB"), cutoff=1)
            img = img.convert("RGBA")
            if mode == "workshop" and img.size[0] != size_i:
                nh = max(1, int(img.size[1] * (size_i / max(1, img.size[0]))))
                img = img.resize((size_i, nh), Image.Resampling.LANCZOS)
            if mode == "workshop":
                parts = proc.process_image_workshop(
                    img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                )
                data = parts.get("full_with_bars.png") or parts.get("full_original.png")
            elif mode == "featured":
                parts = proc.process_image_featured(
                    img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                )
                data = (
                    parts.get("full_with_watermark.png")
                    or parts.get("full_with_bars.png")
                    or parts.get("featured_630.png")
                    or parts.get("full_original.png")
                )
            else:
                parts = proc.process_image_split(
                    img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                )
                data = parts.get("full_with_bars.png") or parts.get("full_original.png")
            out_ext = ".png"

        if not data:
            return JSONResponse({"ok": False, "msg": "Nothing to publish"}, status_code=400)

        gdir = Path(DATA) / "gallery"
        gdir.mkdir(parents=True, exist_ok=True)
        uid = int(user["id"])
        sub = gdir / f"u{uid}"
        sub.mkdir(parents=True, exist_ok=True)
        name = f"{int(time.time())}_{secrets.token_hex(4)}_{mode}{out_ext}"
        path = sub / name
        path.write_bytes(data)
        thumb = None
        try:
            im = Image.open(io.BytesIO(data))
            im.seek(0)
            im = im.convert("RGBA")
            im.thumbnail((400, 400))
            tp = path.with_name(path.stem + ".thumb.png")
            im.save(tp, "PNG")
            thumb = str(tp)
        except Exception:
            pass
        ttl = (title or "").strip() or f"{mode} showcase"
        gid = auth_db.gallery_add(uid, ttl, mode, str(path), thumb, status="approved")
        return {"ok": True, "id": gid, "msg": "Published"}
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"{type(e).__name__}: {e}"}, status_code=500)
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.post("/api/gallery/mod/{item_id}")
async def gallery_mod(item_id: int, request: Request):
    user = _auth_user(request)
    if not (_admin_ok(request) or _is_gallery_admin(user)):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    body = await request.json()
    status = str(body.get("status") or "")
    if not auth_db.gallery_set_status(item_id, status):
        return JSONResponse({"ok": False, "msg": "Bad status"}, status_code=400)
    return {"ok": True, "id": item_id, "status": status}


@app.delete("/api/gallery/{item_id}")
@app.post("/api/gallery/delete/{item_id}")
async def gallery_delete(item_id: int, request: Request):
    """Admin (or post owner) can remove a gallery item."""
    user = _auth_user(request)
    is_admin = _admin_ok(request) or _is_gallery_admin(user)
    item = auth_db.gallery_get(item_id)
    if not item:
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    owner_id = item.get("user_id") or item.get("uid") or item.get("author_id")
    is_owner = False
    if user and owner_id is not None:
        try:
            is_owner = int(user.get("id")) == int(owner_id)
        except Exception:
            is_owner = False
    if not (is_admin or is_owner):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)

    # Remove files first so list won't show a broken card even if DB update is partial
    try:
        p = Path(item.get("image_path") or "")
        if p.is_file():
            p.unlink(missing_ok=True)
        thumb = item.get("thumb_path") or ""
        if thumb:
            Path(thumb).unlink(missing_ok=True)
        elif p:
            tp = p.with_name(p.stem + ".thumb.png")
            if tp.is_file():
                tp.unlink(missing_ok=True)
    except Exception:
        pass

    # Mark as not public — try several status values (auth_db may whitelist)
    marked = False
    for st in ("deleted", "rejected", "removed"):
        try:
            if auth_db.gallery_set_status(item_id, st):
                marked = True
                break
        except Exception:
            continue

    # Hard delete from SQLite if status update failed
    if not marked:
        try:
            conn = auth_db.connect() if hasattr(auth_db, "connect") else None
            if conn is None and hasattr(auth_db, "get_conn"):
                conn = auth_db.get_conn()
            if conn is None:
                # fallback: open DATA db the same way auth often does
                db_path = Path(os.environ.get("DATA_DIR") or DATA) / "auth.db"
                if not db_path.is_file():
                    db_path = Path(DATA) / "users.db"
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                own = True
            else:
                own = False
            try:
                conn.execute("DELETE FROM gallery WHERE id=?", (int(item_id),))
                conn.commit()
                marked = True
            finally:
                if own:
                    conn.close()
        except Exception:
            pass

    return {"ok": True, "id": item_id, "status": "deleted", "db": marked}




# ====================== Gallery social API ======================

@app.post("/api/gallery/{item_id}/like")
async def gallery_like(item_id: int, request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to like"}, status_code=401)
    liked, total = auth_db.gallery_like_toggle(int(user["id"]), int(item_id))
    return {"ok": True, "liked": liked, "likes": total}


@app.get("/api/gallery/{item_id}/comments")
def gallery_comments(item_id: int, request: Request):
    rows = auth_db.gallery_list_comments(int(item_id))
    viewer = _auth_user(request)
    stats = auth_db.gallery_item_stats(int(item_id), int(viewer["id"]) if viewer else None)
    out = []
    for r in rows:
        author = r.get("display_name") or r.get("discord_username") or (r.get("email") or "anon")
        if isinstance(author, str) and "@" in author:
            author = author.split("@")[0]
        uid = r.get("user_id")
        out.append({
            "id": r["id"],
            "parent_id": r.get("parent_id"),
            "body": r.get("body") or "",
            "user_id": uid,
            "author": str(author)[:40],
            "avatar_url": f"/api/auth/avatar/{uid}" if uid else "",
            "created_at": r.get("created_at"),
        })
    # IMPORTANT: do not **stats after "comments" — stats also has key "comments" (int count)
    return {
        "ok": True,
        "comments": out,
        "likes": stats.get("likes", 0),
        "liked": stats.get("liked", False),
        "comment_count": stats.get("comments", len(out)),
    }


@app.post("/api/gallery/{item_id}/comments")
async def gallery_post_comment(item_id: int, request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to comment"}, status_code=401)
    try:
        body_json = await request.json()
    except Exception:
        body_json = {}
    body = str(body_json.get("body") or "").strip()
    parent_id = body_json.get("parent_id")
    try:
        parent_id = int(parent_id) if parent_id not in (None, "", 0, "0") else None
    except Exception:
        parent_id = None
    if not body:
        return JSONResponse({"ok": False, "msg": "Empty comment"}, status_code=400)
    row = auth_db.gallery_add_comment(int(user["id"]), int(item_id), body, parent_id)
    if not row:
        return JSONResponse({"ok": False, "msg": "Failed"}, status_code=400)
    author = row.get("display_name") or row.get("discord_username") or (row.get("email") or user.get("email") or "you")
    if isinstance(author, str) and "@" in author:
        author = author.split("@")[0]
    uid = row.get("user_id") or user["id"]
    return {
        "ok": True,
        "comment": {
            "id": row.get("id"),
            "parent_id": row.get("parent_id"),
            "body": row.get("body") or body,
            "user_id": uid,
            "author": str(author)[:40],
            "avatar_url": f"/api/auth/avatar/{uid}",
            "created_at": row.get("created_at"),
        },
    }


@app.get("/api/notifications")
def api_notifications(request: Request, limit: int = 40):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in"}, status_code=401)
    rows = auth_db.notifications_list(int(user["id"]), limit=min(int(limit), 80))
    unread = auth_db.notifications_unread_count(int(user["id"]))
    out = []
    for r in rows:
        actor = r.get("display_name") or r.get("discord_username") or (r.get("email") or "")
        if isinstance(actor, str) and "@" in actor:
            actor = actor.split("@")[0]
        aid = r.get("actor_id")
        out.append({
            "id": r["id"],
            "kind": r.get("kind"),
            "body": r.get("body") or "",
            "item_id": r.get("item_id"),
            "comment_id": r.get("comment_id"),
            "is_read": bool(r.get("is_read")),
            "created_at": r.get("created_at"),
            "actor": str(actor)[:40],
            "actor_avatar": f"/api/auth/avatar/{aid}" if aid else "",
        })
    return {"ok": True, "items": out, "unread": unread}


@app.post("/api/notifications/read")
async def api_notifications_read(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    ids = body.get("ids")
    if ids is not None and not isinstance(ids, list):
        ids = None
    n = auth_db.notifications_mark_read(int(user["id"]), [int(x) for x in ids] if ids else None)
    return {"ok": True, "marked": n, "unread": auth_db.notifications_unread_count(int(user["id"]))}


@app.get("/api/notifications/unread")
def api_notifications_unread(request: Request):
    user = _auth_user(request)
    if not user:
        return {"ok": True, "unread": 0, "logged_in": False}
    return {"ok": True, "unread": auth_db.notifications_unread_count(int(user["id"])), "logged_in": True}


@app.get("/api/gallery/pending")
async def gallery_pending(request: Request):
    user = _auth_user(request)
    if not (_admin_ok(request) or _is_gallery_admin(user)):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    return {"ok": True, "items": auth_db.gallery_list(status="pending", limit=100)}

@app.get("/api/gallery/am_admin")
def gallery_am_admin(request: Request):
    user = _auth_user(request)
    return {"ok": True, "admin": _is_gallery_admin(user), "email": (user or {}).get("email")}


@app.get("/gallery", response_class=HTMLResponse)
def gallery_page():
    path = STATIC / "gallery.html"
    if path.is_file():
        return HTMLResponse(path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Gallery</h1><p>Add static/gallery.html</p>")


# ====================== Discord OAuth login ======================

def _discord_redirect_uri() -> str:
    """Build redirect URI; collapse accidental double slashes in path."""
    redirect = (os.environ.get("DISCORD_REDIRECT_URI") or "").strip()
    if not redirect:
        base = (os.environ.get("APP_URL") or "").strip().rstrip("/")
        redirect = base + "/api/auth/discord/callback"
    if "://" in redirect:
        scheme, rest = redirect.split("://", 1)
        while "//" in rest:
            rest = rest.replace("//", "/")
        redirect = scheme + "://" + rest
    return redirect


@app.get("/api/auth/discord/login")
def discord_login_start(request: Request):
    cid = (os.environ.get("DISCORD_CLIENT_ID") or "").strip()
    secret = (os.environ.get("DISCORD_CLIENT_SECRET") or "").strip()
    redirect = _discord_redirect_uri()
    if not cid or not secret:
        return JSONResponse(
            {"ok": False, "msg": "DISCORD_CLIENT_ID / DISCORD_CLIENT_SECRET not set on server"},
            status_code=503,
        )
    from urllib.parse import urlencode
    state = secrets.token_hex(16)
    # store state briefly in memory
    if not hasattr(app.state, "discord_pending"):
        app.state.discord_pending = {}
    app.state.discord_pending[state] = time.time()
    q = urlencode({
        "client_id": cid,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "identify email",
        "state": state,
        "prompt": "consent",
    })
    return {"ok": True, "url": f"https://discord.com/api/oauth2/authorize?{q}"}


@app.get("/api/auth/discord/callback")
async def discord_callback(request: Request, code: str = "", state: str = ""):
    pending = getattr(app.state, "discord_pending", {})
    if state not in pending:
        return HTMLResponse("<h3>Discord auth failed (bad state)</h3>", status_code=400)
    pending.pop(state, None)
    cid = (os.environ.get("DISCORD_CLIENT_ID") or "").strip()
    secret = (os.environ.get("DISCORD_CLIENT_SECRET") or "").strip()
    redirect = _discord_redirect_uri()
    try:
        import requests as rq
        tok = rq.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": cid,
                "client_secret": secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if tok.status_code != 200:
            return HTMLResponse(f"<h3>Token error</h3><pre>{_esc_html(tok.text[:400])}</pre>", status_code=400)
        access = tok.json().get("access_token")
        me = rq.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access}"},
            timeout=20,
        )
        if me.status_code != 200:
            return HTMLResponse(f"<h3>User error</h3><pre>{_esc_html(me.text[:400])}</pre>", status_code=400)
        u = me.json()
        did = str(u.get("id") or "")
        uname = u.get("global_name") or u.get("username") or "discord"
        email = u.get("email")
        ok, msg, token = auth_db.register_or_login_discord(did, uname, email)
        if not ok or not token:
            return HTMLResponse(f"<h3>{_esc_html(msg)}</h3>", status_code=400)
        app_url = (os.environ.get("APP_URL") or "/").rstrip("/")
        resp = HTMLResponse(
            f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>OK</title></head>
<body style="font-family:system-ui;background:#0b0b12;color:#eee;display:grid;place-items:center;min-height:100vh;margin:0">
<div style="text-align:center"><h1>Discord connected</h1>
<p>You can close this window.</p>
<a href="{app_url}/app" style="color:#7b5cff">Back to app</a></div>
<script>
try {{ localStorage.setItem('sm_session', {token!r}); }} catch(e) {{}}
try {{ if (window.opener) window.opener.postMessage({{type:'discord_login', token:{token!r}}}, '*'); }} catch(e) {{}}
setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1200);
</script></body></html>"""
        )
        return _attach_session_cookie(resp, token, request)
    except Exception:
        LOGGER.exception("oauth callback failed")
        return HTMLResponse("<h3>Error</h3><p>Sign-in failed. Please try again.</p>", status_code=500)








# ====================== Google OAuth login ======================

def _google_redirect_uri() -> str:
    redirect = (os.environ.get("GOOGLE_REDIRECT_URI") or "").strip()
    if not redirect:
        base = (os.environ.get("APP_URL") or "").strip().rstrip("/")
        redirect = base + "/api/auth/google/callback"
    if "://" in redirect:
        scheme, rest = redirect.split("://", 1)
        while "//" in rest:
            rest = rest.replace("//", "/")
        redirect = scheme + "://" + rest
    return redirect


@app.get("/api/auth/google/login")
def google_login_start(request: Request):
    cid = (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()
    secret = (os.environ.get("GOOGLE_CLIENT_SECRET") or "").strip()
    redirect = _google_redirect_uri()
    if not cid or not secret:
        return JSONResponse(
            {"ok": False, "msg": "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set on server"},
            status_code=503,
        )
    from urllib.parse import urlencode
    state = secrets.token_hex(16)
    if not hasattr(app.state, "google_pending"):
        app.state.google_pending = {}
    app.state.google_pending[state] = time.time()
    q = urlencode({
        "client_id": cid,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    return {"ok": True, "url": f"https://accounts.google.com/o/oauth2/v2/auth?{q}"}


@app.get("/api/auth/google/callback")
async def google_callback(request: Request, code: str = "", state: str = ""):
    pending = getattr(app.state, "google_pending", {})
    if state not in pending:
        return HTMLResponse("<h3>Google auth failed (bad state)</h3>", status_code=400)
    pending.pop(state, None)
    cid = (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()
    secret = (os.environ.get("GOOGLE_CLIENT_SECRET") or "").strip()
    redirect = _google_redirect_uri()
    try:
        import requests as rq
        tok = rq.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": cid,
                "client_secret": secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if tok.status_code != 200:
            return HTMLResponse(f"<h3>Token error</h3><pre>{_esc_html(tok.text[:400])}</pre>", status_code=400)
        access = tok.json().get("access_token")
        me = rq.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access}"},
            timeout=20,
        )
        if me.status_code != 200:
            return HTMLResponse(f"<h3>User error</h3><pre>{_esc_html(me.text[:400])}</pre>", status_code=400)
        u = me.json()
        gid = str(u.get("sub") or "")
        uname = u.get("name") or (u.get("email") or "google").split("@")[0]
        email = u.get("email")
        ok, msg, token = auth_db.register_or_login_google(gid, email, uname)
        if not ok or not token:
            return HTMLResponse(f"<h3>{_esc_html(msg)}</h3>", status_code=400)
        app_url = (os.environ.get("APP_URL") or "/").rstrip("/")
        resp = HTMLResponse(
            f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>OK</title></head>
<body style="font-family:system-ui;background:#0b0b12;color:#eee;display:grid;place-items:center;min-height:100vh;margin:0">
<div style="text-align:center"><h1>Google connected</h1>
<p>You can close this window.</p>
<a href="{app_url}/app" style="color:#7b5cff">Back to app</a></div>
<script>
try {{ localStorage.setItem('sm_session', {token!r}); }} catch(e) {{}}
try {{ if (window.opener) window.opener.postMessage({{type:'google_login', token:{token!r}}}, '*'); }} catch(e) {{}}
setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1200);
</script></body></html>"""
        )
        return _attach_session_cookie(resp, token, request)
    except Exception:
        LOGGER.exception("oauth callback failed")
        return HTMLResponse("<h3>Error</h3><p>Sign-in failed. Please try again.</p>", status_code=500)




# ====================== Telegram Login Widget ======================

def _telegram_bot_token() -> str:
    return (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()


def _telegram_bot_username() -> str:
    return (os.environ.get("TELEGRAM_BOT_USERNAME") or "SteamMakerBot").strip().lstrip("@")


def _verify_telegram_login(data: dict) -> bool:
    """Official HMAC-SHA256 check: https://core.telegram.org/widgets/login"""
    token = _telegram_bot_token()
    if not token or "hash" not in data:
        return False
    received = str(data.get("hash") or "")
    check = {k: str(v) for k, v in data.items() if k != "hash" and v is not None and str(v) != ""}
    data_check_string = "\n".join(f"{k}={check[k]}" for k in sorted(check.keys()))
    secret_key = hashlib.sha256(token.encode("utf-8")).digest()
    calculated = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(calculated, received):
        return False
    try:
        auth_date = int(check.get("auth_date") or 0)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - auth_date) > 86400:
        return False
    return True


@app.get("/api/auth/telegram/config")
def telegram_config():
    uname = _telegram_bot_username()
    ready = bool(_telegram_bot_token() and uname)
    return {
        "ok": ready,
        "bot_username": uname if ready else "",
        "msg": None if ready else "TELEGRAM_BOT_TOKEN / TELEGRAM_BOT_USERNAME not set",
    }


@app.post("/api/auth/telegram")
async def telegram_auth(request: Request):
    """Receive Login Widget payload, verify hash, create session."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "msg": "Bad payload"}, status_code=400)
    if not _telegram_bot_token():
        return JSONResponse({"ok": False, "msg": "Telegram auth not configured"}, status_code=503)
    if not _verify_telegram_login(body):
        return JSONResponse({"ok": False, "msg": "Invalid Telegram signature"}, status_code=401)
    tid = str(body.get("id") or "")
    if not tid:
        return JSONResponse({"ok": False, "msg": "Missing Telegram id"}, status_code=400)
    ok, msg, token = auth_db.register_or_login_telegram(
        telegram_id=tid,
        username=body.get("username"),
        first_name=body.get("first_name"),
        last_name=body.get("last_name"),
        photo_url=body.get("photo_url"),
    )
    if not ok or not token:
        return JSONResponse({"ok": False, "msg": msg or "Auth failed"}, status_code=400)
    resp = JSONResponse({"ok": True, "token": token, "msg": "OK"})
    return _attach_session_cookie(resp, token, request)


@app.get("/api/auth/telegram/callback")
async def telegram_callback(request: Request):
    """Fallback: widget redirect with query params."""
    data = dict(request.query_params)
    if not _verify_telegram_login(data):
        return HTMLResponse("<h3>Telegram auth failed</h3>", status_code=400)
    tid = str(data.get("id") or "")
    ok, msg, token = auth_db.register_or_login_telegram(
        telegram_id=tid,
        username=data.get("username"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        photo_url=data.get("photo_url"),
    )
    if not ok or not token:
        return HTMLResponse(f"<h3>{_esc_html(msg)}</h3>", status_code=400)
    app_url = (os.environ.get("APP_URL") or "/").rstrip("/")
    resp = HTMLResponse(
        f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>OK</title></head>
<body style="font-family:system-ui;background:#0b0b12;color:#eee;display:grid;place-items:center;min-height:100vh;margin:0">
<div style="text-align:center"><h1>Telegram connected</h1>
<p>You can close this window.</p>
<a href="{app_url}/app" style="color:#7b5cff">Back to app</a></div>
<script>
try {{ localStorage.setItem('sm_session', {token!r}); }} catch(e) {{}}
try {{ if (window.opener) window.opener.postMessage({{type:'telegram_login', token:{token!r}}}, '*'); }} catch(e) {{}}
setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1200);
</script></body></html>"""
    )
    return _attach_session_cookie(resp, token, request)



# ====================== Character + background compose ======================

@app.post("/api/compose")
async def api_compose(
    request: Request,
    chroma_key: str = Form("auto"),
    chroma_tol: float = Form(55),
    feather: float = Form(1.6),
    scale: float = Form(1.0),
    offset_x: float = Form(0.5),
    offset_y: float = Form(1.0),
    width: int = Form(750),
    gif_encoder: str = Form("gifski"),
    fps: int = Form(12),
    background: UploadFile = File(...),
    character: UploadFile = File(...),
):
    """Composite character (PNG/GIF, optional chromakey) onto background. Returns PNG or GIF."""
    import tempfile
    bg_raw = await background.read()
    ch_raw = await character.read()
    if len(bg_raw) > MAX_UPLOAD_MB * 1024 * 1024 or len(ch_raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "File too large"}, status_code=400)
    try:
        size_i = int(width)
    except Exception:
        size_i = 750
    if size_i not in (630, 640, 750, 800, 1920):
        size_i = 750
    try:
        bg = Image.open(io.BytesIO(bg_raw)).convert("RGBA")
        # fit background to target width (Steam workshop style)
        if bg.width != size_i:
            nh = max(1, int(bg.height * (size_i / max(1, bg.width))))
            bg = bg.resize((size_i, nh), Image.Resampling.LANCZOS)

        ch_name = (character.filename or "char.png").lower()
        ch_ext = Path(ch_name).suffix.lower()
        key = (chroma_key or "auto").strip().lower()
        try:
            tol = float(chroma_tol)
        except Exception:
            tol = 40.0
        try:
            feather_f = max(0.0, min(4.0, float(feather)))
        except Exception:
            feather_f = 1.6
        try:
            sc = max(0.05, min(4.0, float(scale)))
        except Exception:
            sc = 1.0
        try:
            ox = max(0.0, min(1.0, float(offset_x)))
            oy = max(0.0, min(1.0, float(offset_y)))
        except Exception:
            ox, oy = 0.5, 1.0

        video_exts = (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v")
        is_video = ch_ext in video_exts
        is_anim = ch_ext in (".gif", ".webp") or is_video
        n_frames = 1
        if ch_ext in (".gif", ".webp") and not is_video:
            try:
                with Image.open(io.BytesIO(ch_raw)) as im:
                    n_frames = int(getattr(im, "n_frames", 1) or 1)
            except Exception:
                n_frames = 1

        from fastapi.responses import Response

        if is_video or (is_anim and n_frames > 1):
            tmp = Path(tempfile.mkdtemp(prefix="sm_compose_"))
            try:
                # write original character
                cpath = tmp / f"char{ch_ext or '.bin'}"
                cpath.write_bytes(ch_raw)
                gif_char = cpath
                if is_video:
                    gif_char = tmp / "char.gif"
                    # convert video → gif (short clip for character loops)
                    proc.media_to_gif(cpath, gif_char, fps=12, width=min(bg.width, 800), duration=8)
                    if not gif_char.is_file():
                        return JSONResponse({"ok": False, "msg": "Video→GIF failed (ffmpeg?)"}, status_code=500)
                frames, durs = proc.compose_animated(
                    bg, gif_char,
                    chroma_key=key,
                    chroma_tol=tol,
                    scale=sc,
                    offset_x=ox,
                    offset_y=oy,
                    feather=feather_f,
                )
                out = tmp / "composed.gif"
                enc = (gif_encoder or "ffmpeg").strip().lower()
                if enc not in ("ffmpeg", "gifski", "pillow"):
                    enc = "ffmpeg"
                try:
                    fps_i = max(5, min(30, int(fps)))
                except Exception:
                    fps_i = 12
                if enc == "pillow":
                    frames_p = [proc._quantize_rgba_for_gif(f) for f in frames]
                    proc._save_animated_gif(frames_p, durs, out)
                else:
                    fdir = tmp / "frames"
                    fdir.mkdir(parents=True, exist_ok=True)
                    for i, fr in enumerate(frames):
                        fr.convert("RGBA").save(fdir / f"frame_{i:04d}.png")
                    try:
                        proc.encode_gif_from_png_sequence(fdir, out, fps=fps_i, encoder=enc)
                    except Exception:
                        # fallback pillow
                        frames_p = [proc._quantize_rgba_for_gif(f) for f in frames]
                        proc._save_animated_gif(frames_p, durs, out)
                if not out.is_file():
                    return JSONResponse({"ok": False, "msg": "GIF encode failed"}, status_code=500)
                try:
                    proc.ensure_under_mb(out)
                except Exception:
                    pass
                data = out.read_bytes()
                return Response(
                    content=data,
                    media_type="image/gif",
                    headers={
                        "Content-Disposition": 'attachment; filename="composed.gif"',
                        "X-Compose-Type": "gif",
                        "X-Compose-Encoder": enc,
                        "X-Compose-Size-MB": f"{len(data)/(1024*1024):.2f}",
                    },
                )
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        else:
            char = Image.open(io.BytesIO(ch_raw)).convert("RGBA")
            composed = proc.compose_static(
                bg, char,
                chroma_key=key,
                chroma_tol=tol,
                scale=sc,
                offset_x=ox,
                offset_y=oy,
                feather=feather_f,
            )
            buf = io.BytesIO()
            composed.save(buf, format="PNG")
            return Response(
                content=buf.getvalue(),
                media_type="image/png",
                headers={
                    "Content-Disposition": 'attachment; filename="composed.png"',
                    "X-Compose-Type": "png",
                },
            )
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"{type(e).__name__}: {e}"}, status_code=500)


# ====================== Profile builder API (Steam catalogs, projects) ======================
try:
    import tools_api

    tools_api.init(
        quota_state=quota_state,
        auth_user=_auth_user,
        DATA=DATA,
        JOBS=JOBS,
        MAX_UPLOAD_MB=MAX_UPLOAD_MB,
        FREE_LIMIT=FREE_LIMIT,
    )
    app.include_router(tools_api.router)
    LOGGER.info("tools_api mounted")
except Exception as e:
    # The profile builder is optional and must never prevent the rest of the site from starting.
    LOGGER.exception("tools_api not mounted: %s", e)


# ====================== Steam OpenID login ======================
def _steam_realm() -> str:
    base = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    if not base:
        base = f"http://{HOST}:{PORT}"
    return base


@app.get("/api/auth/steam/login")
def steam_login_start(request: Request):
    """Start Steam OpenID 2.0 sign-in (no API key required for OpenID)."""
    from urllib.parse import urlencode
    realm = _steam_realm()
    return_to = realm + "/api/auth/steam/callback"
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return {"ok": True, "url": "https://steamcommunity.com/openid/login?" + urlencode(params)}


@app.get("/api/auth/steam/callback")
async def steam_callback(request: Request):
    """Verify Steam OpenID assertion, create session, pull public profile snapshot."""
    import requests as _req
    q = dict(request.query_params)
    # local verify with Steam
    payload = {k: v for k, v in q.items()}
    payload["openid.mode"] = "check_authentication"
    try:
        vr = _req.post(
            "https://steamcommunity.com/openid/login",
            data=payload,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 ShowcaseMaker"},
        )
        if "is_valid:true" not in (vr.text or "").lower():
            return HTMLResponse("<h3>Steam login failed (invalid assertion)</h3>", status_code=400)
        claimed = q.get("openid.claimed_id") or q.get("openid.identity") or ""
        m = re.search(r"/openid/id/(\d{17})", claimed)
        if not m:
            return HTMLResponse("<h3>Steam login failed (no steamid)</h3>", status_code=400)
        steam_id = m.group(1)
        # persona name via public XML
        persona = f"steam_{steam_id[-6:]}"
        profile_data = None
        try:
            import steam_catalog
            pr = steam_catalog.profile(f"https://steamcommunity.com/profiles/{steam_id}")
            if pr.get("ok") and pr.get("profile"):
                profile_data = pr["profile"]
                persona = profile_data.get("name") or persona
        except Exception:
            LOGGER.exception("steam profile snapshot failed")
        ok, msg, token = auth_db.register_or_login_steam(steam_id, persona)
        if not ok or not token:
            return HTMLResponse(f"<h3>Login error: {html.escape(msg)}</h3>", status_code=400)
        user = auth_db.user_by_token(token)
        if user and profile_data:
            try:
                auth_db.save_steam_profile_snapshot(int(user["id"]), profile_data)
                auth_db.ensure_profile_username(int(user["id"]), persona)
                # download avatar into local avatars store
                av = (profile_data.get("avatar") or "").strip()
                if av:
                    try:
                        import requests as _rq
                        ar = _rq.get(av, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
                        if ar.status_code == 200 and ar.content[:3] != b"<!":
                            adir = DATA / "avatars"
                            adir.mkdir(parents=True, exist_ok=True)
                            ext = ".jpg"
                            ctype = (ar.headers.get("Content-Type") or "").lower()
                            if "png" in ctype: ext = ".png"
                            elif "webp" in ctype: ext = ".webp"
                            rel = f"avatars/{int(user['id'])}{ext}"
                            (DATA / rel).write_bytes(ar.content)
                            auth_db.update_profile(int(user["id"]), display_name=persona, avatar_path=rel)
                    except Exception:
                        LOGGER.exception("steam avatar download")
            except Exception:
                LOGGER.exception("save steam snapshot")
        resp = HTMLResponse(
            f"""<!doctype html><html><body style="background:#0b0f14;color:#fff;font-family:sans-serif;display:grid;place-items:center;height:100vh">
<p>Steam OK — можно закрыть окно</p>
<script>
try {{ if (window.opener) window.opener.postMessage({{type:'steam_login', token:{token!r}}}, '*'); }} catch(e) {{}}
try {{ localStorage.setItem('sm_session', {token!r}); }} catch(e) {{}}
setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} location.href='/profile'; }}, 600);
</script></body></html>"""
        )
        return _attach_session_cookie(resp, token, request)
    except Exception as e:
        LOGGER.exception("steam callback")
        return HTMLResponse(f"<h3>Steam error: {html.escape(str(e))}</h3>", status_code=500)


@app.get("/api/profile/steam-snapshot")
def api_profile_steam_snapshot(request: Request):
    """Return saved Steam profile JSON for the logged-in user (or ?user_id= for public)."""
    uid = None
    q_uid = (request.query_params.get("user_id") or "").strip()
    if q_uid.isdigit():
        uid = int(q_uid)
    else:
        user = _auth_user(request)
        if not user:
            return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
        uid = int(user["id"])
    snap = auth_db.get_steam_profile_snapshot(uid)
    if not snap:
        return JSONResponse({"ok": False, "msg": "No Steam profile linked"}, status_code=404)
    return {"ok": True, "profile": snap}


@app.post("/api/profile/steam-import")
async def api_profile_steam_import(request: Request):
    """Re-fetch Steam profile for logged-in user (by steam_id or body.url) and save snapshot."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    url = (body.get("url") or "").strip()
    if not url:
        # try linked steam id
        c_user = auth_db.user_by_token(request.cookies.get("sm_session") or "")
        # fallthrough: use steam from snapshot
        snap = auth_db.get_steam_profile_snapshot(int(user["id"]))
        if snap and snap.get("steamid"):
            url = f"https://steamcommunity.com/profiles/{snap['steamid']}"
        elif snap and snap.get("url"):
            url = snap["url"]
    if not url:
        return JSONResponse({"ok": False, "msg": "No Steam URL"}, status_code=400)
    try:
        import steam_catalog
        pr = steam_catalog.profile(url)
        if not pr.get("ok"):
            return JSONResponse(pr, status_code=400)
        auth_db.save_steam_profile_snapshot(int(user["id"]), pr["profile"])
        return {"ok": True, "profile": pr["profile"]}
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)




if __name__ == "__main__":
    import uvicorn
    print(f"\n  Showcase Maker WEB  →  http://{HOST}:{PORT}")
    print(f"  FFmpeg: {proc.find_ffmpeg() or 'НЕ НАЙДЕН'}")
    print(f"  Free limit: {FREE_LIMIT}/day  |  Unlock: SHOWCASE-WEB-PRO\n")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
