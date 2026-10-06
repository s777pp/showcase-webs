"""Pro bought in the Telegram bot: site orders, bot payments, claim links, refunds (2026-10-06)."""
import secrets
import time

import pytest

import auth_db
from smweb import gumroad_billing as gb
from smweb import telegram_billing as tb

SECRET = "bot-secret-for-tests-0123456789"
DAY = 86400


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setenv("BOT_ADMIN_SECRET", SECRET)
    monkeypatch.setenv("APP_URL", "https://site.test")
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "ShopTestBot")
    monkeypatch.delenv("TELEGRAM_SHOP_BOT_USERNAME", raising=False)
    monkeypatch.setattr(tb, "_tell_owner", lambda *a, **k: None)
    monkeypatch.setattr(tb, "_bell", lambda *a, **k: None)


def _user(**fields):
    email = f"tg-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        uid = int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
        for key, value in fields.items():
            c.execute(f"UPDATE users SET {key}=? WHERE id=?", (value, uid))
        c.commit()
        return uid
    finally:
        c.close()


def _tg():
    return str(10_000_000 + secrets.randbelow(900_000_000))


def _pid():
    return secrets.token_hex(12)


def _days_left(uid):
    state = gb.pro_state(uid)
    return round((state["until"] - time.time()) / DAY, 2) if state["pro"] and state["until"] else None


def _pay(tg, plan, **extra):
    extra.setdefault("method", "stars")
    return tb.record_payment(extra.pop("payment_id", None) or _pid(), tg, plan, **extra)


# ---------------------------------------------------------------- the rules (no HTTP)
def test_purchase_started_on_the_site_goes_to_that_account_and_is_remembered():
    uid, tg = _user(display_name="Buyer"), _tg()
    order = tb.create_order(uid, "30d")
    assert order["url"] == f"https://t.me/ShopTestBot?start=buy_{order['token']}" and len(order["url"].split("start=")[1]) <= 64
    assert tb.order_info(order["token"]) == {"plan": "30d", "account": "Buyer", "pro": {"pro": False, "until": None, "lifetime": False}}

    result = _pay(tg, "30d", order_token=order["token"], amount="300", currency="XTR")
    assert result["status"] == "granted" and result["account"] == "Buyer" and result["pro"]["pro"]
    assert _days_left(uid) == 30
    assert tb.order_info(order["token"]) is None, "an order pays once"
    assert tb.account_info(tg)["linked"] and tb.account_info(tg)["account"] == "Buyer"

    # The next purchase comes straight from the bot: no token, same account, days add up.
    assert _pay(tg, "7d")["status"] == "granted"
    assert _days_left(uid) == 37


def test_plan_changed_in_the_bot_still_lands_on_the_account_from_the_link():
    uid, tg = _user(), _tg()
    order = tb.create_order(uid, "7d")
    assert _pay(tg, "90d", order_token=order["token"])["status"] == "granted"
    assert _days_left(uid) == 90


def test_unknown_buyer_gets_a_claim_link_that_works_once():
    tg, payment = _tg(), _pid()
    first = _pay(tg, "7d", payment_id=payment)
    assert first["status"] == "claim" and first["claim_url"].startswith("https://site.test/billing/telegram/claim?tg=")
    token = first["claim_url"].split("tg=")[1]
    assert tb.valid_token(token)
    assert _pay(tg, "7d", payment_id=payment) == first, "the bot may ask again: same link, nothing granted"

    owner, other = _user(), _user()
    claimed = tb.claim(token, owner)
    assert claimed["status"] == "granted" and _days_left(owner) == 7
    assert tb.claim(token, owner)["status"] == "already" and _days_left(owner) == 7
    assert tb.claim(token, other)["status"] == "taken" and _days_left(other) is None
    assert _pay(tg, "7d", payment_id=payment)["status"] == "already"
    # The account is known from now on.
    assert _pay(tg, "1d")["status"] == "granted" and _days_left(owner) == 8
    assert tb.claim("x" * 24, owner)["status"] == "unknown" and tb.claim("bad", owner)["status"] == "unknown"


def test_account_that_signs_in_with_telegram_is_found_by_its_id():
    tg = _tg()
    uid = _user(telegram_id=tg)
    assert tb.account_info(tg)["linked"]
    assert _pay(tg, "30d")["status"] == "granted" and _days_left(uid) == 30


def test_buyer_can_send_the_purchase_to_another_account():
    tg = _tg()
    mine, friend = _user(telegram_id=tg), _user()
    gift = _pay(tg, "7d", claim_only=True)
    assert gift["status"] == "claim" and _days_left(mine) is None
    assert tb.claim(gift["claim_url"].split("tg=")[1], friend)["status"] == "granted"
    assert _days_left(friend) == 7 and _days_left(mine) is None


def test_site_order_wins_over_the_remembered_account():
    tg = _tg()
    first, second = _user(), _user()
    assert _pay(tg, "7d", order_token=tb.create_order(first, "7d")["token"])["status"] == "granted"
    assert _pay(tg, "30d", order_token=tb.create_order(second, "30d")["token"])["status"] == "granted"
    assert (_days_left(first), _days_left(second)) == (7, 30)


def test_one_payment_grants_once_and_an_order_serves_one_payment():
    uid, tg, payment = _user(), _tg(), _pid()
    token = tb.create_order(uid, "30d")["token"]
    for _ in range(3):
        result = _pay(tg, "30d", payment_id=payment, order_token=token)
    assert result["status"] == "already" and _days_left(uid) == 30
    # Somebody else replays the link with their own payment: it is their purchase, not this account's.
    stranger = _pay(_tg(), "30d", order_token=token)
    assert stranger["status"] == "claim" and _days_left(uid) == 30


def test_forever_is_not_shortened_by_a_later_term_purchase():
    uid, tg = _user(), _tg()
    token = tb.create_order(uid, "unlimited")["token"]
    assert _pay(tg, "unlimited", order_token=token)["pro"] == {"pro": True, "until": None, "lifetime": True}
    assert _pay(tg, "7d")["pro"]["lifetime"] is True
    c = auth_db._conn()
    try:
        assert str(c.execute("SELECT pro_code FROM users WHERE id=?", (uid,)).fetchone()["pro_code"]).startswith("TGS-")
    finally:
        c.close()


def test_refund_takes_the_days_back_and_closes_the_claim_link():
    uid, tg = _user(), _tg()
    token = tb.create_order(uid, "7d")["token"]
    first, second = _pid(), _pid()
    _pay(tg, "7d", payment_id=first, order_token=token)
    _pay(tg, "30d", payment_id=second)
    assert _days_left(uid) == 37
    assert tb.revoke(second)["status"] == "revoked" and _days_left(uid) == 7
    assert tb.revoke(second)["status"] == "already" and _days_left(uid) == 7
    assert _pay(tg, "30d", payment_id=second)["status"] == "revoked" and _days_left(uid) == 7
    assert tb.revoke(first)["status"] == "revoked" and gb.pro_state(uid)["pro"] is False

    waiting = _pay(_tg(), "7d", payment_id=(pending := _pid()))
    assert tb.revoke(pending)["status"] == "refunded"
    assert tb.claim(waiting["claim_url"].split("tg=")[1], _user())["status"] == "refunded"
    assert tb.revoke("nothing-like-this")["status"] == "unknown"


def test_refund_of_forever_switches_pro_off():
    uid, tg, payment = _user(), _tg(), _pid()
    _pay(tg, "unlimited", payment_id=payment, order_token=tb.create_order(uid, "unlimited")["token"])
    assert tb.revoke(payment)["status"] == "revoked"
    assert gb.pro_state(uid) == {"pro": False, "until": None, "lifetime": False}


def test_bad_input_is_refused():
    tg = _tg()
    for args in ((_pid(), tg, "2d"), ("short", tg, "7d"), (_pid(), "not-a-number", "7d"), (_pid(), "", "7d")):
        with pytest.raises(ValueError):
            tb.record_payment(*args)
    with pytest.raises(ValueError):
        tb.create_order(_user(), "2d")
    assert tb.order_info("") is None and tb.order_info("z" * 24) is None
    assert tb.account_info("12") == {"linked": False, "account": "", "pro": {"pro": False, "until": None, "lifetime": False}}


def test_old_site_order_is_not_usable(monkeypatch):
    uid, tg = _user(), _tg()
    token = tb.create_order(uid, "7d")["token"]
    c = auth_db._conn()
    try:
        c.execute("UPDATE telegram_orders SET created_at=? WHERE token=?", (time.time() - tb.ORDER_TTL - 60, token))
        c.commit()
    finally:
        c.close()
    assert tb.order_info(token) is None
    assert _pay(tg, "7d", order_token=token)["status"] == "claim"


def test_deleting_the_account_keeps_the_books_but_hands_nothing_out_again():
    uid, tg, payment = _user(), _tg(), _pid()
    token = tb.create_order(uid, "30d")["token"]
    _pay(tg, "30d", payment_id=payment, order_token=token, amount="300", currency="XTR")
    spare = tb.create_order(uid, "7d")["token"]
    exported = auth_db.account_export_data(uid)["telegram_purchases"]
    assert [(row["plan"], row["status"], row["amount"]) for row in exported] == [("30d", "granted", "300")]
    assert "tg_id" not in exported[0] and "claim_token" not in exported[0]

    auth_db.delete_account_data(uid)
    assert tb.account_info(tg)["linked"] is False and tb.order_info(spare) is None
    c = auth_db._conn()
    try:
        row = dict(c.execute("SELECT user_id, status, claim_token FROM telegram_sales WHERE payment_id=?", (payment,)).fetchone())
    finally:
        c.close()
    assert row == {"user_id": None, "status": "granted", "claim_token": None}
    # The bot repeats its report: the Pro was delivered once and is not offered to anybody else.
    assert _pay(tg, "30d", payment_id=payment, order_token=token) == {"status": "already", "plan": "30d", "account": "", "pro": None}


def test_account_name_never_shows_a_full_email():
    plain = _user()
    c = auth_db._conn()
    try:
        email = c.execute("SELECT email FROM users WHERE id=?", (plain,)).fetchone()["email"]
    finally:
        c.close()
    label = tb.account_label(plain)
    assert label == f"{email[:2]}***@example.com" and email not in label
    assert tb.account_label(_user(display_name="  Nick  ")) == "Nick"
    hidden = _user(email=f"steam_{secrets.token_hex(3)}@users.local")
    assert tb.account_label(hidden) == f"#{hidden}"


def test_purchases_and_price_labels_for_the_account_page():
    uid, tg = _user(), _tg()
    _pay(tg, "30d", order_token=tb.create_order(uid, "30d")["token"], amount="300", currency="XTR")
    _pay(tg, "7d", method="crypto", amount="1.99", currency="USDT")
    rows = tb.purchases_for(uid)
    assert sorted((row["plan"], row["method"], row["status"]) for row in rows) == [("30d", "stars", "granted"), ("7d", "crypto", "granted")]
    assert tb.price_label("300", "XTR") == "300 ⭐" and tb.price_label("1.99", "usdt") == "1.99 USDT"
    assert tb.price_label("3.99", "USD") == "$3.99" and tb.price_label("", "XTR") == ""


def test_bot_username_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("TELEGRAM_SHOP_BOT_USERNAME", "@OtherShopBot")
    assert tb.bot_username() == "OtherShopBot"
    monkeypatch.setenv("TELEGRAM_SHOP_BOT_USERNAME", "bad name!")
    assert tb.bot_username() == "ShopTestBot"
    monkeypatch.delenv("BOT_ADMIN_SECRET")
    assert tb.configured() is False


# ---------------------------------------------------------------- HTTP: what the bot calls
def _bot_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from smweb.routers import bot_admin
    app = FastAPI()
    app.include_router(bot_admin.router)
    return TestClient(app)


def test_bot_api_is_closed_without_the_shared_secret(monkeypatch):
    with _bot_client() as client:
        assert client.get("/api/bot-admin/pro/account", params={"tg_id": _tg()}).status_code == 403
        assert client.post("/api/bot-admin/pro/grant", json={}, headers={"X-Bot-Admin-Secret": "wrong"}).status_code == 403
        monkeypatch.delenv("BOT_ADMIN_SECRET")
        assert client.post("/api/bot-admin/pro/grant", json={}, headers={"X-Bot-Admin-Secret": SECRET}).status_code == 404


def test_bot_reports_a_payment_and_later_a_refund():
    uid, tg, payment = _user(display_name="Web"), _tg(), _pid()
    token = tb.create_order(uid, "30d")["token"]
    headers = {"X-Bot-Admin-Secret": SECRET}
    with _bot_client() as client:
        order = client.get("/api/bot-admin/pro/order", params={"token": token}, headers=headers).json()
        assert order["ok"] and order["plan"] == "30d" and order["account"] == "Web"
        assert client.get("/api/bot-admin/pro/order", params={"token": "z" * 24}, headers=headers).status_code == 404

        body = {"payment_id": payment, "tg_id": int(tg), "tg_username": "@buyer", "plan": "30d", "method": "stars",
                "amount": 300, "currency": "XTR", "order_token": token}
        granted = client.post("/api/bot-admin/pro/grant", json=body, headers=headers).json()
        assert granted["ok"] and granted["status"] == "granted" and granted["account"] == "Web" and "user_id" not in granted
        assert client.post("/api/bot-admin/pro/grant", json=body, headers=headers).json()["status"] == "already"
        assert _days_left(uid) == 30

        account = client.get("/api/bot-admin/pro/account", params={"tg_id": tg}, headers=headers).json()
        assert account["linked"] and account["account"] == "Web" and account["pro"]["pro"]
        assert client.post("/api/bot-admin/pro/grant", json={**body, "plan": "2d", "payment_id": _pid()},
                           headers=headers).status_code == 400

        assert client.post("/api/bot-admin/pro/revoke", json={"payment_id": payment}, headers=headers).json()["status"] == "revoked"
    assert gb.pro_state(uid)["pro"] is False


# ---------------------------------------------------------------- HTTP: what the site pages call
def _site_client(monkeypatch, user):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from smweb.routers import billing
    monkeypatch.setattr(billing, "_auth_user", lambda request: user)
    monkeypatch.setattr(gb, "products", lambda force=False: {})
    app = FastAPI()
    app.include_router(billing.router)
    return TestClient(app)


def test_site_starts_a_bot_purchase_only_for_a_signed_in_account(monkeypatch):
    uid = _user()
    with _site_client(monkeypatch, None) as client:
        assert client.post("/api/billing/telegram/order", json={"plan": "7d"}).status_code == 401
    with _site_client(monkeypatch, {"id": uid}) as client:
        assert client.get("/api/billing/plans").json()["telegram"] is True
        assert client.post("/api/billing/telegram/order", json={"plan": "2d"}).json()["code"] == "plan"
        url = client.post("/api/billing/telegram/order", json={"plan": "7d"}).json()["url"]
        assert url.startswith("https://t.me/ShopTestBot?start=buy_")
        assert tb.order_info(url.split("start=buy_")[1])["plan"] == "7d"

        _pay(_tg(), "unlimited", order_token=tb.create_order(uid, "unlimited")["token"])
        assert client.post("/api/billing/telegram/order", json={"plan": "7d"}).status_code == 409

        monkeypatch.delenv("BOT_ADMIN_SECRET")
        assert client.get("/api/billing/plans").json()["telegram"] is False
        assert client.post("/api/billing/telegram/order", json={"plan": "7d"}).status_code == 503


def test_claim_page_api_binds_the_purchase_to_the_signed_in_account(monkeypatch):
    owner, other = _user(), _user()
    token = _pay(_tg(), "7d")["claim_url"].split("tg=")[1]
    with _site_client(monkeypatch, None) as client:
        assert client.post("/api/billing/telegram/claim", json={"token": token}).status_code == 401
    with _site_client(monkeypatch, {"id": owner}) as client:
        assert client.post("/api/billing/telegram/claim", json={"token": "nope"}).status_code == 400
        assert client.post("/api/billing/telegram/claim", json={"token": "y" * 24}).status_code == 404
        done = client.post("/api/billing/telegram/claim", json={"token": token}).json()
        assert done["ok"] and done["code"] == "granted" and done["plan"] == "7d" and done["pro"]["pro"]
        assert client.post("/api/billing/telegram/claim", json={"token": token}).json()["code"] == "already"
        redirect = client.get(f"/billing/telegram/claim?tg={token}", follow_redirects=False)
        assert redirect.status_code == 307 and redirect.headers["location"].endswith(f"/billing/claim?tg={token}")
    with _site_client(monkeypatch, {"id": other}) as client:
        taken = client.post("/api/billing/telegram/claim", json={"token": token})
        assert taken.status_code == 409 and taken.json()["code"] == "taken"
    assert _days_left(owner) == 7 and _days_left(other) is None


def test_new_routes_are_rate_limited_and_the_account_page_lists_bot_purchases(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from smweb.middleware import RateLimitMiddleware
    from smweb.routers import account
    for path in ("/api/billing/telegram/order", "/api/billing/telegram/claim"):
        assert next(prefix for prefix, _limit, _window in RateLimitMiddleware.RULES if path.startswith(prefix)) == path

    uid = _user()
    _pay(_tg(), "30d", order_token=tb.create_order(uid, "30d")["token"], amount="300", currency="XTR")
    monkeypatch.setattr(account, "_auth_user", lambda request: {"id": uid})
    monkeypatch.setattr(account, "quota_state", lambda request: {"used": 0, "limit": 5})
    app = FastAPI()
    app.include_router(account.router)
    with TestClient(app) as client:
        purchases = client.get("/api/account/overview").json()["purchases"]
    assert [(p["source"], p["plan"], p["status"], p["price"]) for p in purchases] == [("telegram", "30d", "granted", "300 ⭐")]
