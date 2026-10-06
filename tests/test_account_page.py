"""Site account page: /api/account/overview, the avatar routes and the page route (2026-10-06)."""
import io
import random
import re
import secrets
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import auth_db
from smweb import core
from smweb.middleware import RateLimitMiddleware
from smweb.routers import account

ROOT = Path(__file__).resolve().parents[1]


def _user(**fields):
    email = f"acc-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        uid = int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
        for key, value in fields.items():
            c.execute(f"UPDATE users SET {key}=? WHERE id=?", (value, uid))
        c.commit()
        row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(row)
    finally:
        c.close()


def _client(monkeypatch, user):
    monkeypatch.setattr(account, "_auth_user", lambda request: user)
    monkeypatch.setattr(account, "quota_state", lambda request: {"used": 2, "limit": 5})
    app = FastAPI()
    app.include_router(account.router)
    return TestClient(app)


def test_guest_gets_401(monkeypatch):
    with _client(monkeypatch, None) as client:
        assert client.get("/api/account/overview").status_code == 401


def test_overview_shows_plan_logins_and_purchases_without_secrets(monkeypatch):
    steam = str(secrets.randbelow(10 ** 12))
    user = _user(is_pro=1, pro_until=time.time() + 5 * 86400 + 60, pro_code="GRS-ABC", steam_id=steam, display_name="Nick")
    secret_code = "SM-SECRET-" + secrets.token_hex(6).upper()
    c = auth_db._conn()
    try:
        now = time.time()
        c.execute("INSERT INTO gumroad_sales (sale_id, user_id, plan, days, status, price_cents, currency, updated_at, sale_created) "
                  "VALUES (?,?,?,?,?,?,?,?,?)", (secrets.token_hex(8), user["id"], "30d", 30, "granted", 399, "usd", now, now))
        c.execute("INSERT INTO used_codes (code, user_id, used_at) VALUES (?,?,?)", (secret_code, user["id"], now - 60))
        c.commit()
    finally:
        c.close()
    with _client(monkeypatch, user) as client:
        data = client.get("/api/account/overview").json()
    assert data["ok"] and data["user"]["name"] == "Nick" and data["user"]["steam"] == steam
    assert data["user"]["email"] == user["email"] and data["user"]["password"] is True
    assert data["plan"]["pro"] and not data["plan"]["lifetime"] and not data["plan"]["trial"] and data["plan"]["days_left"] == 5
    assert data["quota"] == {"used": 2, "limit": 5}
    kinds = [(p["source"], p["plan"], p["price"]) for p in data["purchases"]]
    assert ("gumroad", "30d", "$3.99") in kinds and ("key", None, "") in kinds
    assert secret_code not in str(data), "entered keys are never sent back"


def test_oauth_only_account_has_no_email_or_password(monkeypatch):
    user = _user(email=f"steam_{secrets.token_hex(3)}@users.local", steam_id=str(secrets.randbelow(10 ** 12)))
    with _client(monkeypatch, user) as client:
        data = client.get("/api/account/overview").json()
    assert data["user"]["email"] == "" and data["user"]["password"] is False


def test_trial_code_is_labelled_as_trial(monkeypatch):
    user = _user(is_pro=1, pro_until=time.time() + 3600, pro_code="SM-TRIAL-XYZ")
    with _client(monkeypatch, user) as client:
        plan = client.get("/api/account/overview").json()["plan"]
    assert plan["trial"] and plan["days_left"] == 0


# ---------------------------------------------------------------- avatar (POST / DELETE /api/account/avatar)
def _still(mode="RGB", size=(900, 600), color="#3366cc"):
    out = io.BytesIO()
    Image.new(mode, size, color).save(out, format="PNG")
    return out.getvalue()


def _animation(size=(48, 48), frames=3, noise=False):
    """Animated GIF. With ``noise`` the frames do not compress, so the size is easy to push over a limit."""
    rng = random.Random(7)
    if noise:
        images = [Image.frombytes("L", size, rng.randbytes(size[0] * size[1])) for _ in range(frames)]
    else:
        images = [Image.new("RGB", size, color) for color in ("#ff4477", "#3377dd", "#22cc88")[:frames]]
    out = io.BytesIO()
    images[0].save(out, format="GIF", save_all=True, append_images=images[1:], duration=90, loop=0, optimize=False)
    return out.getvalue()


def _avatar_client(monkeypatch, tmp_path, user):
    """The account router with avatar files under tmp_path and no object storage."""
    monkeypatch.setattr(account, "DATA", tmp_path)
    monkeypatch.setattr(core, "DATA", tmp_path)
    monkeypatch.setattr(account.object_store, "configured", lambda: False)
    return _client(monkeypatch, user)


def _upload(client, raw, name="avatar.png", mime="image/png"):
    return client.post("/api/account/avatar", files={"file": (name, raw, mime)})


def _avatar_files(tmp_path):
    folder = tmp_path / "avatars"
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def test_avatar_routes_need_a_session(monkeypatch, tmp_path):
    with _avatar_client(monkeypatch, tmp_path, None) as client:
        upload = _upload(client, _still())
        removal = client.delete("/api/account/avatar")
    assert upload.status_code == 401 and upload.json()["code"] == "login"
    assert removal.status_code == 401 and removal.json()["code"] == "login"
    assert _avatar_files(tmp_path) == []


def test_opaque_picture_is_saved_as_a_512_px_jpeg(monkeypatch, tmp_path):
    user = _user()
    uid = user["id"]
    with _avatar_client(monkeypatch, tmp_path, user) as client:
        response = _upload(client, _still(size=(900, 600)))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] and re.fullmatch(rf"/api/auth/avatar/{uid}\?v=[0-9a-f]{{8}}", body["avatar_url"])
    stored = auth_db.user_avatar_path(uid)
    assert re.fullmatch(rf"avatars/{uid}-[0-9a-f]{{12}}\.jpg", stored)
    with Image.open(tmp_path / stored) as saved:
        assert saved.format == "JPEG" and saved.width == 512 and saved.height < 512
    assert _avatar_files(tmp_path) == [Path(stored).name]


def test_transparent_picture_stays_a_png(monkeypatch, tmp_path):
    user = _user()
    with _avatar_client(monkeypatch, tmp_path, user) as client:
        assert _upload(client, _still(mode="RGBA", size=(300, 700), color=(40, 120, 255, 0))).status_code == 200
    stored = auth_db.user_avatar_path(user["id"])
    assert stored.endswith(".png")
    with Image.open(tmp_path / stored) as saved:
        assert saved.format == "PNG" and saved.mode == "RGBA" and saved.height == 512 and saved.width < 512
        assert saved.getpixel((0, 0))[3] == 0, "transparency survives the resize"


def test_small_animation_is_kept_frame_for_frame(monkeypatch, tmp_path):
    user = _user()
    raw = _animation()
    with _avatar_client(monkeypatch, tmp_path, user) as client:
        assert _upload(client, raw, "avatar.gif", "image/gif").status_code == 200
    stored = auth_db.user_avatar_path(user["id"])
    assert stored.endswith(".gif")
    assert (tmp_path / stored).read_bytes() == raw
    with Image.open(tmp_path / stored) as saved:
        assert saved.n_frames == 3


def test_bad_uploads_are_rejected_with_a_code_and_save_nothing(monkeypatch, tmp_path):
    heavy_animation = _animation(size=(700, 700), frames=7, noise=True)
    assert account.AVATAR_MAX_ANIMATED < len(heavy_animation) <= account.AVATAR_MAX_UPLOAD
    huge_canvas = _still(mode="L", size=(4100, 4100), color=128)     # 16.8 megapixels in a small file
    assert len(huge_canvas) < account.AVATAR_MAX_UPLOAD
    cases = (
        (b"\0" * (account.AVATAR_MAX_UPLOAD + 1), 413, "too_big"),
        (heavy_animation, 400, "animated_too_big"),
        (huge_canvas, 400, "too_large"),
        (b"this is not a picture", 400, "bad_image"),
    )
    user = _user()
    with _avatar_client(monkeypatch, tmp_path, user) as client:
        for raw, status, code in cases:
            response = _upload(client, raw)
            assert (response.status_code, response.json()) == (status, {"ok": False, "code": code}), code
    assert auth_db.user_avatar_path(user["id"]) == ""
    assert _avatar_files(tmp_path) == []


def test_rejected_upload_keeps_the_current_avatar(monkeypatch, tmp_path):
    user = _user()
    with _avatar_client(monkeypatch, tmp_path, user) as client:
        assert _upload(client, _still()).status_code == 200
        stored = auth_db.user_avatar_path(user["id"])
        assert _upload(client, b"this is not a picture").status_code == 400
    assert auth_db.user_avatar_path(user["id"]) == stored
    assert (tmp_path / stored).is_file()


def test_replacement_removes_the_previous_file(monkeypatch, tmp_path):
    user = _user()
    with _avatar_client(monkeypatch, tmp_path, user) as client:
        assert _upload(client, _still(color="#ff3388")).status_code == 200
        first = auth_db.user_avatar_path(user["id"])
        assert _upload(client, _still(color="#3344cc")).status_code == 200
    second = auth_db.user_avatar_path(user["id"])
    assert second and second != first
    assert _avatar_files(tmp_path) == [Path(second).name]


def test_removal_clears_the_row_and_only_this_users_files(monkeypatch, tmp_path):
    user = _user()
    uid = user["id"]
    with _avatar_client(monkeypatch, tmp_path, user) as client:
        assert _upload(client, _still()).status_code == 200
        folder = tmp_path / "avatars"
        (folder / f"{uid}.png").write_bytes(_still(size=(8, 8)))          # legacy name /api/auth/avatar falls back to
        neighbours = [f"{uid}0.png", f"{uid}0-abcdef.png", f"1{uid}.png"]   # other ids that merely share the digits
        for name in neighbours:
            (folder / name).write_bytes(_still(size=(8, 8)))
        response = client.delete("/api/account/avatar")
    assert response.status_code == 200 and response.json() == {"ok": True, "avatar_url": ""}
    assert auth_db.user_avatar_path(uid) == ""
    assert _avatar_files(tmp_path) == sorted(neighbours)


def test_avatar_route_has_its_own_rate_limit():
    rule = next((prefix for prefix, _limit, _window in RateLimitMiddleware.RULES
                 if "/api/account/avatar".startswith(prefix)), None)
    assert rule == "/api/account/avatar"


def test_pages_load_the_uploader_and_it_explains_every_server_code():
    script = (ROOT / "static/js/avatar-upload.js").read_text(encoding="utf-8")
    router = (ROOT / "smweb/routers/account.py").read_text(encoding="utf-8")
    for code in ("login", "too_big", "animated_too_big", "too_large", "bad_image", "failed"):
        assert f'"{code}"' in router, code
        assert f" {code}: '" in script, f"avatar-upload.js has no text for {code}"
    for page, page_script in (("account.html", "/static/js/account-page.js"), ("profile.html", "/static/js/profile.js")):
        html = (ROOT / "static" / page).read_text(encoding="utf-8")
        assert "/static/js/avatar-upload.js" in html, page
        assert html.index("/static/js/avatar-upload.js") < html.index(page_script), f"{page}: uploader must load first"
