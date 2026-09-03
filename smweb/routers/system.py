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

LOGGER = logging.getLogger("sm")


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



# === GUMROAD LICENSE ACTIVATION ===

_GUMROAD_PRODUCT_ID = 'G80YAnc7y8X8DR3dwbjVMw=='


def _gumroad_verify_license_sync(license_key: str) -> dict:
    """Verify a Gumroad license directly against Gumroad's API."""
    import json as _json
    import urllib.error as _urlerror
    import urllib.parse as _urlparse
    import urllib.request as _urlrequest

    payload = _urlparse.urlencode({
        "product_id": _GUMROAD_PRODUCT_ID,
        "license_key": license_key,
        "increment_uses_count": "false",
    }).encode("utf-8")

    req = _urlrequest.Request(
        "https://api.gumroad.com/v2/licenses/verify",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ShowcaseMaker/1.0",
        },
    )

    try:
        with _urlrequest.urlopen(req, timeout=12) as response:
            raw = response.read().decode("utf-8", "replace")
    except _urlerror.HTTPError as exc:
        if exc.code == 404:
            return {"ok": False, "invalid": True}
        LOGGER.warning("Gumroad license API HTTP error: %s", exc.code)
        return {"ok": False, "unavailable": True}
    except Exception as exc:
        LOGGER.warning(
            "Gumroad license API unavailable: %s",
            type(exc).__name__,
        )
        return {"ok": False, "unavailable": True}

    try:
        data = _json.loads(raw)
    except Exception:
        LOGGER.warning("Gumroad license API returned invalid JSON")
        return {"ok": False, "unavailable": True}

    purchase = data.get("purchase") or {}

    if not data.get("success"):
        return {"ok": False, "invalid": True}

    if str(purchase.get("product_id") or "") != _GUMROAD_PRODUCT_ID:
        LOGGER.warning("Gumroad license rejected: wrong product_id")
        return {"ok": False, "invalid": True}

    if purchase.get("refunded"):
        return {"ok": False, "revoked": True, "reason": "Purchase was refunded"}

    if purchase.get("chargebacked"):
        return {"ok": False, "revoked": True, "reason": "Purchase was charged back"}

    if purchase.get("disputed") and not purchase.get("dispute_won"):
        return {"ok": False, "revoked": True, "reason": "Purchase is disputed"}

    if (
        purchase.get("subscription_ended_at")
        or purchase.get("subscription_cancelled_at")
        or purchase.get("subscription_failed_at")
    ):
        return {"ok": False, "revoked": True, "reason": "Subscription is inactive"}

    sale_id = str(
        purchase.get("sale_id")
        or purchase.get("id")
        or ""
    ).strip()

    if not sale_id:
        LOGGER.warning("Gumroad license response missing sale_id")
        return {"ok": False, "invalid": True}

    return {
        "ok": True,
        "sale_id": sale_id,
        "purchase": purchase,
    }


async def _gumroad_verify_license(license_key: str) -> dict:
    import asyncio
    return await asyncio.to_thread(
        _gumroad_verify_license_sync,
        license_key,
    )


def _gumroad_sale_marker(sale_id: str) -> str:
    """
    Store only a hash of the Gumroad sale ID in our activation table.
    We deliberately do not store the customer's license key.
    """
    import hashlib as _hashlib

    digest = _hashlib.sha256(
        sale_id.encode("utf-8")
    ).hexdigest().upper()

    return "GR-" + digest[:48]



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

    # A code that is not one of our legacy/local ShowcaseMaker codes may be
    # a Gumroad license. Verification happens server-to-server; the browser
    # is never trusted to tell us whether a purchase is valid.
    if code not in codes:
        gumroad = await _gumroad_verify_license(code)

        if gumroad.get("unavailable"):
            return JSONResponse(
                {
                    "ok": False,
                    "msg": "Gumroad verification is temporarily unavailable. Please try again.",
                },
                status_code=503,
            )

        if gumroad.get("revoked"):
            return JSONResponse(
                {
                    "ok": False,
                    "msg": gumroad.get("reason") or "This Gumroad purchase is no longer active",
                },
                status_code=400,
            )

        if not gumroad.get("ok"):
            return JSONResponse(
                {
                    "ok": False,
                    "msg": "Invalid access code or Gumroad license key",
                },
                status_code=400,
            )

        uid = int(user["id"])
        sale_id = gumroad["sale_id"]
        marker = _gumroad_sale_marker(sale_id)

        # Bind one Gumroad sale permanently to one ShowcaseMaker account.
        claimed_uid = auth_db.code_used(marker)

        if claimed_uid is not None:
            try:
                claimed_uid = int(claimed_uid)
            except (TypeError, ValueError):
                LOGGER.error("Invalid Gumroad activation owner for %s", marker)
                return JSONResponse(
                    {"ok": False, "msg": "Activation database error"},
                    status_code=500,
                )

            if claimed_uid != uid:
                return JSONResponse(
                    {
                        "ok": False,
                        "msg": "This Gumroad license is already activated on another ShowcaseMaker account",
                    },
                    status_code=400,
                )
        else:
            auth_db.mark_code_used(marker, uid)

            # Read it back before granting Pro.
            confirmed_uid = auth_db.code_used(marker)
            if confirmed_uid is not None:
                try:
                    confirmed_uid = int(confirmed_uid)
                except (TypeError, ValueError):
                    confirmed_uid = None

                if confirmed_uid != uid:
                    return JSONResponse(
                        {
                            "ok": False,
                            "msg": "This Gumroad license is already activated on another ShowcaseMaker account",
                        },
                        status_code=400,
                    )

        # Never store the actual Gumroad license key on the user account.
        # Store our irreversible sale marker instead.
        auth_db.set_pro(
            uid,
            True,
            code=marker,
            until=None,
        )

        LOGGER.info(
            "Gumroad Pro activated for user_id=%s sale=%s",
            uid,
            marker,
        )

        return {
            "ok": True,
            "label": "Pro",
            "msg": "ShowcaseMaker Pro activated successfully",
            "until": None,
        }
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
        "buy_url": "https://funpay.com/lots/offer?id=76420307",
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
