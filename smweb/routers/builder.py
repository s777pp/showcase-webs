"""Layered showcase builder projects and private source assets.

The browser owns the interactive canvas; this module owns durable project
metadata, source uploads and the Free/Pro export allowance. Keeping those
responsibilities here avoids coupling the editor to the media processing API.
"""
from __future__ import annotations

import json
import io
import os
import re
import secrets
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image, UnidentifiedImageError

import auth_db
import redis_store as rs
from smweb import object_store
from smweb.core import DATA, MAX_UPLOAD_MB, _auth_user, _safe_data_path


router = APIRouter(prefix="/api/builder", tags=["builder"])
_remove_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="builder-bg-remove")
_MODES = {"workshop", "featured", "split"}
_LAYER_TYPES = {"background", "character", "text", "frame", "effect", "dna"}
_EFFECTS = {"particle", "snow", "stars", "matrix", "streaks", "sparks", "custom"}
_ANIMATIONS = {"none", "breathing", "wave"}
_SAFE_MEDIA = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".mp4": "video/mp4",
    ".webm": "video/webm", ".mov": "video/quicktime",
}


def _local_asset_path(rel: str) -> Path:
    base = Path(DATA).resolve()
    path = (base / rel).resolve()
    if base not in path.parents:
        raise ValueError("Invalid asset path")
    return path


def _user(request: Request):
    user = _auth_user(request)
    if not user:
        return None, JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    return user, None


def _validated_project(raw) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Invalid project")
    layers = raw.get("layers")
    if not isinstance(layers, list) or len(layers) > 24:
        raise ValueError("A project may contain up to 24 layers")
    clean_layers = []
    for layer in layers:
        if not isinstance(layer, dict) or layer.get("type") not in _LAYER_TYPES:
            raise ValueError("Invalid layer")
        item = dict(layer)
        item["id"] = re.sub(r"[^a-zA-Z0-9_-]", "", str(item.get("id") or ""))[:64] or secrets.token_hex(6)
        item["name"] = str(item.get("name") or item["type"])[:80]
        for key in ("x", "y", "scale", "rotation", "opacity"):
            try:
                item[key] = float(item.get(key, 0 if key in ("x", "y", "rotation") else 1))
            except (TypeError, ValueError):
                item[key] = 0 if key in ("x", "y", "rotation") else 1
        if "text" in item:
            item["text"] = str(item["text"])[:500]
        if "font" in item:
            item["font"] = str(item["font"])[:80]
        numeric_fields = {
            "fontSize": (14, 180, 64),
            "frameWidth": (1, 30, 4),
            "chromaTolerance": (10, 120, 45),
            "chromaFeather": (0, 40, 16),
        }
        for key, (minimum, maximum, default) in numeric_fields.items():
            if key not in item:
                continue
            try:
                item[key] = max(minimum, min(maximum, float(item[key])))
            except (TypeError, ValueError):
                item[key] = default
        if "color" in item:
            color = str(item["color"])
            item["color"] = color if re.fullmatch(r"#[0-9a-fA-F]{6}", color) else "#52d5ff"
        if item["type"] == "effect":
            item["effect"] = item.get("effect") if item.get("effect") in _EFFECTS else "particle"
        if item["type"] == "dna":
            raw_signals = item.get("signals") if isinstance(item.get("signals"), dict) else {}
            item["signals"] = {}
            for signal in ("focus", "variety", "mastery", "history", "activity", "collector"):
                try:
                    item["signals"][signal] = max(0.0, min(1.0, float(raw_signals.get(signal, 0))))
                except (TypeError, ValueError):
                    item["signals"][signal] = 0.0
            raw_palette = item.get("palette") if isinstance(item.get("palette"), list) else []
            item["palette"] = [
                color for color in (str(value) for value in raw_palette[:3])
                if re.fullmatch(r"#[0-9a-fA-F]{6}", color)
            ] or ["#52d5ff", "#7c5cff", "#ff5ec4"]
            item["seed"] = re.sub(r"[^a-fA-F0-9]", "", str(item.get("seed") or ""))[:32]
            item["archetype"] = re.sub(r"[^a-z_]", "", str(item.get("archetype") or "signal_weaver"))[:40]
        item["animation"] = item.get("animation") if item.get("animation") in _ANIMATIONS else "none"
        item["chroma"] = bool(item.get("chroma", False))
        if "src" in item:
            src = str(item["src"])[:3000]
            if not (src.startswith("/api/builder/assets/") or
                    src.startswith("/api/steam/proxy-image?") or
                    src.startswith("https://shared.cloudflare.steamstatic.com/") or
                    src.startswith("https://cdn.cloudflare.steamstatic.com/")):
                src = ""
            item["src"] = src
        clean_layers.append(item)
    return {
        "version": 1,
        "mode": raw.get("mode") if raw.get("mode") in _MODES else "workshop",
        "width": max(506, min(1200, int(raw.get("width") or 750))),
        "height": max(280, min(1800, int(raw.get("height") or 1000))),
        "background": str(raw.get("background") or "#07131c")[:32],
        "layers": clean_layers,
    }


@router.get("/projects")
def list_projects(request: Request):
    user, error = _user(request)
    if error:
        return error
    pro = auth_db.effective_pro(user)
    return {"ok": True, "is_pro": pro, "retention_days": None if pro else 7,
            "items": auth_db.builder_projects_for_user(int(user["id"]), is_pro=pro)}


@router.post("/projects")
async def save_project(request: Request):
    user, error = _user(request)
    if error:
        return error
    try:
        body = await request.json()
        project = _validated_project(body.get("project"))
        project_id = re.sub(r"[^a-zA-Z0-9_-]", "", str(body.get("id") or ""))[:64]
        if not project_id:
            project_id = secrets.token_hex(12)
        name = str(body.get("name") or "Untitled showcase").strip()[:80] or "Untitled showcase"
        mode = project["mode"]
        pro = auth_db.effective_pro(user)
        item = auth_db.save_builder_project(
            int(user["id"]), project_id, name, mode, project, is_pro=pro
        )
        return {"ok": True, "item": item, "retention_days": None if pro else 7}
    except PermissionError:
        return JSONResponse({"ok": False, "msg": "Project not found"}, status_code=404)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, request: Request):
    user, error = _user(request)
    if error:
        return error
    ok = auth_db.delete_builder_project(int(user["id"]), project_id)
    return JSONResponse({"ok": ok}, status_code=200 if ok else 404)


@router.post("/reserve-export")
def reserve_export(request: Request):
    user, error = _user(request)
    if error:
        return error
    pro = auth_db.effective_pro(user)
    ok, remaining = auth_db.consume_builder_render(int(user["id"]), is_pro=pro)
    if not ok:
        return JSONResponse(
            {"ok": False, "msg": "Free Builder limit reached: 1 export per day", "remaining": 0},
            status_code=429,
        )
    return {"ok": True, "remaining": remaining, "is_pro": pro}


@router.post("/assets")
async def upload_asset(request: Request, file: UploadFile = File(...)):
    user, error = _user(request)
    if error:
        return error
    suffix = Path(file.filename or "").suffix.lower()
    media_type = _SAFE_MEDIA.get(suffix)
    if not media_type:
        return JSONResponse({"ok": False, "msg": "Unsupported media format"}, status_code=400)
    data = await file.read((MAX_UPLOAD_MB + 1) * 1024 * 1024)
    if not data or len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": f"File limit is {MAX_UPLOAD_MB} MB"}, status_code=413)
    if media_type.startswith("image/"):
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError):
            return JSONResponse({"ok": False, "msg": "Invalid image file"}, status_code=400)
    name = secrets.token_hex(16) + suffix
    rel = f"builder/{int(user['id'])}/{name}"
    if object_store.configured():
        object_store.put_bytes(rel, data, public=False, media_type=media_type)
    else:
        path = _local_asset_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return {"ok": True, "url": f"/api/builder/assets/{name}", "media_type": media_type,
            "name": (file.filename or name)[:160]}


@router.get("/assets/{name}")
def get_asset(name: str, request: Request):
    user, error = _user(request)
    if error:
        return error
    if not re.fullmatch(r"[a-f0-9]{32}\.(?:png|jpe?g|webp|gif|mp4|webm|mov)", name, re.I):
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    rel = f"builder/{int(user['id'])}/{name}"
    media_type = _SAFE_MEDIA.get(Path(name).suffix.lower()) or "application/octet-stream"
    if object_store.configured():
        try:
            return Response(object_store.get_bytes(rel, public=False), media_type=media_type,
                            headers={"Cache-Control": "private, max-age=60"})
        except Exception:
            return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    path = _local_asset_path(rel)
    if not path.is_file():
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    return FileResponse(path, media_type=media_type)


@router.post("/remove-background")
async def remove_background(request: Request):
    user, error = _user(request)
    if error:
        return error
    try:
        body = await request.json()
    except Exception:
        body = {}
    match = re.fullmatch(
        r"/api/builder/assets/([a-f0-9]{32}\.(?:png|jpe?g|webp|gif|mp4|webm|mov))",
        str(body.get("url") or ""), re.I,
    )
    if not match:
        return JSONResponse({"ok": False, "msg": "Upload this layer before AI removal"}, status_code=400)
    name = match.group(1)
    source_key = f"builder/{int(user['id'])}/{name}"
    user_key = f"builder-bg:{int(user['id'])}"
    existing = rs.job_find_active(user_key, "builder_bg_remove", source_key)
    if existing:
        return {"ok": True, "job_id": existing[0], "queued": True}
    jid = secrets.token_hex(12)
    payload = {
        "kind": "builder_bg_remove", "status": "queued", "pct": 1,
        "stage": "queued", "user_id": int(user["id"]), "user_key": user_key,
        "source_key": source_key, "output_stem": secrets.token_hex(16),
    }
    external = ((os.environ.get("WORKER_MODE") or "embedded").strip().lower() == "external"
                and rs.redis_ok() and rs.worker_alive())
    rs.job_create(jid, payload, enqueue=external)
    if not external:
        from smweb.background_remove_jobs import run
        _remove_pool.submit(run, jid, payload)
    return {"ok": True, "job_id": jid, "queued": True}


@router.get("/remove-background/{job_id}")
def remove_background_status(job_id: str, request: Request):
    user, error = _user(request)
    if error:
        return error
    job = rs.job_get(job_id)
    if not job or job.get("kind") != "builder_bg_remove" or int(job.get("user_id") or 0) != int(user["id"]):
        return JSONResponse({"ok": False, "msg": "Job not found"}, status_code=404)
    out = {"ok": True, "status": job.get("status"), "pct": int(job.get("pct") or 0),
           "stage": job.get("stage")}
    if job.get("status") == "done":
        out["result"] = job.get("result") or {}
    elif job.get("status") == "error":
        out["error"] = job.get("error") or "Background removal failed"
    return out
