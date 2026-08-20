#!/usr/bin/env python3
"""
Showcase Maker WEB — локальный / серверный прототип
Запуск:  python main.py
URL:     http://127.0.0.1:8080
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import secrets
import shutil
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import auth_db

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DATA_DIR") or (ROOT / "data"))
JOBS = DATA / "jobs"
USAGE_FILE = DATA / "usage.json"
# keys: from repo (shipped with deploy) + optional override on volume
CODES_FILE_REPO = ROOT / "data" / "access_codes.json"
ACCESS_FILE = DATA / "access_codes.json"
STATIC = ROOT / "static"
TEMPLATES = ROOT / "templates"
FONTS = ROOT / "fonts"

for d in (DATA, JOBS, STATIC):
    d.mkdir(parents=True, exist_ok=True)

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

# Коды доступа: снимают лимит. Можно задать env ACCESS_CODES=CODE1,CODE2
# или файл data/access_codes.json
DEFAULT_CODES = {
    # полный безлимит (для тебя / покупателей)
    "SHOWCASE-WEB-PRO": {"type": "unlimited", "label": "Pro"},
    # тестовый
    "WEB-TEST-PRO": {"type": "unlimited", "label": "Test Pro"},
}


def _load_codes() -> dict:
    codes = dict(DEFAULT_CODES)
    for c in os.environ.get("ACCESS_CODES", "").split(","):
        c = c.strip()
        if c:
            codes[c.upper()] = {"type": "unlimited", "label": "Custom"}
    # 1) bundled with app (git), 2) optional on volume
    for path in (CODES_FILE_REPO, ACCESS_FILE):
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    codes.update({str(k).upper(): v for k, v in data.items()})
            except Exception as e:
                print("load codes", path, e)
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


def _ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


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



def _attach_session_cookie(resp, token: str):
    """Persist login across all pages until logout or cookie expires."""
    resp.set_cookie(
        key="sm_session",
        value=token,
        max_age=60 * 60 * 24 * 90,  # 90 days
        path="/",
        httponly=True,
        samesite="lax",
        secure=True,  # HTTPS on Railway
    )
    return resp


def _clear_session_cookie(resp):
    resp.delete_cookie("sm_session", path="/")
    return resp


def quota_state(req: Request) -> dict:
    # 1) logged-in user (Pro is bound to account)
    user = _auth_user(req)
    if user and user.get("is_pro"):
        return {
            "used": 0,
            "limit": -1,
            "left": -1,
            "pro": True,
            "label": "Pro",
            "email": user.get("email"),
            "user_id": user.get("id"),
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
    }


def quota_inc(req: Request, n: int) -> None:
    user = _auth_user(req)
    if user and user.get("is_pro"):
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


app = FastAPI(title="Showcase Maker Web")
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


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



@app.post("/api/auth/register")
async def auth_register(request: Request):
    body = await request.json()
    ok, msg = auth_db.register(str(body.get("email") or ""), str(body.get("password") or ""))
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    # auto-login
    ok2, msg2, token = auth_db.login(str(body.get("email") or ""), str(body.get("password") or ""))
    resp = JSONResponse({"ok": True, "msg": msg, "token": token})
    if token:
        _attach_session_cookie(resp, token)
    return resp


@app.post("/api/auth/login")
async def auth_login(request: Request):
    body = await request.json()
    ok, msg, token = auth_db.login(str(body.get("email") or ""), str(body.get("password") or ""))
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    user = auth_db.user_by_token(token)
    resp = JSONResponse({
        "ok": True,
        "token": token,
        "email": user.get("email") if user else None,
        "is_pro": bool(user and user.get("is_pro")),
    })
    if token:
        _attach_session_cookie(resp, token)
    return resp


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
    return {
        "ok": True,
        "logged_in": True,
        "email": user["email"],
        "is_pro": user["is_pro"],
    }


@app.post("/api/billing/checkout")
async def billing_checkout(request: Request):
    """Покупка Pro — редирект на FunPay (ключ активируется на сайте)."""
    # не требуем логин: можно купить и потом ввести код
    return {
        "ok": True,
        "url": "https://funpay.com/lots/offer?id=75265310",
        "msg": "FunPay",
    }


@app.post("/api/billing/webhook")
async def billing_webhook(request: Request):
    """Stripe webhook: checkout.session.completed → is_pro=1."""
    if not STRIPE_SECRET:
        return JSONResponse({"ok": False}, status_code=503)
    import stripe
    stripe.api_key = STRIPE_SECRET
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        else:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=400)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        uid = (session.get("metadata") or {}).get("user_id")
        if uid:
            try:
                auth_db.set_pro(int(uid), True)
            except Exception:
                pass
    return {"ok": True}


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "ffmpeg": bool(proc.find_ffmpeg()),
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

    auth_db.set_pro(int(user["id"]), True, code=code)
    auth_db.mark_code_used(code, int(user["id"]))
    if code.startswith("SM-WEB-"):
        used.add(code)
        _save_used(used)
    return {"ok": True, "label": "Pro", "msg": "Pro activated on your account"}


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
        "buy_url": "https://funpay.com/lots/offer?id=75265310",
        "stripe_enabled": bool(STRIPE_SECRET and STRIPE_PRICE_ID),
        "pro_label": PRO_PRICE_LABEL,
        "modes": [
            {"id": "workshop", "title": "Workshop", "desc": "5 частей для витрины мастерской"},
            {"id": "featured", "title": "Featured", "desc": "630 px Featured Artwork"},
            {"id": "split", "title": "Artwork Split", "desc": "Центр 506 + бок 100"},
        ],
        "fonts": ["rob", "lap", "caratte", "Fineday"],
        "steam_code": STEAM_CONSOLE_CODE,
    }


STEAM_CONSOLE_CODE = r"""// Вставь в консоль Steam (F12 → Console) на странице загрузки
// После этого выбирай файлы в нужном порядке
$J('#image_upload').attr('multiple','multiple');
console.log('Showcase Maker: multiple upload enabled');"""


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
    files: list[UploadFile] = File(...),
):
    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Лимит {FREE_LIMIT} файлов/сутки. Введи код доступа или купи Pro."},
            status_code=403,
        )

    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)

    wm_on = wm_enable not in ("0", "false", "False", "")
    opacity = (wm_opacity / 100.0) if wm_on else 0.0
    text = wm_text if wm_on else ""

    left = 999 if q["pro"] else q["left"]
    files = files[: max(1, left)]

    job_id = uuid.uuid4().hex[:12]
    job_dir = JOBS / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    zip_buf = io.BytesIO()
    zf = zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED)
    processed = 0
    errors = []
    listed = []

    for uf in files:
        name = uf.filename or "file"
        try:
            raw = await uf.read()
            if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
                errors.append(f"{name}: >{MAX_UPLOAD_MB}MB")
                continue
            ext = Path(name).suffix.lower()
            stem = Path(name).stem[:40]
            folder = f"{stem}_{mode}"
            work = job_dir / folder
            work.mkdir(exist_ok=True)

            if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                img = Image.open(io.BytesIO(raw))
                if mode == "workshop":
                    parts = proc.process_image_workshop(img, text, wm_font, opacity)
                elif mode == "featured":
                    parts = proc.process_image_featured(img)
                else:
                    parts = proc.process_image_split(img, text, wm_font, opacity)
                for pname, data in parts.items():
                    zf.writestr(f"{folder}/{pname}", data)
                    if len(listed) < 20:
                        listed.append({"name": f"{folder}/{pname}", "size": len(data)})
            elif ext in (".gif", ".mp4", ".mov", ".webm", ".avi", ".mkv"):
                src = work / f"source{ext}"
                src.write_bytes(raw)
                gif_src = src
                if ext != ".gif":
                    gif_src = work / "source.gif"
                    proc.media_to_gif(src, gif_src, fps=fps, width=size if mode == "workshop" else (630 if mode == "featured" else 606))
                if mode == "workshop":
                    paths = proc.process_gif_workshop(gif_src, work, text, wm_font, opacity)
                elif mode == "featured":
                    paths = proc.process_gif_featured(gif_src, work, fps=fps)
                else:
                    paths = proc.process_gif_split(gif_src, work, fps=fps, wm_text=text, wm_font=wm_font, wm_opacity=opacity)
                for pname, pth in paths.items():
                    data = Path(pth).read_bytes()
                    zf.writestr(f"{folder}/{pname}", data)
                    if len(listed) < 20:
                        listed.append({"name": f"{folder}/{pname}", "size": len(data)})
            else:
                errors.append(f"{name}: формат не поддерживается")
                continue
            processed += 1
        except Exception as e:
            errors.append(f"{name}: {e}")

    zf.close()
    if processed == 0:
        return JSONResponse({"ok": False, "msg": "Не удалось обработать", "errors": errors}, status_code=400)

    quota_inc(request, processed)
    (job_dir / "result.zip").write_bytes(zip_buf.getvalue())
    q2 = quota_state(request)
    return {
        "ok": True,
        "job_id": job_id,
        "processed": processed,
        "errors": errors,
        "files": listed,
        "download": f"/api/download/{job_id}",
        **{k: q2[k] for k in ("used", "limit", "left", "pro")},
    }


@app.get("/api/download/{job_id}")
def download(job_id: str):
    job_id = "".join(c for c in job_id if c.isalnum())[:16]
    path = JOBS / job_id / "result.zip"
    if not path.is_file():
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    return FileResponse(path, filename=f"showcase_{job_id}.zip", media_type="application/zip")


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

    job_id = uuid.uuid4().hex[:12]
    out_dir = JOBS / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Pinterest images (yt-dlp fails: No video formats) ---
    if "pinterest." in url.lower() or "pin.it" in url.lower():
        try:
            # сначала пробуем yt-dlp (видео-пины)
            try:
                import yt_dlp
                with yt_dlp.YoutubeDL({
                    "outtmpl": str(out_dir / "%(title).80s.%(ext)s"),
                    "quiet": True,
                    "noplaylist": True,
                    "format": "bv*+ba/b",
                }) as ydl:
                    ydl.extract_info(url, download=True)
                files = [p for p in out_dir.iterdir() if p.is_file()]
                if files:
                    f = files[0]
                    quota_inc(request, 1)
                    return {
                        "ok": True,
                        "name": f.name,
                        "download": f"/api/job-file/{job_id}/{f.name}",
                        **quota_state(request),
                    }
            except Exception:
                pass
            # fallback: картинка
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


@app.post("/api/da/upload")
async def da_upload(request: Request):
    """Upload files to DeviantArt Sta.sh (same as desktop)."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    token = user.get("da_access_token")
    if not token:
        return JSONResponse({"ok": False, "msg": "Connect DeviantArt first"}, status_code=401)
    form = await request.form()
    files = []
    items = form.multi_items() if hasattr(form, "multi_items") else list(form.items())
    titles = {}
    for k, v in items:
        k = str(k)
        if k.startswith("title_"):
            titles[k[6:]] = str(v)
    for k, f in items:
        if not str(k).startswith("file"):
            continue
        if f is None or isinstance(f, (str, bytes)) or not hasattr(f, "read"):
            continue
        raw = await f.read()
        name = getattr(f, "filename", None) or "file.png"
        files.append((name, raw, titles.get(name) or Path(name).stem))

    if not files:
        return JSONResponse({"ok": False, "msg": "No files"}, status_code=400)

    import requests as rq

    ok_n = 0
    errors = []
    for name, raw, title in files:
        try:
            r = rq.post(
                "https://www.deviantart.com/api/v1/oauth2/stash/submit",
                headers={"Authorization": f"Bearer {token}"},
                data={"title": title, "artist_comments": "", "is_mature": "false"},
                files={"file": (name, raw)},
                timeout=120,
            )
            if r.status_code == 200:
                ok_n += 1
            else:
                errors.append(f"{name}: {r.status_code} {r.text[:120]}")
                if r.status_code in (401, 403):
                    auth_db.set_da_tokens(int(user["id"]), None, None)
                    break
        except Exception as e:
            errors.append(f"{name}: {e}")
    return {"ok": ok_n > 0, "uploaded": ok_n, "total": len(files), "errors": errors}




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
            return HTMLResponse(f"<h3>Token error</h3><pre>{r.text[:500]}</pre>", status_code=400)
        data = r.json()
        auth_db.set_da_tokens(
            int(pend["user_id"]),
            data.get("access_token"),
            data.get("refresh_token"),
        )
    except Exception as e:
        return HTMLResponse(f"<h3>Error</h3><pre>{e}</pre>", status_code=500)
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


@app.post("/api/da/logout")
async def da_logout(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)
    auth_db.set_da_tokens(int(user["id"]), None, None)
    return {"ok": True}


@app.post("/api/da/upload")
async def da_upload(request: Request):
    """Upload files to DeviantArt Sta.sh (same as desktop)."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    token = user.get("da_access_token")
    if not token:
        return JSONResponse({"ok": False, "msg": "Connect DeviantArt first"}, status_code=401)
    form = await request.form()
    files = []
    items = form.multi_items() if hasattr(form, "multi_items") else list(form.items())
    titles = {}
    for k, v in items:
        k = str(k)
        if k.startswith("title_"):
            titles[k[6:]] = str(v)
    for k, f in items:
        if not str(k).startswith("file"):
            continue
        if f is None or isinstance(f, (str, bytes)) or not hasattr(f, "read"):
            continue
        raw = await f.read()
        name = getattr(f, "filename", None) or "file.png"
        files.append((name, raw, titles.get(name) or Path(name).stem))

    if not files:
        return JSONResponse({"ok": False, "msg": "No files"}, status_code=400)

    import requests as rq

    ok_n = 0
    errors = []
    for name, raw, title in files:
        try:
            r = rq.post(
                "https://www.deviantart.com/api/v1/oauth2/stash/submit",
                headers={"Authorization": f"Bearer {token}"},
                data={"title": title, "artist_comments": "", "is_mature": "false"},
                files={"file": (name, raw)},
                timeout=120,
            )
            if r.status_code == 200:
                ok_n += 1
            else:
                errors.append(f"{name}: {r.status_code} {r.text[:120]}")
                if r.status_code in (401, 403):
                    auth_db.set_da_tokens(int(user["id"]), None, None)
                    break
        except Exception as e:
            errors.append(f"{name}: {e}")
    return {"ok": ok_n > 0, "uploaded": ok_n, "total": len(files), "errors": errors}



if __name__ == "__main__":
    import uvicorn
    print(f"\n  Showcase Maker WEB  →  http://{HOST}:{PORT}")
    print(f"  FFmpeg: {proc.find_ffmpeg() or 'НЕ НАЙДЕН'}")
    print(f"  Free limit: {FREE_LIMIT}/day  |  Unlock: SHOWCASE-WEB-PRO\n")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
