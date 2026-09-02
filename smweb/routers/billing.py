"""Stripe checkout and webhook.

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


from fastapi import APIRouter


from smweb.core import LOGGER, STRIPE_SECRET, STRIPE_WEBHOOK_SECRET



router = APIRouter()


@router.post("/api/billing/checkout")
async def billing_checkout(request: Request):
    """Покупка Pro — редирект на FunPay (ключ активируется на сайте)."""
    # не требуем логин: можно купить и потом ввести код
    return {
        "ok": True,
        "url": "https://funpay.com/lots/offer?id=76420307",
        "msg": "FunPay",
    }


@router.post("/api/billing/webhook")
async def billing_webhook(request: Request):
    """Stripe webhook: checkout.session.completed → is_pro=1."""
    if not STRIPE_SECRET:
        return JSONResponse({"ok": False}, status_code=503)
    # No signing secret means no way to tell Stripe from anyone else. The old
    # fallback parsed the body unverified, so a hand-written POST claiming
    # checkout.session.completed granted Pro to any user_id. Fail closed.
    if not STRIPE_WEBHOOK_SECRET:
        LOGGER.error("billing webhook: STRIPE_WEBHOOK_SECRET unset, refusing unverified event")
        return JSONResponse(
            {"ok": False, "msg": "Webhook not configured"}, status_code=503
        )
    import stripe
    stripe.api_key = STRIPE_SECRET
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        LOGGER.warning("billing webhook rejected: %s", e)
        return JSONResponse({"ok": False, "msg": "Invalid signature"}, status_code=400)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        uid = (session.get("metadata") or {}).get("user_id")
        if uid:
            try:
                auth_db.set_pro(int(uid), True)
            except Exception:
                pass
    return {"ok": True}
