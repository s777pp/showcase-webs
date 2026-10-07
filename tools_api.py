#!/usr/bin/env python3
"""New tool endpoints mounted onto the app in main.py.

Kept out of main.py (already ~5k lines) but wired the same way. main.py calls
`init(...)` with the helpers it owns (quota, auth, paths) and then
`app.include_router(router)` — no import cycle.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, Response
import steam_catalog
from smweb import admin_content
from smweb.remote_media import fetch_media, validate_media_url

LOGGER = logging.getLogger("sm.tools")

router = APIRouter(prefix="/api")

# ---- injected by main.init ------------------------------------------------
_D: dict[str, Any] = {}


def init(**kw) -> None:
    """Receive helpers owned by main.py (quota_state, auth_user, paths…)."""
    _D.update(kw)
    data_dir = _D.get("DATA")
    if data_dir:
        steam_catalog.configure(Path(data_dir))


def _quota(req: Request) -> dict:
    fn: Callable = _D["quota_state"]
    return fn(req)


def _user(req: Request) -> Optional[dict]:
    fn: Callable = _D["auth_user"]
    return fn(req)


def _max_mb() -> int:
    return int(_D.get("MAX_UPLOAD_MB", 40))


def _err(msg: str, status: int = 400, **extra):
    return JSONResponse({"ok": False, "msg": msg, **extra}, status_code=status)


def _internal_error(request: Request, message: str):
    rid = getattr(request.state, "request_id", "-")
    return _err(message, 500, request_id=rid)


# ==========================================================================
# Watermark policy
# ==========================================================================
# Free accounts always carry the service mark. The client used to be able to
# send wm_enable=0 and strip it, so the decision is made here, server-side, and
# the resulting values overwrite whatever arrived in the form.
SERVICE_WM_TEXT = None  # resolved lazily from env via main


def service_wm_text() -> str:
    import os

    return (os.environ.get("SERVICE_WM_TEXT") or "Showcase Maker").strip() or "Showcase Maker"


def enforce_watermark(is_pro: bool, opts: dict) -> dict:
    """Watermark is fully user-controlled on every plan.

    The free tier used to get a forced service mark here. That was dropped on
    purpose: free is limited by the daily quota alone, so the mark only made
    the output worse without protecting anything. Both plans now get exactly
    the options they asked for -- including no mark at all.
    """
    return dict(opts)


@router.get("/watermark/policy")
def watermark_policy(request: Request):
    """Lets the UI explain the rule instead of guessing it."""
    q = _quota(request)
    return {
        "ok": True,
        "pro": bool(q.get("pro")),
        "forced": False,
        "text": service_wm_text(),
    }


# ==========================================================================
# Steam catalog
# ==========================================================================
@router.get("/steam/backgrounds")
def steam_backgrounds(q: str = "", page: int = 0, kind: str = "all", count: int = 24, asset: str = "background"):
    result = steam_catalog.backgrounds(q=q, page=page, kind=kind, count=count, asset=asset)
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        result = dict(result)
        result["items"] = admin_content.apply_catalog_rules(result["items"])
    return result


@router.get("/steam/cards/{appid}")
def steam_cards(appid: int, foil: bool = False):
    """Full trading-card set of one game plus what the badge costs to craft."""
    return steam_catalog.card_set(appid, foil=foil)


@router.get("/steam/achievements/{appid}")
def steam_achievements(appid: str):
    return steam_catalog.achievements(appid)


@router.get("/steam/apps")
def steam_apps(q: str = "", limit: int = 24):
    return steam_catalog.apps(q, limit=limit)


@router.get("/steam/profile")
def steam_profile(url: str = ""):
    """Anonymous fallback of the profile page (signed-in users import through a job).
    Rate-limited as a GET in middleware and never allowed to spend the paid browser route."""
    return steam_catalog.profile(url, paid=False)


@router.get("/steam/proxy-image")
def steam_proxy_image(url: str):
    """Fetch a Steam-hosted asset so the builder can use it on a canvas.

    Two reasons this exists rather than pointing <img> straight at Steam: the
    export canvas would be tainted by a cross-origin draw, and points-shop
    animated items are video files. Restricted to Steam CDN hosts - this must
    not become a generic fetcher.
    """
    # Valve keeps adding CDN subdomains (avatars.steamstatic.com without the
    # cloudflare/akamai/fastly infix is the current avatar host), so an
    # exhaustive host list silently breaks images over time. Match the whole
    # steamstatic.com zone instead and keep the handful of non-steamstatic
    # hosts explicit. Still a closed allowlist - not a generic fetcher.
    try:
        validate_media_url(url)
    except ValueError:
        return _err("Only Steam CDN images are allowed")
    # Steam files never change under the same URL: keep them on disk so a repeat request
    # (another user, a reload, a video seek) is served locally with byte ranges instead of
    # downloading the whole file from Steam again before the first byte goes out.
    cache_dir = Path(_D["DATA"]) / "cache" / "steam-media"
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:40]
    headers = {"Cache-Control": "public, max-age=604800, immutable"}
    # Only finished files: a parallel request (browsers fetch videos in byte ranges) may be
    # writing "<key>.webm.<rand>.tmp" right now; serving it raced with the rename -> HTTP 500.
    for suffix, media_type in _STEAM_MEDIA_TYPES.items():
        hit = cache_dir / (key + suffix)
        try:
            fresh = time.time() - hit.stat().st_mtime < STEAM_MEDIA_CACHE_SECONDS
        except OSError:
            continue
        if fresh:
            return FileResponse(hit, media_type=media_type, headers=headers)
    try:
        body, ctype = fetch_media(url, max_bytes=25 * 1024 * 1024, user_agent=steam_catalog.UA)
    except Exception as exc:
        LOGGER.warning("Steam media proxy failed (%s)", type(exc).__name__)
        return _err("Steam media is temporarily unavailable", 502)
    suffix = next((ext for ext, kind in _STEAM_MEDIA_TYPES.items() if kind == ctype), "")
    if not suffix:
        return Response(content=body, media_type=ctype, headers=headers)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        target = cache_dir / (key + suffix)
        tmp = target.with_name(target.name + "." + uuid.uuid4().hex[:8] + ".tmp")
        tmp.write_bytes(body)
        tmp.replace(target)
        _prune_steam_media_cache(cache_dir)
        return FileResponse(target, media_type=ctype, headers=headers)
    except OSError:
        return Response(content=body, media_type=ctype, headers=headers)


STEAM_MEDIA_CACHE_SECONDS = 7 * 86400
STEAM_MEDIA_CACHE_FILES = 600
_STEAM_MEDIA_TYPES = {".webm": "video/webm", ".mp4": "video/mp4", ".jpg": "image/jpeg",
                      ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}


def _prune_steam_media_cache(cache_dir: Path) -> None:
    """Keep the newest files only (the cache is a convenience, not storage)."""
    try:
        files = sorted((f for f in cache_dir.iterdir() if f.is_file()), key=lambda f: f.stat().st_mtime)
    except OSError:
        return
    now = time.time()
    extra = len(files) - STEAM_MEDIA_CACHE_FILES
    for index, item in enumerate(files):
        try:
            stale = now - item.stat().st_mtime > STEAM_MEDIA_CACHE_SECONDS or item.suffix == ".tmp" and now - item.stat().st_mtime > 600
            if index < extra or stale:
                item.unlink()
        except OSError:
            pass


# ==========================================================================
# Builder projects (Pro) — stored as JSON under DATA/projects/<user_id>/
# ==========================================================================
def _projects_dir(user_id: int) -> Path:
    root = Path(_D["DATA"]) / "projects" / str(int(user_id))
    root.mkdir(parents=True, exist_ok=True)
    return root


@router.get("/projects")
def projects_list(request: Request):
    user = _user(request)
    if not user:
        return _err("Log in required", 401, code="auth")
    if not _quota(request).get("pro"):
        return {"ok": True, "items": [], "pro": False}

    out = []
    for p in sorted(_projects_dir(user["id"]).glob("*.json"), reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append(
                {
                    "id": p.stem,
                    "name": d.get("name") or p.stem,
                    "project_type": d.get("project_type") or "builder",
                    "updated": d.get("updated"),
                }
            )
        except Exception:
            continue
    return {"ok": True, "items": out, "pro": True}


@router.get("/projects/{pid}")
def project_get(pid: str, request: Request):
    user = _user(request)
    if not user:
        return _err("Log in required", 401, code="auth")
    if not _quota(request).get("pro"):
        return _err("Pro only", 403, code="pro")
    safe = re.sub(r"[^\w-]", "", pid)[:64]
    path = _projects_dir(user["id"]) / f"{safe}.json"
    if not path.is_file():
        return _err("Not found", 404)
    try:
        return {"ok": True, "project": json.loads(path.read_text(encoding="utf-8"))}
    except Exception:
        LOGGER.exception("project read failed user_id=%s pid=%s", user["id"], safe)
        return _internal_error(request, "Project could not be read")


@router.post("/projects")
async def project_save(request: Request):
    user = _user(request)
    if not user:
        return _err("Log in required", 401, code="auth")
    if not _quota(request).get("pro"):
        return _err("Saving projects is a Pro feature", 403, code="pro")

    try:
        body = await request.json()
    except Exception:
        return _err("Expected JSON")

    name = str(body.get("name") or "").strip()[:120] or f"project {time.strftime('%d.%m %H:%M')}"
    scene = body.get("scene")
    if not isinstance(scene, dict):
        return _err("scene must be an object")
    if len(json.dumps(scene)) > 200_000:
        return _err("Scene is too large")

    root = _projects_dir(user["id"])
    if len(list(root.glob("*.json"))) >= 200:
        return _err("Project limit reached (200)")

    pid = re.sub(r"[^\w-]", "", str(body.get("id") or ""))[:64] or uuid.uuid4().hex[:12]
    payload = {
        "id": pid,
        "name": name,
        "project_type": str(body.get("project_type") or "builder")[:32],
        "scene": scene,
        "updated": time.time(),
    }
    (root / f"{pid}.json").write_text(json.dumps(payload), encoding="utf-8")
    return {"ok": True, "id": pid, "name": name}


@router.delete("/projects/{pid}")
def project_delete(pid: str, request: Request):
    user = _user(request)
    if not user:
        return _err("Log in required", 401, code="auth")
    safe = re.sub(r"[^\w-]", "", pid)[:64]
    path = _projects_dir(user["id"]) / f"{safe}.json"
    if path.is_file():
        path.unlink()
    return {"ok": True}
