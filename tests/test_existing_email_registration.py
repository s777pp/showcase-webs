from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb.routers import auth


def test_existing_email_stays_on_registration_form_without_sending_code(monkeypatch):
    monkeypatch.setattr(auth.rs, "rate_limit", lambda *_args, **_kwargs: (True, 0))
    monkeypatch.setattr(auth.auth_db, "user_exists", lambda _email: True)
    monkeypatch.setattr(
        auth.auth_db,
        "create_email_code",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("code created")),
    )
    monkeypatch.setattr(
        auth.mailer,
        "send_verify_code",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("email sent")),
    )
    app = FastAPI()
    app.include_router(auth.router)

    response = TestClient(app).post(
        "/api/auth/send-code", json={"email": "Existing@Example.com"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_registered"
