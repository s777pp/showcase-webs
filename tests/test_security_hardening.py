import time
from unittest.mock import patch

import auth_db
from fastapi import FastAPI
from fastapi.testclient import TestClient
from smweb.oauth_util import (
    _oauth_payload_create,
    _oauth_payload_verify,
    _oauth_state_create,
    _oauth_state_verify,
)
from smweb.middleware import OriginGuardMiddleware


def test_current_and_legacy_password_hashes_are_supported():
    current = auth_db._hash_pw("correct horse battery staple")
    assert auth_db._check_pw("correct horse battery staple", current)
    assert not auth_db._check_pw("wrong", current)
    assert not auth_db._password_hash_needs_upgrade(current)

    salt = "0123456789abcdef"
    legacy = auth_db.hashlib.pbkdf2_hmac(
        "sha256", b"old password", salt.encode(), 120_000
    ).hex()
    legacy = f"{salt}${legacy}"
    assert auth_db._check_pw("old password", legacy)
    assert auth_db._password_hash_needs_upgrade(legacy)
    assert auth_db._session_key("browser-cookie").startswith("sha256:")
    assert "browser-cookie" not in auth_db._session_key("browser-cookie")


def test_oauth_state_is_signed_scoped_and_short_lived(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "s" * 64)
    now = int(time.time())
    with patch("smweb.oauth_util.time.time", return_value=now):
        state = _oauth_state_create("discord")
    with patch("smweb.oauth_util.time.time", return_value=now + 60):
        assert _oauth_state_verify(state, "discord")
        assert not _oauth_state_verify(state, "google")
    with patch("smweb.oauth_util.time.time", return_value=now + 601):
        assert not _oauth_state_verify(state, "discord")
    assert not _oauth_state_verify(state[:-1] + ("A" if state[-1] != "A" else "B"), "discord")


def test_deviantart_credentials_are_encrypted_at_rest(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "k" * 64)
    protected = auth_db._protect_credential("client-secret")
    assert protected.startswith("enc:v1:")
    assert "client-secret" not in protected
    assert auth_db._unprotect_credential(protected) == "client-secret"

    state = _oauth_payload_create({"provider": "da", "client_secret": "client-secret"})
    assert "client-secret" not in state
    assert _oauth_payload_verify(state)["client_secret"] == "client-secret"


def test_cookie_authenticated_writes_require_same_origin(monkeypatch):
    monkeypatch.setenv("APP_URL", "https://showcasemaker.com")
    app = FastAPI()
    app.add_middleware(OriginGuardMiddleware)

    @app.post("/change")
    def change():
        return {"ok": True}

    client = TestClient(app, base_url="https://showcasemaker.com")
    client.cookies.set("sm_session", "secret")
    assert client.post("/change", headers={"Origin": "https://showcasemaker.com"}).status_code == 200
    assert client.post("/change", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/change").status_code == 403
