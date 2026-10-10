"""AI animation API (beta, Pro only): info, start, status, files, cancel. Job body: smweb/ai_animate_jobs.py."""
from __future__ import annotations

import io
import re
import secrets
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
from starlette.concurrency import run_in_threadpool

import auth_db
import processor as proc  # noqa: F401  (registers the HEIC opener for Pillow)
import redis_store as rs
from smweb import ai_animate, free_limits, job_diagnostics
from smweb.core import DATA, MAX_UPLOAD_MB, LOGGER, _auth_user, _is_limit_exempt, max_jobs_for_user, owner_key
from smweb.jobs import _job_pool, _worker_mode

router = APIRouter()
KIND = "ai_animate"
FEATURE = "aianim"
MIN_SIDE = 128
MAX_PIXELS = 40_000_000
PUBLIC_FIELDS = ("status", "pct", "stage", "mode", "keep_background", "out_width", "out_height",
                 "out_fps", "gif_bytes", "mp4_bytes", "saved_id")


def _stem(name: str) -> str:
    return re.sub(r"[^\w.-]+", "_", Path(name or "").stem)[:60] or "animation"


def _still_png(raw: bytes) -> tuple[bytes, tuple[int, int]]:
    """The first frame of any picture Pillow reads, as PNG. Raises ValueError for anything else."""
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.seek(0)
            w, h = image.size
            if w * h > MAX_PIXELS:
                raise ValueError("too_large")
            if min(w, h) < MIN_SIDE:
                raise ValueError("too_small")
            frame = image.convert("RGBA" if "A" in image.getbands() else "RGB")
    except ValueError:
        raise
    except Exception:
        raise ValueError("bad_image")
    if frame.mode == "RGBA":
        # Transparent cut-outs get a neutral dark backdrop: the video model needs an opaque picture.
        backdrop = Image.new("RGB", frame.size, (18, 22, 32))
        backdrop.paste(frame, mask=frame.getchannel("A"))
        frame = backdrop
    out = io.BytesIO()
    frame.save(out, "PNG")
    return out.getvalue(), (w, h)


def _user_state(request: Request) -> tuple[dict | None, bool]:
    user = _auth_user(request)
    return user, bool(user and auth_db.effective_pro(user))


@router.get("/api/ai-animate/info")
def info(request: Request):
    user, pro = _user_state(request)
    body = {"ok": True, "available": ai_animate.configured(), "signed_in": bool(user), "pro": pro,
            "modes": list(ai_animate.MODES), "motions": list(ai_animate.MOTIONS),
            "wish_max": ai_animate.WISH_MAX}
    if user and pro:
        usage = ai_animate.usage(int(user["id"]))
        exempt = _is_limit_exempt(user)
        # "quota", not "limit": free-limits.js treats any "limit" object in an answer as a refusal dialog.
        body["quota"] = {"total": usage["total"], "used": usage["used"], "left": None if exempt else usage["left"],
                         "site_busy": usage["site_used"] >= usage["site_limit"]}
    return body


@router.post("/api/ai-animate/start")
async def start(request: Request, file: UploadFile = File(...), mode: str = Form("calm"), motions: str = Form(""),
                wish: str = Form(""), keep_background: bool = Form(True)):
    user, pro = _user_state(request)
    if not user:
        return JSONResponse({"ok": False, "code": "login", "msg": "Sign in to use AI animation"}, status_code=401)
    if not pro:
        return free_limits.refusal(request, "beta", FEATURE)
    if not ai_animate.configured():
        return JSONResponse({"ok": False, "code": "unavailable", "msg": "AI animation is temporarily unavailable"},
                            status_code=503)
    owner = owner_key(request, user)
    if rs.job_count_user(owner) >= max_jobs_for_user(int(user["id"])):
        return JSONResponse({"ok": False, "code": "busy", "msg": "Too many active jobs"}, status_code=429)
    raw = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if not raw or len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "code": "too_big", "msg": f"File missing or larger than {MAX_UPLOAD_MB} MB"},
                            status_code=400)
    try:
        png, (width, height) = await run_in_threadpool(_still_png, raw)
    except ValueError as exc:
        return JSONResponse({"ok": False, "code": str(exc), "msg": "Could not read the picture"}, status_code=400)
    mode = mode if mode in ai_animate.MODES else "calm"
    chosen = [m for m in re.split(r"[,\s]+", motions or "") if m in ai_animate.MOTIONS][:6]
    ticket, refused = ai_animate.take(int(user["id"]), exempt=_is_limit_exempt(user))
    if not ticket:
        if refused == "user":
            return JSONResponse({"ok": False, "code": "ai_beta_used",
                                 "msg": "Your beta AI animations are used. Write to support to get more."},
                                status_code=429)
        return JSONResponse({"ok": False, "code": "ai_site_busy",
                             "msg": "Today's AI animations for the whole site are used up. Try again tomorrow."},
                            status_code=429)
    jid = secrets.token_hex(16)
    root = Path(DATA) / "jobs" / jid
    try:
        root.mkdir(parents=True, exist_ok=False)
        source = root / "source.png"
        source.write_bytes(png)
        external = _worker_mode() == "external" and rs.redis_ok() and rs.worker_alive()
        payload = {"kind": KIND, "queue": "gpu", "job_dir": str(root), "source_path": str(source),
                   "user_key": owner, "user_id": int(user["id"]), "status": "queued", "pct": 2, "stage": "queued",
                   "created": time.time(), "mode": mode, "motions": chosen, "wish": ai_animate.clean_wish(wish),
                   "keep_background": bool(keep_background), "stem": _stem(file.filename),
                   "in_width": width, "in_height": height, "ticket": ticket}
        rs.job_create(jid, payload, enqueue=external)
    except Exception:
        ai_animate.give_back(ticket)
        shutil.rmtree(root, ignore_errors=True)
        LOGGER.exception("ai animate start failed")
        return JSONResponse({"ok": False, "code": "server", "msg": "Could not start the animation"}, status_code=500)
    if not external:
        from smweb.ai_animate_jobs import run
        _job_pool.submit(run, jid, dict(payload))
    return JSONResponse({"ok": True, "job_id": jid}, status_code=202)


def _job(request: Request, job_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id or ""):
        return None
    job = rs.job_get(job_id)
    owner = owner_key(request, _auth_user(request))
    return job if job and job.get("kind") == KIND and owner and job.get("user_key") == owner else None


@router.get("/api/ai-animate/status/{job_id}")
def status(request: Request, job_id: str):
    job = _job(request, job_id)
    if not job:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    done = job.get("status") == "done"
    base = f"/api/ai-animate/file/{job_id}"
    body = {"ok": True, **{key: job.get(key) for key in PUBLIC_FIELDS},
            "gif_url": base + "/gif?inline=1" if done else "", "gif_download": base + "/gif" if done else "",
            "mp4_url": base + "/mp4?inline=1" if done else "", "mp4_download": base + "/mp4" if done else "",
            "source_url": base + "/source"}
    if job.get("status") == "error":
        body["error_code"] = job.get("error_code") or job_diagnostics.public_error(job.get("error")).get("error_code")
        body["error"] = str(job.get("error") or "")[:300]
    return body


@router.get("/api/ai-animate/file/{job_id}/{which}")
def get_file(request: Request, job_id: str, which: str, inline: bool = False):
    job = _job(request, job_id)
    if not job or which not in ("gif", "mp4", "source"):
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    if which != "source" and job.get("status") != "done":
        return JSONResponse({"ok": False, "msg": "Result is not ready"}, status_code=404)
    path = Path(str(job.get({"gif": "gif_path", "mp4": "mp4_path", "source": "source_path"}[which]) or ""))
    root = Path(str(job.get("job_dir") or "")).resolve()
    try:
        resolved = path.resolve()
        if not resolved.is_file() or root not in resolved.parents:
            raise FileNotFoundError
    except Exception:
        return JSONResponse({"ok": False, "msg": "File is unavailable"}, status_code=404)
    media = {"gif": "image/gif", "mp4": "video/mp4", "source": "image/png"}[which]
    name = f"{job.get('stem') or 'animation'}_ai.{which if which != 'source' else 'png'}"
    return FileResponse(resolved, media_type=media, filename=None if inline else name,
                        headers={"Cache-Control": "private, no-store"})


@router.post("/api/ai-animate/cancel/{job_id}")
def cancel(request: Request, job_id: str):
    job = _job(request, job_id)
    if not job:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    was_queued = job.get("status") == "queued"
    updated = rs.job_cancel(job_id) or {}
    if was_queued and updated.get("status") == "cancelled":
        # Never started: the worker will not run it, so the use comes back here.
        ai_animate.give_back(job.get("ticket"))
    return {"ok": True, "status": updated.get("status")}
