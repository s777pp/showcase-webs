import os
import time
from collections import namedtuple

from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_db
from smweb import admin_content, admin_control, maintenance, runtime_settings, user_limits
from smweb.routers import admin as admin_router, support as support_router


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "USING_POSTGRES", False)
    monkeypatch.setattr(auth_db, "DB", tmp_path / "users.db")
    monkeypatch.setattr(auth_db, "DATA", tmp_path)
    monkeypatch.setattr(auth_db, "_SCHEMA_READY", False)
    monkeypatch.setattr(admin_control, "ACCESS_FILE", tmp_path / "access_codes.json")
    monkeypatch.setattr(admin_content, "CATALOG_FILE", tmp_path / "steam_catalog_controls.json")
    monkeypatch.setattr(runtime_settings, "STATE_FILE", tmp_path / "runtime_settings.json")
    monkeypatch.setattr(runtime_settings, "_cache", None)
    monkeypatch.setattr(runtime_settings, "_cache_mtime", -1.0)
    monkeypatch.setattr(maintenance, "STATE_FILE", tmp_path / "maintenance.json")
    monkeypatch.setenv("SECRET_KEY", "admin-test-session-secret-" * 3)
    monkeypatch.setenv("ADMIN_SECRET", "admin-control-test-secret-123456")


def _client():
    app = FastAPI()
    app.include_router(admin_router.router)
    app.include_router(support_router.router)
    return TestClient(app)


def _login(client):
    response = client.post(
        "/api/admin/control/session",
        json={"secret": "admin-control-test-secret-123456"},
    )
    assert response.status_code == 200
    return response.json()["csrf"]


def _mutation_headers(csrf):
    return {"Origin": "http://testserver", "X-Admin-CSRF": csrf}


def test_admin_session_settings_codes_and_audit(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    client = _client()
    assert client.get("/api/admin/control/session").status_code == 401
    assert client.post("/api/admin/control/session", json={"secret": "wrong"}).status_code == 403

    csrf = _login(client)
    assert client.get("/api/admin/control/session").status_code == 200
    assert client.post(
        "/api/admin/control/settings",
        json={"settings": {"process_enabled": False}},
        headers={"Origin": "http://testserver"},
    ).status_code == 403

    response = client.post(
        "/api/admin/control/settings",
        json={"settings": {"process_enabled": False, "free_daily_limit": 9}},
        headers=_mutation_headers(csrf),
    )
    assert response.status_code == 200
    assert response.json()["settings"]["process_enabled"] is False
    assert response.json()["settings"]["free_daily_limit"] == 9

    created = client.post(
        "/api/admin/control/codes",
        json={"count": 2, "duration_days": 7, "label": "Telegram"},
        headers=_mutation_headers(csrf),
    )
    assert created.status_code == 200
    assert len(created.json()["codes"]) == 2
    listed = client.get("/api/admin/control/codes").json()["items"]
    assert len(listed) == 2
    assert all(item["hours"] == 168 for item in listed)

    actions = client.get("/api/admin/control/audit").json()["items"]
    assert {row["action"] for row in actions} >= {"session.login", "settings.update", "codes.generate"}


def test_user_admin_actions_enforce_suspension(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    import mailer
    monkeypatch.setattr(mailer, "send_pro_granted_email", lambda to, days, lang="en": (True, "sent"))
    assert auth_db.register("person@example.com", "password-12345")[0]
    connection = auth_db._conn()
    user_id = int(connection.execute("SELECT id FROM users WHERE email=?", ("person@example.com",)).fetchone()["id"])
    connection.execute(
        "UPDATE users SET display_name=?,profile_username=?,avatar_path=? WHERE id=?",
        ("Person", "person", "avatars/person.png", user_id),
    )
    connection.commit()
    connection.close()

    client = _client()
    csrf = _login(client)
    response = client.post(
        f"/api/admin/control/users/{user_id}/action",
        json={"action": "grant_pro", "days": 7},
        headers=_mutation_headers(csrf),
    )
    assert response.status_code == 200
    assert response.json()["notification"] == {"attempted": True, "delivered": True, "language": "ru"}
    item = client.get("/api/admin/control/users?q=person").json()["items"][0]
    assert item["is_pro"] is True
    assert item["profile_username"] == "person"
    assert item["avatar_path"] == "avatars/person.png"

    response = client.post(
        f"/api/admin/control/users/{user_id}/action",
        json={"action": "suspend", "days": 7, "reason": "Test"},
        headers=_mutation_headers(csrf),
    )
    assert response.status_code == 200
    assert auth_db.login("person@example.com", "password-12345")[0] is False

    response = client.post(
        f"/api/admin/control/users/{user_id}/action",
        json={"action": "unsuspend"},
        headers=_mutation_headers(csrf),
    )
    assert response.status_code == 200
    assert auth_db.login("person@example.com", "password-12345")[0] is True
    actions = client.get("/api/admin/control/audit").json()["items"]
    email_event = next(row for row in actions if row["action"] == "email.pro_granted")
    assert email_event["details"] == {"attempted": True, "delivered": True, "language": "ru"}


def test_system_status_explains_impact_in_plain_language(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(admin_control.rs, "redis_ok", lambda: True)
    monkeypatch.setattr(admin_control.rs, "worker_alive", lambda: True)
    monkeypatch.setattr(admin_control.rs, "queue_depths", lambda: {"media": 2, "profile": 0, "gpu": 1})
    monkeypatch.setattr(admin_control, "_worker_mode", lambda: "external")
    monkeypatch.setattr(admin_control.proc, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(admin_control.proc, "find_gifski", lambda: "gifski")
    usage = namedtuple("usage", "total used free")(100 * 1024**3, 40 * 1024**3, 60 * 1024**3)
    monkeypatch.setattr(admin_control.shutil, "disk_usage", lambda _path: usage)
    monkeypatch.setattr(admin_control.object_store, "configured", lambda: True)
    monkeypatch.setattr(admin_control.object_store, "health", lambda: (True, "ok"))
    monkeypatch.setenv("MODAL_UPSCALE_URL", "https://example.test")
    monkeypatch.setenv("MODAL_PROXY_TOKEN_ID", "id")
    monkeypatch.setenv("MODAL_PROXY_TOKEN_SECRET", "secret")

    snapshot = admin_control.system_snapshot()
    assert snapshot["overall"] == "ok"
    assert snapshot["headline"] == "Всё работает штатно"
    assert snapshot["queues"] == {"media": 2, "profile": 0, "gpu": 1}
    assert all(component["summary"] and component["impact"] for component in snapshot["components"])


def test_maintenance_can_expire_automatically(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    maintenance.set_state(True, "Short notice", ends_at=time.time() - 1)
    state = maintenance.get_state()
    assert state["enabled"] is False
    assert state["message"] == ""


def test_dashboard_does_not_store_admin_secret_in_web_storage():
    root = os.path.dirname(os.path.dirname(__file__))
    source = open(os.path.join(root, "static", "js", "analytics-dashboard.js"), encoding="utf-8").read()
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "X-Admin-Secret" not in source
    assert "X-Admin-CSRF" in source
    assert "prompt('Язык уведомления" not in source
    assert "data-language-for" in source


def test_user_rows_link_public_profiles_and_load_safe_avatar_routes():
    root = os.path.dirname(os.path.dirname(__file__))
    source = open(os.path.join(root, "static", "js", "analytics-dashboard.js"), encoding="utf-8").read()
    assert '/api/auth/avatar/${u.id}' in source
    assert '/profile/${encodeURIComponent(u.profile_username)}' in source
    assert 'target="_blank" rel="noopener"' in source


def test_support_ticket_public_create_and_admin_workflow(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(support_router.rs, "rate_limit", lambda *args, **kwargs: (True, 1))
    client = _client()
    rejected = client.post("/api/support/tickets", json={"message": "Something is broken"})
    assert rejected.status_code == 403
    created = client.post(
        "/api/support/tickets",
        json={"message": "The preview stopped after uploading a file.", "email": "guest@example.com",
              "page": "/app?secret=no", "context": {"language": "en", "viewport": "1280x720"}},
        headers={"Origin": "http://testserver"},
    )
    assert created.status_code == 201
    ticket_id = created.json()["ticket_id"]
    csrf = _login(client)
    listed = client.get("/api/admin/control/support?status=open").json()["items"]
    assert listed[0]["id"] == ticket_id
    assert listed[0]["page"] == "/app"
    assert listed[0]["context"]["viewport"] == "1280x720"
    updated = client.post(
        f"/api/admin/control/support/{ticket_id}",
        json={"status": "resolved", "note": "Checked and fixed"}, headers=_mutation_headers(csrf),
    )
    assert updated.status_code == 200
    assert client.get("/api/admin/control/support?status=resolved").json()["items"][0]["admin_note"] == "Checked and fixed"


def test_announcements_obey_audience_and_are_admin_managed(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    client = _client()
    csrf = _login(client)
    response = client.post(
        "/api/admin/control/announcements",
        json={"title_ru": "Обновление", "body_ru": "Новая версия готова", "body_en": "A new version is ready",
              "audience": "guests", "level": "success", "enabled": True},
        headers=_mutation_headers(csrf),
    )
    assert response.status_code == 200
    public = client.get("/api/announcements").json()["items"]
    assert public[0]["body_ru"] == "Новая версия готова"
    assert public[0]["audience"] == "guests"
    announcement_id = response.json()["id"]
    assert client.delete(f"/api/admin/control/announcements/{announcement_id}", headers=_mutation_headers(csrf)).status_code == 200
    assert client.get("/api/announcements").json()["items"] == []


def test_user_detail_is_metadata_only_and_limits_are_manageable(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    assert auth_db.register("limits@example.com", "password-12345")[0]
    connection = auth_db._conn()
    user_id = int(connection.execute("SELECT id FROM users WHERE email=?", ("limits@example.com",)).fetchone()["id"])
    connection.execute(
        "INSERT INTO builder_projects(id,user_id,name,showcase_mode,project_json,created_at,updated_at,expires_at) VALUES (?,?,?,?,?,?,?,?)",
        ("private-project", user_id, "Visible metadata", "workshop", '{"secret":"must-not-leak"}', time.time(), time.time(), None),
    )
    connection.commit()
    connection.close()
    client = _client()
    csrf = _login(client)
    set_result = client.post(
        f"/api/admin/control/users/{user_id}/action",
        json={"action": "set_limits", "free_daily_limit": 12, "max_jobs": 4, "note": "Support override"},
        headers=_mutation_headers(csrf),
    )
    assert set_result.status_code == 200
    assert user_limits.integer(user_id, "max_jobs", 2) == 4
    detail = client.get(f"/api/admin/control/users/{user_id}").json()
    assert detail["limits"]["free_daily_limit"] == 12
    assert detail["projects"][0]["name"] == "Visible metadata"
    assert "project_json" not in detail["projects"][0]
    assert "secret" not in str(detail)


def test_catalog_rules_feature_and_hide_exact_items(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    client = _client()
    csrf = _login(client)
    url = "https://steamcommunity.com/market/listings/example"
    created = client.post(
        "/api/admin/control/catalog",
        json={"identity": url, "name": "Featured background", "featured": True},
        headers=_mutation_headers(csrf),
    )
    assert created.status_code == 200
    output = admin_content.apply_catalog_rules([{"name": "Other"}, {"name": "Featured background", "buy_url": url}])
    assert output[0]["buy_url"] == url
    hidden = client.post(
        "/api/admin/control/catalog",
        json={"identity": url, "name": "Featured background", "hidden": True},
        headers=_mutation_headers(csrf),
    )
    assert hidden.status_code == 200
    assert admin_content.apply_catalog_rules([{"name": "Featured background", "buy_url": url}]) == []


def test_access_codes_can_expire_before_activation(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    created = admin_control.generate_codes(1, 7, "Campaign", "Launch", 1)
    item = admin_control.codes()["items"][0]
    assert created["codes"] == [item["code"]]
    assert item["campaign"] == "Launch"
    assert item["expires_at"] > time.time()
