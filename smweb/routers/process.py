"""The showcase pipeline: start, status, download, legacy sync route.

Moved out of main.py unchanged.
"""


from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import time
import zipfile
from pathlib import Path

from fastapi import File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, FileResponse, Response

import processor as proc
import redis_store as rs

from smweb import analytics
from smweb import media_assets
from smweb import saved_results
from smweb import square_fx


from fastapi import APIRouter


from smweb.core import JOBS, MAX_UPLOAD_MB, _auth_user, _ip, max_jobs_for_user, quota_inc, quota_state
from smweb.job_access import browser_owns_job
from smweb.jobs import (
    _job_cleanup_old,
    _job_get,
    _job_pool,
    _job_set,
    _run_process_job_from_payload,
    _worker_mode,
)


router = APIRouter()


@router.post("/api/workshop-studio/start")
async def api_workshop_studio_start(
    request: Request,
    rows: int = Form(1),
    fps: int = Form(12),
    duration: float = Form(8),
    outline: str = Form("0"),
    settings: str = Form("[]"),
    layout: str = Form("rows"),
    crop: str = Form(""),
    fx: str = Form(""),
    files: list[UploadFile] = File(default=[]),
):
    """Create Workshop files in a background job.

    ``rows``: one full-height output per row. ``squares``: one source, the
    chosen 5:1 area (``crop`` as source fractions) cut into five 150x150 files.
    """
    layout = (layout or "rows").strip().lower()
    if layout not in ("rows", "squares"):
        return JSONResponse({"ok": False, "msg": "Unknown layout"}, status_code=400)
    if layout == "squares" and rows != 1:
        return JSONResponse({"ok": False, "msg": "Select one file for the squares layout"}, status_code=400)
    if rows not in (1, 2, 3) or len(files) != rows:
        return JSONResponse({"ok": False, "msg": "Select one file for each row"}, status_code=400)
    crop_box = None
    square_effects = None
    if layout == "squares":
        from smweb.workshop_studio_jobs import normalize_crop
        try:
            crop_box = normalize_crop(json.loads(crop))
        except (TypeError, ValueError, KeyError, OverflowError, json.JSONDecodeError):
            return JSONResponse({"ok": False, "msg": "Invalid crop area"}, status_code=400)
        try:
            raw_fx = json.loads(fx) if fx else None
        except (ValueError, json.JSONDecodeError):
            return JSONResponse({"ok": False, "msg": "Invalid frame settings"}, status_code=400)
        # Unknown styles/effects fall back to "none"; numbers are clamped.
        square_effects = square_fx.normalize(raw_fx, legacy_outline=outline.lower() in ("1", "true", "on"))
    q = quota_state(request)
    if not q["pro"] and q["left"] < rows:
        return JSONResponse({"ok": False, "msg": "Not enough free files left today"}, status_code=403)
    try:
        parsed = json.loads(settings)
        if not isinstance(parsed, list) or len(parsed) != rows:
            raise ValueError
        normalized = []
        for item in parsed:
            if not isinstance(item, dict):
                raise ValueError
            normalized.append({
                "brightness": max(50, min(150, int(item.get("brightness", 100)))),
                "contrast": max(50, min(150, int(item.get("contrast", 100)))),
                "saturation": max(0, min(200, int(item.get("saturation", 100)))),
                "hue": max(-180, min(180, int(item.get("hue", 0)))),
                "start": max(0.0, min(600.0, float(item.get("start", 0)))),
            })
    except (TypeError, ValueError, OverflowError, json.JSONDecodeError):
        return JSONResponse({"ok": False, "msg": "Invalid row settings"}, status_code=400)

    fps = max(5, min(24, fps))
    duration = max(1.0, min(8.0, duration))
    user = _auth_user(request)
    user_key = str(user.get("id") or "") if user else _ip(request)
    if user_key and rs.job_count_user(user_key) >= max_jobs_for_user(int(user["id"]) if user else None):
        return JSONResponse({"ok": False, "msg": "Too many active jobs"}, status_code=429)

    jid = secrets.token_hex(12)
    job_dir = JOBS / jid
    job_dir.mkdir(parents=True, exist_ok=True)
    uploaded = []
    uploaded_bytes = 0
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"}
    try:
        for index, file in enumerate(files, 1):
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in allowed:
                raise ValueError("Unsupported file format")
            path = job_dir / f"upload_{index}{suffix}"
            written = 0
            with path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    written += len(chunk)
                    uploaded_bytes += len(chunk)
                    if written > MAX_UPLOAD_MB * 1024 * 1024:
                        raise ValueError(f"Each source must be under {MAX_UPLOAD_MB} MB")
                    if uploaded_bytes > 95 * 1024 * 1024:
                        raise ValueError("All sources together must be under 100 MB")
                    output.write(chunk)
            if not written:
                raise ValueError("One source file is empty")
            uploaded.append({"name": file.filename, "path": str(path), "size": written})
    except ValueError as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)

    worker_mode = _worker_mode()
    external = worker_mode == "external" and rs.redis_ok() and rs.worker_alive()
    payload = {
        "kind": "workshop_studio", "queue": "media", "status": "queued", "pct": 1,
        "stage": "queued", "created": time.time(), "user_key": user_key,
        "files": uploaded,
        "options": {"rows": normalized, "fps": fps, "duration": duration,
                    "outline": outline.lower() in ("1", "true", "on"),
                    "free_watermark": not q["pro"],
                    "layout": layout, "crop": crop_box, "fx": square_effects},
        "opts": {"modes": ["workshop_studio"]},
    }
    rs.job_create(jid, payload, enqueue=external)
    _job_set(jid, status="queued", pct=1, stage="queued", user_key=user_key)
    try:
        quota_inc(request, rows)
    except Exception:
        pass
    if not external:
        from smweb.workshop_studio_jobs import run
        _job_pool.submit(run, jid, payload)
    return {"ok": True, "job_id": jid}


def _analytics_mode(opts: dict) -> str:
    modes = list(opts.get("modes") or [])
    return "all" if len(modes) > 1 else (str(modes[0]) if modes else "")


def _watermark_options(
    quota: dict,
    wm_text: str,
    wm_font: str,
    wm_opacity: int,
    wm_enable: str,
    wm_corner: str,
    wm_scale: float,
    wm_color: str,
    wm_x: str,
    wm_y: str,
) -> tuple[str, str, float, str, float, str, float | None, float | None]:
    """Return trusted watermark settings for the processing pipeline.

    Free-tier branding is enforced here instead of only in the browser, so it
    cannot be disabled or changed by editing the form payload.
    """
    if not quota.get("pro"):
        return "ShowcaseMaker", "Fineday", 0.50, "bl", 1.0, "#ffffff", None, None

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
    return text, wm_font, opacity, corner, scale, color, wm_x_f, wm_y_f


@router.post("/api/process/start")
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
    workshop_outline: str = Form("0"),
    outline_width: int = Form(2),
    outline_color: str = Form("#ffffff"),
    outline_style: str = Form("solid"),
    outline_color2: str = Form("#8a62ff"),
    outline_speed: int = Form(1),
    outline_target: str = Form("squares"),
    gif_encoder: str = Form("gifski"),
    all_modes: str = Form("0"),
    rotations: str = Form("[]"),
    asset_ids: str = Form("[]"),
    files: list[UploadFile] = File(default=[]),
):
    """Start async job; poll /api/process/status/{id} then download."""
    _job_cleanup_old()
    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return JSONResponse(
            {"ok": False, "msg": f"Limit {q['limit']} files/day. Enter access code or buy Pro."},
            status_code=403,
        )
    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)
    do_all = str(all_modes).lower() in ("1", "true", "yes", "on")
    modes = ["workshop", "featured", "split"] if do_all else [mode]
    text, wm_font, opacity, corner, scale, color, wm_x_f, wm_y_f = _watermark_options(
        q, wm_text, wm_font, wm_opacity, wm_enable, wm_corner,
        wm_scale, wm_color, wm_x, wm_y,
    )
    do_ac = str(auto_contrast).lower() in ("1", "true", "yes", "on")
    do_outline = str(workshop_outline).lower() in ("1", "true", "yes", "on")
    try:
        outline_width_i = max(1, min(12, int(outline_width))) if do_outline else 0
    except (TypeError, ValueError):
        outline_width_i = 2 if do_outline else 0
    outline_color_s = str(outline_color or "#ffffff").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", outline_color_s):
        outline_color_s = "#ffffff"
    try:
        size_i = int(size)
    except (TypeError, ValueError):
        size_i = 750
    if size_i not in (630, 640, 750, 800):
        size_i = min((630, 640, 750, 800), key=lambda s: abs(s - size_i))
    try:
        requested_assets = json.loads(asset_ids)
        if not isinstance(requested_assets, list):
            requested_assets = []
        requested_assets = [str(value) for value in requested_assets]
    except (TypeError, ValueError, json.JSONDecodeError):
        requested_assets = []
    left = int(os.environ.get("MAX_FILES_PER_JOB", "10")) if q["pro"] else q["left"]
    batch_limit = max(1, min(left, int(os.environ.get("MAX_FILES_PER_JOB", "10"))))
    requested_assets = requested_assets[:batch_limit]
    files = files[:max(0, batch_limit - len(requested_assets))]
    try:
        requested_rotations = json.loads(rotations)
        if not isinstance(requested_rotations, list):
            requested_rotations = []
    except (TypeError, ValueError, json.JSONDecodeError):
        requested_rotations = []
    if not files and not requested_assets:
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
        "outline_width": outline_width_i,
        "outline_color": outline_color_s,
        # Styled/animated frame for every showcase type; unknown styles fall back to "none".
        # target "squares" = around each part, "strip" = one frame around the whole showcase.
        "outline_fx": square_fx.normalize_frame({
            "style": outline_style, "color": outline_color_s, "color2": outline_color2,
            "width": outline_width_i, "speed": outline_speed, "target": outline_target,
        }) if do_outline else None,
        "size_i": size_i,
        "fps": fps,
        "enc": enc,
        "wm_font": wm_font,
        # The integrated report is available to every signed-in account.
        # Anonymous jobs still download normally and get a sign-in hint.
        "steam_check": bool(q.get("email")),
    }
    user_key = ""
    u = None
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
    if user_key and rs.job_count_user(user_key) >= max_jobs_for_user(int(u["id"]) if u else None):
        return JSONResponse(
            {"ok": False, "msg": "Too many active jobs. Wait for current processing to finish."},
            status_code=429,
        )

    # Persist directly to the shared volume. Do not retain every upload in RAM:
    # several users sending 40 MB files otherwise exhaust the API container
    # before the worker even starts.
    job_upload_dir = JOBS / jid
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    files_meta = []
    asset_owner = media_assets.owner_key(request)
    for asset_index, asset_id in enumerate(requested_assets):
        resolved = media_assets.resolve(asset_id, asset_owner)
        if not resolved:
            shutil.rmtree(job_upload_dir, ignore_errors=True)
            return JSONResponse({"ok": False, "msg": "One of the uploaded assets is unavailable"}, status_code=410)
        meta, path = resolved
        asset_rotation = proc.normalize_rotation(requested_rotations[asset_index] if asset_index < len(requested_rotations) else 0)
        asset_rotation = min((0.0, 90.0, -90.0, -180.0), key=lambda angle: abs(angle - asset_rotation))
        files_meta.append({
            "name": str(meta.get("name") or path.name), "path": str(path),
            "rotation": asset_rotation, "size": int(meta.get("size") or path.stat().st_size),
            "sha256": str(meta.get("sha256") or ""), "asset_id": asset_id,
        })
    per_file_limit = MAX_UPLOAD_MB * 1024 * 1024
    for index, uf in enumerate(files, start=len(files_meta)):
        name = uf.filename or "file"
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:80] or "file"
        p = job_upload_dir / f"{index:02d}_{safe}"
        written = 0
        too_large = False
        digest = hashlib.sha256()
        with p.open("wb") as destination:
            while True:
                chunk = await uf.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > per_file_limit:
                    too_large = True
                    break
                destination.write(chunk)
                digest.update(chunk)
        if too_large:
            shutil.rmtree(job_upload_dir, ignore_errors=True)
            return JSONResponse({"ok": False, "msg": f"{name}: >{MAX_UPLOAD_MB}MB"}, status_code=413)
        if not written:
            p.unlink(missing_ok=True)
            continue
        rotation = proc.normalize_rotation(requested_rotations[index] if index < len(requested_rotations) else 0)
        # Processing uses crisp quarter-turns. Arbitrary rotation belongs to the
        # Character editor, where a transparent expanded canvas is meaningful.
        rotation = min((0.0, 90.0, -90.0, -180.0), key=lambda angle: abs(angle - rotation))
        files_meta.append({"name": name, "path": str(p), "rotation": rotation, "size": written, "sha256": digest.hexdigest()})
    if not files_meta:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        return JSONResponse({"ok": False, "msg": "No files"}, status_code=400)

    event_context = analytics.request_context(request)
    total_upload_bytes = sum(int(item.get("size") or 0) for item in files_meta)
    first_suffix = Path(files_meta[0]["name"]).suffix.lower().lstrip(".")
    total_mb = total_upload_bytes / (1024 * 1024)
    opts["_analytics"] = {
        "session_hash": event_context.get("session_hash") or "",
        "language": event_context.get("language") or "other",
        "user_id": int(u["id"]) if u and u.get("id") else None,
        "file_type": first_suffix,
        "size_bucket": "under_1mb" if total_mb < 1 else "1_5mb" if total_mb < 5 else "5_20mb" if total_mb < 20 else "over_20mb",
    }

    cache_document = {
        "version": 2,
        "owner": user_key,
        "files": [{"sha256": item.get("sha256"), "rotation": item.get("rotation"), "name": item.get("name")} for item in files_meta],
        "options": {key: value for key, value in opts.items() if key != "_analytics"},
    }
    cache_key = hashlib.sha256(json.dumps(cache_document, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    cached_jid = rs.job_cache_get(cache_key)
    cached_job = rs.job_get(cached_jid) if cached_jid else None
    if cached_jid and cached_job and cached_job.get("status") == "done" and (
        cached_job.get("result_key") or Path(str(cached_job.get("zip_path") or "")).is_file()
    ):
        rs.job_update(cached_jid, cache_hit=True)
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        return {"ok": True, "job_id": cached_jid, "cached": True}

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
        "kind": "process", "queue": "media",
        "status": "queued", "pct": 1, "stage": "queued",
        "user_key": user_key, "files": files_meta, "opts": opts,
        "created": time.time(), "cache_key": cache_key,
    }
    rs.job_create(jid, payload, enqueue=external)
    _job_set(jid, status="queued", pct=1, stage="queued", created=time.time(), user_key=user_key)
    try:
        quota_inc(request, len(files_meta))
    except Exception:
        pass
    if not external:
        _job_pool.submit(_run_process_job_from_payload, jid, payload)
    return {"ok": True, "job_id": jid}


def _process_job_for(request: Request, job_id: str) -> dict | None:
    """Return a process job only to the user/IP that created it."""
    if not re.fullmatch(r"[a-f0-9]{24}", job_id or ""):
        return None
    job = _job_get(job_id)
    if not job:
        return None
    owner = str(job.get("user_key") or "")
    if owner:
        user = _auth_user(request)
        caller = str(user.get("id") or "") if user else _ip(request)
        if not secrets.compare_digest(owner, caller):
            return None
    return job


@router.get("/api/process/status/{job_id}")
def api_process_status(job_id: str, request: Request):
    j = _process_job_for(request, job_id)
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
        if j.get("readiness"):
            out["readiness"] = j.get("readiness")
        if j.get("saved_result_id"):
            out["saved_days"] = saved_results.KEEP_DAYS
    return out


@router.get("/api/process/download/{job_id}")
def api_process_download(job_id: str, request: Request):
    j = _process_job_for(request, job_id)
    if not j:
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    if j.get("status") != "done" or not (j.get("zip_path") or j.get("result_key")):
        return JSONResponse(
            {"ok": False, "msg": f"Not ready (status={j.get('status') or 'unknown'})"},
            status_code=409,
        )
    path = Path(str(j.get("zip_path") or ""))
    if not path.is_file() and j.get("result_key"):
        try:
            from smweb import object_store
            from fastapi.responses import RedirectResponse
            url = object_store.presigned_get_url(
                str(j["result_key"]), expires=600, download_name="showcase.zip", media_type="application/zip",
            )
            return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, no-store"})
        except Exception:
            pass
    if not path.is_file():
        # Result was cleaned up, or produced on a filesystem this instance cannot see.
        return JSONResponse(
            {"ok": False, "msg": "Result expired or stored on another instance. Please run the job again."},
            status_code=410,
        )
    event_info = (j.get("opts") or {}).get("_analytics") or {}
    caller = _auth_user(request)
    analytics.record(
        "zip_download", request=request,
        session_hash=event_info.get("session_hash") or "",
        user_id=caller.get("id") if caller else event_info.get("user_id"),
        language=event_info.get("language") or "",
        properties={"mode": _analytics_mode(j.get("opts") or {}), "value": path.stat().st_size},
    )
    return FileResponse(
        path,
        media_type="application/zip",
        filename="showcase.zip",
        headers={"X-Processed": str(j.get("processed") or "")},
    )


def _preview_archive(job_id: str, request: Request):
    job = _process_job_for(request, job_id)
    if not job:
        return None, JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    path = Path(job.get("zip_path") or "")
    if job.get("status") != "done" or not path.is_file():
        return None, JSONResponse({"ok": False, "msg": "Result unavailable or expired"}, status_code=410)
    return path, None


def _preview_entries(archive):
    # Only generated final image files; never expose originals, diagnostics or arbitrary ZIP paths.
    if len(archive.infolist()) > 500:
        raise ValueError("Too many entries")
    return [(index, entry) for index, entry in enumerate(archive.infolist())
            if re.fullmatch(r"(?:part_[1-5]|featured_630|center_506|side_100)\.(?:png|gif|jpg|jpeg)", Path(entry.filename).name, re.I)
            and 0 < entry.file_size <= 32 * 1024 * 1024]


@router.get("/api/process/preview/{job_id}")
def api_process_preview(job_id: str, request: Request):
    path, error = _preview_archive(job_id, request)
    if error is not None:
        return error
    try:
        with zipfile.ZipFile(path) as archive:
            files = [{"name": entry.filename, "size": entry.file_size,
                      "url": f"/api/process/preview/{job_id}/{index}"}
                     for index, entry in _preview_entries(archive)]
        return JSONResponse({"ok": True, "files": files}, headers={"Cache-Control": "private, no-store"})
    except (OSError, ValueError, zipfile.BadZipFile):
        return JSONResponse({"ok": False, "msg": "Preview unavailable"}, status_code=410)


@router.get("/api/process/preview/{job_id}/{entry_index}")
def api_process_preview_file(job_id: str, entry_index: int, request: Request):
    path, error = _preview_archive(job_id, request)
    if error is not None:
        return error
    try:
        with zipfile.ZipFile(path) as archive:
            entry = dict(_preview_entries(archive)).get(entry_index)
            if entry is None:
                return JSONResponse({"ok": False}, status_code=404)
            with archive.open(entry) as source:
                data = source.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024:
                raise ValueError("Preview too large")
            mime = {".png": "image/png", ".gif": "image/gif", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}[Path(entry.filename).suffix.lower()]
        return Response(data, media_type=mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
        return JSONResponse({"ok": False, "msg": "Preview unavailable"}, status_code=410)


@router.post("/api/process")
async def api_process():
    """Retired synchronous endpoint. Encoding inside Uvicorn stalls every visitor;
    use /api/process/start and poll /api/process/status/{id}."""
    return JSONResponse(
        {"ok": False, "msg": "Synchronous processing is disabled; use /api/process/start"},
        status_code=410,
    )


@router.get("/api/download/{job_id}")
def download(job_id: str):
    """Retired unauthenticated one-shot endpoint."""
    return JSONResponse(
        {"ok": False, "msg": "Legacy download expired; run the job again"},
        status_code=410,
    )


@router.get("/api/job-file/{job_id}/{name}")
def job_file(job_id: str, name: str, request: Request):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id or ""):
        return JSONResponse({"ok": False}, status_code=404)
    name = Path(name).name
    if not name or name.startswith("."):
        return JSONResponse({"ok": False}, status_code=404)
    path = JOBS / job_id / name
    if not browser_owns_job(path.parent, request) or not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path, filename=name, headers={"Cache-Control": "private, no-store"})
