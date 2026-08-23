"""DeviantArt OAuth + Sta.sh upload."""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse

import auth_db
from logging_config import log
from utils import auth_user

router = APIRouter(prefix="/api/da", tags=["deviantart"])

_da_pending: dict[str, dict] = {}  # state -> {verifier, user_id, client_id, client_secret, redirect, ts}


@router.get("/debug")
def da_debug(request: Request):
    user = auth_user(request)
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
        "hint": "In DA app settings, Redirect URI must match redirect_uri EXACTLY.",
    }


@router.get("/status")
def da_status(request: Request):
    user = auth_user(request)
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


@router.post("/keys")
async def da_save_keys(request: Request):
    user = auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    body = await request.json()
    cid = str(body.get("client_id") or "").strip().split()[0] if str(body.get("client_id") or "").strip() else ""
    sec = str(body.get("client_secret") or "").strip().split()[0] if str(body.get("client_secret") or "").strip() else ""
    if not cid or not sec:
        return JSONResponse({"ok": False, "msg": "Enter Client ID and Client Secret"}, status_code=400)
    auth_db.set_da_keys(int(user["id"]), cid, sec)
    return {"ok": True, "msg": "Keys saved"}


@router.get("/login")
def da_login_start(request: Request):
    user = auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to Showcase account first"}, status_code=401)
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
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = secrets.token_hex(16)
    _da_pending[state] = {
        "verifier": verifier,
        "user_id": int(user["id"]),
        "client_id": cid,
        "client_secret": sec,
        "redirect": redirect,
        "ts": time.time(),
    }
    # cleanup old pending (>15 min)
    now = time.time()
    for k in list(_da_pending.keys()):
        if now - _da_pending[k].get("ts", 0) > 900:
            _da_pending.pop(k, None)
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


@router.get("/callback")
async def da_callback(request: Request, code: str = "", state: str = ""):
    pend = _da_pending.pop(state, None)
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
            return HTMLResponse(f"<h3>Token error</h3><pre>{r.text[:500]}</pre>", status_code=400)
        data = r.json()
        auth_db.set_da_tokens(
            int(pend["user_id"]),
            data.get("access_token"),
            data.get("refresh_token"),
        )
        log.info("DA connected user_id=%s", pend["user_id"])
    except Exception as e:
        log.exception("DA callback failed")
        return HTMLResponse(f"<h3>Error</h3><pre>{e}</pre>", status_code=500)
    app_url = (os.environ.get("APP_URL") or "/").rstrip("/")
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Success</title></head>
<body style="font-family:system-ui,sans-serif;background:#0b0b12;color:#e8e8f0;display:grid;place-items:center;min-height:100vh;margin:0">
  <div style="text-align:center;padding:32px">
    <h1 style="font-size:1.6rem;margin:0 0 12px">Success!</h1>
    <p style="opacity:.8;margin:0 0 20px">You can close this window.</p>
    <p style="font-size:13px;opacity:.55">DeviantArt access granted · Showcase Maker</p>
    <p style="margin-top:24px"><a href="{app_url}/app#da" style="color:#7b5cff">Back to tools</a></p>
  </div>
  <script>
    try {{ if (window.opener) window.opener.postMessage({{type:'da_connected'}}, '*'); }} catch(e) {{}}
    setTimeout(function(){{ try {{ window.close(); }} catch(e) {{}} }}, 1500);
  </script>
</body></html>"""
    )


@router.post("/logout")
async def da_logout(request: Request):
    user = auth_user(request)
    if not user:
        return JSONResponse({"ok": False}, status_code=401)
    auth_db.set_da_tokens(int(user["id"]), None, None)
    return {"ok": True}


@router.post("/upload")
async def da_upload(request: Request):
    """Upload files to DeviantArt Sta.sh."""
    user = auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    token = user.get("da_access_token")
    if not token:
        return JSONResponse({"ok": False, "msg": "Connect DeviantArt first"}, status_code=401)
    form = await request.form()
    files = []
    items = form.multi_items() if hasattr(form, "multi_items") else list(form.items())
    titles = {}
    for k, v in items:
        k = str(k)
        if k.startswith("title_"):
            titles[k[6:]] = str(v)
    for k, f in items:
        if not str(k).startswith("file"):
            continue
        if f is None or isinstance(f, (str, bytes)) or not hasattr(f, "read"):
            continue
        raw = await f.read()
        name = getattr(f, "filename", None) or "file.png"
        files.append((name, raw, titles.get(name) or Path(name).stem))

    if not files:
        return JSONResponse({"ok": False, "msg": "No files"}, status_code=400)

    import requests as rq

    ok_n = 0
    errors = []
    for name, raw, title in files:
        try:
            r = rq.post(
                "https://www.deviantart.com/api/v1/oauth2/stash/submit",
                headers={"Authorization": f"Bearer {token}"},
                data={"title": title, "artist_comments": "", "is_mature": "false"},
                files={"file": (name, raw)},
                timeout=120,
            )
            if r.status_code == 200:
                ok_n += 1
            else:
                errors.append(f"{name}: {r.status_code} {r.text[:120]}")
                if r.status_code in (401, 403):
                    auth_db.set_da_tokens(int(user["id"]), None, None)
                    break
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
    return {"ok": ok_n > 0, "uploaded": ok_n, "total": len(files), "errors": errors}
