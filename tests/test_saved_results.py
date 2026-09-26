import io
import time
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import auth_db
from smweb import object_store, saved_results
from smweb.routers import results as results_routes


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "USING_POSTGRES", False)
    monkeypatch.setattr(auth_db, "DB", tmp_path / "users.db")
    monkeypatch.setattr(auth_db, "_SCHEMA_READY", False)
    monkeypatch.setattr(saved_results, "ROOT", tmp_path / "results")
    monkeypatch.setattr(object_store, "configured", lambda: False)
    connection = auth_db._conn()
    ids = []
    for email in ("one@example.invalid", "two@example.invalid"):
        connection.execute(
            "INSERT INTO users(email,password_hash,is_pro,email_verified,created_at) VALUES (?,?,?,?,?)",
            (email, "test", 0, 1, time.time()),
        )
    connection.commit()
    ids = [int(row["id"]) for row in connection.execute("SELECT id FROM users ORDER BY id").fetchall()]
    connection.close()
    return ids


def _zip(tmp_path, name="result.zip"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as archive:
        for index in range(1, 6):
            data = io.BytesIO()
            Image.new("RGBA", (150, 150), (index * 40, 20, 200, 255)).save(data, "PNG")
            archive.writestr(f"art_workshop/part_{index}.png", data.getvalue())
        archive.writestr("art_workshop/source.png", b"ignored")
    return path


def _client(user_id):
    app = FastAPI()
    app.include_router(results_routes.router)
    results_routes._auth_user = lambda request: {"id": user_id} if user_id else None
    return TestClient(app)


def test_signed_in_result_is_kept_with_thumbnail_and_anonymous_is_not(monkeypatch, tmp_path):
    user_id, _other = _setup(monkeypatch, tmp_path)
    archive = _zip(tmp_path)
    assert saved_results.save_job_result("a" * 24, user_key="203.0.113.7", zip_path=archive, kind="process") is None
    rid = saved_results.save_job_result("a" * 24, user_key=str(user_id), zip_path=archive, kind="process",
                                        mode="workshop", title="art", file_count=1)
    assert rid and saved_results.RESULT_ID.fullmatch(rid)
    # A second save of the same job (cached re-run) does not duplicate storage.
    assert saved_results.save_job_result("a" * 24, user_key=str(user_id), zip_path=archive, kind="process") is None
    rows = auth_db.saved_results_for_user(user_id)
    assert [row["id"] for row in rows] == [rid]
    assert len(list((tmp_path / "results" / str(user_id)).glob("*.zip"))) == 1
    thumb = saved_results.thumb_path(user_id, rid)
    with Image.open(thumb) as image:
        assert image.format == "WEBP" and image.height == 120 and image.width > 5 * 100
    public = saved_results.public_row(rows[0])
    assert public["download_url"] == f"/api/results/{rid}/download" and public["thumb_url"]
    assert "zip_ref" not in public and "storage" not in public


def test_per_user_cap_and_expiry_remove_files(monkeypatch, tmp_path):
    user_id, _other = _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(saved_results, "MAX_PER_USER", 2)
    archive = _zip(tmp_path)
    ids = []
    for index in range(3):
        ids.append(saved_results.save_job_result(f"{index:024x}", user_key=str(user_id), zip_path=archive, kind="process"))
        time.sleep(0.01)
    kept = [row["id"] for row in auth_db.saved_results_for_user(user_id)]
    assert kept == [ids[2], ids[1]]
    folder = tmp_path / "results" / str(user_id)
    assert not (folder / f"{ids[0]}.zip").exists() and not (folder / f"{ids[0]}.webp").exists()

    connection = auth_db._conn()
    connection.execute("UPDATE saved_results SET expires_at=? WHERE id=?", (time.time() - 1, ids[1]))
    connection.commit()
    connection.close()
    assert saved_results.cleanup_expired() == 1
    assert [row["id"] for row in auth_db.saved_results_for_user(user_id)] == [ids[2]]
    assert not (folder / f"{ids[1]}.zip").exists()


def test_http_routes_are_owner_only(monkeypatch, tmp_path):
    user_id, other_id = _setup(monkeypatch, tmp_path)
    previous = results_routes._auth_user
    try:
        rid = saved_results.save_job_result("b" * 24, user_key=str(user_id), zip_path=_zip(tmp_path),
                                            kind="workshop_studio", title="my art!")
        assert _client(None).get("/api/results").status_code == 401

        owner = _client(user_id)
        listing = owner.get("/api/results").json()
        assert listing["ok"] and listing["keep_days"] == saved_results.KEEP_DAYS
        assert [item["id"] for item in listing["items"]] == [rid]
        download = owner.get(f"/api/results/{rid}/download")
        assert download.status_code == 200 and download.content[:2] == b"PK"
        assert "showcase_my_art.zip" in download.headers["content-disposition"]
        assert owner.get(f"/api/results/{rid}/thumb").headers["content-type"] == "image/webp"

        stranger = _client(other_id)
        assert stranger.get("/api/results").json()["items"] == []
        assert stranger.get(f"/api/results/{rid}/download").status_code == 404
        assert stranger.delete(f"/api/results/{rid}").status_code == 404
        assert _client(user_id).get("/api/results/../../etc/download").status_code == 404

        assert _client(user_id).delete(f"/api/results/{rid}").json() == {"ok": True}
        assert auth_db.saved_results_for_user(user_id) == []
        assert not list((tmp_path / "results" / str(user_id)).iterdir())
    finally:
        results_routes._auth_user = previous


def test_local_zip_reference_cannot_escape_owner_folder(monkeypatch, tmp_path):
    user_id, _other = _setup(monkeypatch, tmp_path)
    secret = tmp_path / "results" / "secret.zip"
    secret.parent.mkdir(parents=True)
    secret.write_bytes(b"PK")
    row = {"id": "c" * 24, "user_id": user_id, "storage": "local", "zip_ref": "../secret.zip"}
    assert saved_results.local_zip_path(row) is None


def test_account_deletion_and_export_cover_saved_results(monkeypatch, tmp_path):
    user_id, _other = _setup(monkeypatch, tmp_path)
    rid = saved_results.save_job_result("d" * 24, user_key=str(user_id), zip_path=_zip(tmp_path), kind="process")
    exported = auth_db.account_export_data(user_id)
    assert [item["id"] for item in exported["saved_results"]] == [rid]
    assert "zip_ref" not in exported["saved_results"][0]
    auth_db.delete_account_data(user_id)
    connection = auth_db._conn()
    assert connection.execute("SELECT COUNT(*) AS n FROM saved_results").fetchone()["n"] == 0
    connection.close()
