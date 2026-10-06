import io

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import processor as proc
from smweb import gif_optimizer as opt
from smweb.routers import gif_optimizer as api


def _noisy_gif(path, frames=12, size=(160, 96), seed=1):
    rng = np.random.default_rng(seed)
    images = []
    for index in range(frames):
        base = np.zeros((size[1], size[0], 3), np.uint8)
        base[..., 0] = np.linspace(0, 255, size[0], dtype=np.uint8)[None, :]
        base[..., 1] = (index * 20) % 255
        noise = rng.integers(0, 60, (size[1], size[0], 3), dtype=np.uint8)
        images.append(Image.fromarray(np.clip(base.astype(int) + noise, 0, 255).astype(np.uint8)))
    images[0].save(path, save_all=True, append_images=images[1:], duration=80, loop=0)
    return path


def _colors_used(path):
    most = 0
    with Image.open(path) as im:
        for index in range(im.n_frames):
            im.seek(index)
            most = max(most, len(im.convert("RGB").getcolors(1 << 24) or []))
    return most


def test_info_reads_frames_size_and_timing(tmp_path):
    gif = _noisy_gif(tmp_path / "a.gif", frames=5)
    meta = opt.info(gif)
    assert meta["frames"] == 5 and (meta["width"], meta["height"]) == (160, 96)
    assert meta["duration_ms"] == 400 and meta["size"] == gif.stat().st_size


def test_info_rejects_a_broken_file(tmp_path):
    bad = tmp_path / "bad.gif"
    bad.write_bytes(b"GIF89a" + b"\0" * 20)
    with pytest.raises(ValueError):
        opt.info(bad)


def test_lossy_percent_maps_to_gifsicle_range():
    assert opt.lossy_value(0) == 0 and opt.lossy_value(30) == 60 and opt.lossy_value(100) == 200
    assert opt.lossy_value(500) == 200 and opt.lossy_value(-5) == 0


def test_manual_builds_the_gifsicle_command(tmp_path, monkeypatch):
    calls = []

    class Done:
        returncode = 0
        stdout = stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        (tmp_path / "out.gif").write_bytes(b"GIF89a")
        return Done()

    monkeypatch.setattr(opt, "find_gifsicle", lambda: "gifsicle")
    monkeypatch.setattr(opt.process_control, "run", fake_run)
    src = _noisy_gif(tmp_path / "in.gif", frames=2)
    assert opt.manual(src, tmp_path / "out.gif", colors=64, lossy=30) == "gifsicle"
    command = calls[0]
    assert command[:3] == ["gifsicle", "--no-warnings", "-O3"]
    assert "--lossy=60" in command and command[command.index("--colors") + 1] == "64"
    # 256 colours and 0 % lossy: only the optimisation pass
    calls.clear()
    opt.manual(src, tmp_path / "out.gif", colors=256, lossy=0)
    assert "--colors" not in calls[0] and not any(a.startswith("--lossy") for a in calls[0])


@pytest.mark.skipif(not proc.find_ffmpeg(), reason="FFmpeg is required")
def test_manual_fallback_limits_colours_and_shrinks(tmp_path, monkeypatch):
    monkeypatch.setattr(opt, "find_gifsicle", lambda: None)
    src = _noisy_gif(tmp_path / "in.gif")
    out = tmp_path / "out.gif"
    assert opt.manual(src, out, colors=32, lossy=90) == "ffmpeg"
    assert out.stat().st_size < src.stat().st_size
    assert _colors_used(out) <= 32
    assert opt.info(out)["frames"] == 12


def test_auto_returns_a_gif_that_already_fits_unchanged(tmp_path):
    src = _noisy_gif(tmp_path / "small.gif", frames=2)
    out = tmp_path / "out.gif"
    assert opt.auto(src, out)["already_fits"] is True
    assert out.read_bytes() == src.read_bytes()


@pytest.mark.skipif(not (proc.find_ffmpeg() and proc.find_gifski()), reason="FFmpeg and gifski are required")
def test_auto_fits_the_limit(tmp_path):
    src = _noisy_gif(tmp_path / "big.gif", frames=16, size=(320, 180))
    limit_mb = src.stat().st_size / 1024 / 1024 * 0.5
    out = tmp_path / "out.gif"
    details = opt.auto(src, out, max_mb=limit_mb)
    assert details["engine"] in ("gifski", "fallback")
    assert out.stat().st_size <= limit_mb * 1024 * 1024
    assert opt.info(out)["frames"] >= 8


def _client(tmp_path, monkeypatch, owner="guest-1", left=5):
    monkeypatch.setattr(api, "DATA", tmp_path)
    monkeypatch.setattr(api, "quota_state", lambda request: {"pro": False, "left": left, "limit": 5})
    # These tests cover the tool itself. While it is in beta it is Pro-only (tests/test_free_limits.py).
    monkeypatch.setenv("BETA_FEATURES", "")
    monkeypatch.setattr(api, "_auth_user", lambda request: None)
    monkeypatch.setattr(api, "owner_key", lambda request, user=None: owner)
    monkeypatch.setattr(api, "_worker_mode", lambda: "embedded")
    monkeypatch.setattr(api, "quota_inc", lambda request, count: None)
    monkeypatch.setattr(api._job_pool, "submit", lambda func, *args: func(*args))
    monkeypatch.setattr(opt, "find_gifsicle", lambda: None)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


@pytest.mark.skipif(not proc.find_ffmpeg(), reason="FFmpeg is required")
def test_api_runs_a_job_and_serves_both_files(tmp_path, monkeypatch):
    raw = _noisy_gif(tmp_path / "src.gif").read_bytes()
    with _client(tmp_path, monkeypatch) as client:
        started = client.post("/api/gif-optimizer/start", data={"mode": "manual", "colors": "64", "lossy": "40"},
                              files={"file": ("My art.gif", raw, "image/gif")})
        assert started.status_code in (200, 202), started.text
        jid = started.json()["job_id"]
        state = client.get(f"/api/gif-optimizer/status/{jid}").json()
        assert state["status"] == "done" and state["size_before"] == len(raw)
        assert 0 < state["size_after"] < len(raw)
        result = client.get(state["download_url"])
        assert result.status_code == 200 and result.content[:6] == b"GIF89a"
        assert "My_art_optimized.gif" in result.headers["content-disposition"]
        assert client.get(state["source_url"]).content == raw


def test_api_rejects_non_gif_and_spent_quota(tmp_path, monkeypatch):
    png = io.BytesIO()
    Image.new("RGB", (10, 10)).save(png, format="PNG")
    with _client(tmp_path, monkeypatch) as client:
        response = client.post("/api/gif-optimizer/start", files={"file": ("a.png", png.getvalue(), "image/png")})
        assert response.status_code == 400 and response.json()["code"] == "not_gif"
    with _client(tmp_path, monkeypatch, left=0) as client:
        response = client.post("/api/gif-optimizer/start", files={"file": ("a.gif", b"GIF89a", "image/gif")})
        assert response.status_code == 403 and response.json()["code"] == "quota"


@pytest.mark.skipif(not proc.find_ffmpeg(), reason="FFmpeg is required")
def test_jobs_are_private_to_their_owner(tmp_path, monkeypatch):
    raw = _noisy_gif(tmp_path / "src.gif", frames=3).read_bytes()
    with _client(tmp_path, monkeypatch, owner="owner-a") as client:
        jid = client.post("/api/gif-optimizer/start", files={"file": ("a.gif", raw, "image/gif")}).json()["job_id"]
    with _client(tmp_path, monkeypatch, owner="owner-b") as client:
        assert client.get(f"/api/gif-optimizer/status/{jid}").status_code == 404
        assert client.get(f"/api/gif-optimizer/file/{jid}/source").status_code == 404
