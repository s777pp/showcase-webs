"""Gumroad Pro plans: orders, Ping, claim, refunds (2026-10-06)."""
import secrets
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_db
from smweb import gumroad_billing as gb
from smweb.routers import billing

PRODUCTS = {
    plan: {"product_id": f"P-{plan}", "permalinks": [permalink], "price": f"${index}.99", "published": plan != "90d",
           "url": f"https://seller.gumroad.com/l/{permalink}"}
    for index, (plan, (permalink, _days)) in enumerate(gb.PLANS.items())
}


@pytest.fixture
def gumroad(monkeypatch):
    sales: dict = {}
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(gb, "products", lambda force=False: PRODUCTS)
    monkeypatch.setattr(gb, "fetch_sale", lambda sale_id: sales.get(sale_id))
    monkeypatch.setattr(gb, "_tell_owner", lambda *a, **k: None)
    return sales


def _sale(sales, plan, **extra):
    sale_id = secrets.token_urlsafe(12)
    sales[sale_id] = {"id": sale_id, "product_id": f"P-{plan}", "product_permalink": "x" + plan,
                      "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "price": 199,
                      "currency": "usd", "refunded": False, "chargedback": False, "disputed": False, **extra}
    return sale_id


def _user():
    email = f"g-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        return int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
    finally:
        c.close()


def _until(uid):
    state = gb.pro_state(uid)
    return state["until"] if state["pro"] else None


def test_order_token_is_read_from_every_url_params_shape():
    token = "A" * 24
    assert gb.order_from_ping({"url_params[sm_order]": token}) == token
    assert gb.order_from_ping({"url_params": {"sm_order": token}}) == token
    assert gb.order_from_ping({"url_params": '{"sm_order": "%s"}' % token}) == token
    assert gb.order_from_ping({"url_params": "{'sm_order' => '%s', 'x' => '1'}" % token}) == token
    assert gb.order_from_ping({"url_params": "{}"}) == ""


def test_ping_with_order_grants_once_and_purchases_add_up(gumroad):
    uid = _user()
    order = gb.create_order(uid, "7d")
    assert "sm_order=" + order["token"] in order["url"] and order["url"].startswith("https://seller.gumroad.com/l/sm-pro-7d?")
    sale = _sale(gumroad, "7d")
    assert gb.sync_sale(sale, order_token=order["token"])["status"] == "granted"
    first = _until(uid)
    assert first and abs(first - (time.time() + 7 * 86400)) < 60
    # Gumroad delivers at least once: the same sale never grants twice.
    assert gb.sync_sale(sale, order_token=order["token"])["status"] == "already"
    assert _until(uid) == first
    second = gb.create_order(uid, "30d")
    assert gb.sync_sale(_sale(gumroad, "30d"), order_token=second["token"])["status"] == "granted"
    assert abs(_until(uid) - (first + 30 * 86400)) < 5, "a second purchase extends the first"


def test_order_for_another_plan_or_reused_token_does_not_bind(gumroad):
    uid = _user()
    order = gb.create_order(uid, "1d")
    assert gb.sync_sale(_sale(gumroad, "30d"), order_token=order["token"])["status"] == "pending"
    used = gb.create_order(uid, "1d")
    assert gb.sync_sale(_sale(gumroad, "1d"), order_token=used["token"])["status"] == "granted"
    assert gb.sync_sale(_sale(gumroad, "1d"), order_token=used["token"])["status"] == "pending", "one order, one sale"


def test_claim_binds_once_and_other_accounts_are_refused(gumroad):
    owner, other = _user(), _user()
    sale = _sale(gumroad, "1d")
    assert gb.sync_sale(sale)["status"] == "pending", "a Ping without an order waits for a claim"
    assert gb.sync_sale(sale, claim_user=owner, source="claim")["status"] == "granted"
    assert gb.pro_state(owner)["pro"]
    assert gb.sync_sale(sale, claim_user=other, source="claim")["status"] == "taken"
    assert not gb.pro_state(other)["pro"]
    assert gb.sync_sale(sale, claim_user=owner, source="claim")["status"] == "already"


def test_refund_takes_the_days_back(gumroad):
    uid = _user()
    keep = _sale(gumroad, "30d")
    gb.sync_sale(keep, claim_user=uid)
    refunded = _sale(gumroad, "7d")
    gb.sync_sale(refunded, claim_user=uid)
    before = _until(uid)
    gumroad[refunded]["refunded"] = True
    assert gb.sync_sale(refunded)["status"] == "revoked"
    assert abs(_until(uid) - (before - 7 * 86400)) < 5
    assert gb.sync_sale(refunded)["status"] == "refunded", "a repeated refund Ping changes nothing"
    gumroad[keep]["disputed"] = True
    assert gb.sync_sale(keep)["status"] == "revoked"
    assert not gb.pro_state(uid)["pro"], "nothing left after both purchases are gone"


def test_refund_before_the_sale_ping_never_grants(gumroad):
    uid = _user()
    sale = _sale(gumroad, "30d", refunded=True)
    assert gb.sync_sale(sale, claim_user=uid)["status"] == "refunded"
    assert not gb.pro_state(uid)["pro"]


def test_lifetime_grant_refund_and_time_plans_on_top(gumroad):
    uid = _user()
    life = _sale(gumroad, "unlimited")
    assert gb.sync_sale(life, claim_user=uid)["status"] == "granted"
    assert gb.pro_state(uid) == {"pro": True, "until": None, "lifetime": True}
    gb.sync_sale(_sale(gumroad, "7d"), claim_user=uid)
    assert gb.pro_state(uid)["lifetime"], "time plans never shorten lifetime Pro"
    gumroad[life]["chargedback"] = True
    assert gb.sync_sale(life)["status"] == "revoked"
    assert not gb.pro_state(uid)["pro"]


def test_unknown_and_foreign_sales_are_ignored(gumroad):
    assert gb.sync_sale("not a sale id!")["status"] == "unknown"
    assert gb.sync_sale("A" * 20)["status"] == "unknown"
    other = _sale(gumroad, "1d")
    gumroad[other]["product_id"] = "P-other"
    assert gb.sync_sale(other)["status"] == "other_product"


def _client(monkeypatch, uid=None):
    monkeypatch.setattr(billing, "_auth_user", lambda request: {"id": uid} if uid else None)
    app = FastAPI()
    app.include_router(billing.router)
    return TestClient(app)


def test_api_plans_order_ping_and_claim(gumroad, monkeypatch):
    uid = _user()
    with _client(monkeypatch) as guest:
        plans = guest.get("/api/billing/plans").json()
        assert plans["enabled"] and not plans["signed_in"]
        assert [p["id"] for p in plans["plans"]] == ["1d", "7d", "30d", "90d", "unlimited"]
        assert [p["id"] for p in plans["plans"] if p["checkout"]] == ["1d", "7d", "30d", "unlimited"],             "an unpublished product is listed but cannot be paid through Gumroad"
        assert guest.post("/api/billing/gumroad/order", json={"plan": "1d"}).status_code == 401
    with _client(monkeypatch, uid) as client:
        assert client.post("/api/billing/gumroad/order", json={"plan": "90d"}).status_code == 400
        url = client.post("/api/billing/gumroad/order", json={"plan": "1d"}).json()["url"]
        token = url.split("sm_order=")[1]
        sale = _sale(gumroad, "1d")
        ping = client.post("/api/billing/gumroad", data={"sale_id": sale, f"url_params[{gb.ORDER_PARAM}]": token})
        assert ping.status_code == 200
        assert client.get("/api/billing/plans").json()["pro"]["pro"], "the Ping switched Pro on"
        claimed = client.post("/api/billing/gumroad/claim", json={"sale_id": sale}).json()
        assert claimed["ok"] and claimed["code"] == "already"
        lost = _sale(gumroad, "7d")
        assert client.post("/api/billing/gumroad/claim", json={"sale_id": lost}).json()["code"] == "granted"


def test_price_label_prefers_dollars_over_cents_sign():
    assert gb.price_label(99, "usd", "99¢") == "$0.99"
    assert gb.price_label(399, "USD") == "$3.99"
    assert gb.price_label(None, "usd", "$1") == "$1"
    assert gb.price_label(500, "jpy", "¥500") == "¥500"


def test_plans_have_default_prices_without_gumroad(monkeypatch):
    monkeypatch.delenv("GUMROAD_ACCESS_TOKEN", raising=False)
    payload = billing._plans_payload()
    assert not payload["enabled"] and len(payload["plans"]) == 5
    assert all(p["price"].startswith("$") and not p["checkout"] for p in payload["plans"])


def test_ping_without_token_or_with_foreign_seller_does_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(gb, "sync_sale", lambda *a, **k: calls.append(a) or {"status": "x"})
    monkeypatch.delenv("GUMROAD_ACCESS_TOKEN", raising=False)
    with _client(monkeypatch) as client:
        assert client.post("/api/billing/gumroad", data={"sale_id": "A" * 20}).status_code == 200
    monkeypatch.setenv("GUMROAD_ACCESS_TOKEN", "t")
    monkeypatch.setenv("GUMROAD_SELLER_ID", "me")
    with _client(monkeypatch) as client:
        assert client.post("/api/billing/gumroad", data={"sale_id": "A" * 20, "seller_id": "someone"}).status_code == 200
    assert calls == []
