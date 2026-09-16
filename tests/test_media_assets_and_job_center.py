import hashlib
import sys
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

import redis_store as rs
from smweb import media_assets
from smweb import process_control
from smweb.routers import assets


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
