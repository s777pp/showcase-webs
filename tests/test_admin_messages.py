"""Owner messages to users (smweb/admin_messages.py, 2026-10-07)."""
import json
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_db
from smweb import admin_control, admin_messages, notify
from smweb.routers import admin as admin_router, gallery as gallery_router

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
    return tmp_path


def _user(email, *, pro=False, nick=None, steam=None):
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        uid = int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
        if pro:
            c.execute("UPDATE users SET is_pro=1, pro_until=? WHERE id=?", (time.time() + 86400, uid))
        if nick:
            c.execute("UPDATE users SET profile_username=? WHERE id=?", (nick, uid))
        if steam:
            c.execute("UPDATE users SET steam_id=? WHERE id=?", (steam, uid))
        c.commit()
    finally:
        c.close()
    return uid


def _rows(uid):
    c = auth_db._conn()
    try:
        return [dict(r) for r in c.execute("SELECT * FROM notifications WHERE user_id=? AND kind='admin_message'", (uid,)).fetchall()]
    finally:
        c.close()


def test_targets_resolve_by_id_email_nick_and_steam(db):
    a = _user("a@example.com", nick="Saba")
    b = _user("b@example.com", steam="76561198000000001")
    ids, missing = admin_messages.resolve_targets(f"{a}, B@example.com\n@saba 76561198000000001 nobody")
    assert ids == [a, b] and missing == ["nobody"]


def test_send_to_people_stores_both_languages_and_pops_up_once(db):
    uid = _user("one@example.com")
    result = admin_messages.send({"audience": "users", "targets": str(uid), "title_ru": "Привет",
                                  "body_ru": "Строка 1\n\n\n\nСтрока 2", "title_en": "Hi", "body_en": "Text", "link": "/app#loop"})
    assert result["recipients"] == 1
    rows = _rows(uid)
    assert len(rows) == 1 and rows[0]["body"] == "Строка 1\n\nСтрока 2" and rows[0]["link"] == "/app#loop"
    meta = json.loads(rows[0]["meta_json"])
    assert meta["popup"] is True and meta["en"] == {"title": "Hi", "body": "Text"} and meta["msg"] == result["id"]
    popup = admin_messages.popup_for(uid)
    assert popup and popup["title"] == "Привет"
    auth_db.notifications_mark_read(uid, [popup["id"]])
    assert admin_messages.popup_for(uid) is None


def test_bell_only_message_never_pops_up(db):
    uid = _user("quiet@example.com")
    admin_messages.send({"audience": "users", "targets": str(uid), "title_ru": "Тихо", "popup": False})
    assert len(_rows(uid)) == 1 and admin_messages.popup_for(uid) is None


def test_broadcast_audiences_and_recall(db):
    free_id = _user("free@example.com")
    pro_id = _user("pro@example.com", pro=True)
    assert admin_messages.count("all")["count"] == 2
    assert admin_messages.count("pro")["count"] == 1 and admin_messages.count("free")["count"] == 1
    sent = admin_messages.send({"audience": "pro", "title_ru": "Для Pro"})
    assert sent["recipients"] == 1 and len(_rows(pro_id)) == 1 and not _rows(free_id)
    everyone = admin_messages.send({"audience": "all", "title_ru": "Всем"})
    assert everyone["recipients"] == 2
    history = {m["id"]: m for m in admin_messages.history()}
    assert history[everyone["id"]]["delivered"] == 2 and history[everyone["id"]]["read"] == 0
    assert admin_messages.recall(everyone["id"]) == 2
    assert len(_rows(free_id)) == 0 and len(_rows(pro_id)) == 1
    assert admin_messages.history()[0]["recalled_at"]


def test_validation(db):
    _user("v@example.com")
    with pytest.raises(ValueError):
        admin_messages.send({"audience": "all", "title_ru": ""})
    with pytest.raises(ValueError):
        admin_messages.send({"audience": "all", "title_ru": "x", "link": "javascript:alert(1)"})
    with pytest.raises(ValueError):
        admin_messages.send({"audience": "all", "title_ru": "x", "link": "//evil.example"})
    with pytest.raises(ValueError):
        admin_messages.send({"audience": "users", "targets": "nobody", "title_ru": "x"})
    with pytest.raises(ValueError):
        admin_messages.send({"audience": "all", "title_ru": "x", "body_en": "only text"})
    assert admin_messages.clean_link("https://showcasemaker.com/ru/news") == "https://showcasemaker.com/ru/news"


def test_messages_outlive_the_weekly_cleanup(db):
    uid = _user("old@example.com")
    admin_messages.send({"audience": "users", "targets": str(uid), "title_ru": "Старое"})
    notify.add(uid, "job_done", title="x")
    c = auth_db._conn()
    try:
        c.execute("UPDATE notifications SET created_at=? WHERE user_id=?", (time.time() - 10 * 86400, uid))
        c.commit()
    finally:
        c.close()
    notify._cleanup(time.time())
    kinds = [r["kind"] for r in auth_db.notifications_list(uid)]
    assert kinds == ["admin_message"]


def test_admin_routes_and_unread_popup(db, monkeypatch):
    uid = _user("route@example.com")
    app = FastAPI()
    app.include_router(admin_router.router)
    client = TestClient(app)
    assert client.get("/api/admin/control/messages").status_code == 403
    csrf = client.post("/api/admin/control/session", json={"secret": SECRET}).json()["csrf"]
    headers = {"Origin": "http://testserver", "X-Admin-CSRF": csrf}
    assert client.post("/api/admin/control/messages", json={"audience": "all", "title_ru": "x"},
                       headers={"Origin": "http://testserver"}).status_code == 403
    counted = client.post("/api/admin/control/messages/count", json={"audience": "users", "targets": f"{uid}, ghost"}, headers=headers).json()
    assert counted["count"] == 1 and counted["missing"] == ["ghost"]
    bad = client.post("/api/admin/control/messages", json={"audience": "all", "title_ru": "x", "link": "ftp://x"}, headers=headers)
    assert bad.status_code == 400
    sent = client.post("/api/admin/control/messages", json={"audience": "users", "targets": str(uid), "title_ru": "Сразу"}, headers=headers)
    assert sent.status_code == 200 and sent.json()["recipients"] == 1
    assert client.get("/api/admin/control/messages").json()["items"][0]["title_ru"] == "Сразу"

    monkeypatch.setattr(gallery_router, "_auth_user", lambda request: {"id": uid})
    unread = gallery_router.api_notifications_unread(object())
    assert unread["popup"]["title"] == "Сразу" and unread["unread"] >= 1

    message_id = sent.json()["id"]
    assert client.delete(f"/api/admin/control/messages/{message_id}", headers=headers).json()["removed"] == 1
    assert gallery_router.api_notifications_unread(object())["popup"] is None
    assert client.delete("/api/admin/control/messages/abc123", headers=headers).status_code == 404
