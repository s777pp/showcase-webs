from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from smweb import admin_notify

client = TestClient(main.app)
H = {"X-Bot-Admin-Secret": "s3cret-for-tests"}


def test_api_is_off_without_secret_and_rejects_wrong_one(monkeypatch):
    monkeypatch.delenv("BOT_ADMIN_SECRET", raising=False)
    assert client.get("/api/bot-admin/status", headers=H).status_code == 404
    monkeypatch.setenv("BOT_ADMIN_SECRET", "s3cret-for-tests")
    assert client.get("/api/bot-admin/status", headers={"X-Bot-Admin-Secret": "nope"}).status_code == 403


def test_maintenance_codes_and_ticket_reply(monkeypatch):
    monkeypatch.setenv("BOT_ADMIN_SECRET", "s3cret-for-tests")
    on = client.post("/api/bot-admin/maintenance", headers=H, json={"enabled": True, "message": "обновление", "hours": 1}).json()
    assert on["maintenance"]["enabled"] and on["maintenance"]["ends_at"]
    off = client.post("/api/bot-admin/maintenance", headers=H, json={"enabled": False}).json()
    assert not off["maintenance"]["enabled"]
    with patch("smweb.admin_control._write_codes"), patch("smweb.admin_control._read_codes", return_value={}):
        codes = client.post("/api/bot-admin/codes", headers=H, json={"count": 3, "hours": 2}).json()["codes"]
    assert len(codes) == 3 and all(c.startswith("SM-TRIAL-") for c in codes)
    from smweb import admin_content
    ticket = admin_content.create_ticket(user_id=None, email="user@example.com", message="Не работает зацикливание",
                                         page="/ru/app", context={})["ticket_id"]
    with patch("mailer.send_email", return_value=(True, "")) as mail:
        res = client.post(f"/api/bot-admin/tickets/{ticket}/reply", headers=H, json={"text": "Исправили, попробуйте ещё раз"}).json()
    assert res == {"ok": True, "emailed": True, "has_email": True}
    assert mail.call_args[0][0] == "user@example.com"
    assert not any(t["id"] == ticket for t in client.get("/api/bot-admin/tickets", headers=H).json()["items"])


def test_notifications_are_silent_when_not_configured(monkeypatch):
    monkeypatch.delenv("ADMIN_BOT_TOKEN", raising=False)
    with patch.object(admin_notify, "_post") as post:
        admin_notify.ticket_created("x", "a@b.c", "hello there friend", "/")
        admin_notify.job_failed("job", {"error": "boom"})
    post.assert_not_called()
