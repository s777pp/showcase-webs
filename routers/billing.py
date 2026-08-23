"""Billing, unlock codes, Stripe webhook, FunPay."""
from __future__ import annotations

import json
import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import auth_db
from config import STRIPE_SECRET, STRIPE_WEBHOOK_SECRET, DATA
from logging_config import log
from utils import auth_user, load_codes

router = APIRouter(tags=["billing"])

USED_CODES_FILE = DATA / "used_codes.json"


def _load_used() -> set:
    if USED_CODES_FILE.is_file():
        try:
            return set(json.loads(USED_CODES_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def _save_used(used: set) -> None:
    try:
        USED_CODES_FILE.write_text(json.dumps(sorted(used), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


@router.post("/api/billing/checkout")
async def billing_checkout(request: Request):
    return {
        "ok": True,
        "url": "https://funpay.com/lots/offer?id=75434891",
        "msg": "FunPay",
    }


@router.post("/api/billing/webhook")
async def billing_webhook(request: Request):
    if not STRIPE_SECRET:
        return JSONResponse({"ok": False}, status_code=503)
    import stripe
    stripe.api_key = STRIPE_SECRET
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        else:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=400)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        uid = (session.get("metadata") or {}).get("user_id")
        if uid:
            try:
                auth_db.set_pro(int(uid), True)
            except Exception:
                pass
    return {"ok": True}


@router.post("/api/unlock")
async def unlock(request: Request):
    body = await request.json()
    code = str(body.get("code") or "").strip().upper().replace(" ", "")
    user = auth_user(request)
    if not user or not user.get("id"):
        return JSONResponse(
            {"ok": False, "msg": "Log in first, then activate the code on your account"},
            status_code=401,
        )
    codes = load_codes()
    if code not in codes:
        return JSONResponse({"ok": False, "msg": "Invalid access code"}, status_code=400)
    if user.get("is_pro"):
        return {"ok": True, "label": "Pro", "msg": "Already Pro on this account"}
    used_uid = auth_db.code_used(code)
    if used_uid is not None:
        return JSONResponse({"ok": False, "msg": "Code already used"}, status_code=400)
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
    log.info("unlock code=%s user=%s", code, user.get("email"))
    return {"ok": True, "label": label, "msg": msg, "until": until}
