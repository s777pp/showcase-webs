"""'Depth' for still pictures: smweb.depth_fx effects, processor.parallax_source and the Process wiring."""

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import processor as proc
from smweb import depth, depth_fx


def _png(size=(320, 180)):
    out = io.BytesIO()
    img = Image.new("RGB", size, "#203060")
    for x in range(0, size[0], 16):
        img.paste((255, 200, 40), (x, 0, x + 4, size[1]))
    img.save(out, "PNG")
    return out.getvalue()


def _fake_depth(image):
    w, h = image.size
    d = np.zeros((h, w), np.float32)
    d[h // 4: 3 * h // 4, w // 3: 2 * w // 3] = 1.0     # a near block in the middle
    return d


def _pixels():
    return np.asarray(Image.open(io.BytesIO(_png())).convert("RGBA"))


def test_normalize_clamps_defaults_and_reads_the_first_version():
    assert depth_fx.normalize(None) is None
    assert depth_fx.normalize({"on": False}) is None
    assert depth_fx.normalize({"camera": {"motion": "none"}}) is None          # nothing would move
    old = depth_fx.normalize({"motion": "spin", "strength": 99, "focus": -1})
    assert old["camera"] == {"motion": "orbit", "strength": 3.0} and old["focus"] == 0.0
    assert proc.normalize_parallax({"motion": "dolly"})["camera"]["strength"] == 1.5
    full = depth_fx.normalize({
        "camera": {"motion": "none"}, "particles": {"kind": "lava", "amount": 9}, "atmosphere": "smoke",
        "breath": {"on": True, "chest": 9, "region": {"cx": 2, "rx": 0}},
        "hair": {"on": True, "strokes": [[0.5, 0.2, 1]] * 900 + ["x"]},
    })
    assert full["particles"] is None and full["atmosphere"] == "none"
    assert full["breath"]["chest"] == 3.0 and full["breath"]["region"]["cx"] == 1 and full["breath"]["region"]["rx"] == 0.03
    assert len(full["hair"]["strokes"]) == depth_fx.MAX_STROKES and full["hair"]["strokes"][0][2] == 0.2
    # Hair without strokes does nothing.
    assert depth_fx.normalize({"camera": {"motion": "none"}, "hair": {"on": True, "strokes": []}}) is None


LOOKS = [
    {"camera": {"motion": motion, "strength": 2}} for motion in depth_fx.CAMERA if motion != "none"
] + [
    {"camera": {"motion": "none"}, "particles": {"kind": kind, "amount": 2}} for kind in depth_fx.PARTICLES if kind != "none"
] + [
    {"camera": {"motion": "none"}, "atmosphere": "fog"},
    {"camera": {"motion": "none"}, "atmosphere": "light"},
    {"camera": {"motion": "none"}, "focuspull": True},
    {"camera": {"motion": "none"}, "breath": {"on": True, "strength": 3, "chest": 2, "region": {"cx": 0.5, "cy": 0.5, "rx": 0.2, "ry": 0.3}}},
    {"camera": {"motion": "none"}, "hair": {"on": True, "strength": 3, "strokes": [[0.5, y / 20, 0.05] for y in range(2, 18)]}},
]


@pytest.mark.parametrize("raw", LOOKS, ids=lambda raw: "-".join(k for k, v in raw.items() if v and k != "camera") or raw["camera"]["motion"])
def test_every_effect_loops_seamlessly_and_moves(raw):
    scene = depth_fx.Scene(_pixels(), _fake_depth(Image.open(io.BytesIO(_png()))), depth_fx.normalize(raw))
    first = scene.frame(0.0).astype(int)
    assert first.shape == (180, 320, 4)
    assert np.abs(first - scene.frame(1.0).astype(int)).max() <= 1
    assert np.abs(first - scene.frame(0.37).astype(int)).max() > 0


def test_particles_hide_behind_nearer_pixels():
    depth_map = np.zeros((180, 320), np.float32)
    depth_map[:, 160:] = 1.0                                   # right half is the nearest thing in the picture
    plain = depth_fx.Scene(_pixels(), depth_map, depth_fx.normalize({"camera": {"motion": "none"}, "focuspull": True}))
    snow = depth_fx.Scene(_pixels(), depth_map, depth_fx.normalize({"camera": {"motion": "none"}, "particles": {"kind": "stars", "amount": 3}}))
    diff = np.abs(snow.frame(0.2).astype(int) - plain.pixels.astype(int)).max(axis=2)
    # Stars live on the far plane: they show on the left (far) half and never in front of the near half.
    assert diff[:, :140].max() > 40 and diff[:, 180:].max() <= 2


def test_body_guess_is_inside_the_picture():
    guess = depth_fx.body_guess(_fake_depth(Image.open(io.BytesIO(_png()))))
    assert 0 < guess["cx"] < 1 and 0 < guess["cy"] < 1 and all(isinstance(v, float) for v in guess.values())


def test_parallax_source_turns_a_still_into_a_loop(monkeypatch, tmp_path):
    if not proc.find_ffmpeg():
        pytest.skip("FFmpeg is not installed")
    monkeypatch.setattr(depth, "estimate", _fake_depth)
    options = {"camera": {"motion": "sway", "strength": 1}, "particles": {"kind": "snow", "amount": 1}}
    name, clip = proc.parallax_source("art.png", _png(), options, tmp_path / "d", 90, 10)
    assert name == "art.mkv" and clip[:4] == b"\x1a\x45\xdf\xa3"
    assert not list((tmp_path / "d").glob("f_*.png"))
    # Videos and GIFs are left alone, and so is everything when the effect is off.
    assert proc.parallax_source("clip.mp4", b"x", {"motion": "sway"}, tmp_path, 0, 10) == ("clip.mp4", b"x")
    assert proc.parallax_source("art.png", b"x", None, tmp_path, 0, 10) == ("art.png", b"x")


def test_depth_preview_routes(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from smweb.routers import process as process_router
    app = FastAPI()
    app.include_router(process_router.router)
    client = TestClient(app)
    monkeypatch.setattr(process_router, "_DEPTH_CACHE", tmp_path / "cache")
    monkeypatch.setattr(depth, "MODEL_PATH", Path("/nonexistent/model.onnx"))
    response = client.post("/api/process/depth", files={"file": ("a.png", _png(), "image/png")})
    assert response.status_code == 503 and response.json()["code"] == "depth_unavailable"
    monkeypatch.setattr(depth, "available", lambda: True)
    monkeypatch.setattr(depth, "estimate", _fake_depth)
    response = client.post("/api/process/depth", files={"file": ("a.png", _png(), "image/png")})
    data = response.json()
    assert response.status_code == 200 and len(data["token"]) == 32 and data["width"] == 320 and "cx" in data["body"]
    options = {"camera": {"motion": "orbit"}, "particles": {"kind": "sakura", "amount": 1}}
    response = client.post("/api/process/depth/render", json={"token": data["token"], "options": options})
    assert response.status_code == 200 and response.headers["content-type"] == "image/webp"
    with Image.open(io.BytesIO(response.content)) as image:
        assert image.n_frames == process_router._DEPTH_RENDER_FRAMES and image.size == (320, 180)
    assert client.post("/api/process/depth/render", json={"token": "0" * 32, "options": options}).json()["code"] == "expired"
    assert client.post("/api/process/depth/render", json={"token": "../x", "options": options}).status_code == 404
    assert client.post("/api/process/depth/render", json={"token": data["token"], "options": {"on": False}}).status_code == 400


def test_eta_counts_a_depth_still_as_motion():
    from smweb.jobs import process_eta_kind
    files = [("art.png", b"")]
    assert process_eta_kind(files, {}) == "still"
    assert process_eta_kind(files, {"parallax": {"motion": "orbit"}, "encode_profile": "standard"}) == "motion-standard"


def test_hair_sways_at_the_ends_and_keeps_the_upper_part_still():
    """Owner sample 2026-10-08: strands painted over the face dragged the eyes. The upper part of the painted hair
    (crown, fringe, face) must not move; the lower part must."""
    w, h = 200, 300
    rng = np.random.default_rng(1)
    pixels = rng.integers(0, 255, (h, w, 3), dtype=np.uint8)
    depth_map = np.full((h, w), 0.8, np.float32)
    strokes = [[x / w, y / h, 0.02] for x in range(60, 141, 8) for y in range(30, 291, 8)]
    scene = depth_fx.Scene(pixels, depth_map, depth_fx.normalize(
        {"camera": {"motion": "none"}, "hair": {"on": True, "strength": 3, "strokes": strokes}}))
    a, b = scene.frame(0.25).astype(int), scene.frame(0.75).astype(int)
    assert np.abs(a[30:110] - b[30:110]).mean() < 0.5        # upper third of the hair: still
    assert np.abs(a[230:290] - b[230:290]).mean() > 5        # the ends: clearly moving


def test_depth_clip_for_the_builder_character(monkeypatch, tmp_path):
    """keep=1 stores a bigger source; /depth/clip renders a seamless loop from it (Builder Character layer):
    H.264 for an opaque picture, VP9 WebM with alpha for a cut-out."""
    import subprocess
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from smweb.routers import process as process_router
    app = FastAPI(); app.include_router(process_router.router)
    client = TestClient(app)
    monkeypatch.setattr(process_router, "_DEPTH_CACHE", tmp_path / "cache")
    monkeypatch.setattr(depth, "available", lambda: True)
    monkeypatch.setattr(depth, "estimate", _fake_depth)
    big = _png((1000, 560))
    data = client.post("/api/process/depth", files={"file": ("a.png", big, "image/png")}, data={"keep": "1"}).json()
    folder = tmp_path / "cache" / data["token"]
    assert (folder / "source.png").is_file() and Image.open(folder / "source.png").size == (1000, 560)
    assert Image.open(folder / "picture.png").width <= 640
    options = {"camera": {"motion": "sway", "strength": 1.5}}
    response = client.post("/api/process/depth/clip", json={"token": data["token"], "options": options})
    assert response.status_code == 200 and response.headers["content-type"] == "video/mp4"
    clip = tmp_path / "clip.mp4"; clip.write_bytes(response.content)
    probe = subprocess.run([proc.find_ffmpeg() or "ffmpeg", "-v", "error", "-i", str(clip), "-f", "rawvideo",
                            "-pix_fmt", "gray", "-"], capture_output=True).stdout
    frames = np.frombuffer(probe, np.uint8).reshape(-1, 560, 1000)
    assert len(frames) == int(proc.PARALLAX_SECONDS * process_router._DEPTH_CLIP_FPS)
    assert np.abs(frames[0].astype(int) - frames[len(frames) // 4].astype(int)).mean() > 0.5   # it moves
    # Without keep the clip falls back to the 640 px picture; unknown tokens and empty options are refused.
    small = client.post("/api/process/depth", files={"file": ("a.png", big, "image/png")}).json()
    assert not (tmp_path / "cache" / small["token"] / "source.png").exists()
    assert client.post("/api/process/depth/clip", json={"token": small["token"], "options": options}).status_code == 200
    assert client.post("/api/process/depth/clip", json={"token": "0" * 32, "options": options}).status_code == 404
    assert client.post("/api/process/depth/clip", json={"token": data["token"], "options": {"on": False}}).status_code == 400
    # A cut-out keeps its transparency: WebM VP9 with an alpha plane, the empty corner stays empty.
    cut = Image.new("RGBA", (320, 240), (0, 0, 0, 0))
    cut.paste(Image.new("RGBA", (160, 200), (220, 120, 90, 255)), (80, 20))
    raw = io.BytesIO(); cut.save(raw, "PNG")
    token = client.post("/api/process/depth", files={"file": ("cut.png", raw.getvalue(), "image/png")}, data={"keep": "1"}).json()["token"]
    response = client.post("/api/process/depth/clip", json={"token": token, "options": {"camera": {"motion": "sway"}, "particles": {"kind": "snow"}}})
    assert response.status_code == 200 and response.headers["content-type"] == "video/webm"
    clip = tmp_path / "clip.webm"; clip.write_bytes(response.content)
    alpha = subprocess.run([proc.find_ffmpeg() or "ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(clip), "-frames:v", "1",
                            "-f", "rawvideo", "-pix_fmt", "rgba", "-"], capture_output=True).stdout
    first = np.frombuffer(alpha, np.uint8).reshape(240, 320, 4)
    assert first[120, 160, 3] > 200            # the figure is opaque
    assert np.median(first[:, :40, 3]) < 30    # the empty side stays (mostly) transparent; snow may pass there


def test_builder_keeps_character_depth_fields_only_when_valid():
    from smweb.routers import builder
    def project(layer):
        return builder._validated_project({"layers": [dict({"id": "a", "type": "character", "src": "/api/builder/assets/x.webm"}, **layer)]})["layers"][0]
    good = project({"depthFx": {"camera": {"motion": "orbit"}}, "depthSource": "/api/builder/assets/still.png", "depthSourceType": "image/jpeg"})
    assert good["depthFx"]["camera"]["motion"] == "orbit" and good["depthSource"].endswith("still.png") and good["depthSourceType"] == "image/jpeg"
    for bad in ({"depthFx": {"camera": {"motion": "orbit"}}, "depthSource": "https://evil.example/x.png"},
                {"depthFx": {"on": False}, "depthSource": "/api/builder/assets/still.png"},
                {"depthFx": "orbit", "depthSource": "/api/builder/assets/still.png"}):
        layer = project(bad)
        assert "depthFx" not in layer and "depthSource" not in layer
    other = builder._validated_project({"layers": [{"id": "c", "type": "background", "depthFx": {"camera": {"motion": "orbit"}},
                                                    "depthSource": "/api/builder/assets/still.png"}]})["layers"][0]
    assert "depthFx" not in other and "depthSource" not in other


@pytest.mark.skipif(not depth.available(), reason="depth model is not installed")
def test_cutout_depth_puts_transparent_pixels_far_and_keeps_edges_clean():
    """A Character-layer cut-out: transparent pixels are the far plane, and warping never darkens the figure's edge."""
    cut = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    figure = Image.new("RGBA", (120, 200), (240, 230, 220, 255))
    cut.paste(figure, (68, 40))
    estimate = depth.estimate(cut)
    assert estimate[5, 5] == 0 and estimate[140, 128] > 0
    scene = depth_fx.Scene(np.asarray(cut), estimate, depth_fx.normalize({"camera": {"motion": "sway", "strength": 2}}))
    frame = scene.frame(0.25)
    edge = frame[(frame[..., 3] > 20) & (frame[..., 3] < 235)]
    # Straight (non-premultiplied) warping mixed the black under the transparent pixels into the edge.
    assert edge.size and edge[:, :3].mean() > 200


def test_painted_body_breathes_only_where_painted():
    """"Mark the body" is a brush now: the painted strokes replace the box, far parts of the picture stay still."""
    strokes = [[x / 100, y / 100, 0.04] for x in range(40, 61, 3) for y in range(45, 71, 3)]
    options = depth_fx.normalize({"camera": {"motion": "none"}, "breath": {"on": True, "strength": 3, "chest": 2, "strokes": strokes,
                                                                           "region": {"cx": 0.2, "cy": 0.2, "rx": 0.1, "ry": 0.1}}})
    assert options["breath"]["strokes"][0] == [0.4, 0.45, 0.04]
    rng = np.random.default_rng(3)
    picture = (rng.random((200, 200, 3)) * 255).astype(np.uint8)
    scene = depth_fx.Scene(picture, np.full((200, 200), 0.5, np.float32), options)
    a, b = scene.frame(0.0).astype(int), scene.frame(0.25).astype(int)
    moved = np.abs(a - b)[..., :3].mean(axis=2)
    assert moved[110:130, 90:110].mean() > 5          # inside the painted body
    assert moved[:40, :40].mean() < 0.5                # the corner the old region pointed at stays still
    assert moved[:, 180:].mean() < 0.5
