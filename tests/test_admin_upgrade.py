"""Control centre round of 2026-10-09: Telegram job owners, purchases, Info box moderation, weekly tries,
overview additions and the new system checks."""
import secrets
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_db
from smweb import (admin_billing, admin_control, admin_jobs, free_limits, gumroad_billing, health_checks, infobox,
                   telegram_billing)
from smweb.routers import admin as admin_router, infobox as infobox_router

SECRET = "admin-control-test-secret-123456"


@pytest.fixture()
def db(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "USING_POSTGRES", False)
    monkeypatch.setattr(auth_db, "DB", tmp_path / "users.db")
    monkeypatch.setattr(auth_db, "DATA", tmp_path)
    monkeypatch.setattr(auth_db, "_SCHEMA_READY", False)
    monkeypatch.setattr(admin_control, "ACCESS_FILE", tmp_path / "access_codes.json")
    monkeypatch.setenv("SECRET_KEY", "admin-test-session-secret-" * 3)
    monkeypatch.setenv("ADMIN_SECRET", SECRET)
    monkeypatch.setenv("APP_URL", "https://site.test")
    monkeypatch.setenv("BOT_ADMIN_SECRET", "bot-secret-for-tests-0123456789")
    monkeypatch.delenv("FREE_WEEKLY_USES", raising=False)
    monkeypatch.setattr(telegram_billing, "_tell_owner", lambda *a, **k: None)
    monkeypatch.setattr(telegram_billing, "_bell", lambda *a, **k: None)
    monkeypatch.setattr(gumroad_billing, "_tell_owner", lambda *a, **k: None)
    monkeypatch.setattr(gumroad_billing, "_bell", lambda *a, **k: None)
    admin_jobs._tg_accounts.clear()
    return tmp_path


def _user(email=None, **fields):
    email = email or f"u-{secrets.token_hex(4)}@example.com"
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


def _pro(uid):
    c = auth_db._conn()
    try:
        row = c.execute("SELECT is_pro, pro_until FROM users WHERE id=?", (uid,)).fetchone()
        return bool(row["is_pro"]), row["pro_until"]
    finally:
        c.close()


def _client():
    app = FastAPI()
    app.include_router(infobox_router.router)
    app.include_router(admin_router.router)
    client = TestClient(app)
    csrf = client.post("/api/admin/control/session", json={"secret": SECRET}).json()["csrf"]
    return client, {"Origin": "http://testserver", "X-Admin-CSRF": csrf}


# ---------------------------------------------------------------- jobs
def test_telegram_job_is_never_shown_as_a_site_account(db):
    job = {"kind": "process", "user_key": "tg:7123456789", "source": "telegram", "status": "done"}
    assert admin_jobs._key_user_id("tg:7123456789") is None
    assert admin_jobs._key_user_id("steam:12") == 12 and admin_jobs._key_user_id("12") == 12
    owner = admin_jobs._owner(job, admin_jobs._users_for([("a", job)]))
    assert owner["id"] is None and owner["name"] == "Telegram 7123456789"
    assert admin_jobs.job_source(job) == "telegram" and admin_jobs.job_tags(job) == ["Telegram-бот"]


def test_telegram_job_of_a_known_buyer_points_to_the_account(db):
    uid = _user(display_name="Saba")
    c = auth_db._conn()
    try:
        c.execute("INSERT INTO telegram_links (tg_id, user_id, updated_at) VALUES (?,?,?)", ("555000111", uid, time.time()))
        c.commit()
    finally:
        c.close()
    job = {"kind": "process", "user_key": "tg:555000111", "status": "done"}
    owner = admin_jobs._owner(job, admin_jobs._users_for([("a", job)]))
    assert owner["id"] == uid and "Telegram" in owner["name"] and owner["telegram"] == "555000111"


def test_jobs_list_filters_by_source_and_depth(db, monkeypatch):
    jobs = [
        ("a" * 24, {"kind": "process", "user_key": "tg:123456", "status": "done", "created": 1}),
        ("b" * 24, {"kind": "process", "user_key": "g:x", "status": "done", "created": 2,
                    "opts": {"modes": ["workshop"], "parallax": {"camera": {"motion": "orbit"}, "particles": {"kind": "snow"},
                                                                 "atmosphere": "fog", "breath": {"strength": 1}}}}),
        ("c" * 24, {"kind": "process", "user_key": "g:y", "status": "done", "created": 3}),
    ]
    monkeypatch.setattr(admin_jobs.rs, "job_list_all", lambda limit: jobs)
    monkeypatch.setattr(admin_jobs.rs, "queue_depths", lambda: {})
    assert [i["id"][0] for i in admin_jobs.list_jobs(source="telegram")["items"]] == ["a"]
    depth = admin_jobs.list_jobs(source="depth")["items"]
    assert [i["id"][0] for i in depth] == ["b"] and "Глубина 3D" in depth[0]["tags"]
    assert any(line == "Глубина 3D: облёт, снег, туман, дыхание" for line in depth[0]["settings"])
    assert len(admin_jobs.list_jobs(source="site")["items"]) == 2


# ---------------------------------------------------------------- weekly tries
def test_bonus_try_works_even_when_the_address_was_used_by_someone_else(db):
    first, second = _user(), _user()
    assert free_limits.consume("loop", first, "10.0.0.1")
    assert not free_limits.consume("loop", second, "10.0.0.1")       # same address: the owner's rule
    week = free_limits.give_bonus(second, ["loop"])
    assert week["features"]["loop"] == {"used": 0, "limit": 1, "bonus": 1, "left": 2}
    assert free_limits.left("loop", second, "10.0.0.1") == 1
    assert free_limits.consume("loop", second, "10.0.0.1")
    assert not free_limits.consume("loop", second, "10.0.0.1")
    assert free_limits.state(second, "10.0.0.1", False)["weekly"]["loop"]["left"] == 0


def test_bonus_for_all_tools_and_clear(db):
    uid = _user()
    week = free_limits.give_bonus(uid, list(free_limits.WEEKLY_FEATURES), 2)
    assert all(row["bonus"] == 2 for row in week["features"].values())
    assert all(row["bonus"] == 0 for row in free_limits.clear_bonus(uid)["features"].values())
    with pytest.raises(ValueError):
        free_limits.give_bonus(uid, ["nope"])


def test_account_deletion_drops_bonus_rows(db):
    uid = _user()
    free_limits.give_bonus(uid, ["bg"])
    auth_db.delete_account_data(uid)
    c = auth_db._conn()
    try:
        assert c.execute("SELECT COUNT(*) AS n FROM feature_uses WHERE subject=?", (f"+u:{uid}",)).fetchone()["n"] == 0
    finally:
        c.close()


def test_user_card_and_try_actions(db):
    uid = _user()
    detail = admin_control.user_detail(uid)
    assert set(detail["weekly"]["features"]) == set(free_limits.WEEKLY_FEATURES)
    assert detail["purchases"]["items"] == [] and detail["results"] == 0
    result = admin_control.user_action(uid, "grant_try", {"feature": "dna"})
    assert result["weekly"]["features"]["dna"]["bonus"] == 1
    result = admin_control.user_action(uid, "grant_try", {"feature": "all", "count": 3})
    assert result["weekly"]["features"]["bg"]["bonus"] == 3
    assert admin_control.user_action(uid, "clear_tries", {})["weekly"]["features"]["dna"]["bonus"] == 0
    with pytest.raises(LookupError):
        admin_control.user_action(999999, "grant_try", {})


# ---------------------------------------------------------------- purchases
def test_telegram_sale_waits_then_owner_attaches_and_refunds(db):
    buyer = _user("buyer@example.com")
    paid = telegram_billing.record_payment("pay-0000-1111", "70000001", "30d", tg_username="buyer", method="stars",
                                          amount="300", currency="XTR")
    assert paid["status"] == "claim"
    listing = admin_billing.purchases(30)
    item = listing["items"][0]
    assert item["status"] == "pending" and item["claim_url"].startswith("https://site.test/") and item["buyer"] == "@buyer"
    assert listing["pending_total"] == 1 and listing["revenue"] == {"⭐": 300.0}
    assert any(a["target"] == "purchases:pending" for a in admin_control.attention_items())

    with pytest.raises(LookupError):
        admin_billing.attach("telegram", "pay-0000-1111", "ghost@example.com")
    result = admin_billing.attach("telegram", "pay-0000-1111", "buyer@example.com")
    assert result["status"] == "granted" and result["user_id"] == buyer and _pro(buyer)[0]
    with pytest.raises(ValueError):
        admin_billing.attach("telegram", "pay-0000-1111", str(buyer))
    card = admin_billing.for_user(buyer)
    assert card["items"][0]["status"] == "granted" and card["telegram_links"][0]["tg_id"] == "70000001"
    assert card["pro_origin"] == "Покупка в Telegram-боте"

    assert admin_billing.refund_telegram("pay-0000-1111")["status"] == "revoked"
    assert not _pro(buyer)[0]
    after = admin_billing.purchases(30, status="revoked")
    assert after["items"][0]["status"] == "revoked" and after["revenue"] == {}


def test_gumroad_sale_attach_and_recheck_read_gumroad(db, monkeypatch):
    uid = _user("g@example.com")
    sale = {"id": "SALE_abc123", "product_permalink": "sm-pro-7d", "price": 199, "currency": "usd",
            "created_at": "2026-10-08T10:00:00Z"}
    monkeypatch.setattr(gumroad_billing, "fetch_sale", lambda sale_id: dict(sale))
    assert gumroad_billing.sync_sale("SALE_abc123")["status"] == "pending"
    assert admin_billing.purchases(3650, source="gumroad")["items"][0]["price"] == "$1.99"
    assert admin_billing.attach("gumroad", "SALE_abc123", str(uid))["status"] == "granted"
    assert _pro(uid)[0]
    assert admin_billing.recheck("SALE_abc123")["status"] == "already"
    sale["refunded"] = True
    assert admin_billing.recheck("SALE_abc123")["status"] == "revoked"
    assert not _pro(uid)[0]


def test_purchase_routes_need_csrf_and_report_errors(db):
    _user("route@example.com")
    telegram_billing.record_payment("pay-route-0001", "70000002", "7d", amount="1.99", currency="USD")
    client, headers = _client()
    listing = client.get("/api/admin/control/purchases?days=30&status=pending").json()
    assert [i["id"] for i in listing["items"]] == ["pay-route-0001"]
    url = "/api/admin/control/purchases/telegram/pay-route-0001/attach"
    assert client.post(url, json={"user": "route@example.com"}, headers={"Origin": "http://testserver"}).status_code == 403
    assert client.post(url, json={"user": "nobody"}, headers=headers).status_code == 404
    assert client.post(url, json={"user": "route@example.com"}, headers=headers).json()["status"] == "granted"
    assert client.post(url, json={"user": "route@example.com"}, headers=headers).status_code == 409
    refund = client.post("/api/admin/control/purchases/telegram/pay-route-0001/refund", json={}, headers=headers)
    assert refund.json()["status"] == "revoked"


# ---------------------------------------------------------------- Info box moderation
def test_infobox_moderation_lists_hides_and_restores(db):
    uid = _user(display_name="Author")
    first = infobox.create(uid, "Рамка", "[h1]Hi[/h1]\nline", "frames")
    infobox.create(uid, "Цитата", "text", "quotes")
    client, headers = _client()
    data = client.get("/api/admin/control/infobox").json()
    assert data["total"] == 2 and data["counts"] == {"published": 2, "hidden": 0} and data["new_week"] == 2
    assert data["items"][1]["author"] == "Author" and data["items"][1]["lines"] == 2
    assert client.delete(f"/api/admin/control/infobox/{first['id']}", headers=headers).json()["ok"] is True
    assert client.delete("/api/admin/control/infobox/missing", headers=headers).status_code == 404
    hidden = client.get("/api/admin/control/infobox?status=hidden").json()
    assert [i["id"] for i in hidden["items"]] == [first["id"]]
    assert client.get("/api/admin/control/infobox?status=all&q=TEXT").json()["total"] == 1
    assert client.post(f"/api/admin/control/infobox/{first['id']}/restore", json={}, headers=headers).json()["ok"]
    assert client.post(f"/api/admin/control/infobox/{first['id']}/restore", json={}, headers=headers).status_code == 404
    assert infobox.listing()[1] == 2


# ---------------------------------------------------------------- overview and system
def test_overview_reports_online_purchases_and_fresh_tools(db, monkeypatch):
    monkeypatch.setattr(admin_control.rs, "job_list_all", lambda limit: [
        ("a" * 24, {"kind": "process", "user_key": "tg:1234", "status": "error"}),
        ("b" * 24, {"kind": "gif_optimizer", "status": "done"})])
    fresh = {row["key"]: row for row in admin_control.fresh_activity()}
    assert fresh["telegram"]["value"] == 1 and "ошибок 1" in fresh["telegram"]["sub"]
    assert fresh["gifopt"]["value"] == 1 and fresh["depth"]["value"] == 0
    assert fresh["telegram"]["target"] == "jobs:all:telegram"
    assert admin_control._purchases_summary(30) == {"sales": 0, "revenue": {}, "pending": 0, "refunds": 0}
    assert isinstance(admin_control._online(), int)


def test_new_system_checks(monkeypatch):
    make = admin_control._component
    from smweb import depth, gif_optimizer, remove_bg_client
    monkeypatch.setattr(gif_optimizer, "find_gifsicle", lambda: None)
    assert health_checks._gifsicle(make)["state"] == "warn"
    monkeypatch.setattr(depth, "available", lambda: False)
    assert health_checks._depth(make)["state"] == "warn"
    monkeypatch.setattr(remove_bg_client, "providers", lambda: ["modal", "iloveapi"])
    monkeypatch.setattr(remove_bg_client, "monthly_cap", lambda name: 100)
    usage = {"modal": 10, "iloveapi": 10}
    monkeypatch.setattr(remove_bg_client, "budget_used", lambda name: usage[name])
    assert health_checks._bg_budget(make)["state"] == "ok"
    usage["iloveapi"] = 90
    assert health_checks._bg_budget(make)["state"] == "warn"
    usage.update(modal=100, iloveapi=120)
    check = health_checks._bg_budget(make)
    assert check["state"] == "down" and "Modal: 100 из 100" in check["technical"]
