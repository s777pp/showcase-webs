"""Telegram mini app: initData check, signed links, ownership of results, the /tg page and its API."""
import hashlib
import hmac
import io
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from smweb import tg_app, telegram_cut

TOKEN = "123456:TEST-token"


def init_data(user_id=777000111, token=TOKEN, age=0, **extra):
    fields = {"auth_date": str(int(time.time()) - age), "query_id": "AAE",
              "user": json.dumps({"id": user_id, "first_name": "Saba", "language_code": "ru"}), **extra}
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


@pytest.fixture
def client(monkeypatch, tmp_path):
    from smweb.routers import tg_app as tg_router
    monkeypatch.setenv("TG_APP_BOT_TOKEN", TOKEN)
    monkeypatch.setattr(tg_app, "JOBS", tmp_path)
    monkeypatch.setattr(tg_router, "JOBS", tmp_path)
    app = FastAPI()
    app.include_router(tg_router.router)
    return TestClient(app)


def test_verify_accepts_only_signed_fresh_data():
    good = init_data()
    assert tg_app.verify(good, TOKEN)["id"] == "777000111"
    assert tg_app.verify(init_data(signature="abc"), TOKEN)["first_name"] == "Saba"   # Bot API 8 field is signed too
    assert tg_app.verify(good, "999:other") is None                                  # another bot
    assert tg_app.verify(good.replace("Saba", "Evil"), TOKEN) is None                 # tampered
    assert tg_app.verify(init_data(age=2 * 86400), TOKEN) is None                      # too old
    assert tg_app.verify("", TOKEN) is None and tg_app.verify("a=b", "") is None


def test_signed_links_expire_and_cannot_be_forged():
    token = tg_app.sign("777000111", "file", "a" * 32, inline=True)
    body = tg_app.unsign(token)
    assert body["t"] == "777000111" and body["k"] == "file" and body["i"] == 1
    data, mac = token.split(".")
    assert tg_app.unsign(data + "." + "0" * 32) is None
    assert tg_app.unsign(tg_app.sign("1", "file", "x", ttl=-5)) is None


def test_page_can_be_framed_by_telegram_only(client):
    response = client.get("/tg")
    assert response.status_code == 200 and "tg-app.js" in response.text
    assert "https://web.telegram.org" in response.headers["content-security-policy"]
    assert "noindex" in response.headers["x-robots-tag"]


def test_api_needs_telegram_signature(client):
    assert client.get("/api/tg-app/me").status_code == 401
    assert client.get("/api/tg-app/me", headers={"X-Tg-Init-Data": init_data(token="1:x")}).status_code == 401


def test_me_reports_the_daily_limit(client):
    response = client.get("/api/tg-app/me", headers={"X-Tg-Init-Data": init_data()})
    data = response.json()
    assert response.status_code == 200 and data["user"]["first_name"] == "Saba"
    assert data["pro"] is False and data["quota"]["left"] == data["quota"]["limit"]


def test_convert_result_belongs_to_its_telegram_user(client, monkeypatch):
    def fake_convert(src, dest, target, fps, width, duration):
        Image.new("RGB", (8, 8), "red").save(dest, "PNG")
    monkeypatch.setattr("processor.convert_media", fake_convert)
    buf = io.BytesIO(); Image.new("RGB", (8, 8)).save(buf, "JPEG")
    headers = {"X-Tg-Init-Data": init_data()}
    response = client.post("/api/tg-app/convert", headers=headers, data={"target": "png"},
                           files={"file": ("pic.jpg", buf.getvalue(), "image/jpeg")})
    data = response.json()
    assert response.status_code == 200 and data["name"] == "pic.png" and data["type"] == "image/png"
    # The signed link serves the file without the header; another user cannot resolve it.
    file_response = client.get(data["preview"])
    assert file_response.status_code == 200 and file_response.content[:4] == b"\x89PNG"
    assert tg_app.resolve("777000111", "file", data["ref"]) is not None
    assert tg_app.resolve("555000222", "file", data["ref"]) is None
    other = client.post("/api/tg-app/send", headers={"X-Tg-Init-Data": init_data(user_id=555000222)},
                        json={"kind": "file", "ref": data["ref"]})
    assert other.status_code == 404
    # The conversion counted against today's free files.
    assert telegram_cut.quota("777000111")["used"] == 1


def test_send_goes_through_the_bot(client, monkeypatch):
    def fake_convert(src, dest, target, fps, width, duration):
        dest.write_bytes(b"GIF89a" + b"0" * 20)
    monkeypatch.setattr("processor.convert_media", fake_convert)
    sent = {}
    monkeypatch.setattr(tg_app, "send_document", lambda chat, name, data, caption="": sent.update(chat=chat, name=name) or (True, ""))
    headers = {"X-Tg-Init-Data": init_data(user_id=888000111)}
    data = client.post("/api/tg-app/convert", headers=headers, data={"target": "gif"},
                       files={"file": ("clip.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")}).json()
    response = client.post("/api/tg-app/send", headers=headers, json={"kind": "file", "ref": data["ref"]})
    assert response.json() == {"ok": True} and sent == {"chat": "888000111", "name": "clip.gif"}


def test_upscale_needs_a_pro_account(client):
    response = client.post("/api/tg-app/upscale/start", headers={"X-Tg-Init-Data": init_data()},
                           data={"preset": "general", "scale": "2"}, files={"file": ("a.png", b"x", "image/png")})
    assert response.status_code == 403 and response.json()["code"] == "no_account"


def test_rate_rules_cover_the_mini_app():
    from smweb.middleware import RateLimitMiddleware
    prefixes = [rule[0] for rule in RateLimitMiddleware.RULES]
    assert prefixes.index("/api/tg-app/cut/start") < prefixes.index("/api/tg-app/")
