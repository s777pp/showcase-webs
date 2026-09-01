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
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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
    quota_inc,
    quota_state,
)
from smweb.downloads import _download_pinterest
from smweb.upscale_models import _UPSCALE_MODELS, _UPSCALE_MODEL_META, _run_hf_upscale



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
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)


@router.get("/api/upscale/models")
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


@router.post("/api/upscale")
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


# ====================== Character + background compose ======================

@router.post("/api/compose")
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
        bg_name = (background.filename or "background.png").lower()
        ch_name = (character.filename or "char.png").lower()
        bg_ext = Path(bg_name).suffix.lower()
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

        def animated(raw: bytes, ext: str) -> bool:
            if ext in video_exts:
                return True
            if ext == ".gif":
                return True
            if ext != ".webp":
                return False
            try:
                with Image.open(io.BytesIO(raw)) as im:
                    return int(getattr(im, "n_frames", 1) or 1) > 1
            except Exception:
                return False

        bg_animated = animated(bg_raw, bg_ext)
        ch_animated = animated(ch_raw, ch_ext)
        try:
            fps_i = max(5, min(30, int(fps)))
        except Exception:
            fps_i = 12

        from fastapi.responses import Response

        if bg_animated or ch_animated:
            tmp = Path(tempfile.mkdtemp(prefix="sm_compose_"))
            try:
                bpath = tmp / f"background{bg_ext or '.bin'}"
                cpath = tmp / f"char{ch_ext or '.bin'}"
                bpath.write_bytes(bg_raw)
                cpath.write_bytes(ch_raw)

                gif_bg = bpath
                gif_char = cpath
                if bg_ext in video_exts:
                    gif_bg = tmp / "background.gif"
                    proc.media_to_gif(bpath, gif_bg, fps=fps_i, width=size_i, duration=8)
                    if not gif_bg.is_file():
                        return JSONResponse({"ok": False, "msg": "Background video→GIF failed (ffmpeg?)"}, status_code=500)
                if ch_ext in video_exts:
                    gif_char = tmp / "char.gif"
                    proc.media_to_gif(cpath, gif_char, fps=fps_i, width=min(size_i, 800), duration=8)
                    if not gif_char.is_file():
                        return JSONResponse({"ok": False, "msg": "Character video→GIF failed (ffmpeg?)"}, status_code=500)

                frames, durs = proc.compose_animated_layers(
                    gif_bg, gif_char,
                    chroma_key=key,
                    chroma_tol=tol,
                    scale=sc,
                    offset_x=ox,
                    offset_y=oy,
                    feather=feather_f,
                    target_width=size_i,
                    fps=fps_i,
                    max_seconds=8,
                )
                out = tmp / "composed.gif"
                enc = (gif_encoder or "ffmpeg").strip().lower()
                if enc not in ("ffmpeg", "gifski", "pillow"):
                    enc = "ffmpeg"
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
            bg = Image.open(io.BytesIO(bg_raw)).convert("RGBA")
            if bg.width != size_i:
                nh = max(1, int(bg.height * (size_i / max(1, bg.width))))
                bg = bg.resize((size_i, nh), Image.Resampling.LANCZOS)
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
