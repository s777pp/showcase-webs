"""Auth: register/login/logout/me, avatar, profile update, unlock codes, quota, meta."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import auth_db
from web import core
from web.core import LOGGER

router = APIRouter(prefix="/api")


@router.post("/auth/register")
async def auth_register(request: Request):
    body = await request.json()
    email = str(body.get("email") or "")
    password = str(body.get("password") or "")
    ok, msg = auth_db.register(email, password)
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    ok2, msg2, token = auth_db.login(email, password)
    resp = JSONResponse({"ok": True, "msg": msg, "token": token})
    if token:
        core._attach_session_cookie(resp, token, request)
    return resp


@router.post("/auth/login")
async def auth_login(request: Request):
    body = await request.json()
    email = str(body.get("email") or "")
    password = str(body.get("password") or "")
    ok, msg, token = auth_db.login(email, password)
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    user = auth_db.user_by_token(token) if token else None
    resp = JSONResponse({
        "ok": True,
        "token": token,
        "email": user.get("email") if user else None,
        "is_pro": bool(user and auth_db.effective_pro(user)),
    })
    if token:
        core._attach_session_cookie(resp, token, request)
    return resp


@router.post("/auth/logout")
async def auth_logout(request: Request):
    tok = (request.headers.get("x-session-token") or "").strip()
    if not tok:
        tok = (request.cookies.get("sm_session") or "").strip()
    if tok:
        auth_db.logout(tok)
    resp = JSONResponse({"ok": True})
    core._clear_session_cookie(resp)
    return resp


@router.get("/auth/me")
def auth_me(request: Request):
    user = core._auth_user(request)
    if not user:
        return {"ok": False, "logged_in": False}
    av = user.get("avatar_path") or ""
    av_url = ""
    if av:
        av_url = f"/api/auth/avatar/{user['id']}"
    else:
        av_dir = Path(core.DATA) / "avatars"
        if av_dir.is_dir() and list(av_dir.glob(f"{user['id']}.*")):
            av_url = f"/api/auth/avatar/{user['id']}"
    return {
        "ok": True,
        "logged_in": True,
        "email": user["email"],
        "is_pro": auth_db.effective_pro(user),
        "pro_until": user.get("pro_until"),
        "pro_code": user.get("pro_code") or "",
        "display_name": user.get("display_name") or "",
        "avatar_url": av_url,
        "is_gallery_admin": core.is_gallery_admin(user),
    }


@router.post("/auth/profile")
async def auth_profile(request: Request):
    user = core._auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in first"}, status_code=401)
    ct = (request.headers.get("content-type") or "").lower()
    display_name = None
    avatar_saved = None
    try:
        if "multipart/form-data" in ct:
            form = await request.form()
            display_name = str(form.get("display_name") or "")
            f = form.get("avatar")
            if f is not None and hasattr(f, "read"):
                raw = await f.read()
                if raw and len(raw) < 3_000_000:
                    av_dir = Path(core.DATA) / "avatars"
                    av_dir.mkdir(parents=True, exist_ok=True)
                    name = getattr(f, "filename", "") or "a.png"
                    ext = Path(name).suffix.lower()
                    head = raw[:12]
                    if head[:6] in (b"GIF87a", b"GIF89a"):
                        ext = ".gif"
                    elif head[:8] == b"\x89PNG\r\n\x1a\n":
                        ext = ".png"
                    elif head[:3] == b"\xff\xd8\xff":
                        ext = ".jpg"
                    elif head[:4] == b"RIFF" and raw[8:12] == b"WEBP":
                        ext = ".webp"
                    elif ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                        ext = ".png"
                    for old in av_dir.glob(f"{user['id']}.*"):
                        try:
                            old.unlink(missing_ok=True)
                        except Exception:
                            pass
                    path = av_dir / f"{user['id']}{ext}"
                    path.write_bytes(raw)
                    avatar_saved = f"avatars/{user['id']}{ext}"
        else:
            body = await request.json()
            display_name = str(body.get("display_name") or "")
        auth_db.update_profile(
            int(user["id"]),
            display_name=display_name,
            avatar_path=avatar_saved,
        )
        av_url = f"/api/auth/avatar/{user['id']}" if (avatar_saved or user.get("avatar_path")) else ""
        if not av_url:
            av_dir = Path(core.DATA) / "avatars"
            if av_dir.is_dir() and list(av_dir.glob(f"{user['id']}.*")):
                av_url = f"/api/auth/avatar/{user['id']}"
        return {
            "ok": True,
            "msg": "Profile updated",
            "display_name": (display_name or "").strip()[:40],
            "avatar_url": av_url,
        }
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"{type(e).__name__}: {e}"}, status_code=500)


@router.get("/auth/avatar/{user_id}")
def auth_avatar(user_id: int):
    c = auth_db._conn()
    row = c.execute("SELECT avatar_path FROM users WHERE id=?", (user_id,)).fetchone()
    c.close()
    stored = ""
    if row and row["avatar_path"]:
        stored = str(row["avatar_path"]).strip()
    # Always resolve INSIDE DATA — see core.safe_data_path.
    path = core.safe_data_path(stored) if stored else None
    if path is None:
        av_dir = Path(core.DATA) / "avatars"
        matches = sorted(av_dir.glob(f"{int(user_id)}.*")) if av_dir.is_dir() else []
        matches = [m for m in matches if m.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")] or matches
        path = matches[0] if matches else None
    if path is None or not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    from fastapi.responses import FileResponse
    media = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path,
        media_type=media,
        headers={"Cache-Control": "no-cache, max-age=0", "Access-Control-Allow-Origin": "*"},
    )


@router.post("/unlock")
async def unlock(request: Request):
    """Activate Pro code — must be logged in. Key is bound to the account."""
    body = await request.json()
    code = str(body.get("code") or "").strip().upper().replace(" ", "")
    user = core._auth_user(request)
    if not user or not user.get("id"):
        return JSONResponse(
            {"ok": False, "msg": "Log in first, then activate the code on your account"},
            status_code=401,
        )
    codes = core._load_codes()
    if code not in codes:
        return JSONResponse({"ok": False, "msg": "Invalid access code"}, status_code=400)
    if user.get("is_pro"):
        return {"ok": True, "label": "Pro", "msg": "Already Pro on this account"}
    used_uid = auth_db.code_used(code)
    if used_uid is not None:
        return JSONResponse({"ok": False, "msg": "Code already used"}, status_code=400)
    used = core._load_used()
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
        core._save_used(used)
    msg = "Pro activated on your account"
    if until:
        msg = f"Trial activated for {int(hours)} hours"
    LOGGER.info("unlock: user=%s code=%s type=%s", user["id"], code, ctype)
    return {"ok": True, "label": label, "msg": msg, "until": until}


@router.get("/quota")
def api_quota(request: Request):
    return core.quota_state(request)


@router.get("/meta")
def meta():
    return {
        "socials": core.SOCIALS,
        "buy_url": core.FUNPAY_OFFER_URL,
        "stripe_enabled": bool(core.STRIPE_SECRET and core.STRIPE_PRICE_ID),
        "pro_label": core.PRO_PRICE_LABEL,
        "modes": [
            {"id": "workshop", "title": "Workshop", "desc": "5 частей для витрины мастерской"},
            {"id": "featured", "title": "Featured", "desc": "630 px Featured Artwork"},
            {"id": "split", "title": "Artwork Split", "desc": "Центр 506 + бок 100"},
        ],
        "fonts": ["rob", "lap", "caratte", "Fineday", "roboto", "gothic-rus"],
        "steam_code": core.STEAM_CONSOLE_CODE,
    }


@router.post("/admin/wipe-users")
async def admin_wipe_users(request: Request):
    """Delete all accounts. Requires header X-Admin-Secret = ADMIN_SECRET env."""
    if not core.admin_ok(request):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    n = auth_db.wipe_all_users()
    LOGGER.warning("wipe-users: deleted %s accounts", n)
    return JSONResponse({"ok": True, "deleted": n})
