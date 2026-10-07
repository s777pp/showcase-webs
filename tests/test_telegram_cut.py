"""Cutting a file sent to the Telegram bot (smweb/telegram_cut.py, /api/bot-admin/cut/*), 2026-10-08."""
import io
import secrets
import zipfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import auth_db
import redis_store as rs
from smweb import telegram_billing as tb
from smweb import telegram_cut as tc
from smweb.routers import bot_admin

SECRET = "bot-secret-for-cut-tests-0123456789"
HEAD = {"X-Bot-Admin-Secret": SECRET}


class _Now:
    """Run the job in the calling thread, so a test can read the finished result."""
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("BOT_ADMIN_SECRET", SECRET)
    monkeypatch.setattr(tc, "_job_pool", _Now())
    monkeypatch.setattr(tc, "_worker_mode", lambda: "embedded")
    app = FastAPI()
    app.include_router(bot_admin.router)
    return TestClient(app)


def _tg():
    return str(10_000_000 + secrets.randbelow(900_000_000))


def _png(w=1000, h=300):
    image = Image.new("RGB", (w, h))
    for x in range(w):
        for y in range(0, h, 10):
            image.putpixel((x, y), (x % 256, (x // 4) % 256, 120))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _start(client, tg, mode="workshop", frame="none", data=None):
    return client.post("/api/bot-admin/cut/start", headers=HEAD,
                       data={"tg_id": tg, "mode": mode, "frame": frame},
                       files={"file": ("art.png", data or _png(), "image/png")})


def test_secret_is_required(client):
    tg = _tg()
    assert client.get(f"/api/bot-admin/cut/quota?tg_id={tg}").status_code == 403
    assert client.get(f"/api/bot-admin/cut/quota?tg_id={tg}", headers={"X-Bot-Admin-Secret": "wrong"}).status_code == 403
    assert client.get("/api/bot-admin/cut/quota?tg_id=abc", headers=HEAD).status_code == 400


def test_cut_a_picture_into_workshop_parts_and_download_the_zip(client):
    tg = _tg()
    assert client.get(f"/api/bot-admin/cut/quota?tg_id={tg}", headers=HEAD).json()["left"] == tc.quota(tg)["limit"]
    started = _start(client, tg, frame="line")
    assert started.status_code == 200, started.text
    job_id = started.json()["job_id"]
    status = client.get(f"/api/bot-admin/cut/status/{job_id}?tg_id={tg}", headers=HEAD).json()
    assert status["status"] == "done", status
    archive = client.get(f"/api/bot-admin/cut/download/{job_id}?tg_id={tg}", headers=HEAD)
    assert archive.status_code == 200 and archive.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(archive.content)).namelist()
    parts = sorted(n.rsplit("/", 1)[-1] for n in names if "part_" in n)
    assert [p.split(".")[0] for p in parts] == ["part_1", "part_2", "part_3", "part_4", "part_5"]
    # Only the Steam files: no preview (where the free watermark would be) and no copy of the original.
    assert not [n for n in names if "full_with" in n or "full_original" in n]
    # Another chat cannot see or download this job.
    other = _tg()
    assert client.get(f"/api/bot-admin/cut/status/{job_id}?tg_id={other}", headers=HEAD).status_code == 404
    assert client.get(f"/api/bot-admin/cut/download/{job_id}?tg_id={other}", headers=HEAD).status_code == 404


def test_free_daily_limit_per_telegram_user_and_pro_has_none(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_CUT_DAILY", "2")
    tg = _tg()
    small = _png(400, 120)
    assert _start(client, tg, mode="featured", data=small).json()["left"] == 1
    assert _start(client, tg, mode="featured", data=small).json()["left"] == 0
    refused = _start(client, tg, mode="featured", data=small)
    assert refused.status_code == 429 and refused.json()["code"] == "limit"
    # A Telegram user linked to a Pro account cuts without the daily limit.
    email = f"cut-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        uid = int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
        c.execute("UPDATE users SET is_pro=1, pro_until=NULL, telegram_id=? WHERE id=?", (tg, uid))
        c.commit()
    finally:
        c.close()
    assert tb.account_for(tg) == uid
    allowed = _start(client, tg, mode="featured", data=small)
    assert allowed.status_code == 200 and allowed.json()["pro"] is True and allowed.json()["left"] == -1


def test_bad_options_fall_back_and_empty_files_are_refused(client):
    tg = _tg()
    assert _start(client, tg, mode="nonsense", frame="laser").status_code == 200
    empty = client.post("/api/bot-admin/cut/start", headers=HEAD, data={"tg_id": tg},
                        files={"file": ("x.png", b"", "image/png")})
    assert empty.status_code == 400 and empty.json()["code"] == "empty"
    assert tc.job_for(tg, "../../etc") is None
