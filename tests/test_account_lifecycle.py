import json
import stat

import auth_db
from smweb import maintenance


def _isolated_auth_db(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "USING_POSTGRES", False)
    monkeypatch.setattr(auth_db, "DB", tmp_path / "users.db")
    monkeypatch.setattr(auth_db, "_SCHEMA_READY", False)
    monkeypatch.setenv("SECRET_KEY", "account-lifecycle-test-secret-" * 3)


def _registered_user(email="person@example.com", password="old-password-123"):
    ok, _message = auth_db.register(email, password)
    assert ok
    ok, _message, token = auth_db.login(email, password)
    assert ok and token
    user = auth_db.user_by_token(token)
    assert user
    return int(user["id"]), token


def test_password_reset_code_is_hashed_one_time_and_revokes_sessions(monkeypatch, tmp_path):
    _isolated_auth_db(monkeypatch, tmp_path)
    user_id, old_token = _registered_user()

    ok, _message, code = auth_db.create_account_action_code(
        "Person@Example.com", "password_reset"
    )
    assert ok and len(code) == 6
    connection = auth_db._conn()
    stored = connection.execute(
        "SELECT code_hash FROM account_action_codes WHERE email=? AND purpose=?",
        ("person@example.com", "password_reset"),
    ).fetchone()["code_hash"]
    connection.close()
    assert code not in stored

    ok, _message, reason = auth_db.reset_password_with_code(
        "person@example.com", "000000", "new-password-456"
    )
    assert not ok and reason == "invalid_code"
    ok, _message, reason = auth_db.reset_password_with_code(
        "person@example.com", code, "new-password-456"
    )
    assert ok and reason == "ok"
    assert auth_db.user_by_token(old_token) is None
    assert not auth_db.login("person@example.com", "old-password-123")[0]
    assert auth_db.login("person@example.com", "new-password-456")[0]

    # A consumed recovery code cannot be reused.
    assert not auth_db.reset_password_with_code(
        "person@example.com", code, "third-password-789"
    )[0]
    assert user_id > 0


def test_account_export_omits_credentials_and_delete_keeps_code_consumed(monkeypatch, tmp_path):
    _isolated_auth_db(monkeypatch, tmp_path)
    user_id, token = _registered_user()
    connection = auth_db._conn()
    connection.execute(
        "UPDATE users SET display_name=?,da_access_token=?,da_refresh_token=?,da_client_secret=?,profile_builder_json=? WHERE id=?",
        ("Person", "access-secret", "refresh-secret", "client-secret", json.dumps({"showcases": [{"type": "artwork"}]}), user_id),
    )
    connection.execute(
        "INSERT INTO builder_projects(id,user_id,name,showcase_mode,project_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
        ("project-1", user_id, "Project", "featured", json.dumps({"layers": []}), 1.0, 2.0),
    )
    connection.commit()
    connection.close()
    auth_db.mark_code_used("TRIAL-7-DAYS", user_id)

    exported = auth_db.account_export_data(user_id)
    assert exported["format"] == "showcase-maker-account-export-v1"
    assert exported["account"]["display_name"] == "Person"
    assert exported["builder_projects"][0]["project"] == {"layers": []}
    assert "password_hash" not in exported["account"]
    assert "da_access_token" not in exported["account"]
    assert "da_refresh_token" not in exported["account"]
    assert "da_client_secret" not in exported["account"]

    plan = auth_db.delete_account_data(user_id)
    assert plan["user_id"] == user_id
    assert auth_db.user_by_token(token) is None
    assert not auth_db.user_exists("person@example.com")
    assert auth_db.code_used("TRIAL-7-DAYS") == 0
    connection = auth_db._conn()
    assert connection.execute(
        "SELECT COUNT(*) AS n FROM builder_projects WHERE user_id=?", (user_id,)
    ).fetchone()["n"] == 0
    connection.close()


def test_maintenance_state_is_atomic_and_persistent(monkeypatch, tmp_path):
    state_file = tmp_path / "maintenance.json"
    monkeypatch.setattr(maintenance, "STATE_FILE", state_file)
    assert maintenance.get_state()["enabled"] is False
    enabled = maintenance.set_state(True, "Short maintenance")
    assert enabled["enabled"] is True
    assert maintenance.get_state()["message"] == "Short maintenance"
    mode = stat.S_IMODE(state_file.stat().st_mode)
    assert mode & stat.S_IRGRP
    assert mode & stat.S_IROTH
    assert not list(tmp_path.glob("maintenance-*.json"))
    maintenance.set_state(False)
    assert maintenance.get_state()["enabled"] is False
    assert maintenance.get_state()["message"] == ""


def test_account_controls_and_recovery_are_localized_for_every_site_language():
    shell = (auth_db.ROOT / "static" / "ss-shell.js").read_text(encoding="utf-8")
    controls = (auth_db.ROOT / "static" / "js" / "account-controls.js").read_text(encoding="utf-8")
    for language in ("en", "ru", "de", "tr", "fr", "uk", "es", "pt"):
        assert f"{language}:{{invalid_email:" in shell
        assert f"    {language}: {{maintenance:" in shell
    assert "document.body.insertAdjacentHTML('afterbegin', maintenanceHTML())" in shell
    assert "/api/auth/account-export" in controls
    assert "/api/auth/account-delete" in controls
    assert "confirm: 'DELETE'" in controls
