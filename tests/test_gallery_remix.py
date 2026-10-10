"""Gallery works that carry their Create a design project ("Change the design", smweb/gallery_remix.py)."""

import auth_db
from smweb import gallery_remix
from smweb.routers.builder import _allowed_source, _validated_project
from tests.test_gallery_releases import _png, _publish, gallery_site  # noqa: F401  (fixture)

ASSET = "a" * 32 + ".png"


def _project(tmp_path):
    (tmp_path / "builder" / "1").mkdir(parents=True, exist_ok=True)
    (tmp_path / "builder" / "1" / ASSET).write_bytes(_png())
    project = {"mode": "workshop", "width": 750, "height": 900, "layers": [
        {"id": "bg", "type": "background", "src": "https://cdn.cloudflare.steamstatic.com/steam/apps/1/x.jpg"},
        {"id": "hero", "type": "character", "src": f"/api/builder/assets/{ASSET}"},
        {"id": "t", "type": "text", "text": "Hello"},
    ]}
    auth_db.save_builder_project(1, "p1", "My design", "workshop", project, is_pro=True)


def test_publish_with_project_then_open_a_copy(gallery_site):  # noqa: F811
    client, data_dir = gallery_site
    _project(data_dir)
    response = _publish(client, builder_project_id="p1", remix_allowed="true")
    assert response.status_code == 200, response.text
    item_id = response.json()["id"]
    row = auth_db.gallery_get(item_id)
    assert row["remix_path"].startswith("gallery_releases/u1/") and row["remix_path"].endswith("/remix")
    # Anyone can read the project; media links point to the work, Steam links stay.
    data = client.get(f"/api/gallery/works/{item_id}/remix").json()
    layers = {layer["id"]: layer for layer in data["project"]["layers"]}
    assert data["ok"] and data["title"] == "My showcase"
    assert layers["hero"]["src"] == f"/api/gallery/works/{item_id}/remix/{ASSET}"
    assert layers["bg"]["src"].startswith("https://cdn.cloudflare.steamstatic.com/")
    media = client.get(layers["hero"]["src"])
    assert media.status_code == 200 and media.content == _png() and media.headers["content-type"] == "image/png"
    # The work card says it can be changed, and the Builder accepts the copy when the remixer saves it.
    assert client.get(f"/api/gallery/works/{item_id}").json()["item"]["remix"] is True
    assert _allowed_source(layers["hero"]["src"])
    assert _validated_project(data["project"])["layers"][1]["src"] == layers["hero"]["src"]
    # Deleting the work removes the copy too.
    folder = data_dir / row["remix_path"]
    assert (folder / "project.json").is_file()
    assert client.delete(f"/api/gallery/works/{item_id}", headers={"X-Session-Token": "owner"}).json()["ok"]
    assert not folder.exists() and client.get(f"/api/gallery/works/{item_id}/remix").status_code == 404


def test_no_project_unless_the_author_allows_it(gallery_site):  # noqa: F811
    client, data_dir = gallery_site
    _project(data_dir)
    item_id = _publish(client, builder_project_id="p1").json()["id"]
    assert not auth_db.gallery_get(item_id)["remix_path"]
    assert client.get(f"/api/gallery/works/{item_id}/remix").status_code == 404
    # Someone else's project id is refused.
    response = client.post("/api/gallery/works", data={"title": "x", "mode": "workshop", "rights_confirmed": "true",
                           "builder_project_id": "p1", "remix_allowed": "true"},
                           files={"preview": ("p.png", _png(), "image/png")}, headers={"X-Session-Token": "visitor"})
    assert response.status_code == 400


def test_only_known_media_names_are_served(tmp_path, monkeypatch):
    monkeypatch.setattr(gallery_remix.core, "DATA", tmp_path)
    monkeypatch.setattr(gallery_remix.object_store, "configured", lambda: False)
    gallery_remix.store("gallery_releases/u1/t/remix", {"layers": []}, {ASSET: b"x"})
    assert gallery_remix.media("gallery_releases/u1/t/remix", ASSET)[0] == b"x"
    for bad in ("project.json", "../x.png", "a.png"):
        try:
            gallery_remix.media("gallery_releases/u1/t/remix", bad)
            raise AssertionError(bad)
        except FileNotFoundError:
            pass


def test_saving_a_copy_moves_the_media_into_the_savers_own_files(gallery_site, monkeypatch):  # noqa: F811
    client, data_dir = gallery_site
    _project(data_dir)
    item_id = _publish(client, builder_project_id="p1", remix_allowed="true").json()["id"]
    monkeypatch.setattr(gallery_remix.core, "DATA", data_dir)
    copy = client.get(f"/api/gallery/works/{item_id}/remix").json()["project"]
    link = f"/api/gallery/works/{item_id}/remix/{ASSET}"
    # Pending work: only its author may copy the media; anybody else keeps the link.
    c = auth_db._conn()
    try:
        c.execute("UPDATE gallery SET status='pending' WHERE id=?", (item_id,))
        c.commit()
    finally:
        c.close()
    kept = gallery_remix.adopt(_validated_project(copy), 2)
    assert kept["layers"][1]["src"] == link
    c = auth_db._conn()
    try:
        c.execute("UPDATE gallery SET status='approved' WHERE id=?", (item_id,))
        c.commit()
    finally:
        c.close()
    saved = gallery_remix.adopt(_validated_project(copy), 2)
    own = saved["layers"][1]["src"]
    assert own.startswith("/api/builder/assets/") and own != f"/api/builder/assets/{ASSET}"
    assert (data_dir / "builder" / "2" / own.rsplit("/", 1)[1]).read_bytes() == _png()
    assert saved["layers"][0]["src"].startswith("https://cdn.cloudflare.steamstatic.com/")
