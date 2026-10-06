"""Site account page: /api/account/overview and the page route (2026-10-06)."""
import secrets
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_db
from smweb.routers import account


def _user(**fields):
    email = f"acc-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        uid = int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
        for key, value in fields.items():
            c.execute(f"UPDATE users SET {key}=? WHERE id=?", (value, uid))
        c.commit()
        row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(row)
    finally:
        c.close()


def _client(monkeypatch, user):
    monkeypatch.setattr(account, "_auth_user", lambda request: user)
    monkeypatch.setattr(account, "quota_state", lambda request: {"used": 2, "limit": 5})
    app = FastAPI()
    app.include_router(account.router)
    return TestClient(app)


def test_guest_gets_401(monkeypatch):
    with _client(monkeypatch, None) as client:
        assert client.get("/api/account/overview").status_code == 401


def test_overview_shows_plan_logins_and_purchases_without_secrets(monkeypatch):
    steam = str(secrets.randbelow(10 ** 12))
    user = _user(is_pro=1, pro_until=time.time() + 5 * 86400 + 60, pro_code="GRS-ABC", steam_id=steam, display_name="Nick")
    secret_code = "SM-SECRET-" + secrets.token_hex(6).upper()
    c = auth_db._conn()
    try:
        now = time.time()
        c.execute("INSERT INTO gumroad_sales (sale_id, user_id, plan, days, status, price_cents, currency, updated_at, sale_created) "
                  "VALUES (?,?,?,?,?,?,?,?,?)", (secrets.token_hex(8), user["id"], "30d", 30, "granted", 399, "usd", now, now))
        c.execute("INSERT INTO used_codes (code, user_id, used_at) VALUES (?,?,?)", (secret_code, user["id"], now - 60))
        c.commit()
    finally:
        c.close()
    with _client(monkeypatch, user) as client:
        data = client.get("/api/account/overview").json()
    assert data["ok"] and data["user"]["name"] == "Nick" and data["user"]["steam"] == steam
    assert data["user"]["email"] == user["email"] and data["user"]["password"] is True
    assert data["plan"]["pro"] and not data["plan"]["lifetime"] and not data["plan"]["trial"] and data["plan"]["days_left"] == 5
    assert data["quota"] == {"used": 2, "limit": 5}
    kinds = [(p["source"], p["plan"], p["price"]) for p in data["purchases"]]
    assert ("gumroad", "30d", "$3.99") in kinds and ("key", None, "") in kinds
    assert secret_code not in str(data), "entered keys are never sent back"


def test_oauth_only_account_has_no_email_or_password(monkeypatch):
    user = _user(email=f"steam_{secrets.token_hex(3)}@users.local", steam_id=str(secrets.randbelow(10 ** 12)))
    with _client(monkeypatch, user) as client:
        data = client.get("/api/account/overview").json()
    assert data["user"]["email"] == "" and data["user"]["password"] is False


def test_trial_code_is_labelled_as_trial(monkeypatch):
    user = _user(is_pro=1, pro_until=time.time() + 3600, pro_code="SM-TRIAL-XYZ")
    with _client(monkeypatch, user) as client:
        plan = client.get("/api/account/overview").json()["plan"]
    assert plan["trial"] and plan["days_left"] == 0
