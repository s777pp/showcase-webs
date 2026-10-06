"""Site account page (2026-10-06, owner reference: steamprofile.io account screen).

``/{lang}/account`` (static/account.html + js/account-page.js) shows the plan, today's usage, how the
person signs in, Pro purchases, recent saved results and the account settings. ``GET /api/account/overview``
gathers all of it in one request. Public-profile data stays on /profile.
"""
from __future__ import annotations

import io
import logging
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, UnidentifiedImageError

import auth_db
from smweb import gumroad_billing, object_store, telegram_billing
from smweb.core import DATA, _auth_user, _safe_data_path, quota_state
from smweb.locales import SUPPORTED_LANGUAGES

router = APIRouter()
LOGGER = logging.getLogger("sm.account")

SYNTHETIC_EMAIL = "@users.local"   # Discord / Google / Telegram / Steam accounts without a real address


def _logins(c, uid: int) -> dict:
    row = c.execute(
        "SELECT email, discord_id, discord_username, google_id, telegram_id, telegram_username, steam_id, "
        "steam_username, created_at FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        return {}
    email = str(row["email"] or "")
    real_email = bool(email) and not email.endswith(SYNTHETIC_EMAIL)
    return {
        "email": email if real_email else "",
        "password": real_email,
        "discord": str(row["discord_username"] or ("✓" if row["discord_id"] else "")),
        "google": bool(row["google_id"]),
        "telegram": str(row["telegram_username"] or ("✓" if row["telegram_id"] else "")),
        "steam": str(row["steam_id"] or ""),
        "steam_name": str(row["steam_username"] or ""),
        "created_at": float(row["created_at"] or 0) or None,
    }


def _purchases(c, uid: int) -> list[dict]:
    rows = c.execute(
        "SELECT plan, days, status, price_cents, currency, sale_created, granted_at, revoked_at "
        "FROM gumroad_sales WHERE user_id=? ORDER BY COALESCE(sale_created, granted_at) DESC LIMIT 30", (uid,)).fetchall()
    items = []
    for row in rows:
        items.append({
            "source": "gumroad", "plan": row["plan"], "days": row["days"], "status": row["status"],
            "price": gumroad_billing.price_label(row["price_cents"], row["currency"]) if row["price_cents"] is not None else "",
            "at": row["sale_created"] or row["granted_at"],
        })
    # Paid in the Telegram bot (Stars, crypto, transfer): smweb/telegram_billing.py.
    for row in telegram_billing.purchases_for(uid):
        items.append({
            "source": "telegram", "plan": row["plan"], "days": row["days"], "status": row["status"],
            "price": telegram_billing.price_label(row["amount"], row["currency"]), "at": row["granted_at"] or row["created_at"],
        })
    # Keys entered by hand (FunPay, giveaways, old bot keys): only the date and the kind, never the code.
    for row in c.execute("SELECT code, used_at FROM used_codes WHERE user_id=? ORDER BY used_at DESC LIMIT 30",
                         (uid,)).fetchall():
        code = str(row["code"] or "")
        kind = "trial" if code.startswith("SM-TRIAL") else ("gumroad_license" if code.startswith("GR-") else "key")
        items.append({"source": kind, "plan": None, "days": None, "status": "granted", "price": "", "at": row["used_at"]})
    items.sort(key=lambda item: float(item.get("at") or 0), reverse=True)
    return items[:30]


def _overview(request: Request, user: dict) -> dict:
    uid = int(user["id"])
    c = auth_db._conn()
    try:
        logins = _logins(c, uid)
        purchases = _purchases(c, uid)
    finally:
        c.close()
    stats = auth_db.account_activity_stats(uid)
    try:
        from smweb import saved_results
        rows = auth_db.saved_results_for_user(uid)
        results = [saved_results.public_row(row) for row in rows]
    except Exception:
        results = []
    quota = quota_state(request)
    state = gumroad_billing.pro_state(uid)
    code = str(user.get("pro_code") or "")
    username = ""
    try:
        username = auth_db.ensure_profile_username(uid, user.get("display_name"))
    except Exception:
        pass
    return {
        "ok": True,
        "user": {
            "id": uid,
            "name": user.get("display_name") or (logins.get("email") or "").split("@")[0] or f"user{uid}",
            "display_name": user.get("display_name") or "",
            "username": username,
            "avatar_url": f"/api/auth/avatar/{uid}" if user.get("avatar_path") else "",
            **logins,
        },
        "plan": {
            **state,
            "trial": state["pro"] and not state["lifetime"] and code.startswith("SM-TRIAL"),
            "days_left": (max(0, int((state["until"] - time.time()) // 86400)) if state.get("until") else None),
        },
        "quota": {"used": int(quota.get("used") or 0), "limit": int(quota.get("limit") or 0)},
        "stats": {"gallery": stats.get("gallery_uploads", 0), "showcases": stats.get("showcase_count", 0),
                  "results": len(results)},
        "results": results[:8],
        "purchases": purchases,
    }


@router.get("/api/account/overview")
async def account_overview(request: Request):
    import asyncio
    user = _auth_user(request)
    if not user or not user.get("id"):
        return JSONResponse({"ok": False, "code": "login"}, status_code=401)
    payload = await asyncio.to_thread(_overview, request, user)
    return JSONResponse(payload, headers={"Cache-Control": "private, no-store"})


# ---------------------------------------------------------------- avatar (account page + public profile page)
AVATAR_MAX_UPLOAD = 6 * 1024 * 1024      # what we read from the request at most
AVATAR_MAX_ANIMATED = 3 * 1024 * 1024    # animated GIF / WebP are kept as they are, so they must already be small
AVATAR_SIDE = 512


def _avatar_bytes(raw: bytes) -> tuple[bytes, str]:
    """Validated avatar file: (bytes, extension). Stills become a 512 px PNG/JPG; animations keep their frames."""
    with Image.open(io.BytesIO(raw)) as image:
        if image.width * image.height > 16_000_000:
            raise ValueError("too_large")
        animated = getattr(image, "is_animated", False) and getattr(image, "n_frames", 1) > 1
        kind = (image.format or "").upper()
        if animated and kind in ("GIF", "WEBP"):
            if len(raw) > AVATAR_MAX_ANIMATED:
                raise ValueError("animated_too_big")
            image.seek(0)
            image.load()
            return raw, ".gif" if kind == "GIF" else ".webp"
        image.load()
        image.thumbnail((AVATAR_SIDE, AVATAR_SIDE), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        if image.mode in ("RGBA", "LA", "P") and ("transparency" in image.info or image.mode != "P"):
            image.convert("RGBA").save(out, "PNG", optimize=True)
            return out.getvalue(), ".png"
        image.convert("RGB").save(out, "JPEG", quality=90, optimize=True)
        return out.getvalue(), ".jpg"


def _local_avatar_files(uid: int) -> list[Path]:
    folder = Path(DATA) / "avatars"
    if not folder.is_dir():
        return []
    return [p for pattern in (f"{uid}.*", f"{uid}-*", f"{uid}_*") for p in folder.glob(pattern) if p.is_file()]


def _drop_old_avatar(uid: int, old: str, keep: str = "") -> None:
    """Remove the previous avatar object/file; never the one just saved."""
    if old and old != keep:
        if object_store.configured():
            try:
                object_store.delete(object_store.key_from_stored(old))
            except Exception:
                LOGGER.debug("old avatar object cleanup failed", exc_info=True)
        path = _safe_data_path(old)
        if path is not None and path.is_file():
            path.unlink(missing_ok=True)
    if not keep:
        # /api/auth/avatar falls back to any local file of the user, so a removal clears them all.
        for path in _local_avatar_files(uid):
            path.unlink(missing_ok=True)


@router.post("/api/account/avatar")
async def account_avatar_upload(request: Request, file: UploadFile = File(...)):
    user = _auth_user(request)
    if not user or not user.get("id"):
        return JSONResponse({"ok": False, "code": "login"}, status_code=401)
    uid = int(user["id"])
    raw = await file.read(AVATAR_MAX_UPLOAD + 1)
    if len(raw) > AVATAR_MAX_UPLOAD:
        return JSONResponse({"ok": False, "code": "too_big"}, status_code=413)
    try:
        data, ext = await run_in_threadpool(_avatar_bytes, raw)
    except ValueError as exc:
        code = str(exc) if str(exc) in ("animated_too_big", "too_large") else "bad_image"
        return JSONResponse({"ok": False, "code": code}, status_code=400)
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return JSONResponse({"ok": False, "code": "bad_image"}, status_code=400)
    key = f"avatars/{uid}-{secrets.token_hex(6)}{ext}"
    old = str(auth_db.user_avatar_path(uid) or "").strip()
    try:
        if object_store.configured():
            await run_in_threadpool(object_store.put_bytes, key, data,
                                    media_type=object_store.content_type(key), immutable=True)
        else:
            path = Path(DATA) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        auth_db.update_profile(uid, avatar_path=key)
    except Exception:
        LOGGER.exception("avatar upload failed for user %s", uid)
        return JSONResponse({"ok": False, "code": "failed"}, status_code=500)
    await run_in_threadpool(_drop_old_avatar, uid, old, key)
    return {"ok": True, "avatar_url": f"/api/auth/avatar/{uid}?v={secrets.token_hex(4)}"}


@router.delete("/api/account/avatar")
async def account_avatar_delete(request: Request):
    user = _auth_user(request)
    if not user or not user.get("id"):
        return JSONResponse({"ok": False, "code": "login"}, status_code=401)
    uid = int(user["id"])
    old = str(auth_db.user_avatar_path(uid) or "").strip()
    auth_db.update_profile(uid, avatar_path="")
    await run_in_threadpool(_drop_old_avatar, uid, old, "")
    return {"ok": True, "avatar_url": ""}


@router.get("/account", include_in_schema=False)
def account_redirect(request: Request):
    from smweb.routers import pages
    return pages._legacy_redirect(request, "/account")


def _account_page(language: str):
    def serve():
        from smweb.routers import pages
        response = pages._localized_html("account.html", language, "/account")
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response
    return serve


for _language in SUPPORTED_LANGUAGES:
    router.add_api_route(f"/{_language}/account", _account_page(_language), methods=["GET"],
                         response_class=HTMLResponse, include_in_schema=False)
