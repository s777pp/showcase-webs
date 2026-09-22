import hashlib
import hmac
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb.routers import oauth


def test_telegram_widget_redirect_verifies_payload_and_returns_to_app(monkeypatch):
    token = "telegram-widget-test-token"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    monkeypatch.setenv("APP_URL", "https://showcasemaker.example")
    monkeypatch.setattr(oauth.auth_db, "user_by_telegram", lambda tid: {"id": 42})
    monkeypatch.setattr(
        oauth.auth_db,
        "register_or_login_telegram",
        lambda **kwargs: (True, "OK", "test-session-token"),
    )
    app = FastAPI()
    app.include_router(oauth.router)
    client = TestClient(app)

    payload = {"id": "42", "first_name": "Test", "auth_date": str(int(time.time()))}
    check_string = "\n".join(f"{key}={payload[key]}" for key in sorted(payload))
    payload["hash"] = hmac.new(
        hashlib.sha256(token.encode()).digest(), check_string.encode(), hashlib.sha256
    ).hexdigest()

    response = client.get("/api/auth/telegram/callback", params=payload)
    assert response.status_code == 200
    assert 'window.location.replace("https://showcasemaker.example/app")' in response.text
    assert "new BroadcastChannel('showcasemaker-auth')" in response.text
    assert "sm_session=" in response.headers.get("set-cookie", "")

    payload["hash"] = "0" * 64
    assert client.get("/api/auth/telegram/callback", params=payload).status_code == 400
