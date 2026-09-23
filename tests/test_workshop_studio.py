import io
import json
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from smweb import workshop_studio_jobs as studio
from smweb.routers import process


def _settings():
    return {"brightness": 100, "contrast": 100, "saturation": 100, "hue": 0, "start": 0}


def test_full_height_image_is_scaled_not_cropped(tmp_path):
    source = tmp_path / "tall.png"
    Image.new("RGB", (300, 1200), "#733abb").save(source)
    output = studio.render_image(source, _settings())
    assert output[-1] == 0x21
    with Image.open(io.BytesIO(output)) as image:
        assert image.size == (750, 3000)


def test_job_outputs_exactly_one_file_per_row(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "JOBS", tmp_path)
    states = []
    monkeypatch.setattr(studio, "_job_set", lambda jid, **fields: states.append(fields))
    uploads = []
    for index in range(3):
        path = tmp_path / f"source_{index}.png"
        Image.new("RGB", (150, 200 + index * 100), (index * 50, 40, 90)).save(path)
        uploads.append({"path": str(path), "name": path.name})
    studio.run("a" * 24, {"files": uploads, "options": {"rows": [_settings()] * 3, "fps": 12, "duration": 4}})
    assert states[-1]["status"] == "done"
    with zipfile.ZipFile(tmp_path / ("a" * 24) / "result.zip") as archive:
        assert archive.namelist() == ["row_1.png", "row_2.png", "row_3.png"]
        for index in range(3):
            payload = archive.read(f"row_{index + 1}.png")
            assert payload[-1] == 0x21
            with Image.open(io.BytesIO(payload)) as image:
                assert image.size == (750, 1000 + index * 500)


def test_api_keeps_selected_row_count(tmp_path, monkeypatch):
    monkeypatch.setattr(process, "JOBS", tmp_path)
    monkeypatch.setattr(studio, "JOBS", tmp_path)
    monkeypatch.setattr(process, "quota_state", lambda request: {"pro": True, "left": -1})
    monkeypatch.setattr(process, "_auth_user", lambda request: None)
    monkeypatch.setattr(process, "_ip", lambda request: "test-client")
    monkeypatch.setattr(process.rs, "job_count_user", lambda user: 0)
    monkeypatch.setattr(process.rs, "job_create", lambda jid, payload, enqueue=False: None)
    monkeypatch.setattr(process, "_worker_mode", lambda: "embedded")
    monkeypatch.setattr(process, "quota_inc", lambda request, count: None)
    monkeypatch.setattr(process._job_pool, "submit", lambda func, *args: func(*args))
    monkeypatch.setattr(process, "_job_set", lambda jid, **fields: None)
    monkeypatch.setattr(studio, "_job_set", lambda jid, **fields: None)
    buffer = io.BytesIO()
    Image.new("RGB", (150, 300), "#235070").save(buffer, format="PNG")
    app = FastAPI()
    app.include_router(process.router)
    with TestClient(app) as client:
        response = client.post("/api/workshop-studio/start", data={"rows": "2", "fps": "12", "duration": "4",
            "settings": json.dumps([_settings(), _settings()])},
            files=[("files", ("first.png", buffer.getvalue(), "image/png")),
                   ("files", ("second.png", buffer.getvalue(), "image/png"))])
    assert response.status_code == 200
    jid = response.json()["job_id"]
    with zipfile.ZipFile(tmp_path / jid / "result.zip") as archive:
        assert archive.namelist() == ["row_1.png", "row_2.png"]


def test_gif_row_stays_animated_and_hex_patched(tmp_path):
    import processor
    if not processor.find_ffmpeg():
        return
    source = tmp_path / "source.gif"
    frames = [Image.new("RGB", (150, 300), color) for color in ("red", "blue")]
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=200, loop=0)
    target = tmp_path / "row_1.gif"
    studio.render_animation(source, target, _settings(), fps=5, duration=1, start=0,
                            outline=True, free_watermark=True)
    assert target.read_bytes()[-1] == 0x21
    # HEX 21 replaces the GIF trailer for Steam; restore it only for Pillow.
    with Image.open(io.BytesIO(target.read_bytes()[:-1] + b";")) as result:
        assert result.size == (750, 1500)
        assert result.n_frames > 1
