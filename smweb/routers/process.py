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
from starlette.concurrency import run_in_threadpool

import processor as proc
import redis_store as rs

from smweb import analytics
from smweb import free_limits
from smweb import job_diagnostics
from smweb import media_assets
from smweb import saved_results
from smweb import square_fx


from fastapi import APIRouter


from smweb.core import JOBS, MAX_UPLOAD_MB, StartGuard, _auth_user, max_jobs_for_user, owner_key, quota_state
from smweb.job_access import browser_owns_job
from smweb.jobs import _sniff_extension
from smweb.jobs import (
    _job_cleanup_old,
    _job_get,
    _job_pool,
    _job_set,
    _run_process_job_from_payload,
    _worker_mode,
)
import logging
_LOG = logging.getLogger(__name__)


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
    crops: str = Form(""),
    fx: str = Form(""),
    encode_profile: str = Form("standard"),
    include_original: str = Form("0"),
    include_preview: str = Form("0"),
    files: list[UploadFile] = File(default=[]),
):
    """Create Workshop files in a background job.

    ``rows``: one full-height output per row (optional frame around each file).
    ``squares``: one source per row; the chosen 5:1 area of each (``crops``, a
    list of source fractions; ``crop`` for a single row) becomes five 150x150 files.
    """
    layout = (layout or "rows").strip().lower()
    if layout not in ("rows", "squares"):
        return JSONResponse({"ok": False, "msg": "Unknown layout"}, status_code=400)
    if rows not in (1, 2, 3) or len(files) != rows:
        return JSONResponse({"ok": False, "msg": "Select one file for each row"}, status_code=400)
    crop_boxes = None
    try:
        raw_fx = json.loads(fx) if fx else None
    except (ValueError, json.JSONDecodeError):
        return JSONResponse({"ok": False, "msg": "Invalid frame settings"}, status_code=400)
    # Unknown styles/effects fall back to "none"; numbers are clamped.
    effects = square_fx.normalize(raw_fx, legacy_outline=outline.lower() in ("1", "true", "on")) if raw_fx else None
    if layout == "squares":
        from smweb.workshop_studio_jobs import normalize_crop
        try:
            raw_crops = json.loads(crops) if crops else [json.loads(crop)]
            if not isinstance(raw_crops, list) or len(raw_crops) != rows:
                raise ValueError
            crop_boxes = [normalize_crop(item) for item in raw_crops]
        except (TypeError, ValueError, KeyError, OverflowError, json.JSONDecodeError):
            return JSONResponse({"ok": False, "msg": "Invalid crop area"}, status_code=400)
        if effects is None:
            effects = square_fx.normalize(None, legacy_outline=outline.lower() in ("1", "true", "on"))
    elif effects is not None:
        # Full-height rows take a frame only; effects are a squares feature.
        effects["effect"]["type"] = "none"
        effects["frame"]["target"] = "strip"
    q = quota_state(request)
    if not q["pro"] and q["left"] < rows:
        return free_limits.refusal(request, "daily_more" if q["left"] > 0 else "daily", "files", n=q["limit"])
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
    user_key = owner_key(request, user)
    guard = StartGuard(request, q, user_key)
    if not guard.lock():
        return JSONResponse({"ok": False, "msg": "Your previous upload is still starting. Try again in a moment."}, status_code=429)
    try:
        if user_key and rs.job_count_user(user_key) >= max_jobs_for_user(int(user["id"]) if user else None):
            return JSONResponse({"ok": False, "msg": "Too many active jobs"}, status_code=429)
        if not guard.reserve(rows):
            return free_limits.refusal(request, "daily_more" if q["left"] > 0 else "daily", "files", n=q["limit"])

        jid = secrets.token_hex(12)
        job_dir = JOBS / jid
        job_dir.mkdir(parents=True, exist_ok=True)
        uploaded = []
        uploaded_bytes = 0
        allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"}
        try:
            for index, file in enumerate(files, 1):
                suffix = Path(file.filename or "").suffix.lower()
                # Other still-image formats are stored as-is first and converted to PNG below.
                path = job_dir / f"upload_{index}{suffix if suffix in allowed else '.src'}"
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
                await run_in_threadpool(proc.restore_gif_trailer_file, path)  # a part of a Steam-ready ZIP (HEX 21) used as a source
                if suffix not in allowed:
                    # Names like "From Klickpin.com- Long title" lost their extension: trust the bytes.
                    with path.open("rb") as head_file:
                        sniffed = _sniff_extension(head_file.read(32))
                    if sniffed in allowed:
                        real = job_dir / f"upload_{index}{sniffed}"
                        path.replace(real)
                        path, suffix = real, sniffed
                if suffix not in allowed:
                    png = await run_in_threadpool(lambda source=path: proc.still_image_to_png(source.read_bytes()))
                    path.unlink(missing_ok=True)
                    if png is None:
                        raise ValueError("Unsupported file format")
                    path = job_dir / f"upload_{index}.png"
                    path.write_bytes(png)
                    written = len(png)
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
                        "layout": layout, "crops": crop_boxes, "fx": effects,
                        # Same choices as Process: encode speed and the optional extra files.
                        "encode_profile": proc.normalize_encode_profile(encode_profile),
                        "extras": sorted(_selected_extras(include_original, include_preview))},
            "opts": {"modes": ["workshop_studio"]},
        }
        rs.job_create(jid, payload, enqueue=external)
        _job_set(jid, status="queued", pct=1, stage="queued", user_key=user_key)
        guard.settle(rows)
        if not external:
            from smweb.workshop_studio_jobs import run
            _job_pool.submit(run, jid, payload)
        return {"ok": True, "job_id": jid}
    finally:
        guard.release()


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


def _json_object(raw: str) -> dict:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _selected_extras(include_original, include_preview) -> set[str]:
    on = lambda value: str(value or "").strip().lower() in ("1", "true", "yes", "on")
    extras = set()
    if on(include_original):
        extras.add(proc.EXTRA_ORIGINAL)
    if on(include_preview):
        extras.add(proc.EXTRA_PREVIEW)
    return extras


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
    outline_shape: str = Form("rect"),
    outline_plate: int = Form(0),
    grade: str = Form(""),
    parallax: str = Form(""),
    gif_encoder: str = Form("gifski"),
    all_modes: str = Form("0"),
    rotations: str = Form("[]"),
    asset_ids: str = Form("[]"),
    encode_profile: str = Form("standard"),
    include_original: str = Form("0"),
    include_preview: str = Form("0"),
    files: list[UploadFile] = File(default=[]),
):
    """Start async job; poll /api/process/status/{id} then download."""
    _job_cleanup_old()
    q = quota_state(request)
    if not q["pro"] and q["left"] <= 0:
        return free_limits.refusal(request, "daily", "files", n=q["limit"])
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
            "shape": outline_shape, "plate": outline_plate,
        }) if do_outline else None,
        "size_i": size_i,
        # Colour correction (brightness/contrast/saturation/hue); None when neutral.
        "grade": proc.normalize_grade(_json_object(grade)),
        # "Depth" (2.5D parallax loop for stills, processor.parallax_source); None when off.
        "parallax": proc.normalize_parallax(_json_object(parallax)) if parallax else None,
        "fps": fps,
        "enc": enc,
        "wm_font": wm_font,
        # Animated outputs: "standard" (fast) or "max" (slow, fills 5 MB); see processor.encode_profile.
        "encode_profile": proc.normalize_encode_profile(encode_profile),
        # Optional files next to the Steam files; by default the ZIP holds only what Steam needs.
        "extras": sorted(_selected_extras(include_original, include_preview)),
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
        user_key = owner_key(request, u)
    except Exception:
        user_key = ""
    # One start at a time per owner; the free files are reserved atomically and the
    # unused part is given back (smweb.core.StartGuard).
    guard = StartGuard(request, q, user_key)
    if not guard.lock():
        return JSONResponse({"ok": False, "msg": "Your previous upload is still starting. Try again in a moment."}, status_code=429)
    try:
        # Check the per-user cap BEFORE registering the job or charging quota,
        # otherwise a rejected request still burns a free-tier slot.
        if user_key and rs.job_count_user(user_key) >= max_jobs_for_user(int(u["id"]) if u else None):
            return JSONResponse(
                {"ok": False, "msg": "Too many active jobs. Wait for current processing to finish."},
                status_code=429,
            )
        if not guard.reserve(len(files) + len(requested_assets)):
            return free_limits.refusal(request, "daily", "files", n=q["limit"])

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
            _LOG.info(f"[job {jid[:8]}] WORKER_MODE=external but no live worker "
                f"(redis={rs.redis_ok()} beat={rs.worker_alive()}) — running embedded")

        payload = {
            "kind": "process", "queue": "media",
            "status": "queued", "pct": 1, "stage": "queued",
            "user_key": user_key, "files": files_meta, "opts": opts,
            "created": time.time(), "cache_key": cache_key,
        }
        rs.job_create(jid, payload, enqueue=external)
        _job_set(jid, status="queued", pct=1, stage="queued", created=time.time(), user_key=user_key)
        analytics.record("process_started", session_hash=opts["_analytics"]["session_hash"],
                         user_id=opts["_analytics"]["user_id"], language=opts["_analytics"]["language"],
                         properties={"mode": _analytics_mode(opts), "file_type": opts["_analytics"]["file_type"]},
                         event_key=f"process:{jid}:started")
        guard.settle(len(files_meta))
        if not external:
            _job_pool.submit(_run_process_job_from_payload, jid, payload)
        return {"ok": True, "job_id": jid}
    finally:
        guard.release()


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
        caller = owner_key(request, user)
        if not secrets.compare_digest(owner, caller):
            return None
    return job


# Seconds per unit of work (one file x one showcase type) until a server has its own history (measured on the
# OVH VPS, 2026-09-28: Workshop / Featured from an 8 s video ~40 s, pictures ~1-2 s).
_ETA_DEFAULT = {"still": 2.0, "motion-standard": 30.0, "motion-max": 40.0}


def _process_eta(job_id: str, job: dict) -> dict:
    """Queue position, "seconds left" and a time-based progress for the running job.

    The estimate is per kind of work (pictures vs GIF / video, fast vs best encoding) and per unit (file x
    showcase type): one median for every job said "5 s left" for GIFs that still needed half a minute. Once the
    estimate runs out the answer is ``eta_over`` ("almost done") instead of a number that keeps lying.
    """
    status = job.get("status")
    if status not in ("queued", "running"):
        return {}
    kind = str(job.get("eta_kind") or "")
    units = max(1, int(job.get("eta_units") or 1))
    per_unit = rs.eta_typical(f"process:{kind}") if kind else None
    if per_unit:
        total = per_unit * units
    elif kind in _ETA_DEFAULT:
        total = _ETA_DEFAULT[kind] * units
    else:
        total = rs.eta_typical("process")             # jobs queued before this change
    out: dict = {}
    if status == "queued":
        ahead = rs.queue_ahead(job_id)
        if ahead is not None:
            out["queue_ahead"] = ahead
            if total:
                workers = max(1, int(os.environ.get("MAX_JOB_WORKERS") or 1))
                out["eta_seconds"] = int(total * (1 + ahead // workers))
    elif total:
        elapsed = max(0.0, time.time() - float(job.get("started") or time.time()))
        left = total - elapsed
        # Past the estimate the job says "almost done" rather than a number that stays wrong.
        if left > 2:
            out["eta_seconds"] = int(left + 0.999)
        else:
            out["eta_over"] = True
        out["pct_time"] = round(min(95.0, 100.0 * elapsed / total), 1)
    return out


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
        "file_no": j.get("file_no"),
        "files_total": j.get("files_total"),
        "error": j.get("error"),
        "processed": j.get("processed"),
        "errors": j.get("errors") or [],
    }
    out.update(_process_eta(job_id, j))
    if j.get("status") == "error":
        out.update(job_diagnostics.public_error(j.get("error")))
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
    # Files of a profile preview the owner chose to share (smweb.routers.preview.share_preview).
    shared = (path.parent / ".public").is_file() and (path.parent / "preview.html").is_file()
    if not (shared or browser_owns_job(path.parent, request)) or not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path, filename=name, headers={"Cache-Control": "private, no-store"})


# ---------------------------------------------------------------- "Depth" preview (static/js/process-depth.js)
# POST /api/process/depth: the picture (the browser sends it upright, <= 640 px) -> depth map, both kept for an hour
# under DATA/cache/depth-preview/<token>; answers the token and a first guess of the body region.
# POST /api/process/depth/render: token + options -> an animated WebP rendered by smweb.depth_fx, the same code as the
# final clip (processor.parallax_source), only smaller and at 10 fps.
# POST /api/process/depth/clip: token + options -> a seamless clip (15 fps, PARALLAX_SECONDS) at up to _DEPTH_CLIP_SIDE
# px for the Builder's Character layer (static/js/builder-depth.js): WebM VP9 with alpha for a cut-out, else H.264 MP4. Needs the picture prepared with keep=1,
# which also stores source.png at that size; the depth map is the 640 px one, scaled up (it is smooth anyway).
import threading as _threading  # noqa: E402

_DEPTH_SLOTS = _threading.BoundedSemaphore(max(1, int(os.environ.get("DEPTH_PREVIEW_CONCURRENCY", "2") or 2)))
_DEPTH_PREVIEW_SIDE = 640
# Preview size: the whole 640 px picture; "large" (the Builder window, which keeps source.png) up to 760 px.
# 900 px took ~6 s and 3.5 MB per change, too slow for sliders. Owner asked for a sharper preview (2026-10-08).
_DEPTH_RENDER_BOX = (640, 640)
_DEPTH_RENDER_BOX_LARGE = (760, 760)
_DEPTH_RENDER_QUALITY = 84
_DEPTH_RENDER_FRAMES = 40
_DEPTH_TTL = 3600
_DEPTH_CACHE = JOBS.parent / "cache" / "depth-preview"
_DEPTH_CLIP_SIDE = 1600
_DEPTH_CLIP_FPS = 15


def _depth_slot():
    if not _DEPTH_SLOTS.acquire(timeout=20):
        raise TimeoutError("busy")


def _depth_prune():
    now = time.time()
    try:
        for item in _DEPTH_CACHE.iterdir():
            if now - item.stat().st_mtime > _DEPTH_TTL:
                shutil.rmtree(item, ignore_errors=True)
    except OSError:
        pass


def _depth_prepare(data: bytes, keep: bool = False) -> dict:
    import io
    import numpy as np
    from PIL import Image
    from smweb import depth, depth_fx
    _depth_slot()
    try:
        with Image.open(io.BytesIO(proc.restore_gif_trailer(data))) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError("too_large")
            image.seek(0)
            picture = image.convert("RGBA")
        source = None
        if keep:
            source = picture.copy()
            source.thumbnail((_DEPTH_CLIP_SIDE, _DEPTH_CLIP_SIDE), Image.Resampling.LANCZOS)
        picture.thumbnail((_DEPTH_PREVIEW_SIDE, _DEPTH_PREVIEW_SIDE), Image.Resampling.LANCZOS)
        estimate = depth.estimate(picture)
    finally:
        _DEPTH_SLOTS.release()
    _depth_prune()
    token = secrets.token_hex(16)
    folder = _DEPTH_CACHE / token
    folder.mkdir(parents=True, exist_ok=True)
    picture.save(folder / "picture.png", compress_level=1)
    if source is not None:
        source.save(folder / "source.png", compress_level=1)
    np.save(folder / "depth.npy", estimate.astype(np.float16))
    return {"ok": True, "token": token, "width": picture.width, "height": picture.height,
            "body": depth_fx.body_guess(estimate)}


def _depth_render(token: str, options: dict, large: bool = False) -> bytes:
    import io
    import numpy as np
    from PIL import Image
    from smweb import depth_fx
    folder = _DEPTH_CACHE / token
    if not re.fullmatch(r"[a-f0-9]{32}", token or "") or not (folder / "depth.npy").is_file():
        raise FileNotFoundError(token)
    folder.touch()
    large = large and (folder / "source.png").is_file()
    with Image.open(folder / ("source.png" if large else "picture.png")) as image:
        picture = image.convert("RGBA")
    estimate = np.load(folder / "depth.npy").astype(np.float32)
    picture.thumbnail(_DEPTH_RENDER_BOX_LARGE if large else _DEPTH_RENDER_BOX, Image.Resampling.LANCZOS)
    estimate = np.asarray(Image.fromarray(estimate).resize(picture.size, Image.Resampling.BILINEAR), dtype=np.float32)
    _depth_slot()
    try:
        scene = depth_fx.Scene(np.asarray(picture, dtype=np.uint8), estimate, options)
        frames = [Image.fromarray(scene.frame(i / _DEPTH_RENDER_FRAMES), "RGBA") for i in range(_DEPTH_RENDER_FRAMES)]
    finally:
        _DEPTH_SLOTS.release()
    out = io.BytesIO()
    duration = int(round(proc.PARALLAX_SECONDS * 1000 / _DEPTH_RENDER_FRAMES))
    frames[0].save(out, "WEBP", save_all=True, append_images=frames[1:], duration=duration, loop=0, quality=_DEPTH_RENDER_QUALITY, method=2)
    return out.getvalue()


def _depth_clip(token: str, options: dict) -> tuple[bytes, str]:
    """The seamless loop for the Builder's Character layer: the same Scene as the preview and the Process files.

    A cut-out (any transparent pixel) becomes a WebM with alpha (VP9, yuva420p), anything else an H.264 MP4.
    Returns (bytes, media type).
    """
    import subprocess
    import tempfile
    import numpy as np
    from PIL import Image
    from smweb import depth_fx
    folder = _DEPTH_CACHE / token
    if not re.fullmatch(r"[a-f0-9]{32}", token or "") or not (folder / "depth.npy").is_file():
        raise FileNotFoundError(token)
    folder.touch()
    source = folder / "source.png" if (folder / "source.png").is_file() else folder / "picture.png"
    with Image.open(source) as image:
        picture = image.convert("RGBA")
    transparent = picture.getchannel("A").getextrema()[0] < 255
    # yuv420p / yuva420p need even sides.
    width, height = picture.width - picture.width % 2, picture.height - picture.height % 2
    picture = picture.crop((0, 0, width, height))
    estimate = np.load(folder / "depth.npy").astype(np.float32)
    estimate = np.asarray(Image.fromarray(estimate).resize((width, height), Image.Resampling.BICUBIC), dtype=np.float32)
    frames = int(round(proc.PARALLAX_SECONDS * _DEPTH_CLIP_FPS))
    _depth_slot()
    try:
        scene = depth_fx.Scene(np.asarray(picture, dtype=np.uint8), estimate, options)
        with tempfile.TemporaryDirectory() as work:
            target = Path(work) / ("clip.webm" if transparent else "clip.mp4")
            if transparent:
                # -auto-alt-ref 0: libvpx drops the alpha plane with alt-ref frames on.
                codec = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "28", "-deadline", "realtime",
                         "-cpu-used", "6", "-row-mt", "1", "-auto-alt-ref", "0"]
            else:
                codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
            command = [proc.find_ffmpeg() or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                       "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", str(_DEPTH_CLIP_FPS), "-i", "-",
                       *codec, "-an", str(target)]
            encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for index in range(frames):
                    frame = scene.frame(index / frames)
                    if frame.shape[2] == 3:
                        frame = np.dstack([frame, np.full(frame.shape[:2], 255, np.uint8)])
                    encoder.stdin.write(np.ascontiguousarray(frame).tobytes())
                encoder.stdin.close()
                if encoder.wait(timeout=120) != 0:
                    raise RuntimeError("ffmpeg failed")
            finally:
                if encoder.poll() is None:
                    encoder.kill()
            return target.read_bytes(), "video/webm" if transparent else "video/mp4"
    finally:
        _DEPTH_SLOTS.release()


@router.post("/api/process/depth/clip")
async def depth_clip(request: Request):
    """Seamless clip of the "Depth" effects for the Builder's Character layer (picture prepared with keep=1)."""
    from smweb import depth_fx
    try:
        body = await request.json()
    except Exception:
        body = None
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "code": "bad_request"}, status_code=400)
    options = depth_fx.normalize(body.get("options"))
    if not options:
        return JSONResponse({"ok": False, "code": "nothing"}, status_code=400)
    try:
        clip, media_type = await run_in_threadpool(_depth_clip, str(body.get("token") or ""), options)
    except FileNotFoundError:
        return JSONResponse({"ok": False, "code": "expired"}, status_code=404)
    except TimeoutError:
        return JSONResponse({"ok": False, "code": "busy", "msg": "Busy, try again"}, status_code=503)
    except Exception:
        _LOG.exception("depth clip render failed")
        return JSONResponse({"ok": False, "code": "failed"}, status_code=500)
    return Response(clip, media_type=media_type, headers={"Cache-Control": "no-store"})


def _depth_unavailable():
    return JSONResponse({"ok": False, "code": "depth_unavailable", "msg": "Depth is not available right now"}, status_code=503)


@router.post("/api/process/depth/render")
async def depth_render(request: Request):
    """Preview of the "Depth" effects for a picture prepared by /api/process/depth."""
    from smweb import depth_fx
    try:
        body = await request.json()
    except Exception:
        body = None
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "code": "bad_request"}, status_code=400)
    options = depth_fx.normalize(body.get("options"))
    if not options:
        return JSONResponse({"ok": False, "code": "nothing"}, status_code=400)
    try:
        webp = await run_in_threadpool(_depth_render, str(body.get("token") or ""), options, body.get("size") == "large")
    except FileNotFoundError:
        return JSONResponse({"ok": False, "code": "expired"}, status_code=404)
    except TimeoutError:
        return JSONResponse({"ok": False, "code": "busy", "msg": "Busy, try again"}, status_code=503)
    except Exception:
        _LOG.exception("depth preview render failed")
        return JSONResponse({"ok": False, "code": "failed"}, status_code=500)
    return Response(webp, media_type="image/webp", headers={"Cache-Control": "no-store"})


@router.post("/api/process/depth")
async def depth_preview(file: UploadFile = File(...), keep: str = Form("")):
    """Depth map of a picture for the "Depth" preview; the frames come from /api/process/depth/render."""
    from smweb import depth
    if not depth.available():
        return _depth_unavailable()
    data = await file.read(25 * 1024 * 1024 + 1)
    if not data or len(data) > 25 * 1024 * 1024:
        return JSONResponse({"ok": False, "code": "too_large", "msg": "File is too large"}, status_code=413)
    try:
        result = await run_in_threadpool(_depth_prepare, data, keep in ("1", "true", "yes"))
    except TimeoutError:
        return JSONResponse({"ok": False, "code": "busy", "msg": "Busy, try again"}, status_code=503)
    except Exception:
        return JSONResponse({"ok": False, "code": "bad_image", "msg": "Could not read the picture"}, status_code=400)
    return JSONResponse(result, headers={"Cache-Control": "no-store"})
