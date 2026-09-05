"""DeviantArt OAuth and upload.

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


from smweb.core import LOGGER, _auth_user, _esc_html
from smweb.da_client import _da_guess_mime, _da_refresh_token
from smweb.oauth_util import _app_origin, _oauth_payload_create, _oauth_payload_verify



router = APIRouter()


def _da_api_get(user: dict, path: str, params: Optional[dict] = None):
    """Call DeviantArt as the connected user and refresh an expired token once."""
    import requests as rq

    token = str(user.get("da_access_token") or "").strip().strip('"').strip("'")
    if not token:
        return None, JSONResponse({"ok": False, "msg": "Connect DeviantArt first"}, status_code=401)

    url = "https://www.deviantart.com/api/v1/oauth2/" + path.lstrip("/")

    def request_with(access: str):
        query = dict(params or {})
        query["access_token"] = access
        return rq.get(url, params=query, headers={"Authorization": f"Bearer {access}"}, timeout=30)

    response = request_with(token)
    if response.status_code in (401, 403):
        refreshed = _da_refresh_token(user)
        if refreshed:
            response = request_with(refreshed)
        else:
            auth_db.set_da_tokens(int(user["id"]), None, None)
    return response, None


@router.get("/api/da/works")
def da_works(request: Request, offset: int = 0, limit: int = 24):
    """List the connected DeviantArt account's own gallery."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    limit = max(1, min(int(limit or 24), 48))
    offset = max(0, int(offset or 0))

    who, error = _da_api_get(user, "user/whoami")
    if error:
        return error
    if who.status_code != 200:
        return JSONResponse({"ok": False, "msg": f"DeviantArt user error ({who.status_code})"}, status_code=502)
    username = str((who.json() or {}).get("username") or "").strip()
    if not username:
        return JSONResponse({"ok": False, "msg": "DeviantArt username is unavailable"}, status_code=502)

    gallery, error = _da_api_get(
        user,
        "gallery/all",
        {"username": username, "offset": offset, "limit": limit, "mature_content": "true"},
    )
    if error:
        return error
    if gallery.status_code != 200:
        return JSONResponse({"ok": False, "msg": f"DeviantArt gallery error ({gallery.status_code})"}, status_code=502)

    payload = gallery.json() or {}
    works = []
    for item in payload.get("results") or []:
        content = item.get("content") or {}
        thumbs = item.get("thumbs") or []
        preview = content.get("src") or (thumbs[-1].get("src") if thumbs else "")
        if not preview:
            continue
        works.append(
            {
                "id": str(item.get("deviationid") or ""),
                "title": str(item.get("title") or "Untitled")[:200],
                "preview": preview,
                "url": item.get("url") or "",
                "filename": Path(urlparse(preview).path).name or f"deviation_{item.get('deviationid')}.jpg",
            }
        )
    return {
        "ok": True,
        "username": username,
        "works": works,
        "has_more": bool(payload.get("has_more")),
        "next_offset": payload.get("next_offset"),
    }


@router.get("/api/da/work-file/{deviation_id}")
def da_work_file(request: Request, deviation_id: str):
    """Return media for one work selected from the connected user's gallery."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    if not re.fullmatch(r"[0-9a-fA-F-]{8,80}", deviation_id or ""):
        return JSONResponse({"ok": False, "msg": "Invalid deviation id"}, status_code=400)

    deviation, error = _da_api_get(user, f"deviation/{deviation_id}")
    if error:
        return error
    if deviation.status_code != 200:
        return JSONResponse({"ok": False, "msg": f"DeviantArt work error ({deviation.status_code})"}, status_code=502)
    item = deviation.json() or {}
    media_url = str((item.get("content") or {}).get("src") or "")
    parsed = urlparse(media_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "deviantart.net" or host.endswith(".deviantart.net") or host == "wixmp.com" or host.endswith(".wixmp.com")):
        return JSONResponse({"ok": False, "msg": "Unsupported DeviantArt media host"}, status_code=400)

    import requests as rq
    upstream = rq.get(media_url, stream=True, timeout=45)
    if upstream.status_code != 200:
        return JSONResponse({"ok": False, "msg": f"Media download error ({upstream.status_code})"}, status_code=502)
    size = int(upstream.headers.get("content-length") or 0)
    if size and size > 100 * 1024 * 1024:
        upstream.close()
        return JSONResponse({"ok": False, "msg": "Work is larger than 100 MB"}, status_code=413)
    mime = upstream.headers.get("content-type") or "application/octet-stream"
    name = Path(parsed.path).name or f"deviation_{deviation_id}"
    return StreamingResponse(
        upstream.iter_content(chunk_size=256 * 1024),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{name.replace(chr(34), "")}"'},
    )


@router.post("/api/da/logout")
async def da_logout(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)
    auth_db.set_da_tokens(int(user["id"]), None, None)
    return {"ok": True}


@router.post("/api/da/upload")
async def da_upload(request: Request):
    """Upload files to DeviantArt Sta.sh."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    token = (user.get("da_access_token") or "").strip().strip('"').strip("'")
    if not token:
        return JSONResponse({"ok": False, "msg": "Connect DeviantArt first"}, status_code=401)
    # debug length only (never log full token)
    print(f"da_upload: user={user.get('id')} token_len={len(token)} files incoming")

    form = await request.form()
    items = form.multi_items() if hasattr(form, "multi_items") else list(form.items())

    titles: dict[str, str] = {}
    for k, v in items:
        ks = str(k)
        if ks.startswith("title_"):
            titles[ks[6:]] = str(v or "")

    files: list[tuple[str, bytes, str]] = []
    idx = 0
    for k, f in items:
        ks = str(k)
        # accept file, file_0, files, etc.
        if not (ks == "file" or ks.startswith("file_") or ks.startswith("files")):
            continue
        if f is None or isinstance(f, (str, bytes, int, float)):
            continue
        if not hasattr(f, "read"):
            continue
        try:
            raw = await f.read()
        except Exception:
            raw = f.file.read() if hasattr(f, "file") else b""
        if not raw:
            continue
        name = getattr(f, "filename", None) or f"file_{idx}.png"
        name = Path(str(name)).name  # strip path
        title = titles.get(name) or titles.get(str(idx)) or Path(name).stem
        files.append((name, raw, (title or Path(name).stem)[:50]))
        idx += 1

    if not files:
        return JSONResponse({"ok": False, "msg": "No files received"}, status_code=400)

    import requests as rq

    def submit_one(access: str, name: str, raw: bytes, title: str):
        """DA Sta.sh: access_token must be in form body for multipart uploads."""
        access = (access or "").strip()
        if not access:
            raise ValueError("empty access_token")
        mime = _da_guess_mime(name)
        # Token in form field + query + Bearer — DA is picky with multipart
        return rq.post(
            "https://www.deviantart.com/api/v1/oauth2/stash/submit",
            params={"access_token": access},
            headers={"Authorization": f"Bearer {access}"},
            data={
                "access_token": access,
                "title": title or Path(name).stem,
                "artist_comments": "",
                "is_mature": "0",
            },
            files={"file": (name, raw, mime)},
            timeout=180,
        )

    ok_n = 0
    errors: list[str] = []
    access = token

    for name, raw, title in files:
        try:
            r = submit_one(access, name, raw, title)
            # expired token → refresh once and retry
            if r.status_code in (401, 403):
                new_tok = _da_refresh_token(user)
                if new_tok:
                    access = new_tok
                    user = {**user, "da_access_token": new_tok}
                    r = submit_one(access, name, raw, title)
                else:
                    auth_db.set_da_tokens(int(user["id"]), None, None)
                    errors.append(f"{name}: session expired — reconnect DeviantArt")
                    break
            if r.status_code == 200:
                try:
                    body = r.json()
                except Exception:
                    body = {}
                # DA returns {"status":"success", ...} or error object with status error
                if isinstance(body, dict) and body.get("status") == "error":
                    err_desc = body.get("error_description") or body.get("error") or r.text[:160]
                    errors.append(f"{name}: {err_desc}")
                else:
                    ok_n += 1
            else:
                snippet = (r.text or "")[:180].replace("\n", " ")
                errors.append(f"{name}: HTTP {r.status_code} {snippet}")
                if r.status_code in (401, 403):
                    auth_db.set_da_tokens(int(user["id"]), None, None)
                    break
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")

    return {
        "ok": ok_n > 0,
        "uploaded": ok_n,
        "total": len(files),
        "errors": errors,
        "msg": None if ok_n > 0 else (errors[0] if errors else "Upload failed"),
    }


@router.get("/api/da/debug")
def da_debug(request: Request):
    """Safe debug: no secrets, helps fix OAuth."""
    user = _auth_user(request)
    redirect = (os.environ.get("DA_REDIRECT_URI") or "").strip()
    if not redirect:
        redirect = (os.environ.get("APP_URL") or "").rstrip("/") + "/api/da/callback"
    cid = ""
    if user:
        cid = (user.get("da_client_id") or "")[:12]
    return {
        "logged_in": bool(user),
        "has_keys": bool(user and user.get("da_client_id") and user.get("da_client_secret")),
        "client_id_prefix": cid,
        "redirect_uri": redirect,
        "authorize_base": "https://www.deviantart.com/oauth2/authorize",
        "hint": "In DA app settings, Redirect URI must match redirect_uri EXACTLY. OAuth page URL contains /oauth2/authorize — not the DA home feed.",
    }


@router.get("/api/da/status")
def da_status(request: Request):
    user = _auth_user(request)
    if not user:
        return {"ok": False, "logged_in": False, "da": False, "has_keys": False}
    return {
        "ok": True,
        "logged_in": True,
        "da": bool(user.get("da_access_token")),
        "has_keys": bool(user.get("da_client_id") and user.get("da_client_secret")),
        "client_id": (user.get("da_client_id") or "")[:8] + "…" if user.get("da_client_id") else "",
        "email": user.get("email"),
        "redirect_hint": (os.environ.get("APP_URL") or "").rstrip("/") + "/api/da/callback",
    }


@router.post("/api/da/keys")
async def da_save_keys(request: Request):
    """Save user's own DeviantArt app Client ID / Secret (desktop-style)."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    body = await request.json()
    cid = str(body.get("client_id") or "").strip().split()[0] if str(body.get("client_id") or "").strip() else ""
    sec = str(body.get("client_secret") or "").strip().split()[0] if str(body.get("client_secret") or "").strip() else ""
    if not cid or not sec:
        return JSONResponse({"ok": False, "msg": "Enter Client ID and Client Secret"}, status_code=400)
    auth_db.set_da_keys(int(user["id"]), cid, sec)
    return {"ok": True, "msg": "Keys saved"}


@router.get("/api/da/login")
def da_login_start(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to Showcase account first"}, status_code=401)
    # Prefer user's own keys; fallback to server env
    cid = (user.get("da_client_id") or "").strip() or (os.environ.get("DA_CLIENT_ID") or "").strip()
    sec = (user.get("da_client_secret") or "").strip() or (os.environ.get("DA_CLIENT_SECRET") or "").strip()
    redirect = (os.environ.get("DA_REDIRECT_URI") or "").strip()
    if not redirect:
        redirect = (os.environ.get("APP_URL") or "").rstrip("/") + "/api/da/callback"
    if not cid or not sec:
        return JSONResponse(
            {
                "ok": False,
                "msg": "Enter your DeviantArt Client ID & Secret (create app at deviantart.com/developers). Redirect URI must be: " + redirect,
            },
            status_code=400,
        )
    import base64
    import hashlib
    from urllib.parse import urlencode

    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = _oauth_payload_create({
        "verifier": verifier,
        "user_id": int(user["id"]),
        "client_id": cid,
        "client_secret": sec,
        "redirect": redirect,
    })
    q = urlencode(
        {
            "response_type": "code",
            "client_id": cid,
            "redirect_uri": redirect,
            "scope": "stash publish browse",
            "duration": "permanent",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
        }
    )
    return {"ok": True, "url": f"https://www.deviantart.com/oauth2/authorize?{q}"}


@router.get("/api/da/callback")
async def da_callback(request: Request, code: str = "", state: str = ""):
    pend = _oauth_payload_verify(state)
    if not pend or not code:
        return HTMLResponse("<h3>DeviantArt auth failed</h3><p>Close this tab and try again.</p>", status_code=400)
    try:
        import requests as rq

        r = rq.post(
            "https://www.deviantart.com/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": pend["client_id"],
                "client_secret": pend["client_secret"],
                "code": code,
                "redirect_uri": pend["redirect"],
                "code_verifier": pend["verifier"],
            },
            timeout=30,
        )
        if r.status_code != 200:
            LOGGER.warning("DeviantArt token exchange failed status=%s", r.status_code)
            return HTMLResponse("<h3>DeviantArt sign-in failed</h3>", status_code=400)
        data = r.json()
        auth_db.set_da_tokens(
            int(pend["user_id"]),
            data.get("access_token"),
            data.get("refresh_token"),
        )
    except Exception:
        LOGGER.exception("oauth callback failed")
        return HTMLResponse("<h3>Error</h3><p>Sign-in failed. Please try again.</p>", status_code=500)
    app_url = _app_origin()
    target_origin = json.dumps(app_url)
    # Same idea as desktop localhost page: "Success! You can close this window."
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Success</title></head>
<body style="font-family:system-ui,sans-serif;background:#0b0b12;color:#e8e8f0;display:grid;place-items:center;min-height:100vh;margin:0">
  <div style="text-align:center;padding:32px">
    <h1 style="font-size:1.6rem;margin:0 0 12px">Success!</h1>
    <p style="opacity:.8;margin:0 0 20px">You can close this window.</p>
    <p style="font-size:13px;opacity:.55">DeviantArt access granted · Showcase Maker</p>
    <p style="margin-top:24px"><a href="{_esc_html(app_url)}/app#da" style="color:#7b5cff">Back to tools</a></p>
  </div>
  <script>
    try {{ if (window.opener) window.opener.postMessage({{type:'da_connected'}}, {target_origin}); }} catch(e) {{}}
    setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1500);
  </script>
</body></html>"""
    )
