"""Health, readiness, quota, access codes and site meta.

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
from smweb import object_store


from fastapi import APIRouter


from smweb.core import (
    DATA,
    FONTS,
    PRO_PRICE_LABEL,
    SOCIALS,
    STEAM_CONSOLE_CODE,
    STRIPE_PRICE_ID,
    STRIPE_SECRET,
    TEMPLATES,
    TRUSTED_PROXY_HOPS,
    _admin_ok,
    _auth_user,
    _ip,
    _load_codes,
    _load_used,
    _save_used,
    quota_state,
)
from smweb.jobs import MAX_JOB_WORKERS, _worker_mode



router = APIRouter()


@router.get("/api/ready")
def api_ready():
    """Readiness: DB must answer."""
    try:
        c = auth_db._conn()
        c.execute("SELECT 1")
        c.close()
        return {"ok": True}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse({"ok": False}, status_code=503)


@router.get("/api/health")
def api_health_prod():
    db_ok = True
    try:
        c = auth_db._conn()
        c.execute("SELECT 1")
        c.close()
    except Exception:
        db_ok = False
    try:
        redis_ok = rs.redis_ok()
    except Exception:
        redis_ok = False
    r2_ok, r2_error = object_store.health()
    mode = _worker_mode()
    # writability, not just readability: a readonly volume still answers SELECT 1,
    # which is why the old db:true hid the "readonly database" failure entirely.
    db_writable = False
    db_write_error = None
    try:
        c = auth_db._conn()
        c.execute("CREATE TABLE IF NOT EXISTS _health_probe (id INTEGER PRIMARY KEY)")
        c.commit()
        c.close()
        db_writable = True
    except Exception as e:
        db_write_error = f"{type(e).__name__}: {e}"
    ff = None
    gs = None
    try:
        ff = proc.find_ffmpeg()
    except Exception:
        ff = None
    try:
        gs = proc.find_gifski() if hasattr(proc, "find_gifski") else None
    except Exception:
        gs = None
    return {
        "ok": True,
        "db": db_ok,
        "storage": {
            "dir": str(DATA),
            "writable": auth_db.DATA_WRITABLE,
            "error": auth_db.DATA_ERROR,
            "db_path": str(auth_db.DB),
            "db_writable": db_writable,
            "db_write_error": db_write_error,
            "database_backend": "postgresql" if auth_db.USING_POSTGRES else "sqlite",
        },
        "r2": {"configured": object_store.configured(), "ok": r2_ok, "error": r2_error},
        "redis": redis_ok,
        # why Redis is down — the old endpoint only ever said "false"
        "redis_detail": {
            "configured": rs.configured(),
            "ok": redis_ok,
            "host": rs.redis_host(),
            "error": rs.last_error(),
        },
        "worker": {
            "mode": mode,
            "external_alive": rs.worker_alive() if redis_ok else False,
            "max_concurrent": MAX_JOB_WORKERS,
            "queue": rs.queue_depth() if redis_ok else 0,
        },
        "ffmpeg": bool(ff),
        "gifski": bool(gs),
        "ffmpeg_path": ff or None,
        "gifski_path": gs or None,
        "version": "prod-opt-2",
    }


@router.get("/api/health_legacy")

def health():
    ff = proc.find_ffmpeg()
    gs = proc.find_gifski() if hasattr(proc, "find_gifski") else None
    return {
        "ok": True,
        "ffmpeg": bool(ff),
        "gifski": bool(gs),
        "ffmpeg_path": ff or None,
        "gifski_path": gs or None,
        "fonts": [f.name for f in FONTS.glob("*.ttf")] if FONTS.is_dir() else [],
        "templates": [f.name for f in TEMPLATES.glob("*.png")] if TEMPLATES.is_dir() else [],
    }


@router.get("/api/admin/whoami")
def api_admin_whoami(request: Request):
    """Show how the proxy chain resolves to a client IP.

    TRUSTED_PROXY_HOPS has to match the real number of proxies that append to
    X-Forwarded-For. Too low and every visitor shares one quota bucket (the
    tunnel container's address); too high and a client can forge its own.
    The value is topology-dependent, so it needs checking against the live
    chain rather than being assumed.
    """
    if not _admin_ok(request):
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    xff = request.headers.get("x-forwarded-for") or ""
    parts = [x.strip() for x in xff.split(",") if x.strip()]
    return {
        "ok": True,
        "resolved_ip": _ip(request),
        "trusted_proxy_hops": TRUSTED_PROXY_HOPS,
        "x_forwarded_for": parts,
        "xff_entries": len(parts),
        "cf_connecting_ip": request.headers.get("cf-connecting-ip") or "",
        "socket_peer": (request.client.host if request.client else ""),
        "hint": (
            "resolved_ip must equal cf_connecting_ip. If it does not, set "
            "TRUSTED_PROXY_HOPS = xff_entries - index_of_real_client_from_right."
        ),
    }


@router.get("/api/quota")
def api_quota(request: Request):
    return quota_state(request)


@router.post("/api/unlock")
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

    meta = codes[code] if isinstance(codes.get(code), dict) else {"type": "unlimited", "label": "Pro"}
    ctype = str(meta.get("type") or "unlimited")
    hours = float(meta.get("hours") or 0)
    label = str(meta.get("label") or "Pro")
    until = None
    if ctype == "trial" and hours > 0:
        until = time.time() + hours * 3600
    auth_db.set_pro(int(user["id"]), True, code=code, until=until)
    auth_db.mark_code_used(code, int(user["id"]))
    if code.startswith("SM-WEB-") or code.startswith("SM-TRIAL-"):
        used.add(code)
        _save_used(used)
    msg = "Pro activated on your account"
    if until:
        msg = f"Trial activated for {int(hours)} hours"
    return {"ok": True, "label": label, "msg": msg, "until": until}


@router.get("/api/meta")
def meta():
    return {
        "socials": SOCIALS,
        "buy_url": "https://funpay.com/lots/offer?id=75434891",
        "stripe_enabled": bool(STRIPE_SECRET and STRIPE_PRICE_ID),
        "pro_label": PRO_PRICE_LABEL,
        "modes": [
            {"id": "workshop", "title": "Workshop", "desc": "5 частей для витрины мастерской"},
            {"id": "featured", "title": "Featured", "desc": "630 px Featured Artwork"},
            {"id": "split", "title": "Artwork Split", "desc": "Центр 506 + бок 100"},
        ],
        "fonts": ["rob", "lap", "caratte", "Fineday", "roboto", "gothic-rus"],
        "steam_code": STEAM_CONSOLE_CODE,
    }
