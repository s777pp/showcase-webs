"""Encode profile (Standard / Maximum quality) and the optional extra files in the ZIP."""
import io
import json
import subprocess
import zipfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageChops, ImageDraw

import processor as proc
from smweb import jobs
from smweb import workshop_studio_jobs as studio
from smweb.routers import process


def _frames(directory: Path, count: int = 3, size=(120, 80)) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        Image.new("RGB", size, (40 * index, 90, 160)).save(directory / f"frame_{index + 1:04d}.png")
    return directory


def _capture_gifski(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"GIF89a" + b"x" * 100)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(proc, "find_gifski", lambda: "gifski")
    monkeypatch.setattr(proc.subprocess, "run", fake_run)
    return calls


def test_profile_switches_gifski_flags(tmp_path, monkeypatch):
    calls = _capture_gifski(monkeypatch)
    frames = _frames(tmp_path / "frames")
    with proc.encode_profile("standard"):
        assert proc._gifski_from_frames(frames, tmp_path / "a.gif", fps=12, quality=80, extra=True)
    with proc.encode_profile("max"):
        assert proc._gifski_from_frames(frames, tmp_path / "b.gif", fps=12, quality=80, extra=True)
    fast_cmd, max_cmd = calls
    assert "--fast" in fast_cmd and "--extra" not in fast_cmd
    assert "--extra" in max_cmd and "--fast" not in max_cmd


def test_gifski_output_is_pinned_to_the_frame_size(tmp_path, monkeypatch):
    # Without --width gifski halves large animations (750x1500 came out 375x750).
    calls = _capture_gifski(monkeypatch)
    proc._gifski_from_frames(_frames(tmp_path / "frames", size=(750, 1500)), tmp_path / "a.gif", fps=12)
    cmd = calls[0]
    assert cmd[cmd.index("--width") + 1] == "750" and cmd[cmd.index("--height") + 1] == "1500"


def test_unknown_profile_from_a_form_means_standard_and_default_context_is_max():
    assert proc.normalize_encode_profile("max") == "max"
    assert proc.normalize_encode_profile("nonsense") == "standard"
    assert proc.normalize_encode_profile(None) == "standard"
    # Direct callers (gallery, profile) never set a profile and keep the old encoding.
    assert proc.encode_fast() is False


def test_standard_search_stops_earlier():
    limit = 1000

    def sizes(quality):
        return int(10 * 1.06 ** quality)  # smooth, monotonic size curve

    probes = []

    def size_at(quality):
        probes.append(quality)
        return sizes(quality)

    with proc.encode_profile("max"):
        best_max = proc._best_quality(size_at, limit)
    max_probes = len(probes)
    probes.clear()
    with proc.encode_profile("standard"):
        best_std = proc._best_quality(size_at, limit)
    assert sizes(best_max) <= limit and sizes(best_std) <= limit
    assert sizes(best_std) >= 0.88 * limit
    assert len(probes) <= max_probes


def test_extra_files_follow_the_users_choice():
    assert jobs._extra_wanted("part_1.gif", frozenset())
    assert not jobs._extra_wanted("full_original.gif", frozenset())
    assert not jobs._extra_wanted("full_with_bars.png", frozenset())
    assert not jobs._extra_wanted("full_with_watermark.gif", {proc.EXTRA_ORIGINAL})
    assert jobs._extra_wanted("full_original.png", {proc.EXTRA_ORIGINAL})
    assert jobs._extra_wanted("full_with_bars.gif", {proc.EXTRA_PREVIEW})
    # Jobs queued before the option existed keep everything.
    assert jobs._extra_wanted("full_original.gif", None)


def test_selected_extras_parses_form_switches():
    assert process._selected_extras("1", "0") == {proc.EXTRA_ORIGINAL}
    assert process._selected_extras("on", "true") == {proc.EXTRA_ORIGINAL, proc.EXTRA_PREVIEW}
    assert process._selected_extras("", None) == set()


@pytest.fixture
def clip(tmp_path):
    if not proc.find_ffmpeg():
        pytest.skip("FFmpeg is not installed")
    path = tmp_path / "clip.mp4"
    subprocess.run([proc.find_ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=320x400:rate=24:duration=3", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_ffmpeg_panel_cut_matches_pillow_and_cuts_every_panel_to_the_duration(tmp_path, clip):
    fast_full, fast_parts, count = proc._prepare_workshop_frame_sets(
        clip, tmp_path, fps=10, width=300, duration=1.5, outline_width=2,
        outline_color="#ff8800", need_full=True)
    # `-t` binds to one output only; every panel must stop at the same frame.
    counts = [len(list(directory.glob("frame_*.png"))) for directory in fast_parts]
    assert counts == [count] * 5 and count == 15
    assert len(list(fast_full.glob("frame_*.png"))) == count
    # Same pixels as cropping the full frame in Pillow and drawing the stroke there.
    for index, part_dir in enumerate(fast_parts):
        with Image.open(fast_full / "frame_0007.png") as full:
            expected = full.convert("RGBA").crop((index * 60, 0, index * 60 + 60, full.height))
        draw = ImageDraw.Draw(expected)
        for offset in range(2):
            draw.rectangle((offset, offset, expected.width - 1 - offset, expected.height - 1 - offset),
                           outline=(255, 136, 0), width=1)
        with Image.open(part_dir / "frame_0007.png") as actual:
            assert ImageChops.difference(expected, actual.convert("RGBA")).getbbox() is None


def test_split_cut_writes_both_parts_without_full_frames(tmp_path, clip):
    full, parts, count = proc._prepare_split_frame_sets(clip, tmp_path, fps=8, duration=1, need_full=False)
    assert [len(list(p.glob("*.png"))) for p in parts] == [count, count]
    assert not list(full.glob("*.png"))
    with Image.open(parts[0] / "frame_0001.png") as center, Image.open(parts[1] / "frame_0001.png") as side:
        assert center.width == 506 and side.width == 100


@pytest.mark.skipif(not proc.find_gifski(), reason="gifski is not installed")
def test_workshop_gif_without_extras_holds_only_the_steam_files(tmp_path, clip):
    with proc.encode_profile("standard"):
        only_steam = proc.process_video_workshop(clip, tmp_path / "a", fps=8, width=300, duration=1,
                                                 encoder="gifski", extras=())
    assert sorted(only_steam) == [f"part_{index}.gif" for index in range(1, 6)]
    with proc.encode_profile("standard"):
        everything = proc.process_video_workshop(clip, tmp_path / "b", fps=8, width=300, duration=1,
                                                 encoder="gifski")
    assert {"full_original.gif", "full_with_bars.gif"} <= set(everything)


@pytest.mark.skipif(not proc.find_gifski(), reason="gifski is not installed")
def test_featured_video_is_encoded_once(tmp_path, clip, monkeypatch):
    calls = []
    original = proc.media_to_gif
    monkeypatch.setattr(proc, "media_to_gif", lambda *a, **k: calls.append(a[0]) or original(*a, **k))
    with proc.encode_profile("standard"):
        result = proc.process_video_featured(clip, tmp_path, fps=8, duration=1, encoder="gifski", extras=())
    assert sorted(result) == ["featured_630.gif"]
    assert calls == [clip]  # straight from the video, no intermediate GIF
    assert result["featured_630.gif"].read_bytes()[-1] == 0x21


def test_extract_frames_feeds_the_character_compositor(tmp_path, clip):
    count = proc.extract_frames(clip, tmp_path / "bg", fps=6, width=320, duration=1)
    still = tmp_path / "char.png"
    Image.new("RGBA", (40, 40), (255, 0, 0, 255)).save(still)
    frames, durations = proc.compose_animated_layers(tmp_path / "bg", still, chroma_key="none",
                                                     target_width=320, fps=6, max_seconds=1)
    assert count == 6 and len(frames) == 6 and set(durations) == {round(1000 / 6)}


def test_squares_extras_are_optional(tmp_path):
    source = tmp_path / "art.png"
    Image.new("RGB", (750, 300), "#335577").save(source)
    crop = studio.normalize_crop({"x": 0, "y": 0, "w": 1, "h": 0.5})
    settings = {"brightness": 100, "contrast": 100, "saturation": 100, "hue": 0, "start": 0}
    steam_only = studio.render_squares_image(source, settings, crop, extras=())
    assert sorted(steam_only) == [f"part_{index}.png" for index in range(1, 6)]
    both = studio.render_squares_image(source, settings, crop, extras=(proc.EXTRA_ORIGINAL, proc.EXTRA_PREVIEW))
    assert {"full_original.png", "preview.png"} <= set(both)
    with Image.open(io.BytesIO(both["full_original.png"])) as strip:
        assert strip.size == (750, 150)


def test_start_routes_store_the_choice(tmp_path, monkeypatch):
    captured = []
    monkeypatch.setattr(process, "JOBS", tmp_path)
    monkeypatch.setattr(process.rs, "job_create", lambda jid, payload, enqueue=False: captured.append(payload))
    monkeypatch.setattr(process, "_job_set", lambda *a, **k: None)
    monkeypatch.setattr(process._job_pool, "submit", lambda *a, **k: None)
    # Other tests in the run spend the shared free daily limit.
    monkeypatch.setattr(process, "quota_state", lambda _request: {"pro": False, "left": 5, "limit": 5, "email": ""})
    monkeypatch.setattr(process.rs, "quota_inc", lambda ip, day, n=1: 0)  # StartGuard reserves through it
    buffer = io.BytesIO()
    Image.new("RGB", (300, 300), "#235070").save(buffer, format="PNG")
    app = FastAPI()
    app.include_router(process.router)
    with TestClient(app) as client:
        response = client.post("/api/process/start", data={"mode": "workshop", "encode_profile": "max",
                                                           "include_preview": "1"},
                               files=[("files", ("a.png", buffer.getvalue(), "image/png"))])
        assert response.status_code == 200, response.text
        response = client.post("/api/workshop-studio/start", data={
            "rows": "1", "settings": json.dumps([{"brightness": 100}])},
            files=[("files", ("b.png", buffer.getvalue(), "image/png"))])
        assert response.status_code == 200, response.text
    process_opts = captured[0]["opts"]
    assert process_opts["encode_profile"] == "max" and process_opts["extras"] == [proc.EXTRA_PREVIEW]
    studio_opts = captured[1]["options"]
    assert studio_opts["encode_profile"] == "standard" and studio_opts["extras"] == []


def test_job_without_extras_zips_only_steam_files(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "JOBS", tmp_path)
    still = io.BytesIO()
    Image.new("RGB", (750, 400), "#446688").save(still, format="PNG")
    source = tmp_path / "art.png"
    source.write_bytes(still.getvalue())
    opts = {"modes": ["featured"], "text": "", "opacity": 0.0, "color": "#ffffff", "corner": "bl", "scale": 1.0,
            "wm_x": None, "wm_y": None, "do_ac": False, "size_i": 750, "fps": 12, "enc": "gifski",
            "wm_font": "lap", "extras": []}
    jobs._run_process_job("a" * 24, [("art.png", source, 0)], opts)
    with zipfile.ZipFile(tmp_path / ("a" * 24) / "result.zip") as archive:
        assert archive.namelist() == ["art_featured/featured_630.png"]
