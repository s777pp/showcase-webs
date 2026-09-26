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


def test_squares_cut_the_chosen_area_into_five_150px_files(tmp_path):
    source = tmp_path / "character.png"
    image = Image.new("RGB", (750, 1000), "black")
    # A red band exactly where the chosen strip is: y 400..550 of the source.
    image.paste((230, 20, 20), (0, 400, 750, 550))
    image.save(source)
    crop = studio.normalize_crop({"x": 0, "y": 0.4, "w": 1, "h": 0.15})
    outputs = studio.render_squares_image(source, _settings(), crop)
    assert sorted(outputs) == ["part_1.png", "part_2.png", "part_3.png", "part_4.png", "part_5.png", "preview.png"]
    for index in range(1, 6):
        payload = outputs[f"part_{index}.png"]
        assert payload[-1] == 0x21
        with Image.open(io.BytesIO(payload)) as part:
            assert part.size == (150, 150)
            red, green, _ = part.convert("RGB").getpixel((75, 75))
            assert red > 200 and green < 60
    with Image.open(io.BytesIO(outputs["preview.png"])) as preview:
        assert preview.size == (766, 150)


def test_squares_free_watermark_marks_only_the_preview(tmp_path):
    source = tmp_path / "flat.png"
    Image.new("RGB", (750, 150), "#101820").save(source)
    crop = studio.normalize_crop({"x": 0, "y": 0, "w": 1, "h": 1})
    clean = studio.render_squares_image(source, _settings(), crop, free_watermark=False)
    marked = studio.render_squares_image(source, _settings(), crop, free_watermark=True)
    for index in range(1, 6):
        assert marked[f"part_{index}.png"] == clean[f"part_{index}.png"]
    assert marked["preview.png"] != clean["preview.png"]


def test_square_fx_are_validated_and_static_frame_stays_png(tmp_path):
    from smweb import square_fx
    fx = square_fx.normalize({"frame": {"style": "evil", "width": 99, "color": "red"},
                              "effect": {"type": "rain", "speed": 9999, "density": -5}})
    assert fx["frame"]["style"] == "none" and fx["frame"]["width"] == 10 and fx["frame"]["color"] == "#8de9ff"
    assert fx["effect"]["speed"] == 300 and fx["effect"]["density"] == 25
    assert square_fx.normalize(None, legacy_outline=True)["frame"]["style"] == "solid"
    source = tmp_path / "flat.png"
    Image.new("RGB", (750, 150), "#101820").save(source)
    crop = studio.normalize_crop({"x": 0, "y": 0, "w": 1, "h": 1})
    outputs = studio.render_squares_image(source, _settings(), crop, fx={"frame": {"style": "neon", "color": "#ff00aa"}})
    with Image.open(io.BytesIO(outputs["part_3.png"])) as part:
        assert part.size == (150, 150)
        assert part.convert("RGB").getpixel((0, 75))[0] > 150, "the neon frame is drawn on every square"


def test_square_fx_loop_is_seamless():
    from smweb import square_fx
    base = Image.new("RGBA", (750, 150), (10, 20, 30, 255))
    for style, effect in (("rgb", "none"), ("comet", "particle"), ("dashes", "petals"), ("pulse", "stars")):
        fx = square_fx.normalize({"frame": {"style": style, "speed": 2}, "effect": {"type": effect}})
        assert square_fx.is_animated(fx)
        start, end = square_fx.apply(base, 0.0, fx), square_fx.apply(base, 1.0, fx)
        assert start.tobytes() == end.tobytes(), f"{style}/{effect} must loop without a jump"
        assert square_fx.apply(base, 0.37, fx).tobytes() != start.tobytes()


def test_still_image_with_animated_frame_becomes_synchronized_gifs(tmp_path):
    import processor
    if not processor.find_ffmpeg():
        return
    source = tmp_path / "still.png"
    Image.new("RGB", (900, 600), "#203050").save(source)
    crop = studio.normalize_crop({"x": 0, "y": 0.2, "w": 1, "h": 0.25})
    outputs = studio.render_squares_still_animation(
        source, tmp_path / "work", _settings(), crop, {"frame": {"style": "rgb", "width": 3}, "effect": {"type": "sparks"}},
        fps=8, duration=1, free_watermark=True)
    for index in range(1, 6):
        payload = outputs[f"part_{index}.gif"].read_bytes()
        assert payload[-1] == 0x21
        with Image.open(io.BytesIO(payload[:-1] + b";")) as part:
            assert part.size == (150, 150) and part.n_frames > 1


def test_short_gif_is_looped_to_the_clip_length_when_effects_are_on(tmp_path):
    import processor
    if not processor.find_ffmpeg():
        return
    source = tmp_path / "short.gif"
    frames = [Image.new("RGB", (800, 500), color) for color in ("#402060", "#204060", "#206040")]
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=120, loop=0)  # 0.36 s
    crop = studio.normalize_crop({"x": 0, "y": 0.3, "w": 1, "h": 0.32})
    outputs = studio.render_squares_animation(source, tmp_path / "work", _settings(), crop, fps=8, duration=2, start=0,
                                              fx={"frame": {"style": "dashes"}})
    payload = outputs["part_1.gif"].read_bytes()
    with Image.open(io.BytesIO(payload[:-1] + b";")) as part:
        assert part.n_frames == 16, "2 s at 8 fps, not the 0.36 s of the source"


def test_squares_crop_is_clamped_and_kept_at_five_to_one():
    crop = studio.normalize_crop({"x": 0.9, "y": -3, "w": 0.5, "h": 0.2})
    assert crop == {"x": 0.5, "y": 0.0, "w": 0.5, "h": 0.2}
    left, top, right, bottom = studio._crop_box((1000, 1000), crop)
    assert round((right - left) / (bottom - top), 6) == 5
    import pytest
    with pytest.raises(ValueError):
        studio.normalize_crop({"x": float("nan"), "y": 0, "w": 1, "h": 1})


def test_squares_job_writes_five_parts(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "JOBS", tmp_path)
    states = []
    monkeypatch.setattr(studio, "_job_set", lambda jid, **fields: states.append(fields))
    path = tmp_path / "wide.png"
    Image.new("RGB", (1500, 900), "#3060a0").save(path)
    options = {"layout": "squares", "crop": {"x": 0, "y": 0.2, "w": 1, "h": 1 / 3},
               "rows": [_settings()], "fps": 12, "duration": 4, "free_watermark": True, "outline": True}
    studio.run("b" * 24, {"files": [{"path": str(path), "name": path.name}], "options": options})
    assert states[-1]["status"] == "done"
    with zipfile.ZipFile(tmp_path / ("b" * 24) / "result.zip") as archive:
        assert sorted(archive.namelist()) == ["part_1.png", "part_2.png", "part_3.png", "part_4.png", "part_5.png", "preview.png"]
    assert not path.exists()


def test_api_rejects_squares_without_valid_crop(monkeypatch):
    monkeypatch.setattr(process, "quota_state", lambda request: {"pro": True, "left": -1})
    buffer = io.BytesIO()
    Image.new("RGB", (300, 300), "#235070").save(buffer, format="PNG")
    app = FastAPI()
    app.include_router(process.router)
    with TestClient(app) as client:
        response = client.post("/api/workshop-studio/start", data={"rows": "1", "layout": "squares", "crop": "{}",
            "settings": json.dumps([_settings()])},
            files=[("files", ("one.png", buffer.getvalue(), "image/png"))])
    assert response.status_code == 400


def test_squares_animation_stays_synchronized_and_hex_patched(tmp_path):
    import processor
    if not processor.find_ffmpeg():
        return
    source = tmp_path / "source.gif"
    frames = [Image.new("RGB", (400, 600), color) for color in ("red", "blue")]
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=200, loop=0)
    crop = studio.normalize_crop({"x": 0, "y": 0.3, "w": 1, "h": 400 / 5 / 600})
    outputs = studio.render_squares_animation(source, tmp_path / "work", _settings(), crop, fps=5, duration=1,
                                              start=0, outline=True, free_watermark=True)
    for index in range(1, 6):
        payload = outputs[f"part_{index}.gif"].read_bytes()
        assert payload[-1] == 0x21
        with Image.open(io.BytesIO(payload[:-1] + b";")) as part:
            assert part.size == (150, 150)
            assert part.n_frames > 1


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
