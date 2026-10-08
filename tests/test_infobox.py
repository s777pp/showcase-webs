"""Community templates for Steam's Custom Info Box (smweb/infobox.py, smweb/routers/infobox.py)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_db
from smweb import core, infobox
from smweb.routers import infobox as infobox_router


@pytest.fixture
def site(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "USING_POSTGRES", False)
    monkeypatch.setattr(auth_db, "DB", tmp_path / "users.db")
    monkeypatch.setattr(auth_db, "DATA", tmp_path)
    monkeypatch.setattr(auth_db, "_SCHEMA_READY", False)
    monkeypatch.setattr(core, "DATA", tmp_path)
    monkeypatch.setattr(infobox_router.rs, "rate_limit", lambda *_a, **_k: (True, 0))
    monkeypatch.setattr(infobox_router, "_auth_user", lambda request: {
        "author": {"id": 1}, "other": {"id": 2}}.get(request.headers.get("x-user")))
    connection = auth_db._conn()
    for uid, name in ((1, "author"), (2, "other")):
        connection.execute("INSERT INTO users(id,email,password_hash,display_name,profile_username,created_at) "
                           "VALUES (?,?,?,?,?,0)", (uid, f"{name}@example.test", "x", name.title(), name))
    connection.commit()
    connection.close()
    app = FastAPI()
    app.include_router(infobox_router.router)
    with TestClient(app) as client:
        yield client


def _publish(client, user="author", **fields):
    body = {"title": "Star frame", "body": "[h1]Hi[/h1]\n✦ line", "category": "frames", "rights": True, **fields}
    return client.post("/api/infobox/templates", json=body, headers={"X-User": user} if user else {})


def test_publish_needs_sign_in_and_rights(site):
    assert _publish(site, user=None).status_code == 401
    assert _publish(site, rights=False).status_code == 400
    assert _publish(site, title="   ").status_code == 400


def test_list_use_and_owner_delete(site):
    created = _publish(site)
    assert created.status_code == 200, created.text
    template_id = created.json()["id"]
    listing = site.get("/api/infobox/templates", headers={"X-User": "author"}).json()
    assert listing["total"] == 1
    item = listing["items"][0]
    assert item["title"] == "Star frame" and item["body"] == "[h1]Hi[/h1]\n✦ line" and item["author"] == "Author"
    assert item["owner"] is True and "user_id" not in item
    assert site.get("/api/infobox/templates", headers={"X-User": "other"}).json()["items"][0]["owner"] is False
    assert site.get("/api/infobox/templates?category=games").json()["total"] == 0
    site.post(f"/api/infobox/templates/{template_id}/use")
    assert site.get("/api/infobox/templates").json()["items"][0]["uses"] == 1
    assert site.delete(f"/api/infobox/templates/{template_id}", headers={"X-User": "other"}).status_code == 404
    assert site.delete(f"/api/infobox/templates/{template_id}", headers={"X-User": "author"}).status_code == 200
    assert site.get("/api/infobox/templates").json()["total"] == 0


def test_admin_hide_requires_an_admin_session(site, monkeypatch):
    template_id = _publish(site).json()["id"]
    assert site.delete(f"/api/admin/control/infobox/{template_id}").status_code == 403
    monkeypatch.setattr(infobox_router.admin_control, "authorised", lambda request, mutation=False: True)
    monkeypatch.setattr(infobox_router.admin_control, "origin_allowed", lambda request: True)
    monkeypatch.setattr(infobox_router.admin_control, "audit", lambda *a, **k: None)
    assert site.delete(f"/api/admin/control/infobox/{template_id}").json()["ok"] is True
    assert site.get("/api/infobox/templates").json()["total"] == 0


def test_text_is_cleaned_and_bounded():
    assert infobox.clean_body("a\r\nb\x00\x07c") == "a\nbc"
    assert len(infobox.clean_body("x" * 9000)) == infobox.BODY_MAX
    assert infobox.clean_title("  many   spaces  ") == "many spaces"


def test_account_export_and_deletion_cover_templates(site):
    _publish(site)
    exported = auth_db.account_export_data(1)
    assert exported["infobox_templates"][0]["title"] == "Star frame"
    auth_db.delete_account_data(1)
    assert site.get("/api/infobox/templates").json()["total"] == 0
