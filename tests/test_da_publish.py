import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb import da_publish
from smweb.routers import deviantart


OWNER_STYLE = (
    '<p>✦・<a href="https://www.deviantart.com/users/outgoing?https://ko-fi.com/s/abba9c6f64">'
    '<b>LINK DOWNLOAD</b></a>・✦</p><p>💠 <b>Price:</b> Only <b>$2</b></p>'
    '<script>alert(1)</script><a href="javascript:alert(1)">bad</a><h4>THANK YOU ♡</h4>'
    '<img src="x" onerror="alert(1)"><span style="color:red">kept text</span>'
)


def test_description_keeps_formatting_and_drops_unsafe_parts():
    cleaned = da_publish.clean_description(OWNER_STYLE)
    assert '<a href="https://ko-fi.com/s/abba9c6f64"><b>LINK DOWNLOAD</b></a>' in cleaned
    assert "<b>$2</b>" in cleaned and "<h4>THANK YOU ♡</h4>" in cleaned
    assert "script" not in cleaned and "javascript" not in cleaned and "onerror" not in cleaned
    assert "<img" not in cleaned and "style=" not in cleaned
    assert "bad" in cleaned and "kept text" in cleaned, "text of dropped tags stays"


def test_plain_text_description_keeps_line_breaks():
    assert da_publish.clean_description("line one\nline <two>") == "line one<br>line &lt;two&gt;"


def test_tags_follow_deviantart_rules():
    tags = da_publish.clean_tags(["Anime Girl", "#steam", "steam", "work-shop", "", "аниме"] + [f"t{i}" for i in range(40)])
    assert tags[:4] == ["animegirl", "steam", "workshop", "аниме"]
    assert len(tags) == da_publish.TAG_MAX
    assert da_publish.clean_tags("anime, digitalart #pixelart") == ["anime", "digitalart", "pixelart"]


def test_settings_are_clamped():
    settings = da_publish.clean_settings({"mode": "publish", "is_mature": "true", "mature_level": "evil",
                                          "mature_classification": ["gore", "bad"], "display_resolution": 99,
                                          "add_watermark": True, "galleryids": ["not-a-uuid"]})
    assert settings["mode"] == "publish" and settings["mature_level"] == "moderate"
    assert settings["mature_classification"] == ["gore"] and settings["display_resolution"] == 8
    assert settings["add_watermark"] is True and settings["galleryids"] == []
    plain = da_publish.clean_settings(None)
    assert plain["mode"] == "stash" and plain["feature"] and plain["allow_comments"]
    assert not da_publish.clean_settings({"add_watermark": True})["add_watermark"], "watermark needs a display size"


def test_publish_fields_only_send_what_applies():
    settings = da_publish.clean_settings({"tags": ["anime"], "galleryids": ["0F0F0F0F-1111-2222-3333-444444444444"]})
    fields = da_publish.publish_fields(42, settings)
    names = [name for name, _ in fields]
    assert ("itemid", "42") in fields and ("is_mature", "false") in fields
    assert "mature_level" not in names and "display_resolution" not in names and "add_watermark" not in names
    assert ("galleryids[]", "0F0F0F0F-1111-2222-3333-444444444444") in fields and ("tags[]", "anime") in fields


class _Response:
    def __init__(self, payload, status=200):
        self.payload, self.status_code, self.text = payload, status, json.dumps(payload)

    def json(self):
        return self.payload


def _client(monkeypatch, calls):
    import requests

    def fake_post(url, params=None, headers=None, data=None, files=None, timeout=None):
        calls.append((url.rsplit("/", 2)[-2] + "/" + url.rsplit("/", 1)[-1], list(data or []), files))
        if url.endswith("stash/submit"):
            return _Response({"status": "success", "itemid": 777})
        return _Response({"status": "success", "url": "https://www.deviantart.com/n1t1337/art/x-1", "deviationid": "ABC"})

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(deviantart, "_auth_user", lambda request: {"id": 1, "da_access_token": "token"})
    app = FastAPI()
    app.include_router(deviantart.router)
    return TestClient(app)


def test_upload_publishes_with_description_and_tags(monkeypatch):
    calls = []
    client = _client(monkeypatch, calls)
    settings = {"mode": "publish", "description": OWNER_STYLE, "tags": ["anime", "steam"], "noai": True}
    response = client.post("/api/da/upload", data={"settings": json.dumps(settings), "title_a.png": "Steam Workshop Showcase - Anime"},
                           files=[("file", ("a.png", b"\x89PNG fake", "image/png"))])
    body = response.json()
    assert body["ok"] and body["results"][0]["url"].endswith("/art/x-1")
    submit, publish = calls
    assert submit[0] == "stash/submit" and publish[0] == "stash/publish"
    assert ("title", "Steam Workshop Showcase - Anime") in submit[1]
    assert ("tags[]", "anime") in submit[1] and ("noai", "true") in submit[1]
    description = dict(submit[1])["artist_comments"]
    assert "ko-fi.com/s/abba9c6f64" in description and "<script" not in description
    assert "<p>" not in description and "\n" in description, "classic DeviantArt markup: new lines, no blocks"
    assert ("itemid", "777") in publish[1] and ("agree_tos", "true") in publish[1]


def test_upload_without_settings_stays_in_stash(monkeypatch):
    calls = []
    client = _client(monkeypatch, calls)
    response = client.post("/api/da/upload", files=[("file", ("b.gif", b"GIF89a", "image/gif"))])
    body = response.json()
    assert body["ok"] and body["mode"] == "stash" and body["results"][0]["stash"]
    assert [call[0] for call in calls] == ["stash/submit"]


def test_presets_are_saved_per_user(monkeypatch):
    import auth_db
    import secrets
    email = f"da-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    user = auth_db.get_user_by_email(email) if hasattr(auth_db, "get_user_by_email") else None
    uid = int(user["id"]) if user else int(auth_db._conn().execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
    monkeypatch.setattr(deviantart, "_auth_user", lambda request: {"id": uid})
    app = FastAPI()
    app.include_router(deviantart.router)
    client = TestClient(app)
    saved = client.post("/api/da/presets", json={"name": "Ko-fi shop", "preset": {
        "title": "Steam Workshop Showcase - {title}", "link": "https://ko-fi.com/s/abc", "price": "$2",
        "description": "<b>{link}</b><script>x</script>", "tags": ["Anime Girl"], "mode": "publish"}}).json()
    assert saved["ok"]
    listed = client.get("/api/da/presets").json()["presets"]
    assert listed[0]["name"] == "Ko-fi shop"
    preset = listed[0]["preset"]
    assert preset["tags"] == ["animegirl"] and "<script" not in preset["description"] and preset["mode"] == "publish"
    assert client.delete("/api/da/presets/" + saved["preset"]["id"]).json()["ok"]
    assert client.get("/api/da/presets").json()["presets"] == []


def test_presets_keep_the_link_placeholder_but_uploads_do_not():
    html = '<a href="{link}"><b>LINK DOWNLOAD</b></a>'
    assert 'href="{link}"' in da_publish.clean_description(html, placeholders=True)
    assert "href" not in da_publish.clean_description(html)


def test_description_is_sent_as_deviantart_markup():
    editor = ('<p>✦・<a href="https://ko-fi.com/s/abc"><b>LINK DOWNLOAD</b></a>・✦</p>'
              '<p>💠 <strong>Price:</strong> Only <b>$2</b></p>'
              '<p>᠌────────── ✦ ──────────</p>'
              '<p>✨ <b>Notes:</b><br>✅ Preview may appear in lower quality.<br>✅ DM me anytime.</p>'
              '<p><br></p>'
              '<h4>THANK YOU ♡</h4><ul><li>one</li><li>two</li></ul>')
    markup = da_publish.to_da_markup(da_publish.clean_description(editor))
    assert markup.split("\n") == [
        '✦・<a href="https://ko-fi.com/s/abc"><b>LINK DOWNLOAD</b></a>・✦',
        '💠 <b>Price:</b> Only <b>$2</b>',
        '᠌────────── ✦ ──────────',
        '✨ <b>Notes:</b>',
        '✅ Preview may appear in lower quality.',
        '✅ DM me anytime.',
        '',
        '<b>THANK YOU ♡</b>',
        '• one',
        '• two',
    ]
