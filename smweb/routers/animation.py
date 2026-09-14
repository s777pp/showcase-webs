"""Authenticated, allowlisted Builder AI experiment. Off by default."""
from __future__ import annotations
import io
import os
import re
import secrets
import hashlib
import json
from typing import Literal
from fastapi import APIRouter, Request, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field
import redis_store as rs
from smweb.core import _auth_user
from smweb import object_store
from smweb.animation_selection import AutoMask, MotionSelection, selection_mask, selection_prompts
from smweb.animation_experiment import (
    keys, segmentation_key, prepare_image, MAX_INPUT_BYTES, MAX_OUTPUT_BYTES,
    PROTOCOL_VERSION, SEGMENTATION_MODEL_ID,
)
from smweb.animation_jobs import reserve, release, TTL
from smweb.modal_animation_client import AnimationClient

router = APIRouter(prefix="/api/animation", tags=["animation"])

class Options(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    selection: MotionSelection
    intensity: Literal["gentle", "normal", "strong"] = "normal"
    quality: Literal["draft", "quality"] = "draft"
    matte: str = Field(default="#00ff00", pattern=r"^#[a-fA-F0-9]{6}$")

def allowed(request):
    user = _auth_user(request)
    emails = {x.strip().casefold() for x in os.environ.get("ANIMATION_ALLOWED_EMAILS", "").split(",") if x.strip()}
    return user if os.environ.get("ANIMATION_ENABLED", "0") == "1" and user and str(user.get("email", "")).casefold() in emails else None

def error(code, status=400):
    return JSONResponse({"ok": False, "error": code}, status_code=status, headers={"Cache-Control": "no-store"})


AUTO_TARGETS = {"hair", "breathing", "eyes", "cloth"}


def validate_segmentation_result(data, requested):
    if not isinstance(data, dict) or data.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("Invalid segmentation response")
    if data.get("model") != SEGMENTATION_MODEL_ID or not isinstance(data.get("masks"), list):
        raise ValueError("Invalid segmentation response")
    result, seen = [], set()
    for item in data["masks"]:
        if not isinstance(item, dict) or item.get("target") not in requested or item["target"] in seen:
            raise ValueError("Invalid segmentation response")
        seen.add(item["target"])
        if item.get("found") is False:
            confidence = item.get("confidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
                raise ValueError("Invalid segmentation response")
            result.append({"target": item["target"], "found": False,
                           "confidence": round(float(confidence), 3)})
            continue
        mask = AutoMask.model_validate({key: item.get(key) for key in
                                        ("target", "width", "height", "png", "confidence")})
        result.append({"found": True, **mask.model_dump()})
    if seen != set(requested):
        raise ValueError("Incomplete segmentation response")
    return result

def owner_job(request, jid):
    user = allowed(request)
    if not user or not re.fullmatch(r"[a-f0-9]{32}", jid):
        return None
    job = rs.job_get(jid)
    return job if job and job.get("kind") == "ai_animation" and job.get("user_key") == str(user["id"]) else None

@router.get("/config")
def config(request: Request):
    user = allowed(request)
    jid = None
    if user:
        try:
            r = rs.get_redis()
            raw = r.get(f"sm:animation:last:{user['id']}") if r else None
            candidate = raw.decode() if isinstance(raw, bytes) else raw
            if isinstance(candidate, str) and owner_job(request, candidate):
                jid = candidate
        except Exception:
            pass
    return JSONResponse({"enabled": bool(user), "user_id": str(user["id"]) if user else None, "job_id": jid}, headers={"Cache-Control": "no-store"})

@router.post("/prompt")
async def prompt(request: Request):
    if not allowed(request):
        return error("unavailable", 403)
    raw = await request.body()
    if len(raw) > 256000:
        return error("invalid_selection")
    try:
        options = Options.model_validate_json(raw)
        positive, _ = selection_prompts(options.selection, options.intensity)
        return {"ok": True, "prompt": positive}
    except ValueError:
        return error("invalid_selection")


@router.post("/segment")
async def segment(request: Request, file: UploadFile = File(...), targets: str = Form("[]")):
    user = allowed(request)
    if not user:
        return error("unavailable", 403)
    try:
        selected = json.loads(targets)
        if (not isinstance(selected, list) or not 1 <= len(selected) <= 4
                or any(not isinstance(target, str) or target not in AUTO_TARGETS for target in selected)
                or len(set(selected)) != len(selected)):
            return error("no_detectable_targets")
        raw = await file.read(MAX_INPUT_BYTES + 1)
        image = await run_in_threadpool(prepare_image, raw, "#00ff00", canonical=True)
        saved = io.BytesIO()
        image.save(saved, format="PNG", optimize=True)
        content = saved.getvalue()
        if len(content) > MAX_INPUT_BYTES:
            return error("invalid_image")
    except Exception:
        return error("invalid_image")

    cache_key = "sm:animation:segment:" + hashlib.sha256(
        content + json.dumps(sorted(selected), separators=(",", ":")).encode() + str(PROTOCOL_VERSION).encode()
    ).hexdigest()
    try:
        redis = rs.get_redis()
        cached = redis.get(cache_key) if redis else None
        if isinstance(cached, bytes):
            cached = cached.decode("utf-8")
        if isinstance(cached, str):
            masks = validate_segmentation_result(json.loads(cached), selected)
            return JSONResponse({"ok": True, "cached": True, "masks": masks},
                                headers={"Cache-Control": "no-store"})
    except Exception:
        cached = None
    if not object_store.configured():
        return error("service_unavailable", 503)
    try:
        client = AnimationClient()
        if (await run_in_threadpool(client.health)).get("protocol_version") != PROTOCOL_VERSION:
            return error("update_modal", 503)
    except Exception:
        return error("service_unavailable", 503)
    try:
        permitted, _ = await run_in_threadpool(
            rs.rate_limit, f"animation-segment:{user['id']}",
            max(1, min(50, int(os.environ.get("ANIMATION_SEGMENT_DAILY_LIMIT", "20")))),
            86400, fail_closed=True,
        )
        if not permitted:
            return error("detect_limit", 429)
    except Exception:
        return error("service_unavailable", 503)

    jid = secrets.token_hex(16)
    source = segmentation_key(jid)
    try:
        await run_in_threadpool(object_store.put_bytes, source, content,
                                public=False, media_type="image/png")
        payload = {"request_id": jid,
                   "source_url": object_store.presigned_get_url(source, expires=600),
                   "targets": selected}
        remote = await run_in_threadpool(client.segment, payload)
        masks = validate_segmentation_result(remote, selected)
        try:
            redis = rs.get_redis()
            if redis:
                redis.set(cache_key, json.dumps(remote, separators=(",", ":")), ex=86400)
        except Exception:
            pass
        return JSONResponse({"ok": True, "cached": False, "masks": masks},
                            headers={"Cache-Control": "no-store"})
    except Exception:
        return error("detect_failed", 502)
    finally:
        try:
            object_store.delete(source, public=False)
        except Exception:
            pass

@router.post("/start")
async def start(request: Request, file: UploadFile = File(...), options: str = Form(...), confirm_cost: str = Form(""), request_id: str = Form("")):
    user = allowed(request)
    if not user:
        return error("unavailable", 403)
    if confirm_cost != "yes":
        return error("consent_required")
    if request_id and not re.fullmatch(r"[a-f0-9]{32}", request_id):
        return error("invalid_request")
    if len(options) > 256000:
        return error("invalid_selection")
    try:
        opts = Options.model_validate_json(options)
        raw = await file.read(MAX_INPUT_BYTES + 1)
        image = await run_in_threadpool(prepare_image, raw, opts.matte, canonical=True)
        if opts.selection.lock_outside and selection_mask(opts.selection, image.size).getbbox() is None:
            return error("invalid_selection")
        saved = io.BytesIO()
        image.save(saved, format="PNG")
        if saved.tell() > MAX_INPUT_BYTES:
            return error("invalid_image")
    except Exception:
        return error("invalid_image")
    jid = request_id or secrets.token_hex(16)
    fingerprint = hashlib.sha256(saved.getvalue() + json.dumps(opts.model_dump(), sort_keys=True).encode()).hexdigest()
    existing = await run_in_threadpool(rs.job_get, jid)
    if existing:
        if existing.get("kind") != "ai_animation" or existing.get("user_key") != str(user["id"]):
            return error("not_found", 404)
        if existing.get("fingerprint") != fingerprint:
            return error("request_changed", 409)
        return JSONResponse({"ok": True, "job_id": jid}, status_code=202)
    if not object_store.configured() or not rs.redis_ok() or not rs.worker_alive():
        return error("service_unavailable", 503)
    try:
        client = AnimationClient()
        if (await run_in_threadpool(client.health)).get("protocol_version") != PROTOCOL_VERSION:
            return error("update_modal", 503)
    except Exception:
        return error("service_unavailable", 503)
    try:
        admission = await run_in_threadpool(reserve, jid, str(user["id"]))
    except Exception:
        return error("service_unavailable", 503)
    if admission != 1:
        return error("busy" if admission == 0 else "daily_limit", 429)
    source, output = keys(jid)
    try:
        await run_in_threadpool(object_store.put_bytes, source, saved.getvalue(), public=False, media_type="image/png")
    except Exception:
        try:
            await run_in_threadpool(release, jid)
        except Exception:
            pass
        return error("service_unavailable", 503)
    try:
        await run_in_threadpool(rs.job_create, jid, {
            "kind": "ai_animation", "user_key": str(user["id"]), "source_key": source,
            "result_key": output, **opts.model_dump(), "status": "queued",
            "fingerprint": fingerprint,
        }, fail_closed=True)
    except Exception:
        # Queue delivery might have succeeded. Do not delete its input/free the
        # paid slot after an ambiguous transactional response.
        return JSONResponse({"ok": False, "error": "outcome_unknown", "job_id": jid}, status_code=503)
    return JSONResponse({"ok": True, "job_id": jid}, status_code=202)

@router.get("/status/{jid}")
def status(request: Request, jid: str):
    job = owner_job(request, jid)
    if not job:
        return error("not_found", 404)
    return JSONResponse({key: job.get(key) for key in ("status", "stage", "pct", "error", "motion_low")}, headers={"Cache-Control": "no-store"})

@router.post("/cancel/{jid}")
def cancel(request: Request, jid: str):
    job = owner_job(request, jid)
    if not job:
        return error("not_found", 404)
    if job.get("status") in {"done", "error", "cancelled"}:
        return error("already_finished", 409)
    try:
        r = rs.get_redis()
        if not r:
            raise RuntimeError()
        r.set(f"sm:animation:cancel:{jid}", "1", ex=TTL)
        return {"ok": True, "status": "cancel_pending"}
    except Exception:
        return error("service_unavailable", 503)

@router.get("/download/{jid}")
def download(request: Request, jid: str):
    job = owner_job(request, jid)
    if not job:
        return error("not_found", 404)
    if job.get("status") != "done":
        return error("not_ready", 409)
    params = {"Bucket": object_store.PRIVATE_BUCKET, "Key": keys(jid)[1]}
    requested_range = request.headers.get("range", "")
    if requested_range:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested_range)
        if not match or not any(match.groups()):
            return error("invalid_range", 416)
        begin, end = match.groups()
        if (begin and int(begin) >= MAX_OUTPUT_BYTES or end and int(end) > MAX_OUTPUT_BYTES
                or begin and end and int(begin) > int(end) or not begin and int(end) == 0):
            return error("invalid_range", 416)
        params["Range"] = requested_range
    try:
        result = object_store.client().get_object(**params)
        size = int(result["ContentLength"])
        body = result["Body"]
        if not 0 < size <= MAX_OUTPUT_BYTES:
            body.close()
            return error("invalid_output", 502)
    except Exception as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code")
        if code == "InvalidRange":
            return error("invalid_range", 416)
        return error("expired", 410)
    def chunks():
        try:
            remaining = size
            while remaining:
                chunk = body.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        except Exception:
            raise RuntimeError("Animation download interrupted") from None
        finally:
            body.close()
    headers = {"Cache-Control": "private, no-store", "Content-Length": str(size), "Accept-Ranges": "bytes"}
    content_range = result.get("ContentRange")
    if requested_range and isinstance(content_range, str) and re.fullmatch(r"bytes \d+-\d+/\d+", content_range):
        headers["Content-Range"] = content_range
    return StreamingResponse(chunks(), media_type="video/mp4", status_code=206 if "Content-Range" in headers else 200, headers=headers)
