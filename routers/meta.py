"""Health, quota, meta, admin wipe."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import auth_db
import processor as proc
from config import ADMIN_SECRET, FONTS, TEMPLATES, SOCIALS, PRO_PRICE_LABEL, STRIPE_SECRET, STRIPE_PRICE_ID, STEAM_CONSOLE_CODE
from utils import quota_state, auth_user

router = APIRouter(tags=["meta"])


@router.get("/api/health")
def health():
    return {
        "ok": True,
        "ffmpeg": bool(proc.find_ffmpeg()),
        "fonts": [f.name for f in FONTS.glob("*.ttf")] if FONTS.is_dir() else [],
        "templates": [f.name for f in TEMPLATES.glob("*.png")] if TEMPLATES.is_dir() else [],
    }


@router.get("/api/quota")
def api_quota(request: Request):
    return quota_state(request)


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


@router.post("/api/admin/wipe-users")
async def admin_wipe_users(request: Request):
    secret = ADMIN_SECRET
    got = (request.headers.get("x-admin-secret") or "").strip()
    if not secret or got != secret:
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    n = auth_db.wipe_all_users()
    return JSONResponse({"ok": True, "deleted": n})
