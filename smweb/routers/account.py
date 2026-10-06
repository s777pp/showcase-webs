"""Site account page (2026-10-06, owner reference: steamprofile.io account screen).

``/{lang}/account`` (static/account.html + js/account-page.js) shows the plan, today's usage, how the
person signs in, Pro purchases, recent saved results and the account settings. ``GET /api/account/overview``
gathers all of it in one request. Public-profile data stays on /profile.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

import auth_db
from smweb import gumroad_billing
from smweb.core import _auth_user, quota_state
from smweb.locales import SUPPORTED_LANGUAGES

router = APIRouter()

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
    # Keys entered by hand (FunPay, Telegram bot, giveaways): only the date and the kind, never the code.
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
