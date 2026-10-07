"""Races and availability fixes from the 2026-10-07 audit."""
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

import auth_db
import redis_store as rs
import steam_catalog
from smweb import core
from smweb.middleware import GZipMiddleware, RateLimitMiddleware, _GZipResponder
from smweb.routers import system


@pytest.fixture()
def db(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "USING_POSTGRES", False)
    monkeypatch.setattr(auth_db, "DB", tmp_path / "users.db")
    monkeypatch.setattr(auth_db, "DATA", tmp_path)
    monkeypatch.setattr(auth_db, "_SCHEMA_READY", False)
    return tmp_path


def _user(email):
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        return int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
    finally:
        c.close()


def _row(uid):
    c = auth_db._conn()
    try:
        return dict(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    finally:
        c.close()


# ---------------------------------------------------------------- C2: one code, one account
def test_claim_code_has_exactly_one_winner_under_concurrency(db):
    users = [_user(f"c{i}@example.com") for i in range(8)]
    wins, barrier = [], threading.Barrier(len(users))

    def claim(uid):
        barrier.wait()
        if auth_db.claim_code("SM-TRIAL-RACE", uid):
            wins.append(uid)

    threads = [threading.Thread(target=claim, args=(uid,)) for uid in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(wins) == 1 and auth_db.code_used("SM-TRIAL-RACE") == wins[0]
    assert not auth_db.claim_code("SM-TRIAL-RACE", wins[0]), "a used code is not granted twice, even to its owner"


def _unlock_client(monkeypatch, codes, who):
    monkeypatch.setattr(system, "_load_codes", lambda: dict(codes))
    monkeypatch.setattr(system, "_load_used", lambda: set())
    monkeypatch.setattr(system, "_save_used", lambda used: None)
    monkeypatch.setattr(system, "_auth_user", lambda request: _row(who["uid"]))
    app = FastAPI()
    app.include_router(system.router)
    return TestClient(app)


def test_unlock_codes_bind_once_and_respect_existing_pro(db, monkeypatch):
    codes = {"SM-TRIAL-A": {"type": "trial", "hours": 2}, "SM-TRIAL-B": {"type": "trial", "hours": 2},
             "SM-WEB-FOREVER": {"type": "unlimited", "label": "Pro"}}
    first, second = _user("first@example.com"), _user("second@example.com")
    who = {"uid": first}
    client = _unlock_client(monkeypatch, codes, who)

    assert client.post("/api/unlock", json={"code": "SM-TRIAL-A"}).json()["ok"] is True
    assert _row(first)["is_pro"] == 1 and _row(first)["pro_until"] > time.time()
    who["uid"] = second
    taken = client.post("/api/unlock", json={"code": "SM-TRIAL-A"})
    assert taken.status_code == 400 and _row(second)["is_pro"] == 0

    # A bought day: a shorter trial code is refused WITHOUT being burned...
    c = auth_db._conn()
    c.execute("UPDATE users SET is_pro=1, pro_until=? WHERE id=?", (time.time() + 86400, second))
    c.commit()
    c.close()
    longer = client.post("/api/unlock", json={"code": "SM-TRIAL-B"}).json()
    assert longer["ok"] is True and auth_db.code_used("SM-TRIAL-B") is None
    # ...and a permanent key upgrades it (it used to answer "Already Pro").
    forever = client.post("/api/unlock", json={"code": "SM-WEB-FOREVER"}).json()
    assert forever["ok"] is True and _row(second)["pro_until"] is None and _row(second)["is_pro"] == 1
    assert "Already Pro" in client.post("/api/unlock", json={"code": "SM-TRIAL-B"}).json()["msg"]


def test_an_ended_trial_no_longer_blocks_a_new_code(db, monkeypatch):
    uid = _user("ended@example.com")
    c = auth_db._conn()
    c.execute("UPDATE users SET is_pro=1, pro_until=? WHERE id=?", (time.time() - 60, uid))
    c.commit()
    c.close()
    client = _unlock_client(monkeypatch, {"SM-TRIAL-NEW": {"type": "trial", "hours": 2}}, {"uid": uid})
    answer = client.post("/api/unlock", json={"code": "SM-TRIAL-NEW"}).json()
    assert answer["ok"] is True and "Already" not in answer["msg"]
    assert _row(uid)["pro_until"] > time.time()


# ---------------------------------------------------------------- H2: expiry vs a fresh purchase
def test_expiry_check_does_not_wipe_a_purchase_that_just_landed(db):
    uid = _user("renew@example.com")
    c = auth_db._conn()
    c.execute("UPDATE users SET is_pro=1, pro_until=? WHERE id=?", (time.time() - 5, uid))
    c.commit()
    stale = _row(uid)  # a request read the user while the old day had just ended
    c.execute("UPDATE users SET is_pro=1, pro_until=? WHERE id=?", (time.time() + 86400, uid))  # bought now
    c.commit()
    c.close()
    assert auth_db.effective_pro(stale) is False
    fresh = _row(uid)
    assert fresh["is_pro"] == 1 and fresh["pro_until"] > time.time(), "the stale copy wiped the new purchase"
    # A really expired row is still cleared.
    c = auth_db._conn()
    c.execute("UPDATE users SET pro_until=? WHERE id=?", (time.time() - 5, uid))
    c.commit()
    c.close()
    assert auth_db.effective_pro(_row(uid)) is False and _row(uid)["is_pro"] == 0


# ---------------------------------------------------------------- H1: live stream not buffered
def test_event_stream_is_never_gzip_buffered():
    responder = _GZipResponder(None, GZipMiddleware(None))
    start = lambda ctype: {"type": "http.response.start", "status": 200, "headers": [(b"content-type", ctype.encode())]}
    assert responder._compressible(start("text/event-stream; charset=utf-8")) is False
    assert responder._compressible(start("text/html; charset=utf-8")) is True


# ---------------------------------------------------------------- H3: anonymous Steam profile
def test_anonymous_profile_get_is_limited_and_never_paid(monkeypatch):
    assert any(prefix == "/api/steam/profile" for prefix, _, _ in RateLimitMiddleware.GET_RULES)
    calls = []

    def fake_routes(progress):
        return [("server", lambda c: calls.append("server") or ""), ("browser", lambda c: calls.append("browser") or "<html>")]

    monkeypatch.setattr(steam_catalog, "_profile_routes", fake_routes)
    monkeypatch.setattr(steam_catalog.steam_profile_guard, "route_wait", lambda *a, **k: 0)
    monkeypatch.setattr(steam_catalog.steam_profile_guard, "route_pause", lambda *a, **k: None)
    steam_catalog._page_via_routes("https://steamcommunity.com/id/x", None, "unused", paid=False)
    assert calls == ["server"], "the paid browser route ran for an anonymous request"


# ---------------------------------------------------------------- H4: atomic start
def _request(ip="10.1.2.3"):
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": (ip, 1234)})


def test_start_guard_serialises_and_reserves_atomically(monkeypatch):
    monkeypatch.setattr(rs, "_r", lambda: None)
    monkeypatch.setattr(core, "_legacy_usage_add", lambda ip, n: None)
    ip = "10.9.%d.%d" % (int(time.time()) % 250, threading.get_ident() % 250)
    quota = {"pro": False, "used": 0, "limit": 5}
    first, second = core.StartGuard(_request(ip), quota, "owner-x"), core.StartGuard(_request(ip), quota, "owner-x")
    assert first.lock() and not second.lock(), "two starts of one owner ran at once"
    assert first.reserve(4) and rs.quota_get(ip, core._day()) == 4
    first.settle(3)                                   # one file turned out empty
    first.release()
    assert rs.quota_get(ip, core._day()) == 3
    assert second.lock()
    assert not second.reserve(3), "8 of 5 files were let through"
    assert rs.quota_get(ip, core._day()) == 3, "a refused reservation must be given back"
    assert second.reserve(2)
    second.release()                                  # never settled: the start failed
    assert rs.quota_get(ip, core._day()) == 3
    pro = core.StartGuard(_request(ip), {"pro": True}, "owner-pro")
    assert pro.reserve(50) and rs.quota_get(ip, core._day()) == 3


# ---------------------------------------------------------------- quick wins
def test_expired_sessions_are_pruned(db, monkeypatch):
    uid = _user("sessions@example.com")
    ok, _, token = auth_db.login("sessions@example.com", "a-long-password-1")
    assert ok and token
    c = auth_db._conn()
    c.execute("INSERT INTO sessions(token, user_id, created_at) VALUES (?,?,?)", ("sha256:old", uid, time.time() - 400 * 86400))
    c.commit()
    c.close()
    monkeypatch.setattr(auth_db, "_last_session_prune", 0.0)
    assert auth_db.prune_sessions() == 1
    assert auth_db.user_by_token(token) is not None
    assert auth_db.prune_sessions() == 0, "throttled to once per interval"
