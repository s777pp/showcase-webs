"""Billing: legacy checkout redirect, Stripe webhook, Gumroad Pro plans (orders, Ping, claim page)."""


from __future__ import annotations

import hashlib
import os

from fastapi import Request
from fastapi.responses import JSONResponse


import auth_db
from smweb import analytics


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
                analytics.record(
                    "pro_activated", user_id=int(uid),
                    properties={"method": "stripe"},
                    event_key=f"pro:stripe:{event.get('id') or hashlib.sha256(payload).hexdigest()[:24]}",
                )
            except Exception:
                pass
    return {"ok": True}

# ---------------------------------------------------------------- Gumroad Pro plans (2026-10-06)
# Flow and safety notes: smweb/gumroad_billing.py.
from fastapi import BackgroundTasks  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402

from smweb import gumroad_billing as gumroad  # noqa: E402
from smweb.core import _auth_user  # noqa: E402
from smweb.locales import SUPPORTED_LANGUAGES  # noqa: E402


def _plans_payload() -> dict:
    """Every plan with its price; ``checkout`` is true when the Gumroad product is published and can be paid."""
    try:
        known = gumroad.products() if gumroad.configured() else {}
    except gumroad.Unavailable:
        known = {}
    plans = []
    for plan, (_permalink, days) in gumroad.PLANS.items():
        info = known.get(plan) or {}
        plans.append({"id": plan, "days": days, "lifetime": days is None,
                      "price": info.get("price") or gumroad.DEFAULT_PRICES.get(plan, ""),
                      "checkout": bool(info.get("published"))})
    return {"ok": True, "enabled": any(item["checkout"] for item in plans), "plans": plans}


@router.get("/api/billing/plans")
async def billing_plans(request: Request):
    """All Pro plans with prices, which of them can be paid through Gumroad now, and the caller's Pro state."""
    import asyncio
    payload = await asyncio.to_thread(_plans_payload)
    user = _auth_user(request)
    payload["signed_in"] = bool(user and user.get("id"))
    if payload["signed_in"]:
        payload["pro"] = await asyncio.to_thread(gumroad.pro_state, int(user["id"]))
    return JSONResponse(payload, headers={"Cache-Control": "private, no-store"})


@router.post("/api/billing/gumroad/order")
async def gumroad_order(request: Request):
    """Start a checkout bound to the signed-in account; the browser opens the returned Gumroad URL."""
    import asyncio
    user = _auth_user(request)
    if not user or not user.get("id"):
        return JSONResponse({"ok": False, "code": "login"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    plan = str((body or {}).get("plan") or "")
    available = {item["id"] for item in (await asyncio.to_thread(_plans_payload))["plans"] if item["checkout"]}
    if plan not in available:
        return JSONResponse({"ok": False, "code": "plan"}, status_code=400)
    state = await asyncio.to_thread(gumroad.pro_state, int(user["id"]))
    if state.get("lifetime"):
        return JSONResponse({"ok": False, "code": "lifetime"}, status_code=409)
    order = await asyncio.to_thread(gumroad.create_order, int(user["id"]), plan)
    analytics.record("checkout_started", request=request, user_id=int(user["id"]), properties={"method": "gumroad"})
    return {"ok": True, "url": order["url"]}


def _ping_job(sale_id: str, order_token: str, is_test: bool) -> None:
    try:
        result = gumroad.sync_sale(sale_id, order_token=order_token, source="ping", is_test=is_test)
        LOGGER.info("gumroad ping: %s", result.get("status"))
    except gumroad.Unavailable:
        # Gumroad stops retrying once we answered 2xx; the buyer can still claim, and refunds are rechecked hourly.
        LOGGER.warning("gumroad ping: API unavailable, sale left for claim/recheck")
    except Exception:
        LOGGER.exception("gumroad ping failed")


@router.post("/api/billing/gumroad")
async def gumroad_ping(request: Request, background: BackgroundTasks):
    """Gumroad Ping (sale, refund, dispute...). Unsigned, so it only triggers a read-back through the API."""
    try:
        form = await request.form()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Invalid Gumroad payload"}, status_code=400)
    data: dict = {}
    for key, value in form.multi_items():
        if isinstance(value, str):
            data.setdefault(key, value)
    sale_id = str(data.get("sale_id") or "").strip()
    seller = (os.environ.get("GUMROAD_SELLER_ID") or "").strip()
    if seller and str(data.get("seller_id") or "") != seller:
        LOGGER.warning("gumroad ping: foreign seller_id ignored")
        return {"ok": True}
    if not gumroad.valid_sale_id(sale_id):
        return {"ok": True}
    if not gumroad.configured():
        LOGGER.warning("gumroad ping received but GUMROAD_ACCESS_TOKEN is not set")
        return {"ok": True}
    is_test = str(data.get("test") or "").lower() == "true"
    background.add_task(_ping_job, sale_id, gumroad.order_from_ping(data), is_test)
    return {"ok": True}


@router.post("/api/billing/gumroad/claim")
async def gumroad_claim(request: Request):
    """Bind a Gumroad sale to the signed-in account (purchase made outside the site, or a lost Ping)."""
    import asyncio
    user = _auth_user(request)
    if not user or not user.get("id"):
        return JSONResponse({"ok": False, "code": "login"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    sale_id = str((body or {}).get("sale_id") or "").strip()
    if not gumroad.valid_sale_id(sale_id):
        return JSONResponse({"ok": False, "code": "unknown"}, status_code=400)
    try:
        result = await asyncio.to_thread(gumroad.sync_sale, sale_id, claim_user=int(user["id"]), source="claim")
    except gumroad.Unavailable:
        return JSONResponse({"ok": False, "code": "unavailable"}, status_code=503)
    status = result.get("status")
    if status in ("granted", "already"):
        state = await asyncio.to_thread(gumroad.pro_state, int(user["id"]))
        return {"ok": True, "code": status, "plan": result.get("plan"), "pro": state}
    codes = {"taken": 409, "refunded": 410, "revoked": 410, "unknown": 404, "other_product": 404}
    return JSONResponse({"ok": False, "code": status}, status_code=codes.get(status, 400))


@router.get("/billing/gumroad/claim", include_in_schema=False)
def gumroad_claim_redirect(request: Request):
    from smweb.routers import pages
    return pages._legacy_redirect(request, "/billing/claim")


def _claim_page(language: str):
    def serve():
        from smweb.routers import pages
        response = pages._localized_html("billing-claim.html", language, "/billing/claim")
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response
    return serve


for _language in SUPPORTED_LANGUAGES:
    router.add_api_route(f"/{_language}/billing/claim", _claim_page(_language), methods=["GET"],
                         response_class=HTMLResponse, include_in_schema=False)
