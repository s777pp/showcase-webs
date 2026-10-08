"""Steam-ready sets from gallery works for the extension's automatic upload (smweb/gallery_steam.py)."""

import io
import zipfile

import pytest

import auth_db
from smweb import gallery_steam
from smweb.steam_readiness import Candidate
from tests.test_gallery_releases import _gif, _png, gallery_site  # noqa: F401  (fixture)


def _zip(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in files:
            archive.writestr(name, data)
    return output.getvalue()


def _publish(client, mode, archive):
    response = client.post("/api/gallery/works", data={
        "title": "Set", "mode": mode, "rights_confirmed": "true", "is_paid": "false", "is_adult": "false",
    }, files={"preview": ("preview.png", _png(), "image/png"), "archive": ("w.zip", archive, "application/zip")},
        headers={"X-Session-Token": "owner"})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _names(sets):
    return [[item.name for item in found["files"]] for found in sets]


def test_process_zip_workshop_set_skips_previews_and_orders_parts():
    entries = [(f"part_{n}.gif", _gif()) for n in (3, 1, 5, 2, 4)]
    entries += [("full_original.gif", _gif()), ("full_with_bars.gif", _gif())]
    sets = gallery_steam.find_sets(entries, "workshop")
    assert _names(sets) == [[f"part_{n}.gif" for n in range(1, 6)]]
    # HEX 21 is applied (the extension does not do it).
    assert all(item.data.endswith(b"\x21") for item in sets[0]["files"])


def test_workshop_rows_are_separate_sets_in_natural_order():
    entries = [(f"row_{row}/part_{n}.png", _png(size=(150, 150))) for row in (10, 2) for n in range(1, 6)]
    sets = gallery_steam.find_sets(entries, "workshop")
    assert [found["label"] for found in sets] == ["row_2", "row_10"]


def test_split_by_names_or_widths_wide_part_first():
    named = [("side_100.png", _png(size=(100, 422))), ("center_506.png", _png(size=(506, 422))), ("extra.png", _png())]
    assert _names(gallery_steam.find_sets(named, "split")) == [["center_506.png", "side_100.png"]]
    by_width = [("b.png", _png(size=(100, 300))), ("a.png", _png(size=(506, 300))), ("c.png", _png(size=(64, 64)))]
    assert _names(gallery_steam.find_sets(by_width, "split")) == [["center_506.png", "side_100.png"]]


def test_featured_picks_named_files_and_labels_them():
    entries = [("v1/featured_a.gif", _gif()), ("v1/featured_b.gif", _gif()), ("v1/notes.png", _png())]
    sets = gallery_steam.find_sets(entries, "featured")
    assert [found["label"] for found in sets] == ["v1/featured_a.gif", "v1/featured_b.gif"]
    assert _names(sets) == [["featured_630.gif"], ["featured_630.gif"]]


def test_no_set_and_too_large_codes():
    with pytest.raises(gallery_steam.NoSteamSet) as missing:
        gallery_steam.find_sets([("a.png", _png()), ("b.png", _png())], "workshop")
    assert missing.value.code == "no_set"
    with pytest.raises(gallery_steam.NoSteamSet) as large:
        gallery_steam.find_sets([(f"part_{n}.png", _png()) for n in range(1, 5)], "workshop", oversized=True)
    assert large.value.code == "too_large"


def test_routes_serve_parts_to_signed_in_visitors_and_count_a_download(gallery_site):  # noqa: F811
    client, data_dir = gallery_site
    item_id = _publish(client, "workshop", _zip([(f"part_{n}.png", _png(size=(150, 422))) for n in range(1, 6)]))
    assert client.get(f"/api/gallery/works/{item_id}/steam").status_code == 401
    response = client.get(f"/api/gallery/works/{item_id}/steam", headers={"X-Session-Token": "visitor"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "workshop" and len(body["sets"]) == 1
    files = body["sets"][0]["files"]
    assert [file["name"] for file in files] == [f"part_{n}.png" for n in range(1, 6)]
    part = client.get(files[0]["url"], headers={"X-Session-Token": "visitor"})
    assert part.status_code == 200 and part.headers["content-type"] == "image/png"
    assert part.content.endswith(b"\x21")
    assert client.get(files[0]["url"]).status_code == 401
    assert auth_db.gallery_get(item_id)["download_count"] == 1
    # The second request is served from the cache folder.
    assert (data_dir / "cache" / "gallery-steam").is_dir()
    assert client.get(f"/api/gallery/works/{item_id}/steam", headers={"X-Session-Token": "visitor"}).json()["sets"]


def test_route_explains_when_the_zip_has_no_set(gallery_site):  # noqa: F811
    client, _ = gallery_site
    item_id = _publish(client, "split", _zip([("a.png", _png()), ("b.png", _png()), ("c.png", _png())]))
    response = client.get(f"/api/gallery/works/{item_id}/steam", headers={"X-Session-Token": "visitor"})
    assert response.status_code == 422 and response.json()["code"] == "no_set"


def test_candidate_names_survive_backslashes():
    sets = gallery_steam.find_sets([("set\\featured.png", _png(size=(630, 300)))], "featured")
    assert sets[0]["label"] == "set" and isinstance(sets[0]["files"][0], Candidate)
