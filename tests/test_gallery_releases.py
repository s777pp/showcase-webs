"""Contract tests for the new community gallery; never touch the real data directory."""

import io
import zipfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import auth_db
from smweb import core
from smweb.routers import gallery, gallery_releases


def _png(color="#49b9dc", size=(64, 96)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


def _gif():
    output = io.BytesIO()
    frames = [Image.new("RGB", (64, 96), color) for color in ("#ff4477", "#3377dd")]
    frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:],
                   duration=100, loop=0)
    return output.getvalue()


def _zip(payload=None, name="part_1.png", mode="workshop"):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        if payload is not None:
            archive.writestr(name, payload)
        elif mode == "workshop":
            for index in range(1, 6):
                archive.writestr(f"part_{index}.png", _png(size=(150, 422)))
        elif mode == "split":
            archive.writestr("center_506.png", _png(size=(506, 422)))
            archive.writestr("side_100.png", _png(size=(100, 422)))
        else:
            archive.writestr("featured.png", _png(size=(630, 422)))
    return output.getvalue()


@pytest.fixture
def gallery_site(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "USING_POSTGRES", False)
    monkeypatch.setattr(auth_db, "DB", tmp_path / "users.db")
    monkeypatch.setattr(auth_db, "DATA", tmp_path)
    monkeypatch.setattr(auth_db, "_SCHEMA_READY", False)
    monkeypatch.setattr(core, "DATA", tmp_path)
    monkeypatch.setattr(gallery_releases, "DATA", tmp_path)
    monkeypatch.setattr(gallery, "DATA", tmp_path)
    monkeypatch.setattr(gallery_releases.object_store, "configured", lambda: False)
    monkeypatch.setattr(gallery_releases.rs, "rate_limit", lambda *_args, **_kwargs: (True, 0))
    monkeypatch.setattr(gallery_releases, "_auth_user", lambda request: {
        "owner": {"id": 1}, "visitor": {"id": 2},
    }.get(request.headers.get("x-session-token")))
    connection = auth_db._conn()
    connection.execute(
        "INSERT INTO users(id,email,password_hash,display_name,profile_username,created_at) "
        "VALUES (1,'owner@example.test','x','Owner','owner',0)"
    )
    connection.execute(
        "INSERT INTO users(id,email,password_hash,display_name,profile_username,created_at) "
        "VALUES (2,'visitor@example.test','x','Visitor','visitor',0)"
    )
    connection.commit()
    connection.close()
    app = FastAPI()
    app.include_router(gallery_releases.router)
    app.include_router(gallery.router)
    with TestClient(app) as client:
        yield client, tmp_path


def _publish(client, *, paid=False, animated=False, adult=False, mode="workshop", **fields):
    data = {"title": "My showcase", "description": "A finished work", "mode": mode,
            "rights_confirmed": "true", "is_paid": str(paid).lower(),
            "is_adult": str(adult).lower(), **fields}
    files = {"preview": ("preview.gif" if animated else "preview.png",
                         _gif() if animated else _png(),
                         "image/gif" if animated else "image/png")}
    if not paid:
        files["archive"] = ("ready.zip", _zip(mode=mode), "application/zip")
    return client.post("/api/gallery/works", data=data, files=files,
                       headers={"X-Session-Token": "owner"})


def test_free_release_preview_download_and_author_stats(gallery_site):
    client, data_dir = gallery_site
    response = _publish(client, mode="split", background_url="https://steamcommunity.com/market/listings/753/example")
    assert response.status_code == 200, response.text
    item_id = response.json()["id"]
    row = auth_db.gallery_get(item_id)
    assert row["release_version"] == 2 and row["status"] == "approved"
    assert row["archive_path"] and (data_dir / row["archive_path"]).is_file()
    assert client.get(f"/api/gallery/image/{item_id}").status_code == 200
    assert client.get(f"/api/gallery/works/{item_id}/thumb").status_code == 200

    blocked = client.get(f"/api/gallery/works/{item_id}/download")
    assert blocked.status_code == 401
    assert auth_db.gallery_get(item_id)["download_count"] == 0
    downloaded = client.get(f"/api/gallery/works/{item_id}/download",
                            headers={"X-Session-Token": "visitor"})
    assert downloaded.status_code == 200
    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
        assert archive.namelist() == ["center_506.png", "side_100.png"]
        assert archive.read("center_506.png") == _png(size=(506, 422))
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert auth_db.gallery_get(item_id)["download_count"] == 1

    listed = client.get("/api/gallery/works?mode=split&author=owner").json()
    assert listed["total"] == 1
    item = listed["items"][0]
    assert item["download_url"].endswith(f"/{item_id}/download")
    assert item["background_url"].startswith("https://steamcommunity.com/")
    assert listed["author"]["stats"] == {"works": 1, "downloads": 1, "likes": 0}


def test_paid_release_uses_external_sale_link_without_private_archive(gallery_site):
    client, _ = gallery_site
    response = _publish(client, paid=True, mode="featured",
                        sale_url="https://shop.example.test/sale?item=1")
    assert response.status_code == 200, response.text
    item_id = response.json()["id"]
    row = auth_db.gallery_get(item_id)
    assert row["is_paid"] == 1 and row["archive_path"] is None
    item = client.get(f"/api/gallery/works/{item_id}").json()["item"]
    assert item["paid"] is True and item["download_url"] == ""
    assert item["sale_url"] == "https://shop.example.test/sale?item=1"
    assert client.get(f"/api/gallery/works/{item_id}/download",
                      headers={"X-Session-Token": "visitor"}).status_code == 403


def test_filters_separate_showcase_mode_animation_and_legacy(gallery_site):
    client, _ = gallery_site
    static_id = _publish(client, mode="workshop").json()["id"]
    animated_id = _publish(client, mode="featured", animated=True, adult=True).json()["id"]
    legacy_id = auth_db.gallery_add(1, "Old gallery item", "featured", "old.png", status="approved")
    all_items = client.get("/api/gallery/works").json()
    assert all_items["total"] == 2
    assert {item["id"] for item in all_items["items"]} == {static_id, animated_id}
    assert legacy_id not in {item["id"] for item in all_items["items"]}

    filtered = client.get("/api/gallery/works?mode=featured&animation=animated").json()
    assert filtered["total"] == 1
    item = filtered["items"][0]
    assert item["id"] == animated_id and item["animated"] and item["adult"]
    assert client.get("/api/gallery/works?animation=static").json()["total"] == 1
    assert client.get("/api/gallery/works?mode=split").json()["total"] == 0
    assert client.get(f"/api/gallery/works/{legacy_id}").status_code == 404
    assert client.get("/api/gallery/works?author=no-such-author").status_code == 404


def test_video_preview_metadata_is_exposed_without_serving_an_image(gallery_site):
    client, _ = gallery_site
    item_id = auth_db.gallery_release_create(1, title="Motion", mode="workshop",
        image_path="gallery/u1/preview.mp4", thumb_path="gallery/u1/thumb.jpg",
        archive_path="gallery_releases/u1/files.zip", description="", background_url="",
        sale_url="", is_paid=False, is_adult=False, is_animated=True)
    listed = client.get("/api/gallery/works?animation=animated").json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == item_id
    assert listed["items"][0]["video_preview"] is True
    assert client.get(f"/api/gallery/works/{item_id}").json()["item"]["video_preview"] is True


@pytest.mark.parametrize("overrides,expected", [
    ({"rights_confirmed": "false"}, "rights"),
    ({"mode": "not-a-mode"}, "showcase"),
    ({"sale_url": "javascript:alert(1)"}, "https"),
    ({"sale_url": "https://user:secret@example.test/buy"}, "https"),
])
def test_publish_rejects_invalid_metadata(gallery_site, overrides, expected):
    client, _ = gallery_site
    response = _publish(client, paid=True, **overrides)
    assert response.status_code == 400
    assert expected.lower() in response.json()["msg"].lower()
    assert client.get("/api/gallery/works").json()["total"] == 0


@pytest.mark.parametrize("name,payload", [
    ("ready.zip", b"not-a-zip"),
    ("ready.zip", _zip(b"not a PNG")),
    ("ready.zip", _zip(_png(), "script.html")),
    ("ready.zip", _zip(_png(), "../part_1.png")),
    ("ready.zip", _zip(_png(), "/part_1.png")),
    ("ready.zip", _zip(_png(), "C:/part_1.png")),
    ("ready.zip", _zip(_png(), "part_1.png")),
])
def test_publish_rejects_invalid_archive_contents(gallery_site, name, payload):
    client, _ = gallery_site
    response = client.post("/api/gallery/works", data={"title": "Nope", "mode": "workshop",
        "rights_confirmed": "true"}, files={"preview": ("preview.png", _png(), "image/png"),
        "archive": (name, payload, "application/zip")}, headers={"X-Session-Token": "owner"})
    assert response.status_code == 400
    assert client.get("/api/gallery/works").json()["total"] == 0


def test_publish_requires_auth_and_valid_preview(gallery_site):
    client, _ = gallery_site
    anonymous = client.post("/api/gallery/works", data={"title": "Nope"})
    assert anonymous.status_code == 401
    invalid = client.post("/api/gallery/works", data={"title": "Nope", "mode": "workshop",
        "rights_confirmed": "true", "is_paid": "true", "sale_url": "https://shop.example.test/item"},
        files={"preview": ("preview.png", b"<script>alert(1)</script>", "image/png")},
        headers={"X-Session-Token": "owner"})
    assert invalid.status_code == 400


def test_publish_respects_per_user_storage_limit(gallery_site, monkeypatch):
    client, _ = gallery_site
    monkeypatch.setattr(gallery_releases, "FREE_STORAGE_LIMIT", 1)
    response = _publish(client)
    assert response.status_code == 413
    assert response.json()["code"] == "GALLERY_STORAGE_QUOTA"
    assert client.get("/api/gallery/works").json()["total"] == 0


def test_avatar_replacement_cleans_previous_local_file(gallery_site):
    client, data_dir = gallery_site
    first = client.post("/api/gallery/author/avatar",
        files={"file": ("avatar.png", _png("#ff3388"), "image/png")},
        headers={"X-Session-Token": "owner"})
    assert first.status_code == 200
    connection = auth_db._conn()
    old_key = connection.execute("SELECT avatar_path FROM users WHERE id=1").fetchone()["avatar_path"]
    connection.close()
    assert (data_dir / old_key).is_file()
    second = client.post("/api/gallery/author/avatar",
        files={"file": ("avatar.png", _png("#3344cc"), "image/png")},
        headers={"X-Session-Token": "owner"})
    assert second.status_code == 200
    assert not (data_dir / old_key).exists()


def test_owner_can_edit_and_remove_but_other_user_cannot(gallery_site):
    client, data_dir = gallery_site
    item_id = _publish(client).json()["id"]
    row = auth_db.gallery_get(item_id)
    payload = {"title": "Renamed", "description": "Details", "mode": "workshop",
               "background_url": "", "sale_url": "", "is_paid": False, "is_adult": True}
    assert client.put(f"/api/gallery/works/{item_id}", json=payload,
                      headers={"X-Session-Token": "visitor"}).status_code == 404
    edited = client.put(f"/api/gallery/works/{item_id}", json=payload,
                        headers={"X-Session-Token": "owner"})
    assert edited.status_code == 200 and edited.json()["ok"] is True
    detail = client.get(f"/api/gallery/works/{item_id}").json()["item"]
    assert detail["title"] == "Renamed" and detail["mode"] == "workshop" and detail["adult"]
    wrong_mode = client.put(f"/api/gallery/works/{item_id}", json={**payload, "mode": "featured"},
                            headers={"X-Session-Token": "owner"})
    assert wrong_mode.status_code == 400
    assert auth_db.gallery_get(item_id)["mode"] == "workshop"
    assert client.delete(f"/api/gallery/works/{item_id}",
                         headers={"X-Session-Token": "visitor"}).status_code == 404
    assert client.delete(f"/api/gallery/works/{item_id}",
                         headers={"X-Session-Token": "owner"}).json()["ok"] is True
    assert client.get(f"/api/gallery/works/{item_id}").status_code == 404
    assert client.get("/api/gallery/works").json()["total"] == 0
    assert not (data_dir / row["image_path"]).exists()
    assert not (data_dir / row["archive_path"]).exists()


def test_invalid_edit_and_author_json_returns_bad_request(gallery_site):
    client, _ = gallery_site
    item_id = _publish(client).json()["id"]
    for path in (f"/api/gallery/works/{item_id}", "/api/gallery/author/me"):
        response = client.put(path, content="{", headers={"X-Session-Token": "owner",
            "Content-Type": "application/json"})
        assert response.status_code == 400
        assert response.json()["ok"] is False


def test_paid_release_cannot_be_changed_to_free_without_zip(gallery_site):
    client, _ = gallery_site
    item_id = _publish(client, paid=True, sale_url="https://shop.example.test/buy").json()["id"]
    edited = client.put(f"/api/gallery/works/{item_id}", json={"title": "Renamed",
        "description": "", "mode": "workshop", "is_paid": False, "sale_url": ""},
        headers={"X-Session-Token": "owner"})
    assert edited.status_code == 400
    assert "ZIP" in edited.json()["msg"]
    assert auth_db.gallery_get(item_id)["is_paid"] == 1


def test_processing_job_auto_attaches_zip_and_derives_preview(gallery_site, monkeypatch):
    client, data_dir = gallery_site
    result_file = _png("#aa55dd")
    result_buffer = io.BytesIO()
    with zipfile.ZipFile(result_buffer, "w") as archive:
        archive.writestr("full_with_bars.png", result_file)
        for index in range(1, 6):
            archive.writestr(f"part_{index}.png", _png(size=(150, 422)))
    result_zip = result_buffer.getvalue()
    seen = []
    monkeypatch.setattr(gallery_releases, "_job_archive", lambda request, job_id:
                        seen.append(job_id) or result_zip)
    job_id = "a" * 24
    response = client.post("/api/gallery/works", data={"title": "Builder result",
        "mode": "workshop", "rights_confirmed": "true", "job_id": job_id},
        headers={"X-Session-Token": "owner"})
    assert response.status_code == 200, response.text
    assert seen == [job_id]
    row = auth_db.gallery_get(response.json()["id"])
    assert (data_dir / row["archive_path"]).read_bytes() == result_zip
    assert (data_dir / row["image_path"]).read_bytes() == result_file
    assert row["is_paid"] == 0

    invalid = client.post("/api/gallery/works", data={"title": "Invalid job",
        "mode": "workshop", "rights_confirmed": "true", "job_id": "../wrong"},
        headers={"X-Session-Token": "owner"})
    assert invalid.status_code == 400 and seen == [job_id]

    paid = client.post("/api/gallery/works", data={"title": "Paid job",
        "mode": "workshop", "rights_confirmed": "true", "job_id": job_id,
        "is_paid": "true", "sale_url": "https://example.test/buy"},
        headers={"X-Session-Token": "owner"})
    assert paid.status_code == 200 and seen == [job_id, job_id]
    assert auth_db.gallery_get(paid.json()["id"])["archive_path"] is None


def test_author_links_are_validated_and_public_stats_are_consistent(gallery_site):
    client, _ = gallery_site
    item_id = _publish(client).json()["id"]
    auth_db.gallery_like_toggle(2, item_id)
    bad = client.put("/api/gallery/author/me", json={"name": "Owner", "username": "owner",
        "links": {"website": "http://unsafe.example.test"}}, headers={"X-Session-Token": "owner"})
    assert bad.status_code == 400
    good = client.put("/api/gallery/author/me", json={"name": "Creator", "username": "owner",
        "bio": "A profile", "links": {"website": "https://example.test"}},
        headers={"X-Session-Token": "owner"})
    assert good.status_code == 200, good.text
    author = client.get("/api/gallery/author/owner").json()
    assert author["name"] == "Creator" and author["links"]["website"] == "https://example.test"
    assert author["stats"] == {"works": 1, "downloads": 0, "likes": 1}


def test_legacy_gallery_entries_are_retired_from_public_endpoints(gallery_site):
    client, data_dir = gallery_site
    old_id = auth_db.gallery_add(1, "Old work", "workshop", "gallery/old.png", status="approved")
    old_path = data_dir / "gallery" / "old.png"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.write_bytes(_png())
    assert client.get("/api/gallery/list").json()["items"] == []
    assert client.get(f"/api/gallery/image/{old_id}").status_code == 404
    assert old_path.is_file()  # Retire publicly without deleting historical user data.
