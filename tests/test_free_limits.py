"""Free tier: weekly tries, beta features for Pro only, Builder exports per day (2026-10-06)."""
import secrets
import time
from datetime import datetime, timezone

import pytest

import auth_db
from smweb import free_limits as fl

TUESDAY = datetime(2026, 10, 6, 15, 30, tzinfo=timezone.utc).timestamp()
NEXT_MONDAY = datetime(2026, 10, 12, tzinfo=timezone.utc).timestamp()
WEEK = 7 * 86400


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    for name in ("FREE_WEEKLY_USES", "BUILDER_EXPORTS_PER_DAY", "BETA_FEATURES"):
        monkeypatch.delenv(name, raising=False)


def _uid():
    return 10_000_000 + secrets.randbelow(900_000_000)


def _ip():
    return ".".join(str(secrets.randbelow(250) + 1) for _ in range(4))


# ---------------------------------------------------------------- the rules (no HTTP)
def test_week_runs_from_monday_to_monday_utc():
    assert fl.week(TUESDAY) == "2026-W41" and fl.week_resets_at(TUESDAY) == NEXT_MONDAY
    assert fl.week(NEXT_MONDAY - 1) == "2026-W41" and fl.week(NEXT_MONDAY) == "2026-W42"
    assert fl.week_resets_at(NEXT_MONDAY) == NEXT_MONDAY + WEEK
    assert fl.day_resets_at(TUESDAY) == datetime(2026, 10, 7, tzinfo=timezone.utc).timestamp()


def test_one_use_a_week_per_tool_and_it_returns_on_monday():
    uid, ip = _uid(), _ip()
    assert fl.left("loop", uid, ip, TUESDAY) == 1
    assert fl.consume("loop", uid, ip, TUESDAY) is True
    assert fl.left("loop", uid, ip, TUESDAY) == 0 and fl.consume("loop", uid, ip, TUESDAY) is False
    assert fl.left("design", uid, ip, TUESDAY) == 1, "every tool has its own weekly use"
    assert fl.left("loop", uid, ip, NEXT_MONDAY - 1) == 0
    assert fl.left("loop", uid, ip, NEXT_MONDAY) == 1 and fl.consume("loop", uid, ip, NEXT_MONDAY) is True


def test_second_account_from_the_same_address_gets_no_second_try():
    first, second, ip = _uid(), _uid(), _ip()
    assert fl.consume("bg", first, ip, TUESDAY)
    assert fl.left("bg", second, ip, TUESDAY) == 0 and fl.consume("bg", second, ip, TUESDAY) is False
    # ...and the refused attempt spent nothing for that second account elsewhere.
    assert fl.left("bg", second, _ip(), TUESDAY) == 1


def test_same_account_from_another_address_gets_no_second_try():
    uid = _uid()
    assert fl.consume("da", uid, _ip(), TUESDAY)
    other_ip = _ip()
    assert fl.consume("da", uid, other_ip, TUESDAY) is False
    assert fl.left("da", _uid(), other_ip, TUESDAY) == 1, "the refused attempt did not burn the new address"


def test_failed_job_gives_the_use_back_once(monkeypatch):
    import redis_store as rs
    uid, ip = _uid(), _ip()
    now = time.time()
    assert fl.consume("dna", uid, ip, now)
    ticket = fl.ticket("dna", uid, ip, now)
    assert ticket == {"feature": "dna", "subjects": fl.subjects(uid, ip), "period": fl.week(now)}
    marks = []
    monkeypatch.setattr(rs, "_job_update", lambda jid, **kw: marks.append((jid, kw)))
    fl.refund_job("job-1", {"free_try": ticket})
    assert marks == [("job-1", {"free_try_refunded": True})] and fl.left("dna", uid, ip, now) == 1
    fl.refund_job("job-1", {"free_try": ticket, "free_try_refunded": True})
    fl.refund_job("job-2", {})
    fl.refund_job("job-3", None)
    assert len(marks) == 1
    # A second refund of the same ticket cannot create a use out of nothing.
    assert fl.refund_ticket(ticket) is True and fl.left("dna", uid, ip, now) == 1
    assert fl.consume("dna", uid, ip, now) and fl.consume("dna", uid, ip, now) is False
    assert fl.refund_ticket(None) is False and fl.refund_ticket({"subjects": ["u:1"]}) is False


def test_error_status_of_a_job_triggers_the_refund(monkeypatch):
    import redis_store as rs
    uid, ip = _uid(), _ip()
    now = time.time()
    assert fl.consume("loop", uid, ip, now)
    job = {"kind": "seamless_loop", "free_try": fl.ticket("loop", uid, ip, now)}
    writes = []
    monkeypatch.setattr(rs, "_job_update", lambda jid, **kw: writes.append(kw))
    monkeypatch.setattr(rs, "job_get", lambda jid: dict(job))
    rs.job_update("j" * 32, status="running", pct=10)
    assert fl.left("loop", uid, ip, now) == 0
    rs.job_update("j" * 32, status="error", error="Loop processing failed")
    assert fl.left("loop", uid, ip, now) == 1 and {"free_try_refunded": True} in writes


def test_address_is_stored_only_as_a_keyed_hash():
    ip = "203.0.113.77"
    subject = fl.subjects(None, ip)[0]
    assert subject.startswith("ip:") and ip not in subject and len(subject) == 27
    assert fl.subjects(5, ip) == ["u:5", subject] and fl.subjects(None, "") == []
    assert fl.consume("loop", None, "", TUESDAY) is False and fl.left("loop", None, None) == 0
    assert fl.consume("upscale", _uid(), _ip()) is False, "Upscale has no free try"


def test_owner_can_raise_the_weekly_number(monkeypatch):
    monkeypatch.setenv("FREE_WEEKLY_USES", "2")
    uid, ip = _uid(), _ip()
    assert [fl.consume("doctor", uid, ip, TUESDAY) for _ in range(3)] == [True, True, False]
    monkeypatch.setenv("FREE_WEEKLY_USES", "nonsense")
    assert fl.weekly_limit() == 1


def test_beta_list_comes_from_the_environment(monkeypatch):
    assert fl.beta_features() == ("aianim", "gifopt") and fl.is_beta("gifopt") and fl.is_beta("aianim") and not fl.is_beta("loop")
    monkeypatch.setenv("BETA_FEATURES", " Loop, gifopt ,,")
    assert fl.beta_features() == ("gifopt", "loop")
    monkeypatch.setenv("BETA_FEATURES", "")
    assert fl.beta_features() == () and not fl.is_beta("gifopt")


def test_state_for_the_pages():
    uid, ip = _uid(), _ip()
    assert fl.consume("loop", uid, ip)
    free = fl.state(uid, ip, pro=False)
    assert free["pro"] is False and free["beta"] == ["aianim", "gifopt"] and free["weekly_limit"] == 1
    assert free["weekly"]["loop"] == {"limit": 1, "left": 0} and free["weekly"]["design"] == {"limit": 1, "left": 1}
    assert set(free["weekly"]) == set(fl.WEEKLY_FEATURES)
    assert free["builder"] == {"limit": 3, "left": 3}
    assert free["week_resets_at"] > time.time() and free["day_resets_at"] > time.time()
    guest = fl.state(None, ip, pro=False)
    assert guest["weekly"]["loop"]["left"] == 0 and "builder" not in guest, "the address is already spent"
    pro = fl.state(uid, ip, pro=True)
    assert pro["pro"] is True and "weekly" not in pro and pro["beta"] == ["aianim", "gifopt"]


def test_builder_gives_three_exports_a_day(monkeypatch):
    email = f"fl-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        uid = int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
    finally:
        c.close()
    limit = fl.builder_exports_per_day()
    assert limit == 3
    results = [auth_db.consume_builder_render(uid, is_pro=False, limit=limit) for _ in range(4)]
    assert results == [(True, 2), (True, 1), (True, 0), (False, 0)]
    assert auth_db.consume_builder_render(uid, is_pro=True, limit=limit) == (True, None)
    assert fl.state(uid, _ip(), pro=False)["builder"] == {"limit": 3, "left": 0}
    monkeypatch.setenv("BUILDER_EXPORTS_PER_DAY", "5")
    assert fl.builder_exports_per_day() == 5


def test_deleting_the_account_removes_its_counters():
    email = f"fl-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        uid = int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
    finally:
        c.close()
    ip = _ip()
    assert fl.consume("loop", uid, ip)
    auth_db.delete_account_data(uid)
    c = auth_db._conn()
    try:
        rows = c.execute("SELECT COUNT(*) AS n FROM feature_uses WHERE subject=?", (f"u:{uid}",)).fetchone()["n"]
    finally:
        c.close()
    assert rows == 0 and fl.left("loop", None, ip) == 0, "the address stays counted: re-registering gives no new try"


def test_every_refusal_text_exists_in_all_eight_languages():
    languages = {"en", "ru", "de", "tr", "fr", "uk", "es", "pt"}
    for kind, texts in fl.MESSAGES.items():
        assert set(texts) == languages, kind
        assert all(text.strip() for text in texts.values()), kind
    assert "{n}" not in fl.message("daily", "ru", n=5) and "5" in fl.message("daily", "ru", n=5)
    assert fl.message("weekly", "xx") == fl.MESSAGES["weekly"]["en"]
    assert set(fl._STATUS) == set(fl.MESSAGES)


# ---------------------------------------------------------------- HTTP
def _app(*routers):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    for router in routers:
        app.include_router(router)
    return TestClient(app)


def test_refusal_carries_text_in_the_visitors_language_and_what_the_dialog_needs():
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    app = FastAPI()

    @app.get("/refuse/{kind}")
    def refuse(kind: str, request: Request):
        return fl.refusal(request, kind, "loop", n=5, **({"code": "limit"} if kind == "weekly" else {}))

    with TestClient(app) as client:
        weekly = client.get("/refuse/weekly", cookies={"sm_lang": "ru"})
        assert weekly.status_code == 429
        body = weekly.json()
        assert body["ok"] is False and body["code"] == "limit" and body["msg"] == fl.MESSAGES["weekly"]["ru"]
        assert body["limit"]["kind"] == "weekly" and body["limit"]["feature"] == "loop" and body["limit"]["resets_at"] > time.time()
        beta = client.get("/refuse/beta", headers={"Accept-Language": "de"})
        assert beta.status_code == 403 and beta.json()["code"] == "beta" and beta.json()["msg"] == fl.MESSAGES["beta"]["de"]
        assert beta.json()["limit"] == {"kind": "beta", "feature": "loop", "resets_at": None}
        builder = client.get("/refuse/builder").json()
        assert builder["code"] == "builder_limit" and builder["remaining"] == 0 and "5" in builder["msg"]
        more = client.get("/refuse/daily_more")
        assert more.status_code == 403 and more.json()["code"] == "quota" and more.json()["limit"]["kind"] == "daily"


def test_quota_endpoint_reports_weekly_tries(monkeypatch):
    from smweb.routers import system
    uid, ip = _uid(), _ip()
    monkeypatch.setattr(system, "quota_state", lambda request: {"pro": False, "used": 1, "limit": 5, "left": 4, "user_id": uid})
    monkeypatch.setattr("smweb.core._ip", lambda request: ip)
    assert fl.consume("design", uid, ip)
    with _app(system.router) as client:
        free = client.get("/api/quota").json()
    assert free["left"] == 4 and free["free"]["weekly"]["design"]["left"] == 0 and free["free"]["weekly"]["loop"]["left"] == 1
    assert free["free"]["beta"] == ["aianim", "gifopt"] and free["free"]["builder"]["limit"] == 3


def test_loop_is_open_to_a_free_account_once_a_week(monkeypatch, tmp_path):
    from smweb.routers import seamless_loop as loop
    uid, ip = _uid(), _ip()
    created = []
    monkeypatch.setattr(loop, "DATA", str(tmp_path))
    monkeypatch.setattr(loop, "_auth_user", lambda request: {"id": uid})
    monkeypatch.setattr(loop, "_ip", lambda request: ip)
    monkeypatch.setattr(loop.rs, "job_count_user", lambda owner: 0)
    monkeypatch.setattr(loop.rs, "rate_limit", lambda *a, **k: (True, 0))
    monkeypatch.setattr(loop.rs, "job_cache_get", lambda key: None)
    monkeypatch.setattr(loop, "_worker_mode", lambda: "external")
    monkeypatch.setattr(loop.rs, "redis_ok", lambda: True)
    monkeypatch.setattr(loop.rs, "worker_alive", lambda: True)
    monkeypatch.setattr(loop.rs, "job_create", lambda jid, payload, enqueue=True: created.append(payload))
    files = {"file": ("source.gif", b"GIF89a" + b"x" * 30, "image/gif")}
    with _app(loop.router) as client:
        first = client.post("/api/loop/start", files=files, data={"mode": "blend"})
        assert first.status_code == 202 and created[0]["free_try"]["feature"] == "loop"
        second = client.post("/api/loop/start", files=files, data={"mode": "blend"})
        assert second.status_code == 429 and second.json()["code"] == "weekly_limit" and second.json()["limit"]["kind"] == "weekly"
        assert client.post("/api/loop/preview", files=files, data={"mode": "blend"}).status_code == 429
    assert len(created) == 1
    # The job failed: the use comes back and the next start is accepted.
    fl.refund_ticket(created[0]["free_try"])
    with _app(loop.router) as client:
        assert client.post("/api/loop/start", files=files, data={"mode": "blend"}).status_code == 202


def test_design_selection_and_profile_rating_are_weekly_for_free(monkeypatch):
    from smweb.routers import profile_insights as pi
    uid, ip = _uid(), _ip()
    created = []
    monkeypatch.setattr(pi, "quota_state", lambda request: {"pro": False, "email": "a@b.c", "user_id": uid})
    monkeypatch.setattr(pi, "_ip", lambda request: ip)
    monkeypatch.setattr(pi, "configured", lambda: True)
    monkeypatch.setattr(pi, "_public_profile_url", lambda value: "https://steamcommunity.com/id/example")
    monkeypatch.setattr(pi.rs, "job_find_active", lambda *a, **k: None)
    monkeypatch.setattr(pi.rs, "rate_limit", lambda *a, **k: (True, 0))
    monkeypatch.setattr(pi.rs, "redis_ok", lambda: True)
    monkeypatch.setattr(pi.rs, "worker_alive", lambda: True)
    monkeypatch.setattr(pi.rs, "job_create", lambda jid, payload, enqueue=True: created.append(payload))
    monkeypatch.setenv("WORKER_MODE", "external")
    with _app(pi.router) as client:
        for kind in ("design", "doctor"):
            body = {"kind": kind, "url": "https://steamcommunity.com/id/example"}
            assert client.post("/api/profile-insights/start", json=body).json()["queued"] is True, kind
            again = client.post("/api/profile-insights/start", json=body)
            assert again.status_code == 429 and again.json()["code"] == "limit" and again.json()["limit"]["feature"] == kind
    assert [p["free_try"]["feature"] for p in created] == ["design", "doctor"]


def test_gif_optimizer_is_pro_only_while_it_is_in_beta(monkeypatch):
    from smweb.routers import gif_optimizer as api
    monkeypatch.setattr(api, "quota_state", lambda request: {"pro": False, "left": 5, "limit": 5})
    with _app(api.router) as client:
        response = client.post("/api/gif-optimizer/start", files={"file": ("a.gif", b"GIF89a", "image/gif")})
        assert response.status_code == 403 and response.json()["code"] == "beta"
        assert response.json()["limit"] == {"kind": "beta", "feature": "gifopt", "resets_at": None}
        monkeypatch.setenv("BETA_FEATURES", "")
        monkeypatch.setattr(api, "quota_state", lambda request: {"pro": False, "left": 0, "limit": 5})
        spent = client.post("/api/gif-optimizer/start", files={"file": ("a.gif", b"GIF89a", "image/gif")})
        assert spent.status_code == 403 and spent.json()["code"] == "quota" and spent.json()["limit"]["kind"] == "daily"


def test_builder_export_refusal_names_the_daily_number(monkeypatch):
    from smweb.routers import builder
    monkeypatch.setattr(builder, "_user", lambda request: ({"id": 1}, None))
    monkeypatch.setattr(builder.auth_db, "effective_pro", lambda user: False)
    monkeypatch.setattr(builder.auth_db, "consume_builder_render", lambda uid, is_pro=False, limit=3: (False, 0))
    with _app(builder.router) as client:
        response = client.post("/api/builder/reserve-export")
    assert response.status_code == 429 and response.json()["code"] == "builder_limit" and "3" in response.json()["msg"]
    assert response.json()["remaining"] == 0 and response.json()["limit"]["kind"] == "builder"


def test_deviantart_publication_is_weekly_for_free_and_a_failed_one_is_not_counted(monkeypatch):
    import requests
    from smweb.routers import deviantart
    uid, ip = _uid(), _ip()
    answers = {"status": "error", "error_description": "DeviantArt is down"}

    class _Response:
        status_code, text = 200, "{}"

        def json(self):
            return dict(answers)

    monkeypatch.setattr(requests, "post", lambda *a, **k: _Response())
    monkeypatch.setattr(deviantart, "_auth_user", lambda request: {"id": uid, "da_access_token": "token"})
    monkeypatch.setattr(deviantart, "_ip", lambda request: ip)
    files = [("file", ("a.png", b"\x89PNG fake", "image/png"))]
    with _app(deviantart.router) as client:
        failed = client.post("/api/da/upload", files=files).json()
        assert failed["ok"] is False and fl.left("da", uid, ip) == 1, "nothing was published: the use is kept"
        answers.clear()
        answers.update({"status": "success", "itemid": 5})
        assert client.post("/api/da/upload", files=files).json()["ok"] is True and fl.left("da", uid, ip) == 0
        again = client.post("/api/da/upload", files=files)
        assert again.status_code == 429 and again.json()["code"] == "weekly_limit" and again.json()["limit"]["feature"] == "da"


def test_background_removal_is_weekly_for_free_and_daily_for_pro(monkeypatch):
    import redis_store as rs
    from smweb.routers import builder
    uid, ip = _uid(), _ip()
    pro = {"value": False}
    monkeypatch.setattr(builder, "_user", lambda request: ({"id": uid}, None))
    monkeypatch.setattr(builder, "_ip", lambda request: ip)
    monkeypatch.setattr(builder.auth_db, "effective_pro", lambda user: pro["value"])
    monkeypatch.setattr(builder.remove_bg_client, "configured", lambda: True)
    monkeypatch.setattr(builder._remove_pool, "submit", lambda *a, **k: None)
    monkeypatch.setattr(rs, "job_find_active", lambda *a, **k: None)
    body = {"url": "/api/builder/assets/" + "a" * 32 + ".png"}
    with _app(builder.router) as client:
        first = client.post("/api/builder/remove-background", json=body)
        assert first.status_code == 200, first.text
        assert rs.job_get(first.json()["job_id"])["free_try"]["feature"] == "bg"
        second = client.post("/api/builder/remove-background", json=body)
        assert second.status_code == 429 and second.json()["code"] == "remove_bg_limit" and second.json()["limit"]["kind"] == "weekly"
        pro["value"] = True
        paid = client.post("/api/builder/remove-background", json=body)
        assert paid.status_code == 200 and "free_try" not in rs.job_get(paid.json()["job_id"])
