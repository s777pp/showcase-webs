import io
import zipfile

from PIL import Image

import processor
import redis_store as rs
from smweb import jobs as jobs_module
from smweb import square_fx


def _opts(style: str, **extra) -> dict:
    return {"modes": ["workshop"], "text": "", "opacity": 0, "color": "#ffffff", "corner": "bl", "scale": 1.0,
            "wm_x": None, "wm_y": None, "do_ac": False, "size_i": 750, "fps": 8, "enc": "ffmpeg", "wm_font": "lap",
            "outline_width": 3, "outline_color": "#ff00aa",
            "outline_fx": square_fx.normalize_frame({"style": style, "color": "#ff00aa", "width": 3, "speed": 1}), **extra}


def _run(tmp_path, monkeypatch, name: str, data: bytes, opts: dict) -> tuple[dict, zipfile.ZipFile]:
    monkeypatch.setattr(jobs_module, "JOBS", tmp_path)
    monkeypatch.setattr(jobs_module, "_record_process_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(jobs_module.object_store, "configured", lambda: False)
    monkeypatch.setattr(rs, "_r", lambda: None)
    rs._local_jobs.clear()
    jid = "f" * 24
    (tmp_path / jid).mkdir()
    source = tmp_path / jid / f"00_{name}"
    source.write_bytes(data)
    jobs_module._run_process_job(jid, [(name, source, 0)], opts)
    job = rs.job_get(jid)
    assert job["status"] == "done", job.get("error")
    return job, zipfile.ZipFile(tmp_path / jid / "result.zip")


def _png(size=(750, 400)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "#203040").save(buffer, format="PNG")
    return buffer.getvalue()


def test_static_neon_outline_stays_png_on_every_panel(tmp_path, monkeypatch):
    _, archive = _run(tmp_path, monkeypatch, "art.png", _png(), _opts("neon"))
    parts = sorted(name for name in archive.namelist() if "/part_" in name)
    assert [name.rsplit("/", 1)[1] for name in parts] == [f"part_{i}.png" for i in range(1, 6)]
    with Image.open(io.BytesIO(archive.read(parts[2]))) as part:
        r, g, b = part.convert("RGB").getpixel((1, 200))
        assert r > 150 and b > 100, "neon outline on the left edge of panel 3"


def test_animated_outline_turns_a_still_into_synchronized_gifs(tmp_path, monkeypatch):
    if not processor.find_ffmpeg():
        return
    _, archive = _run(tmp_path, monkeypatch, "art.png", _png(), _opts("rgb"))
    parts = sorted(name for name in archive.namelist() if "/part_" in name)
    assert len(parts) == 5 and all(name.endswith(".gif") for name in parts)
    frame_counts = set()
    for name in parts:
        payload = archive.read(name)
        assert payload[-1] == 0x21
        with Image.open(io.BytesIO(payload[:-1] + b";")) as part:
            assert part.width == 150
            frame_counts.add(part.n_frames)
    assert len(frame_counts) == 1 and frame_counts.pop() > 1


def test_animated_outline_on_a_gif_source(tmp_path, monkeypatch):
    if not processor.find_ffmpeg():
        return
    buffer = io.BytesIO()
    frames = [Image.new("RGB", (750, 300), color) for color in ("#402060", "#204060")]
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=150, loop=0)
    _, archive = _run(tmp_path, monkeypatch, "anim.gif", buffer.getvalue(), _opts("comet"))
    parts = sorted(name for name in archive.namelist() if "/part_" in name)
    assert len(parts) == 5


def _mode_opts(mode: str, style: str, target: str = "squares") -> dict:
    opts = _opts(style, modes=[mode])
    opts["outline_fx"] = square_fx.normalize_frame(
        {"style": style, "color": "#ff00aa", "width": 3, "speed": 1, "target": target})
    return opts


def _png_entry(archive, suffix):
    name = next(name for name in archive.namelist() if name.endswith(suffix))
    return Image.open(io.BytesIO(archive.read(name))).convert("RGB")


def test_featured_gets_a_frame_around_the_whole_artwork(tmp_path, monkeypatch):
    _, archive = _run(tmp_path, monkeypatch, "art.png", _png((1260, 700)), _mode_opts("featured", "solid"))
    with _png_entry(archive, "featured_630.png") as featured:
        assert featured.width == 630
        assert featured.getpixel((1, 150)) == (255, 0, 170)
        assert featured.getpixel((628, 150)) == (255, 0, 170)
        assert featured.getpixel((315, 150)) == (0x20, 0x30, 0x40)


def test_split_frames_each_part_or_the_whole_pair(tmp_path, monkeypatch):
    _, archive = _run(tmp_path, monkeypatch, "art.png", _png((606, 300)), _mode_opts("split", "solid"))
    with _png_entry(archive, "center_506.png") as center, _png_entry(archive, "side_100.png") as side:
        assert center.getpixel((504, 100)) == (255, 0, 170), "each part: right edge of center framed"
        assert side.getpixel((1, 100)) == (255, 0, 170), "each part: left edge of side framed"

    (tmp_path / "whole").mkdir()
    _, archive = _run(tmp_path / "whole", monkeypatch, "art.png", _png((606, 300)),
                      _mode_opts("split", "solid", target="strip"))
    with _png_entry(archive, "center_506.png") as center, _png_entry(archive, "side_100.png") as side:
        assert center.getpixel((1, 100)) == (255, 0, 170)
        assert center.getpixel((504, 100)) == (0x20, 0x30, 0x40), "whole pair: no line between the parts"
        assert side.getpixel((98, 100)) == (255, 0, 170)


def test_animated_frame_on_featured_and_split_stills_becomes_looping_gifs(tmp_path, monkeypatch):
    if not processor.find_ffmpeg():
        return
    _, archive = _run(tmp_path, monkeypatch, "art.png", _png((1260, 600)), _mode_opts("featured", "comet"))
    payload = archive.read(next(n for n in archive.namelist() if n.endswith("featured_630.gif")))
    assert payload[-1] == 0x21 and len(payload) <= 5 * 1024 * 1024
    with Image.open(io.BytesIO(payload[:-1] + b";")) as featured:
        assert featured.width == 630 and featured.n_frames > 1

    (tmp_path / "split").mkdir()
    _, archive = _run(tmp_path / "split", monkeypatch, "art.png", _png((606, 300)), _mode_opts("split", "rgb"))
    counts = set()
    for suffix, width in (("center_506.gif", 506), ("side_100.gif", 100)):
        payload = archive.read(next(n for n in archive.namelist() if n.endswith(suffix)))
        with Image.open(io.BytesIO(payload[:-1] + b";")) as part:
            assert part.width == width
            counts.add(part.n_frames)
    assert len(counts) == 1 and counts.pop() > 1, "center and side stay synchronized"


def test_gifski_accepts_a_single_frame_sequence(tmp_path):
    if not processor.find_gifski():
        return
    frames = tmp_path / "frames"
    frames.mkdir()
    Image.new("RGB", (120, 60), "#203040").save(frames / "frame_0001.png")
    destination = tmp_path / "out.gif"
    assert processor._gifski_from_frames(frames, destination, fps=12)
    with Image.open(destination) as gif:
        assert gif.size == (120, 60)
