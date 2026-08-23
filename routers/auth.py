"""Auth routes: register, login, profile, logout, me."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse

import auth_db
from config import DATA, ADMIN_SECRET
from logging_config import log
from utils import auth_user, attach_session_cookie, clear_session_cookie

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
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
        attach_session_cookie(resp, token, request)
    log.info("register ok email=%s", email)
    return resp


@router.post("/login")
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
        attach_session_cookie(resp, token, request)
    return resp


@router.post("/profile")
async def auth_profile(request: Request):
    user = auth_user(request)
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
                    av_dir = Path(DATA) / "avatars"
                    av_dir.mkdir(parents=True, exist_ok=True)
                    name = getattr(f, "filename", "") or "a.png"
                    ext = Path(name).suffix.lower()
                    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                        ext = ".png"
                    path = av_dir / f"{user['id']}{ext}"
                    path.write_bytes(raw)
                    avatar_saved = str(path.resolve())
        else:
            body = await request.json()
            display_name = str(body.get("display_name") or "")
        auth_db.update_profile(
            int(user["id"]),
            display_name=display_name,
            avatar_path=avatar_saved,
        )
        return {
            "ok": True,
            "msg": "Profile updated",
            "display_name": (display_name or "").strip()[:40],
        }
    except Exception as e:
        log.exception("profile update failed")
        return JSONResponse({"ok": False, "msg": f"{type(e).__name__}: {e}"}, status_code=500)


@router.get("/avatar/{user_id}")
def auth_avatar(user_id: int):
    c = auth_db._conn()
    row = c.execute("SELECT avatar_path FROM users WHERE id=?", (user_id,)).fetchone()
    c.close()
    if not row or not row["avatar_path"]:
        return JSONResponse({"ok": False}, status_code=404)
    path = Path(row["avatar_path"])
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path)


@router.post("/logout")
async def auth_logout(request: Request):
    tok = (request.headers.get("x-session-token") or "").strip()
    if not tok:
        tok = (request.cookies.get("sm_session") or "").strip()
    if tok:
        auth_db.logout(tok)
    resp = JSONResponse({"ok": True})
    clear_session_cookie(resp)
    return resp


@router.get("/me")
def auth_me(request: Request):
    user = auth_user(request)
    if not user:
        return {"ok": False, "logged_in": False}
    av = user.get("avatar_path") or ""
    av_url = f"/api/auth/avatar/{user['id']}" if av else ""
    return {
        "ok": True,
        "logged_in": True,
        "email": user["email"],
        "is_pro": auth_db.effective_pro(user),
        "pro_until": user.get("pro_until"),
        "pro_code": user.get("pro_code") or "",
        "display_name": user.get("display_name") or "",
        "avatar_url": av_url,
    }
