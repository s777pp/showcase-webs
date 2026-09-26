import io
import re
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from smweb.middleware import GuestCookieMiddleware
from smweb.routers import pages, preview, process


def _png(width, height):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "#305070").save(buffer, "PNG")
    return buffer.getvalue() + b"!"  # final Steam files carry the HEX 21 byte


def _app(monkeypatch, tmp_path):
    for module in (preview, pages, process):
        monkeypatch.setattr(module, "JOBS", tmp_path)
    archive = tmp_path / "result.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("art_split/center_506.png", _png(506, 300))
        zf.writestr("art_split/side_100.png", _png(100, 300))
        zf.writestr("art_split/full_with_bars.png", _png(612, 300))
    job = {"status": "done", "zip_path": str(archive)}
    monkeypatch.setattr(process, "_process_job_for", lambda request, job_id: job if job_id == "a" * 24 else None)
    app = FastAPI()
    app.add_middleware(GuestCookieMiddleware)
    for router in (preview.router, pages.router, process.router):
        app.include_router(router)
    return app


def test_result_preview_uses_final_files_and_can_be_shared(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    owner, visitor = TestClient(app), TestClient(app)
    owner.get("/api/process/status/" + "b" * 24)  # receive the guest cookie
    built = owner.post("/api/process/profile-preview/" + "a" * 24).json()
    assert built["ok"] and built["mode"] == "split"
    page = owner.get(built["open"])
    assert page.status_code == 200 and 'id="smShare"' in page.text and "noindex" in page.text
    images = re.findall(r'/api/job-file/[a-f0-9]{32}/(result_[\w.]+)', page.text)
    assert sorted(images) == ["result_center_506.png", "result_side_100.png"]

    preview_id = built["open"].rsplit("/", 1)[1]
    assert visitor.get(built["open"]).status_code == 404
    assert visitor.get(f"/api/job-file/{preview_id}/result_side_100.png").status_code == 404
    assert visitor.post(f"/api/preview/{preview_id}/share").status_code == 404  # only the owner can share

    shared = owner.post(f"/api/preview/{preview_id}/share").json()
    assert shared == {"ok": True, "url": built["open"], "days": 7}
    seen = visitor.get(built["open"])
    assert seen.status_code == 200 and "smShare" not in seen.text
    assert visitor.get(f"/api/job-file/{preview_id}/result_side_100.png").status_code == 200


def test_preview_of_someone_elses_job_is_refused(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path)
    assert TestClient(app).post("/api/process/profile-preview/" + "c" * 24).status_code == 404
