import hashlib
import sys
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

import redis_store as rs
from smweb import media_assets
from smweb import process_control
from smweb.routers import assets
from smweb.routers import jobs
from starlette.routing import Match


def test_job_event_stream_is_not_shadowed_by_job_detail():
    scope = {"type": "http", "path": "/api/jobs/events", "method": "GET"}
    matched = next(route for route in jobs.router.routes if route.matches(scope)[0] == Match.FULL)
    assert matched.endpoint is jobs.events


def test_job_actions_reject_active_retry_and_unsupported_cancellation(monkeypatch):
    app = FastAPI()
    app.include_router(jobs.router)
    client = TestClient(app)
    job = {"kind": "process", "status": "running"}
    monkeypatch.setattr(jobs, "_owned", lambda request, jid: job)
    def unexpected(*args, **kwargs):
        raise AssertionError("Rejected action must not mutate the job or dispatch work")
    monkeypatch.setattr(rs, "job_create", unexpected)
    monkeypatch.setattr(rs, "job_cancel", unexpected)
    jid = "a" * 24
    assert client.post(f"/api/jobs/{jid}/retry").status_code == 409
    for kind, status in [("upscale", "running"), ("process", "done"), ("process", "cancelled")]:
        job.update(kind=kind, status=status)
        assert client.post(f"/api/jobs/{jid}/cancel").status_code == 409


def test_job_actions_hide_other_users_jobs(monkeypatch):
    app = FastAPI()
    app.include_router(jobs.router)
    monkeypatch.setattr(jobs, "_owner", lambda request: "owner")
    monkeypatch.setattr(jobs, "_auth_user", lambda request: None)
    monkeypatch.setattr(rs, "job_get", lambda jid: {"user_key": "someone-else"})
    client = TestClient(app)
    jid = "b" * 24
    assert client.get(f"/api/jobs/{jid}").status_code == 404
    for action in ["retry", "cancel"]:
        assert client.post(f"/api/jobs/{jid}/{action}").status_code == 404


def test_scoped_job_history_and_owner_isolation(monkeypatch):
    monkeypatch.setattr(jobs, "_owner", lambda request: "42")
    monkeypatch.setattr(jobs, "_auth_user", lambda request: {"id": 42})
    jid = "d" * 24
    record = {"user_key": "builder-bg:42", "kind": "builder_bg_remove", "status": "running"}
    monkeypatch.setattr(rs, "job_get", lambda key: record)
    monkeypatch.setattr(rs, "job_list_user", lambda owner, limit: [(jid, record)] if owner == record["user_key"] else [])
    monkeypatch.setattr(rs, "queue_depths", lambda: {})
    app = FastAPI()
    app.include_router(jobs.router)
    client = TestClient(app)
    history = client.get("/api/jobs").json()["jobs"]
    assert [row["id"] for row in history] == [jid]
    assert history[0]["can_cancel"] is False  # Cannot cancel a paid upstream call.
    assert client.get(f"/api/jobs/{jid}").status_code == 200
    record["user_key"] = "builder-bg:43"
    assert client.get(f"/api/jobs/{jid}").status_code == 404
    assert client.get("/api/jobs").json()["jobs"] == []


def test_retry_rechecks_quota_concurrency_and_current_watermark(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "JOBS", tmp_path / "jobs")
    source = tmp_path / "input.png"
    source.write_bytes(b"fixture")
    old = {"kind": "process", "status": "done", "user_key": "42",
           "files": [{"path": str(source)}], "opts": {"text": "", "opacity": 0}}
    quota = {"pro": False, "left": 0, "user_id": 42, "email": "test@example.invalid"}
    active = {"count": 0}
    created, charged = [], []
    monkeypatch.setattr(jobs, "_owned", lambda request, jid: old)
    monkeypatch.setattr(jobs, "_owner", lambda request: "42")
    monkeypatch.setattr(jobs, "quota_state", lambda request: quota)
    monkeypatch.setattr(jobs, "max_jobs_for_user", lambda uid: 2)
    monkeypatch.setattr(rs, "job_count_user", lambda owner: active["count"])
    monkeypatch.setattr(rs, "rate_limit", lambda *args, **kwargs: (True, 0))
    monkeypatch.setattr(rs, "job_create", lambda jid, payload, **kwargs: created.append(payload))
    monkeypatch.setattr(jobs, "quota_inc", lambda request, n: charged.append(n))
    monkeypatch.setattr(jobs, "_worker_mode", lambda: "embedded")
    monkeypatch.setattr(jobs, "_dispatch_embedded", lambda *args: None)
    app = FastAPI()
    app.include_router(jobs.router)
    client = TestClient(app)
    url = "/api/jobs/" + "c" * 24 + "/retry"
    assert client.post(url).status_code == 403
    quota["left"] = 5
    active["count"] = 2
    assert client.post(url).status_code == 429
    assert created == charged == []
    active["count"] = 0
    assert client.post(url).status_code == 202
    assert charged == [1]
    assert created[0]["opts"]["text"] == "ShowcaseMaker"
    assert created[0]["opts"]["opacity"] == 0.5
    assert old["opts"]["opacity"] == 0
    retried_source = __import__("pathlib").Path(created[0]["files"][0]["path"])
    assert retried_source != source
    source.unlink()
    assert retried_source.read_bytes() == b"fixture"


def test_resumable_asset_upload_and_owner_isolation(tmp_path, monkeypatch):
    monkeypatch.setattr(media_assets, "ROOT", tmp_path / "assets")
    app = FastAPI()
    app.include_router(assets.router)
    owner = TestClient(app)

    created = owner.post("/api/assets/uploads", json={
        "name": "scene.png", "size": 6, "type": "image/png",
    })
    assert created.status_code == 201
    upload_id = created.json()["upload"]["id"]

    first = owner.patch(
        f"/api/assets/uploads/{upload_id}", content=b"abc",
        headers={"Upload-Offset": "0", "Content-Type": "application/offset+octet-stream"},
    )
    assert first.status_code == 204
    assert first.headers["upload-offset"] == "3"

    mismatch = owner.patch(
        f"/api/assets/uploads/{upload_id}", content=b"def",
        headers={"Upload-Offset": "0", "Content-Type": "application/offset+octet-stream"},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["offset"] == 3

    # Simulate a connection dying after bytes reached disk but before its
    # offset metadata was committed. The retry must replace that orphan tail.
    with (media_assets.ROOT / upload_id / "upload.part").open("ab") as partial:
        partial.write(b"ZZ")
    assert owner.patch(
        f"/api/assets/uploads/{upload_id}", content=b"def",
        headers={"Upload-Offset": "3", "Content-Type": "application/offset+octet-stream"},
    ).status_code == 204
    completed = owner.post(
        f"/api/assets/uploads/{upload_id}/complete",
        json={"sha256": hashlib.sha256(b"abcdef").hexdigest()},
    )
    assert completed.status_code == 200
    assert completed.json()["asset"]["status"] == "ready"
    assert owner.get(f"/api/assets/{upload_id}/content").content == b"abcdef"

    assert media_assets.resolve(upload_id, "ip:203.0.113.9") is None


def test_job_history_cache_and_queued_cancellation(monkeypatch):
    monkeypatch.setattr(rs, "_r", lambda: None)
    with rs._local_lock:
        rs._local_jobs.clear()
        rs._local_job_cache.clear()

    rs.job_create("a" * 24, {"kind": "process", "user_key": "owner"}, enqueue=False)
    rs.job_update("a" * 24, status="done", pct=100)
    history = rs.job_list_user("owner")
    assert history and history[0][1]["status"] == "done"

    rs.job_cache_put("fingerprint", "a" * 24)
    assert rs.job_cache_get("fingerprint") == "a" * 24

    rs.job_create("b" * 24, {"kind": "compose", "user_key": "owner"}, enqueue=False)
    cancelled = rs.job_cancel("b" * 24)
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancel_requested"] is True


def test_explicit_queue_assignment(monkeypatch):
    monkeypatch.setattr(rs, "_r", lambda: None)
    with rs._local_lock:
        rs._local_jobs.clear()
    rs.job_create("c" * 24, {"kind": "process", "user_key": "u"}, enqueue=False)
    rs.job_create("d" * 24, {"kind": "upscale", "user_key": "u"}, enqueue=False)
    rs.job_create("e" * 24, {"kind": "profile_insight", "user_key": "u"}, enqueue=False)
    assert rs.job_get("c" * 24)["queue"] == "media"
    assert rs.job_get("d" * 24)["queue"] == "gpu"
    assert rs.job_get("e" * 24)["queue"] == "profile"


def test_running_subprocess_is_actually_terminated_on_cancel(monkeypatch):
    checks = {"count": 0}

    def job_get(_jid):
        checks["count"] += 1
        return {"cancel_requested": checks["count"] >= 3}

    monkeypatch.setattr(process_control.rs, "job_get", job_get)
    started = time.monotonic()
    try:
        process_control.run(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            job_id="f" * 24, capture_output=True,
        )
        raise AssertionError("cancelled command returned normally")
    except process_control.JobCancelled:
        pass
    assert time.monotonic() - started < 4
