"""One-shot media tools: convert, hex21, url download, watermark, upscale, compose.

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
from starlette.concurrency import run_in_threadpool
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db


from fastapi import APIRouter


from smweb.core import (
    DATA,
    FREE_LIMIT,
    JOBS,
    LOGGER,
    MAX_UPLOAD_MB,
    _auth_user,
    _check_public_url,
    _ip,
    quota_inc,
    quota_state,
)
from smweb.downloads import _download_pinterest
from smweb.jobs import _job_pool, _worker_mode
from smweb import modal_upscale_client, object_store



router = APIRouter()


@router.post("/api/convert")
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
        # Waiting for FFmpeg in the event-loop thread stalls unrelated pages.
        await run_in_threadpool(proc.convert_media, src, dest, target, fps, width, duration)
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


@router.post("/api/hex21")
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


@router.post("/api/download-url")
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


# ====================== Watermark live preview ======================

@router.post("/api/preview_wm")
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
    except Exception:
        rid = getattr(request.state, "request_id", "-")
        LOGGER.exception("watermark preview failed rid=%s", rid)
        return JSONResponse({"ok": False, "msg": "Preview failed", "request_id": rid}, status_code=500)


@router.get("/api/upscale/models")
def upscale_models():
    return {
        "ok": True,
        "models": [
            {"id": "general", "label": "Photo / general", "group": "general"},
            {"id": "anime", "label": "Anime / artwork", "group": "art"},
        ],
        "default": "general",
        "scales": [2, 4],
        "media": ["image", "gif", "video"],
        "configured": modal_upscale_client.configured() and object_store.configured(),
    }


def _upscale_media(raw: bytes) -> tuple[str, str, str] | None:
    """Return (kind, source extension, result content type) from trusted magic bytes."""
    head = raw[:32]
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image", ".png", "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image", ".jpg", "image/png"
    if head[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image", ".webp", "image/png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif", ".gif", "image/gif"
    if len(raw) >= 12 and raw[4:8] == b"ftyp":
        return "video", ".mp4", "video/mp4"
    if head[:4] == b"\x1aE\xdf\xa3":
        return "video", ".webm", "video/mp4"
    if head[:4] == b"RIFF" and raw[8:12] == b"AVI ":
        return "video", ".avi", "video/mp4"
    return None


def _upscale_owner(user: dict) -> str:
    return str(int(user["id"]))


@router.post("/api/upscale/start")
async def api_upscale_start(
    request: Request,
    file: UploadFile = File(...),
    preset: str = Form("general"),
    scale: int = Form(2),
):
    """Queue an authenticated image/GIF/video upscale on Modal (Pro only)."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in required", "code": "auth"}, status_code=401)
    if not auth_db.effective_pro(user):
        return JSONResponse(
            {"ok": False, "msg": "Upscale is available for Pro subscribers", "code": "pro"},
            status_code=403,
        )
    if not modal_upscale_client.configured() or not object_store.configured():
        return JSONResponse({"ok": False, "msg": "Upscale service is not configured"}, status_code=503)
    if not (rs.redis_ok() and rs.worker_alive()):
        return JSONResponse({"ok": False, "msg": "Upscale worker is temporarily unavailable"}, status_code=503)

    user_key = _upscale_owner(user)
    if rs.job_count_user(user_key) >= int(os.environ.get("MAX_JOBS_PER_USER", "2")):
        return JSONResponse({"ok": False, "msg": "Too many active jobs. Wait for the current job."}, status_code=429)
    allowed, _ = rs.rate_limit(f"upscale-start:{user_key}", 8, 3600)
    if not allowed:
        return JSONResponse({"ok": False, "msg": "Too many upscale requests. Try again later."}, status_code=429)

    raw = await file.read()
    if not raw:
        return JSONResponse({"ok": False, "msg": "Empty file"}, status_code=400)
    max_mb = min(MAX_UPLOAD_MB, int(os.environ.get("MODAL_UPSCALE_MAX_UPLOAD_MB", "40")))
    if len(raw) > max_mb * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": f"File too large for upscale (max {max_mb}MB)"}, status_code=413)
    media = _upscale_media(raw)
    if not media:
        return JSONResponse({"ok": False, "msg": "PNG/JPG/WEBP/GIF/MP4/WEBM/AVI only"}, status_code=400)
    media_kind, source_ext, result_type = media
    preset = (preset or "general").strip().lower()
    if preset not in ("general", "anime"):
        return JSONResponse({"ok": False, "msg": "Unknown upscale preset"}, status_code=400)
    if scale not in (2, 4):
        return JSONResponse({"ok": False, "msg": "Scale must be 2 or 4"}, status_code=400)
    if media_kind == "video" and scale != 2:
        return JSONResponse({"ok": False, "msg": "Video upscale supports 2x only"}, status_code=400)

    jid = secrets.token_hex(16)
    result_ext = ".gif" if media_kind == "gif" else ".mp4" if media_kind == "video" else ".png"
    source_key = f"upscale/input/{jid}{source_ext}"
    result_key = f"upscale/result/{jid}{result_ext}"
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file.filename or "upscale").stem)[:80] or "upscale"
    try:
        object_store.put_bytes(source_key, raw, public=False, media_type=file.content_type or "application/octet-stream")
        rs.job_create(jid, {
            "kind": "upscale", "user_key": user_key, "status": "queued", "pct": 1,
            "stage": "queued", "source_key": source_key, "result_key": result_key,
            "filename": f"{safe_stem}{source_ext}", "download_name": f"{safe_stem}_upscaled{result_ext}",
            "media_kind": media_kind, "content_type": result_type,
            "preset": preset, "scale": scale, "input_size": len(raw),
        }, enqueue=True)
    except Exception:
        object_store.delete(source_key, public=False)
        LOGGER.exception("upscale queue failed jid=%s", jid)
        return JSONResponse({"ok": False, "msg": "Could not queue upscale job"}, status_code=503)
    return JSONResponse({"ok": True, "job_id": jid, "status": "queued"}, status_code=202)


@router.get("/api/upscale/status/{job_id}")
def api_upscale_status(request: Request, job_id: str):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in required", "code": "auth"}, status_code=401)
    job = rs.job_get(job_id) if re.fullmatch(r"[a-f0-9]{32}", job_id or "") else None
    if not job or job.get("kind") != "upscale" or job.get("user_key") != _upscale_owner(user):
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    return {
        "ok": True, "status": job.get("status", "queued"), "pct": int(job.get("pct") or 0),
        "stage": job.get("stage", "queued"), "error": job.get("error", ""),
        "media_kind": job.get("media_kind", "image"),
        "download_url": f"/api/upscale/download/{job_id}" if job.get("status") == "done" else "",
        "preview_url": f"/api/upscale/download/{job_id}?inline=1" if job.get("status") == "done" else "",
    }


@router.get("/api/upscale/download/{job_id}")
def api_upscale_download(request: Request, job_id: str, inline: bool = False):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in required", "code": "auth"}, status_code=401)
    job = rs.job_get(job_id) if re.fullmatch(r"[a-f0-9]{32}", job_id or "") else None
    if not job or job.get("kind") != "upscale" or job.get("user_key") != _upscale_owner(user):
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    if job.get("status") != "done":
        return JSONResponse({"ok": False, "msg": "Result is not ready"}, status_code=409)
    try:
        url = object_store.presigned_get_url(
            str(job["result_key"]), expires=600,
            download_name=None if inline else str(job.get("download_name") or "upscaled-result"),
            media_type=str(job.get("content_type") or "application/octet-stream"),
        )
    except Exception:
        LOGGER.exception("upscale download URL failed jid=%s", job_id)
        return JSONResponse({"ok": False, "msg": "Result is unavailable"}, status_code=503)
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, no-store"})


@router.post("/api/upscale")
def api_upscale_legacy():
    return JSONResponse(
        {"ok": False, "msg": "Synchronous upscale is disabled; use /api/upscale/start"},
        status_code=410,
    )


# ====================== Character + background compose ======================

def _compose_user_key(request, user) -> str:
    try:
        return str(user.get("id") or "") if user else _ip(request)
    except Exception:
        return ""


@router.post("/api/compose/start")
async def api_compose_start(
    request: Request,
    chroma_key: str = Form("auto"), chroma_tol: float = Form(55),
    feather: float = Form(1.6), scale: float = Form(1.0),
    offset_x: float = Form(0.5), offset_y: float = Form(1.0),
    width: int = Form(750), gif_encoder: str = Form("gifski"), fps: int = Form(12),
    background: UploadFile = File(...), character: UploadFile = File(...),
):
    """Accept the inputs quickly and render in the background.

    Composing an animated character over a background takes minutes; answering
    it synchronously meant Cloudflare closed the connection at its proxy timeout
    and the browser received Cloudflare's HTML error page instead of the GIF.
    """
    user = None
    try:
        user = _auth_user(request)
    except Exception:
        user = None
    user_key = _compose_user_key(request, user)

    # Same budget as /api/process/start. Without this a single client could keep
    # the render pool busy indefinitely -- compose is the most expensive route.
    if user_key and rs.job_count_user(user_key) >= int(os.environ.get("MAX_JOBS_PER_USER", "2")):
        return JSONResponse(
            {"ok": False, "msg": "Too many active jobs. Wait for current processing to finish."},
            status_code=429,
        )

    bg_raw, ch_raw = await background.read(), await character.read()
    limit = MAX_UPLOAD_MB * 1024 * 1024
    if not bg_raw or not ch_raw or len(bg_raw) > limit or len(ch_raw) > limit:
        return JSONResponse({"ok": False, "msg": "File missing or too large"}, status_code=400)

    jid = secrets.token_urlsafe(18)
    job_dir = Path(DATA) / "jobs" / jid
    job_dir.mkdir(parents=True, exist_ok=False)
    bg_ext = Path(background.filename or "background.png").suffix.lower() or ".bin"
    ch_ext = Path(character.filename or "character.png").suffix.lower() or ".bin"
    bg_path, ch_path = job_dir / f"input_bg{bg_ext}", job_dir / f"input_char{ch_ext}"
    bg_path.write_bytes(bg_raw); ch_path.write_bytes(ch_raw)

    # Hand the job to worker.py only when one is actually draining the queue,
    # otherwise it would sit in Redis forever. Mirrors /api/process/start.
    mode = _worker_mode()
    external = mode == "external" and rs.redis_ok() and rs.worker_alive()
    if mode == "external" and not external:
        LOGGER.warning(
            "[compose %s] WORKER_MODE=external but no live worker (redis=%s beat=%s) - running embedded",
            jid[:8], rs.redis_ok(), rs.worker_alive(),
        )

    payload = {
        "kind": "compose", "job_dir": str(job_dir),
        "background_path": str(bg_path), "character_path": str(ch_path),
        "options": {"chroma_key": chroma_key, "chroma_tol": chroma_tol, "feather": feather,
                    "scale": scale, "offset_x": offset_x, "offset_y": offset_y,
                    "width": width, "gif_encoder": gif_encoder, "fps": fps},
        "status": "queued", "pct": 2, "stage": "queued",
        "user_key": user_key, "created": time.time(),
    }
    rs.job_create(jid, payload, enqueue=external)
    if not external:
        from smweb.compose_jobs import run as _compose_run
        _job_pool.submit(_compose_run, jid, dict(payload))
    return JSONResponse({"ok": True, "job_id": jid}, status_code=202)


def _compose_job_for(request: Request, job_id: str) -> dict | None:
    """Fetch a compose job, enforcing that it belongs to the caller."""
    job = rs.job_get(job_id)
    if not job or job.get("kind") != "compose":
        return None
    owner = str(job.get("user_key") or "")
    if owner:
        try:
            user = _auth_user(request)
        except Exception:
            user = None
        if _compose_user_key(request, user) != owner:
            return None
    return job


@router.get("/api/compose/status/{job_id}")
def api_compose_status(request: Request, job_id: str):
    job = _compose_job_for(request, job_id)
    if not job:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    return {"ok": True, "status": job.get("status"), "pct": job.get("pct", 0),
            "stage": job.get("stage", ""), "error": job.get("error", ""),
            "filename": job.get("filename", "")}


@router.get("/api/compose/download/{job_id}")
def api_compose_download(request: Request, job_id: str):
    from fastapi.responses import Response
    from smweb import object_store
    job = _compose_job_for(request, job_id)
    if not job or job.get("status") != "done":
        return JSONResponse({"ok": False, "msg": "Result is not ready"}, status_code=404)
    try:
        if job.get("result_key"):
            data = object_store.get_bytes(job["result_key"], public=False)
        else:
            data = Path(job["result_path"]).read_bytes()
        filename = str(job.get("filename") or "composed.png")
        return Response(data, media_type=job.get("media_type") or "application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                                 "Cache-Control": "no-store"})
    except Exception as exc:
        LOGGER.exception("compose result unavailable for %s", job_id)
        return JSONResponse({"ok": False, "msg": f"Result unavailable: {type(exc).__name__}"}, status_code=404)
