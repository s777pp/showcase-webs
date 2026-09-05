"""Discord, Google, Telegram and Steam sign-in.

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


from smweb.core import DATA, LOGGER, _attach_session_cookie, _esc_html
from smweb.oauth_util import (
    _discord_redirect_uri,
    _google_redirect_uri,
    _app_origin,
    _oauth_state_create,
    _oauth_state_verify,
    _telegram_bot_token,
    _telegram_bot_username,
    _verify_telegram_login,
)
from smweb.steam import _merge_steam_api, _steam_realm



router = APIRouter()


@router.get("/api/auth/discord/login")
def discord_login_start(request: Request):
    cid = (os.environ.get("DISCORD_CLIENT_ID") or "").strip()
    secret = (os.environ.get("DISCORD_CLIENT_SECRET") or "").strip()
    redirect = _discord_redirect_uri()
    if not cid or not secret:
        return JSONResponse(
            {"ok": False, "msg": "DISCORD_CLIENT_ID / DISCORD_CLIENT_SECRET not set on server"},
            status_code=503,
        )
    from urllib.parse import urlencode
    try:
        state = _oauth_state_create("discord")
    except RuntimeError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=503)
    q = urlencode({
        "client_id": cid,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "identify email",
        "state": state,
        "prompt": "consent",
    })
    return {"ok": True, "url": f"https://discord.com/api/oauth2/authorize?{q}"}


@router.get("/api/auth/discord/callback")
async def discord_callback(request: Request, code: str = "", state: str = ""):
    if not _oauth_state_verify(state, "discord"):
        return HTMLResponse("<h3>Discord auth failed (bad state)</h3>", status_code=400)
    cid = (os.environ.get("DISCORD_CLIENT_ID") or "").strip()
    secret = (os.environ.get("DISCORD_CLIENT_SECRET") or "").strip()
    redirect = _discord_redirect_uri()
    try:
        import requests as rq
        tok = rq.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": cid,
                "client_secret": secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if tok.status_code != 200:
            LOGGER.warning("discord token exchange failed status=%s", tok.status_code)
            return HTMLResponse("<h3>Discord sign-in failed</h3>", status_code=400)
        access = tok.json().get("access_token")
        me = rq.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access}"},
            timeout=20,
        )
        if me.status_code != 200:
            LOGGER.warning("discord user lookup failed status=%s", me.status_code)
            return HTMLResponse("<h3>Discord sign-in failed</h3>", status_code=400)
        u = me.json()
        did = str(u.get("id") or "")
        uname = u.get("global_name") or u.get("username") or "discord"
        email = u.get("email")
        ok, msg, token = auth_db.register_or_login_discord(did, uname, email)
        if not ok or not token:
            return HTMLResponse(f"<h3>{_esc_html(msg)}</h3>", status_code=400)
        app_url = _app_origin()
        target_origin = json.dumps(app_url)
        resp = HTMLResponse(
            f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>OK</title></head>
<body style="font-family:system-ui;background:#0b0b12;color:#eee;display:grid;place-items:center;min-height:100vh;margin:0">
<div style="text-align:center"><h1>Discord connected</h1>
<p>You can close this window.</p>
<a href="{_esc_html(app_url)}/app" style="color:#7b5cff">Back to app</a></div>
<script>
try {{ if (window.opener) window.opener.postMessage({{type:'discord_login'}}, {target_origin}); }} catch(e) {{}}
setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1200);
</script></body></html>"""
        )
        return _attach_session_cookie(resp, token, request)
    except Exception:
        LOGGER.exception("oauth callback failed")
        return HTMLResponse("<h3>Error</h3><p>Sign-in failed. Please try again.</p>", status_code=500)


@router.get("/api/auth/google/login")
def google_login_start(request: Request):
    cid = (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()
    secret = (os.environ.get("GOOGLE_CLIENT_SECRET") or "").strip()
    redirect = _google_redirect_uri()
    if not cid or not secret:
        return JSONResponse(
            {"ok": False, "msg": "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set on server"},
            status_code=503,
        )
    from urllib.parse import urlencode
    try:
        state = _oauth_state_create("google")
    except RuntimeError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=503)
    q = urlencode({
        "client_id": cid,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    })
    return {"ok": True, "url": f"https://accounts.google.com/o/oauth2/v2/auth?{q}"}


@router.get("/api/auth/google/callback")
async def google_callback(request: Request, code: str = "", state: str = ""):
    if not _oauth_state_verify(state, "google"):
        return HTMLResponse("<h3>Google auth failed (bad state)</h3>", status_code=400)
    cid = (os.environ.get("GOOGLE_CLIENT_ID") or "").strip()
    secret = (os.environ.get("GOOGLE_CLIENT_SECRET") or "").strip()
    redirect = _google_redirect_uri()
    try:
        import requests as rq
        tok = rq.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": cid,
                "client_secret": secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        if tok.status_code != 200:
            LOGGER.warning("google token exchange failed status=%s", tok.status_code)
            return HTMLResponse("<h3>Google sign-in failed</h3>", status_code=400)
        access = tok.json().get("access_token")
        me = rq.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access}"},
            timeout=20,
        )
        if me.status_code != 200:
            LOGGER.warning("google user lookup failed status=%s", me.status_code)
            return HTMLResponse("<h3>Google sign-in failed</h3>", status_code=400)
        u = me.json()
        gid = str(u.get("sub") or "")
        uname = u.get("name") or (u.get("email") or "google").split("@")[0]
        email = u.get("email")
        ok, msg, token = auth_db.register_or_login_google(gid, email, uname)
        if not ok or not token:
            return HTMLResponse(f"<h3>{_esc_html(msg)}</h3>", status_code=400)
        app_url = _app_origin()
        target_origin = json.dumps(app_url)
        resp = HTMLResponse(
            f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>OK</title></head>
<body style="font-family:system-ui;background:#0b0b12;color:#eee;display:grid;place-items:center;min-height:100vh;margin:0">
<div style="text-align:center"><h1>Google connected</h1>
<p>You can close this window.</p>
<a href="{_esc_html(app_url)}/app" style="color:#7b5cff">Back to app</a></div>
<script>
try {{ if (window.opener) window.opener.postMessage({{type:'google_login'}}, {target_origin}); }} catch(e) {{}}
setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1200);
</script></body></html>"""
        )
        return _attach_session_cookie(resp, token, request)
    except Exception:
        LOGGER.exception("oauth callback failed")
        return HTMLResponse("<h3>Error</h3><p>Sign-in failed. Please try again.</p>", status_code=500)


@router.get("/api/auth/telegram/config")
def telegram_config():
    uname = _telegram_bot_username()
    ready = bool(_telegram_bot_token() and uname)
    return {
        "ok": ready,
        "bot_username": uname if ready else "",
        "msg": None if ready else "TELEGRAM_BOT_TOKEN / TELEGRAM_BOT_USERNAME not set",
    }


@router.post("/api/auth/telegram")
async def telegram_auth(request: Request):
    """Receive Login Widget payload, verify hash, create session."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        return JSONResponse({"ok": False, "msg": "Bad payload"}, status_code=400)
    if not _telegram_bot_token():
        return JSONResponse({"ok": False, "msg": "Telegram auth not configured"}, status_code=503)
    if not _verify_telegram_login(body):
        return JSONResponse({"ok": False, "msg": "Invalid Telegram signature"}, status_code=401)
    tid = str(body.get("id") or "")
    if not tid:
        return JSONResponse({"ok": False, "msg": "Missing Telegram id"}, status_code=400)
    ok, msg, token = auth_db.register_or_login_telegram(
        telegram_id=tid,
        username=body.get("username"),
        first_name=body.get("first_name"),
        last_name=body.get("last_name"),
        photo_url=body.get("photo_url"),
    )
    if not ok or not token:
        return JSONResponse({"ok": False, "msg": msg or "Auth failed"}, status_code=400)
    resp = JSONResponse({"ok": True, "session": True, "msg": "OK"})
    return _attach_session_cookie(resp, token, request)


@router.get("/api/auth/telegram/callback")
async def telegram_callback(request: Request):
    """Fallback: widget redirect with query params."""
    data = dict(request.query_params)
    if not _verify_telegram_login(data):
        return HTMLResponse("<h3>Telegram auth failed</h3>", status_code=400)
    tid = str(data.get("id") or "")
    ok, msg, token = auth_db.register_or_login_telegram(
        telegram_id=tid,
        username=data.get("username"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        photo_url=data.get("photo_url"),
    )
    if not ok or not token:
        return HTMLResponse(f"<h3>{_esc_html(msg)}</h3>", status_code=400)
    app_url = _app_origin()
    target_origin = json.dumps(app_url)
    resp = HTMLResponse(
        f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>OK</title></head>
<body style="font-family:system-ui;background:#0b0b12;color:#eee;display:grid;place-items:center;min-height:100vh;margin:0">
<div style="text-align:center"><h1>Telegram connected</h1>
<p>You can close this window.</p>
<a href="{_esc_html(app_url)}/app" style="color:#7b5cff">Back to app</a></div>
<script>
try {{ if (window.opener) window.opener.postMessage({{type:'telegram_login'}}, {target_origin}); }} catch(e) {{}}
setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1200);
</script></body></html>"""
    )
    return _attach_session_cookie(resp, token, request)


@router.get("/api/auth/steam/login")
def steam_login_start(request: Request):
    """Start Steam OpenID 2.0 sign-in (no API key required for OpenID)."""
    from urllib.parse import urlencode
    realm = _steam_realm()
    return_to = realm + "/api/auth/steam/callback"
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return {"ok": True, "url": "https://steamcommunity.com/openid/login?" + urlencode(params)}


@router.get("/api/auth/steam/callback")
async def steam_callback(request: Request):
    """Verify Steam OpenID assertion, create session, pull public profile snapshot."""
    import requests as _req
    q = dict(request.query_params)
    # local verify with Steam
    payload = {k: v for k, v in q.items()}
    payload["openid.mode"] = "check_authentication"
    try:
        vr = _req.post(
            "https://steamcommunity.com/openid/login",
            data=payload,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 ShowcaseMaker"},
        )
        if "is_valid:true" not in (vr.text or "").lower():
            return HTMLResponse("<h3>Steam login failed (invalid assertion)</h3>", status_code=400)
        claimed = q.get("openid.claimed_id") or q.get("openid.identity") or ""
        m = re.search(r"/openid/id/(\d{17})", claimed)
        if not m:
            return HTMLResponse("<h3>Steam login failed (no steamid)</h3>", status_code=400)
        steam_id = m.group(1)
        # persona name via public XML
        persona = f"steam_{steam_id[-6:]}"
        profile_data = None
        try:
            import steam_catalog
            pr = steam_catalog.profile(f"https://steamcommunity.com/profiles/{steam_id}")
            if pr.get("ok") and pr.get("profile"):
                profile_data = _merge_steam_api(pr["profile"])
                persona = profile_data.get("name") or persona
        except Exception:
            LOGGER.exception("steam profile snapshot failed")
        ok, msg, token = auth_db.register_or_login_steam(steam_id, persona)
        if not ok or not token:
            return HTMLResponse(f"<h3>Login error: {html.escape(msg)}</h3>", status_code=400)
        user = auth_db.user_by_token(token)
        if user and profile_data:
            try:
                auth_db.save_steam_profile_snapshot(int(user["id"]), profile_data)
                auth_db.ensure_profile_username(int(user["id"]), persona)
                # download avatar into local avatars store
                av = (profile_data.get("avatar") or "").strip()
                if av:
                    try:
                        import requests as _rq
                        ar = _rq.get(av, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
                        if ar.status_code == 200 and ar.content[:3] != b"<!":
                            ext = ".jpg"
                            ctype = (ar.headers.get("Content-Type") or "").lower()
                            if "png" in ctype: ext = ".png"
                            elif "webp" in ctype: ext = ".webp"
                            rel = f"avatars/{int(user['id'])}{ext}"
                            if object_store.configured():
                                object_store.put_bytes(rel, ar.content, media_type=ctype.split(";", 1)[0] or object_store.content_type(rel))
                            else:
                                (DATA / rel).parent.mkdir(parents=True, exist_ok=True)
                                (DATA / rel).write_bytes(ar.content)
                            auth_db.update_profile(int(user["id"]), display_name=persona, avatar_path=rel)
                    except Exception:
                        LOGGER.exception("steam avatar download")
            except Exception:
                LOGGER.exception("save steam snapshot")
        app_origin = _app_origin()
        target_origin = json.dumps(app_origin)
        resp = HTMLResponse(
            f"""<!doctype html><html><body style="background:#0b0f14;color:#fff;font-family:sans-serif;display:grid;place-items:center;height:100vh">
<p>Steam OK — можно закрыть окно</p>
<script>
try {{ if (window.opener) window.opener.postMessage({{type:'steam_login'}}, {target_origin}); }} catch(e) {{}}
setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} location.href='/profile'; }}, 600);
</script></body></html>"""
        )
        return _attach_session_cookie(resp, token, request)
    except Exception:
        LOGGER.exception("steam callback")
        return HTMLResponse("<h3>Steam sign-in failed</h3>", status_code=500)
