"""Telegram mini app: the page at /tg and its API (/api/tg-app/*). Identity, limits and delivery: smweb/tg_app.py."""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Body, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

import processor as proc
import redis_store as rs
from smweb import tg_app, telegram_cut
from smweb.core import JOBS, MAX_UPLOAD_MB

router = APIRouter()
LOGGER = logging.getLogger(__name__)
PAGE = Path(__file__).resolve().parents[2] / "static" / "tg-app.html"
# Telegram's web clients show mini apps in an iframe; everything else about the CSP stays the site's.
PAGE_CSP = "; ".join((
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://telegram.org",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data: blob: https:",
    "media-src 'self' data: blob: https:",
    "connect-src 'self' https: blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org",
))
CONVERT_TYPES = {"gif": "image/gif", "mp4": "video/mp4", "webm": "video/webm", "png": "image/png",
                 "jpg": "image/jpeg", "webp": "image/webp"}
MEDIA_TYPES = {".gif": "image/gif", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
               ".zip": "application/zip"}


def _fail(code: str, status: int, msg: str = "", **extra) -> JSONResponse:
    return JSONResponse({"ok": False, "code": code, "msg": msg or code, **extra}, status_code=status)


def _who(request: Request):
    user = tg_app.user_from(request)
    if not user:
        return None, _fail("auth", 401, "Open the app from the Telegram bot")
    return user, None


def _limit_refusal(quota: dict) -> JSONResponse:
    return _fail("limit", 429, "Daily limit reached", limit=quota.get("limit"), left=0)


# ---------------------------------------------------------------- page
@router.get("/tg", include_in_schema=False)
@router.get("/tg/", include_in_schema=False)
def page():
    return FileResponse(PAGE, media_type="text/html; charset=utf-8",
                        headers={"Cache-Control": "no-cache", "Content-Security-Policy": PAGE_CSP,
                                 "X-Robots-Tag": "noindex"})


@router.get("/api/tg-app/config")
def config():
    """Public: the bot to send people to when the page is opened outside Telegram."""
    import os
    bot = (os.environ.get("TELEGRAM_SHOP_BOT_USERNAME") or os.environ.get("TELEGRAM_BOT_USERNAME") or "").strip().lstrip("@")
    return {"ok": True, "bot": bot}


# ---------------------------------------------------------------- who am I
@router.get("/api/tg-app/me")
def me(request: Request):
    user, denied = _who(request)
    if denied:
        return denied
    from smweb.routers.media import modal_upscale_client, object_store
    import auth_db
    quota = telegram_cut.quota(user["id"])
    account = tg_app.account(user["id"])
    return {"ok": True, "user": {"first_name": user["first_name"], "username": user["username"]},
            "quota": quota, "account": bool(account),
            "pro": bool(account and auth_db.effective_pro(account)) or quota["pro"],
            "upscale": modal_upscale_client.configured() and object_store.configured(),
            "max_mb": MAX_UPLOAD_MB}


# ---------------------------------------------------------------- cut (an ordinary Process job, smweb/telegram_cut.py)
@router.post("/api/tg-app/cut/start")
async def cut_start(request: Request, mode: str = Form("workshop"), frame: str = Form("none"),
                    file: UploadFile = File(...)):
    user, denied = _who(request)
    if denied:
        return denied
    data = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    code, body = await run_in_threadpool(telegram_cut.start, user["id"], file.filename or "file", data, mode, frame)
    return JSONResponse(body, status_code=code)


@router.get("/api/tg-app/cut/status/{job_id}")
def cut_status(job_id: str, request: Request):
    user, denied = _who(request)
    if denied:
        return denied
    job = telegram_cut.job_for(user["id"], job_id)
    if not job:
        return _fail("not_found", 404)
    return {"ok": True, **telegram_cut.describe(job_id, job)}


# ---------------------------------------------------------------- download by link (the site's /api/download-url)
@router.post("/api/tg-app/download")
def download(request: Request, body: dict = Body(...)):
    user, denied = _who(request)
    if denied:
        return denied
    allowed, quota = tg_app.can_use(user["id"])
    if not allowed:
        return _limit_refusal(quota)
    from smweb.routers.media import download_url
    # "process" = not charged to the browser's daily files; the Telegram user's limit is charged below instead.
    result = download_url(request, {"url": str((body or {}).get("url") or "").strip()[:2000], "purpose": "process"})
    if isinstance(result, Response):
        return result
    match = re.match(r"^/api/job-file/([0-9a-f]{32})/(.+)$", str(result.get("download") or ""))
    if not match:
        return _fail("failed", 500)
    job_id, name = match.group(1), Path(match.group(2)).name
    tg_app.mark(JOBS / job_id, user["id"], name, MEDIA_TYPES.get(Path(name).suffix.lower(), "application/octet-stream"))
    tg_app.charge(user["id"], quota)
    return _file_reply(user["id"], "file", job_id, name)


# ---------------------------------------------------------------- convert (the site's converter, processor.convert_media)
@router.post("/api/tg-app/convert")
async def convert(request: Request, target: str = Form("gif"), file: UploadFile = File(...)):
    user, denied = _who(request)
    if denied:
        return denied
    allowed, quota = tg_app.can_use(user["id"])
    if not allowed:
        return _limit_refusal(quota)
    target = (target or "gif").lower().lstrip(".").replace("jpeg", "jpg")
    if target not in CONVERT_TYPES:
        return _fail("target", 400)
    raw = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if not raw:
        return _fail("empty", 400)
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return _fail("too_big", 413)
    job_id = uuid.uuid4().hex
    folder = JOBS / job_id
    folder.mkdir(parents=True, exist_ok=True)
    name = file.filename or "file"
    src = folder / ("src" + (Path(name).suffix.lower()[:8] or ".bin"))
    src.write_bytes(raw)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem)[:40] or "file"
    dest = folder / f"{stem}.{target}"
    try:
        await run_in_threadpool(proc.convert_media, src, dest, target, 12, 0, 0)
    except Exception as exc:
        LOGGER.warning("tg app conversion failed (%s)", type(exc).__name__)
        return _fail("convert_failed", 400)
    finally:
        src.unlink(missing_ok=True)
    tg_app.mark(folder, user["id"], dest.name, CONVERT_TYPES[target])
    tg_app.charge(user["id"], quota)
    return _file_reply(user["id"], "file", job_id, dest.name)


# ---------------------------------------------------------------- upscale (Pro account, the site's Modal queue)
@router.post("/api/tg-app/upscale/start")
async def upscale_start(request: Request, preset: str = Form("general"), scale: int = Form(2),
                        file: UploadFile = File(...)):
    user, denied = _who(request)
    if denied:
        return denied
    account = await run_in_threadpool(tg_app.account, user["id"])
    if not account:
        return _fail("no_account", 403)
    from smweb.routers import media
    refused = media.upscale_refusal(account)
    if refused:
        return refused
    raw = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    return await run_in_threadpool(media.queue_upscale, account, raw, file.filename or "upscale",
                                   file.content_type or "application/octet-stream", preset, scale)


@router.get("/api/tg-app/upscale/status/{job_id}")
def upscale_status(job_id: str, request: Request):
    user, denied = _who(request)
    if denied:
        return denied
    from smweb import job_diagnostics
    account = tg_app.account(user["id"])
    job = rs.job_get(job_id) if re.fullmatch(r"[a-f0-9]{32}", job_id or "") else None
    if not account or not job or job.get("kind") != "upscale" or job.get("user_key") != str(int(account["id"])):
        return _fail("not_found", 404)
    out = {"ok": True, "status": job.get("status", "queued"), "pct": int(job.get("pct") or 0),
           "stage": job.get("stage", "queued")}
    if job.get("status") == "error":
        out.update(job_diagnostics.public_error(job.get("error")))
    if job.get("status") == "done":
        out.update(_file_reply(user["id"], "upscale", job_id, str(job.get("download_name") or "upscaled.png")))
    return out


# ---------------------------------------------------------------- results: preview link, download link, into the chat
def _file_reply(tg_id: str, kind: str, ref: str, name: str) -> dict:
    item = tg_app.resolve(tg_id, kind, ref) or {}
    return {"ok": True, "kind": kind, "ref": ref, "name": name, "type": item.get("type") or "",
            "size": tg_app.size_of(item) if item else None,
            "preview": "/api/tg-app/dl/" + tg_app.sign(tg_id, kind, ref, inline=True),
            "download": "/api/tg-app/dl/" + tg_app.sign(tg_id, kind, ref)}


@router.post("/api/tg-app/link")
def link(request: Request, body: dict = Body(...)):
    user, denied = _who(request)
    if denied:
        return denied
    kind, ref = str(body.get("kind") or ""), str(body.get("ref") or "")
    item = tg_app.resolve(user["id"], kind, ref)
    if not item:
        return _fail("not_found", 404)
    return _file_reply(user["id"], kind, ref, item["name"])


@router.get("/api/tg-app/dl/{token}")
def signed_file(token: str):
    """A short-lived signed link (preview images, WebApp.downloadFile): no header, the signature is the access."""
    body = tg_app.unsign(token)
    item = tg_app.resolve(str(body["t"]), str(body["k"]), str(body["r"])) if body else None
    if not item:
        return _fail("not_found", 404)
    inline = bool(body.get("i"))
    if item.get("path"):
        return FileResponse(str(item["path"]), media_type=item["type"], filename=item["name"],
                            content_disposition_type="inline" if inline else "attachment",
                            headers={"Cache-Control": "private, no-store"})
    from smweb import object_store
    url = object_store.presigned_get_url(item["key"], expires=600, download_name=None if inline else item["name"],
                                         media_type=item["type"])
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, no-store"})


@router.post("/api/tg-app/send")
async def send(request: Request, body: dict = Body(...)):
    user, denied = _who(request)
    if denied:
        return denied
    allowed, _ = rs.rate_limit(f"tgapp-send:{user['id']}", 20, 600)
    if not allowed:
        return _fail("busy", 429)
    item = tg_app.resolve(user["id"], str(body.get("kind") or ""), str(body.get("ref") or ""))
    if not item:
        return _fail("not_found", 404)
    size = tg_app.size_of(item)
    if size is not None and size > tg_app.SEND_MAX_BYTES:
        return _fail("too_big", 413)
    try:
        data = await run_in_threadpool(tg_app.read_bytes, item)
    except Exception:
        LOGGER.warning("tg app: result unreadable", exc_info=True)
        return _fail("expired", 410)
    ok, code = await run_in_threadpool(tg_app.send_document, user["id"], item["name"], data, "Showcase Maker")
    return {"ok": True} if ok else _fail(code, 502 if code == "telegram" else 400)


@router.post("/api/tg-app/text")
async def send_text(request: Request, body: dict = Body(...)):
    """The Info box text into the chat, to copy it on any device."""
    user, denied = _who(request)
    if denied:
        return denied
    text = str(body.get("text") or "")[:12000]
    if not text.strip():
        return _fail("empty", 400)
    allowed, _ = rs.rate_limit(f"tgapp-send:{user['id']}", 20, 600)
    if not allowed:
        return _fail("busy", 429)
    ok, code = await run_in_threadpool(tg_app.send_text, user["id"], text)
    return {"ok": True} if ok else _fail(code, 502 if code == "telegram" else 400)
