"""Redirect URIs and Telegram signature verification.

Moved out of main.py unchanged; see docs/STRUCTURE.md.
"""


from __future__ import annotations

import hashlib
import hmac
import base64
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


# ====================== Discord OAuth login ======================

def _discord_redirect_uri() -> str:
    """Build redirect URI; collapse accidental double slashes in path."""
    redirect = (os.environ.get("DISCORD_REDIRECT_URI") or "").strip()
    if not redirect:
        base = (os.environ.get("APP_URL") or "").strip().rstrip("/")
        redirect = base + "/api/auth/discord/callback"
    if "://" in redirect:
        scheme, rest = redirect.split("://", 1)
        while "//" in rest:
            rest = rest.replace("//", "/")
        redirect = scheme + "://" + rest
    return redirect


# ====================== Google OAuth login ======================

def _google_redirect_uri() -> str:
    redirect = (os.environ.get("GOOGLE_REDIRECT_URI") or "").strip()
    if not redirect:
        base = (os.environ.get("APP_URL") or "").strip().rstrip("/")
        redirect = base + "/api/auth/google/callback"
    if "://" in redirect:
        scheme, rest = redirect.split("://", 1)
        while "//" in rest:
            rest = rest.replace("//", "/")
        redirect = scheme + "://" + rest
    return redirect


# ====================== Telegram Login Widget ======================

def _telegram_bot_token() -> str:
    return (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()


def _telegram_bot_username() -> str:
    return (os.environ.get("TELEGRAM_BOT_USERNAME") or "SteamMakerBot").strip().lstrip("@")


def _verify_telegram_login(data: dict) -> bool:
    """Official HMAC-SHA256 check: https://core.telegram.org/widgets/login"""
    token = _telegram_bot_token()
    if not token or "hash" not in data:
        return False
    received = str(data.get("hash") or "")
    check = {k: str(v) for k, v in data.items() if k != "hash" and v is not None and str(v) != ""}
    data_check_string = "\n".join(f"{k}={check[k]}" for k in sorted(check.keys()))
    secret_key = hashlib.sha256(token.encode("utf-8")).digest()
    calculated = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(calculated, received):
        return False
    try:
        auth_date = int(check.get("auth_date") or 0)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - auth_date) > 86400:
        return False
    return True
# OAuth state must survive routing to another Uvicorn process. A short-lived,
# HMAC-signed value avoids per-process dictionaries and rejects forged state.
def _oauth_state_create(provider: str) -> str:
    secret = (os.environ.get("SECRET_KEY") or "").strip()
    if len(secret) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 characters")
    payload = f"{provider}:{int(time.time())}:{secrets.token_urlsafe(24)}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    raw = payload.encode() + b"." + sig.hex().encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _oauth_state_verify(state: str, provider: str, max_age: int = 600) -> bool:
    secret = (os.environ.get("SECRET_KEY") or "").strip()
    try:
        raw = base64.urlsafe_b64decode(state + "=" * (-len(state) % 4))
        payload, supplied_hex = raw.rsplit(b".", 1)
        supplied = bytes.fromhex(supplied_hex.decode())
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        if len(secret) < 32 or not secrets.compare_digest(supplied, expected):
            return False
        p, ts, _nonce = payload.decode().split(":", 2)
        age = int(time.time()) - int(ts)
        return p == provider and 0 <= age <= max_age
    except Exception:
        return False


def _app_origin() -> str:
    value = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise RuntimeError("APP_URL must be an absolute http(s) URL")
    return f"{parsed.scheme}://{parsed.netloc}"


def _oauth_payload_create(values: dict) -> str:
    """Encrypt short-lived provider state that must cross API processes."""
    from cryptography.fernet import Fernet
    secret = (os.environ.get("SECRET_KEY") or "").strip()
    if len(secret) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 characters")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    payload = dict(values)
    payload["ts"] = int(time.time())
    return Fernet(key).encrypt(json.dumps(payload, separators=(",", ":")).encode()).decode()


def _oauth_payload_verify(value: str, max_age: int = 600) -> dict | None:
    from cryptography.fernet import Fernet, InvalidToken
    secret = (os.environ.get("SECRET_KEY") or "").strip()
    if len(secret) < 32:
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    try:
        payload = json.loads(Fernet(key).decrypt(value.encode(), ttl=max_age).decode())
        age = int(time.time()) - int(payload.get("ts") or 0)
        return payload if 0 <= age <= max_age else None
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return None
