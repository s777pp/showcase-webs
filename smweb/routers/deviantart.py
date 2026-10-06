"""DeviantArt OAuth and upload.

Moved out of main.py unchanged.
"""


from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool


import auth_db


from fastapi import APIRouter


from smweb.core import LOGGER, MAX_UPLOAD_MB, _auth_user, _esc_html, _ip
from smweb import da_publish, free_limits
from smweb.da_client import _da_guess_mime, _da_refresh_token
from smweb.oauth_util import (
    _app_origin,
    _bind_oauth_browser,
    _clear_oauth_browser,
    _oauth_browser_matches,
    _oauth_payload_create,
    _oauth_payload_verify,
)
import logging
_LOG = logging.getLogger(__name__)


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


@router.get("/api/da/presets")
def da_presets(request: Request):
    """Saved publishing presets of the signed-in user."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    return {"ok": True, "presets": auth_db.da_presets_for_user(int(user["id"]))}


@router.post("/api/da/presets")
async def da_save_preset(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    name = re.sub(r"\s+", " ", str(body.get("name") or "")).strip()[:60]
    if not name:
        return JSONResponse({"ok": False, "msg": "Name the preset"}, status_code=400)
    preset_id = str(body.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,40}", preset_id):
        preset_id = secrets.token_urlsafe(12)
    raw = body.get("preset") if isinstance(body.get("preset"), dict) else {}
    settings = da_publish.clean_settings(raw, placeholders=True)
    preset = {
        "title": str(raw.get("title") or "")[:120],
        "link": da_publish.safe_href(str(raw.get("link") or "")),
        "price": str(raw.get("price") or "")[:40],
    }
    preset.update({key: settings[key] for key in (
        "mode", "description", "tags", "is_mature", "mature_level", "mature_classification", "is_ai_generated",
        "noai", "galleryids", "display_resolution", "add_watermark", "allow_free_download", "allow_comments",
        "feature")})
    try:
        saved = auth_db.save_da_preset(int(user["id"]), preset_id, name, preset)
    except PermissionError:
        return JSONResponse({"ok": False, "msg": "Preset not found"}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)
    return {"ok": True, "preset": saved}


@router.delete("/api/da/presets/{preset_id}")
def da_delete_preset(request: Request, preset_id: str):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    return {"ok": auth_db.delete_da_preset(int(user["id"]), preset_id)}


@router.get("/api/da/folders")
def da_folders(request: Request):
    """Gallery folders of the connected account (publish targets)."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    response, error = _da_api_get(user, "gallery/folders", {"calculate_size": "false", "limit": 50})
    if error:
        return error
    if response.status_code != 200:
        return JSONResponse({"ok": False, "msg": f"DeviantArt folders error ({response.status_code})"}, status_code=502)
    folders = [{"id": str(item.get("folderid") or ""), "name": str(item.get("name") or "")[:80]}
               for item in (response.json() or {}).get("results") or [] if item.get("folderid")]
    return {"ok": True, "folders": folders}


@router.get("/api/da/work-meta/{deviation_id}")
def da_work_meta(request: Request, deviation_id: str):
    """Title, description and tags of one of the user's works, to reuse as a template."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    if not re.fullmatch(r"[0-9a-fA-F-]{8,80}", deviation_id or ""):
        return JSONResponse({"ok": False, "msg": "Invalid deviation id"}, status_code=400)
    response, error = _da_api_get(user, "deviation/metadata",
                                  {"deviationids[]": deviation_id, "ext_submission": "true"})
    if error:
        return error
    if response.status_code != 200:
        return JSONResponse({"ok": False, "msg": f"DeviantArt metadata error ({response.status_code})"}, status_code=502)
    items = (response.json() or {}).get("metadata") or []
    if not items:
        return JSONResponse({"ok": False, "msg": "Work not found"}, status_code=404)
    item = items[0]
    tags = [str(t.get("tag_name") or "") for t in item.get("tags") or [] if isinstance(t, dict)]
    return {
        "ok": True,
        "title": str(item.get("title") or "")[:120],
        "description": da_publish.clean_description(item.get("description") or ""),
        "tags": da_publish.clean_tags(tags),
        "is_mature": bool(item.get("is_mature")),
    }


@router.post("/api/da/upload")
async def da_upload(request: Request):
    """Upload files to Sta.sh and, when asked, publish each one as a deviation.

    Form: ``file`` parts, ``title_<name>`` per file and ``settings`` (JSON: mode
    stash|publish, description HTML, tags, mature/AI flags, gallery folders, display
    size, watermark, free download, comments, feature). Old clients send no settings
    and keep the previous behaviour (Sta.sh only, empty description).
    """
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    token = (user.get("da_access_token") or "").strip().strip('"').strip("'")
    if not token:
        return JSONResponse({"ok": False, "msg": "Connect DeviantArt first"}, status_code=401)
    _LOG.info(f"da_upload: user={user.get('id')} token_len={len(token)} files incoming")
    # Pro: no limit. Free: one publication a week, any number of files in it (smweb/free_limits.py).
    pro = auth_db.effective_pro(user)
    if not pro and free_limits.left("da", int(user["id"]), _ip(request)) <= 0:
        return free_limits.refusal(request, "weekly", "da")

    try:
        form = await request.form(
            max_files=20,
            max_fields=60,
            max_part_size=MAX_UPLOAD_MB * 1024 * 1024,
        )
    except Exception:
        return JSONResponse(
            {"ok": False, "msg": f"Each file must be under {MAX_UPLOAD_MB} MB"},
            status_code=413,
        )
    items = form.multi_items() if hasattr(form, "multi_items") else list(form.items())

    titles: dict[str, str] = {}
    raw_settings = None
    for k, v in items:
        ks = str(k)
        if ks.startswith("title_"):
            titles[ks[6:]] = str(v or "")
        elif ks == "settings" and isinstance(v, str):
            try:
                raw_settings = json.loads(v)
            except ValueError:
                return JSONResponse({"ok": False, "msg": "Invalid publish settings"}, status_code=400)
    settings = da_publish.clean_settings(raw_settings)

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
        if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
            return JSONResponse(
                {"ok": False, "msg": f"Each file must be under {MAX_UPLOAD_MB} MB"},
                status_code=413,
            )
        name = getattr(f, "filename", None) or f"file_{idx}.png"
        name = Path(str(name)).name  # strip path
        title = titles.get(name) or titles.get(str(idx)) or Path(name).stem
        files.append((name, raw, da_publish.clean_title(title, Path(name).stem)))
        idx += 1

    if not files:
        return JSONResponse({"ok": False, "msg": "No files received"}, status_code=400)

    free_try = None
    if not pro:
        if not free_limits.consume("da", int(user["id"]), _ip(request)):
            return free_limits.refusal(request, "weekly", "da")
        free_try = free_limits.ticket("da", int(user["id"]), _ip(request))

    import requests as rq

    def call(path: str, access: str, fields: list, upload=None):
        """DA multipart: access_token in the form body, the query and the Bearer header."""
        return rq.post(
            "https://www.deviantart.com/api/v1/oauth2/" + path,
            params={"access_token": access},
            headers={"Authorization": f"Bearer {access}"},
            data=[("access_token", access)] + list(fields),
            files=upload,
            timeout=180,
        )

    def api_error(response) -> str:
        try:
            body = response.json()
        except Exception:
            body = {}
        if isinstance(body, dict) and (body.get("error_description") or body.get("error")):
            details = body.get("error_details")
            extra = "; ".join(f"{k}: {v}" for k, v in details.items()) if isinstance(details, dict) else ""
            return str(body.get("error_description") or body.get("error")) + (f" ({extra})" if extra else "")
        return f"HTTP {response.status_code} " + (response.text or "")[:160].replace("\n", " ")

    state = {"access": token, "user": user, "lost": False}

    def with_refresh(make):
        response = make(state["access"])
        if response.status_code in (401, 403):
            refreshed = _da_refresh_token(state["user"])
            if refreshed:
                state["access"] = refreshed
                state["user"] = {**state["user"], "da_access_token": refreshed}
                response = make(refreshed)
            else:
                auth_db.set_da_tokens(int(user["id"]), None, None)
                state["lost"] = True
        return response

    def json_of(response) -> dict:
        try:
            body = response.json()
        except Exception:
            body = {}
        return body if isinstance(body, dict) else {}

    results: list[dict] = []
    for name, raw, title in files:
        entry = {"name": name, "title": title, "ok": False}
        results.append(entry)
        if state["lost"]:
            entry["error"] = "session expired — reconnect DeviantArt"
            continue
        try:
            mime = _da_guess_mime(name)
            submitted = with_refresh(lambda a: call("stash/submit", a, da_publish.submit_fields(title, settings),
                                                     {"file": (name, raw, mime)}))
            body = json_of(submitted)
            if submitted.status_code != 200 or body.get("status") == "error" or not body.get("itemid"):
                entry["error"] = api_error(submitted)
                continue
            entry["itemid"] = body.get("itemid")
            if settings["mode"] != "publish":
                entry["ok"] = True
                entry["stash"] = True
                continue
            itemid = entry["itemid"]
            published = with_refresh(lambda a: call("stash/publish", a, da_publish.publish_fields(itemid, settings)))
            pbody = json_of(published)
            if published.status_code != 200 or pbody.get("status") == "error":
                entry["error"] = "saved to Sta.sh, publishing failed: " + api_error(published)
                entry["stash"] = True
                continue
            entry["ok"] = True
            entry["url"] = str(pbody.get("url") or "")
            entry["deviationid"] = str(pbody.get("deviationid") or "")
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {e}"

    ok_n = sum(1 for entry in results if entry["ok"])
    if not ok_n:
        free_limits.refund_ticket(free_try)   # nothing reached DeviantArt: the weekly use is not spent
    errors = [f"{entry['name']}: {entry['error']}" for entry in results if entry.get("error")]
    return {
        "ok": ok_n > 0,
        "mode": settings["mode"],
        "uploaded": ok_n,
        "total": len(files),
        "results": results,
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
    # One ShowcaseMaker DeviantArt application for all users.
    # Each user receives their own OAuth access/refresh tokens after authorization.
    cid = (os.environ.get("DA_CLIENT_ID") or "").strip()
    sec = (os.environ.get("DA_CLIENT_SECRET") or "").strip()
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
    response = JSONResponse({"ok": True, "url": f"https://www.deviantart.com/oauth2/authorize?{q}"})
    return _bind_oauth_browser(response, request, "deviantart", state)


@router.get("/api/da/callback")
async def da_callback(request: Request, code: str = "", state: str = ""):
    pend = _oauth_payload_verify(state)
    if not pend or not code or not _oauth_browser_matches(request, "deviantart", state):
        response = HTMLResponse("<h3>DeviantArt auth failed</h3><p>Close this tab and try again.</p>", status_code=400)
        return _clear_oauth_browser(response, "deviantart")
    try:
        import requests as rq

        r = await run_in_threadpool(
            rq.post,
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
            allow_redirects=False,
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
    response = HTMLResponse(
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
    return _clear_oauth_browser(response, "deviantart")
