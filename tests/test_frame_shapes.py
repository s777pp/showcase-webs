"""HUD frame designs (plate + outline), panel roles for Artwork Split and the
two outline animations (shimmer = animation 1, grain = animation 2)."""
import io
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from smweb import frame_designs, square_fx
from tests.test_process_frames import _mode_opts, _png, _png_entry, _run

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "static" / "js" / "workshop-squares-fx.js"
PANELS = [((0, 0, 506, 824), "left"), ((0, 0, 100, 824), "right"), ((0, 0, 630, 420), "full"),
          ((0, 0, 150, 150), "full"), ((0, 0, 750, 150), "full")]


def _frame(style: str, shape: str, **extra) -> dict:
    return square_fx.normalize_frame({"style": style, "shape": shape, "width": 3, "color": "#40e0ff",
                                      "color2": "#8a62ff", "speed": 1, **extra})


def test_catalog_and_normalize():
    assert len(frame_designs.design_ids()) >= 12
    assert square_fx.FRAME_SHAPES[:3] == ("rect", "bevel", "notch")
    assert set(frame_designs.design_ids()) <= set(square_fx.FRAME_SHAPES)
    assert _frame("solid", "hud", plate=250)["plate"] == 100
    assert _frame("solid", "../../etc")["shape"] == "rect"
    assert {"shimmer", "grain"} <= square_fx.ANIMATED_FRAMES


@pytest.mark.parametrize("shape", square_fx.FRAME_SHAPES)
def test_outlines_stay_near_their_panel(shape):
    for rect, role in PANELS:
        x, y, w, h = rect
        col = frame_designs._catalog()[shape]["col"] if shape in frame_designs.design_ids() else 70
        slack = 8 * frame_designs.unit(role, w, h, col) + 2
        for points, _closed in square_fx.shape_paths(shape, rect, 3, role):
            for px, py in points:
                assert x - slack <= px <= x + w + slack and y - slack <= py <= y + h + slack, (shape, rect, role)


@pytest.mark.parametrize("shape", frame_designs.design_ids())
def test_split_pair_has_equal_columns_and_the_right_one_fits_in_100px(shape):
    """Split: one frame around the 606 px pair (Featured thickness), cut at 506."""
    plate, _ = square_fx._panel_masks(shape, (606, 824), 3, "full")
    mask = np.asarray(plate, dtype=float) / 255
    left, right = mask[:, :100], mask[:, 506:]
    best = min(np.abs(np.roll(left[:, ::-1], shift, axis=1) - right)[:, 1:-1].mean() for shift in (-1, 0, 1))
    assert best < 0.01, (shape, best)
    col = frame_designs._catalog()[shape]["col"] * frame_designs.unit("full", 606, 824)
    assert col <= 100, (shape, col)


@pytest.mark.parametrize("shape", square_fx.FRAME_SHAPES)
def test_textures_and_solid_loop_on_every_design(shape):
    base = Image.new("RGBA", (750, 150), (10, 20, 30, 255))
    for style in ("solid", "shimmer", "grain"):
        frame = dict(_frame(style, shape, plate=80), target="strip")
        start, end = square_fx.draw_frame(base, 0.0, frame), square_fx.draw_frame(base, 1.0, frame)
        assert start.tobytes() == end.tobytes(), f"{shape}/{style}"
        if style != "solid":
            assert square_fx.draw_frame(base, 0.4, frame).tobytes() != start.tobytes(), f"{shape}/{style} moves"


def test_every_style_works_on_a_hud_design():
    base = Image.new("RGBA", (606, 300), (10, 20, 30, 255))
    for style in sorted(square_fx.FRAME_STYLES - {"none"}):
        frame = dict(_frame(style, "hud", plate=100), target="strip")
        start = square_fx.draw_frame(base, 0.0, frame, role="left")
        assert start.tobytes() == square_fx.draw_frame(base, 1.0, frame, role="left").tobytes(), style
        assert np.asarray(start)[..., 2].max() > 150, f"{style} draws a visible outline"


def test_plate_darkens_outside_the_window_only():
    base = Image.new("RGBA", (630, 400), (200, 60, 60, 255))
    framed = square_fx.draw_frame(base, 0.0, dict(_frame("solid", "bevel", plate=100), target="strip")).convert("RGB")
    assert framed.getpixel((2, 2)) == square_fx.PLATE_RGB, "cut corner is covered by the plate"
    assert framed.getpixel((315, 200)) == (200, 60, 60), "the art shows through the window"


def test_bars_only_design_keeps_the_middle_clear():
    base = Image.new("RGBA", (606, 300), (200, 60, 60, 255))
    framed = square_fx.draw_frame(base, 0.0, dict(_frame("solid", "twin", plate=100), target="strip")).convert("RGB")
    assert framed.getpixel((303, 150)) == (200, 60, 60)
    assert framed.getpixel((23, 150)) != (200, 60, 60), "left bar"


def test_outline_is_cut_where_bars_overlap():
    """Crossing bars (blade) must not show an outline inside the plate."""
    _plate, interior = square_fx._panel_masks("blade", (606, 824), 3, "full")
    base = Image.new("RGBA", (606, 824), (0, 0, 0, 255))
    framed = np.asarray(square_fx.draw_frame(base, 0.0, dict(_frame("solid", "blade", plate=100), target="strip")))
    inside = np.asarray(interior) == 255
    assert inside.any() and framed[inside][:, 2].max() < 40


def test_split_job_frames_both_parts_as_one(tmp_path, monkeypatch):
    opts = _mode_opts("split", "solid")
    opts["outline_fx"] = square_fx.normalize_frame({"style": "solid", "shape": "hud", "plate": 100,
                                                    "color": "#ff00aa", "width": 3})
    _, archive = _run(tmp_path, monkeypatch, "art.png", _png((606, 300)), opts)
    with _png_entry(archive, "center_506.png") as center, _png_entry(archive, "side_100.png") as side:
        assert center.getpixel((2, 150)) == square_fx.PLATE_RGB, "506 part: ornament column on its left"
        assert center.getpixel((300, 150)) == (0x20, 0x30, 0x40)
        assert side.getpixel((97, 150)) == square_fx.PLATE_RGB, "100 part: ornament column on its right"


def test_workshop_line_with_a_shape_uses_the_shaped_renderer(tmp_path, monkeypatch):
    from tests.test_process_frames import _opts
    opts = _opts("solid")
    opts["outline_fx"] = square_fx.normalize_frame({"style": "solid", "shape": "bevel", "plate": 100,
                                                    "color": "#ff00aa", "width": 3})
    _, archive = _run(tmp_path, monkeypatch, "art.png", _png(), opts)
    part = sorted(name for name in archive.namelist() if "/part_" in name)[0]
    with Image.open(io.BytesIO(archive.read(part))) as image:
        assert image.convert("RGB").getpixel((1, 1)) == square_fx.PLATE_RGB


def _node(script: str) -> dict:
    prelude = ("global.window={};global.document={getElementById(){return null},addEventListener(){}};"
               "require(%s);const api=window.SMSquaresFx;api.useDesigns(JSON.parse(require('fs').readFileSync(%s,'utf8')));"
               % (json.dumps(str(JS)), json.dumps(str(frame_designs.DESIGNS_FILE))))
    return json.loads(subprocess.run(["node", "-e", prelude + script], capture_output=True, text=True, check=True).stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_browser_builds_the_same_geometry():
    cases = [[list(rect), role] for rect, role in PANELS]
    data = _node("const out={};for(const s of api.FRAME_SHAPES)out[s]=%s.map(c=>api.panelGeometry(s,c[0],3,c[1]));"
                 "console.log(JSON.stringify({shapes:api.FRAME_SHAPES,animated:api.ANIMATED_FRAMES,out}))" % json.dumps(cases))
    assert tuple(data["shapes"]) == square_fx.FRAME_SHAPES
    assert set(data["animated"]) == square_fx.ANIMATED_FRAMES

    def rounded(paths):
        return [[round(v, 5) for point in path for v in point] for path in paths]
    for shape in square_fx.FRAME_SHAPES:
        for (rect, role), js in zip(PANELS, data["out"][shape]):
            even_odd, bars, paths = square_fx.panel_geometry(shape, rect, 3, role)
            assert rounded(even_odd) == rounded(js["evenOdd"]), (shape, rect, role)
            assert rounded(bars) == rounded(js["bars"]), (shape, rect, role)
            assert [closed for _p, closed in paths] == [closed for _p, closed in js["paths"]]
            assert rounded([p for p, _c in paths]) == rounded([p for p, _c in js["paths"]]), (shape, rect, role)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_browser_outline_textures_match_the_server():
    points = [(x * 37.3, y * 11.7, u / 7) for x in range(12) for y in range(6) for u in range(7)]
    data = _node("const pts=%s,out={};for(const s of ['shimmer','grain'])for(const sp of [1,3])"
                 "out[s+sp]=pts.map(p=>api.textureLevel(s,p[0],p[1],p[2],0.8,sp));console.log(JSON.stringify(out))"
                 % json.dumps(points))
    xs = np.array([p[0] for p in points])
    ys = np.array([p[1] for p in points])
    for style in ("shimmer", "grain"):
        for speed in (1, 3):
            expected = [float(square_fx.texture_level(style, xs[i:i + 1], ys[i:i + 1], points[i][2], 0.8, speed)[0])
                        for i in range(len(points))]
            assert data[style + str(speed)] == pytest.approx(expected, abs=1e-9)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_browser_grain_hash_matches_the_server():
    data = _node("const out=[];for(let i=0;i<40;i++)for(let j=0;j<20;j++)out.push(api.hash3(i*37,j,i%5));"
                 "console.log(JSON.stringify(out))")
    expected = [float(square_fx._hash3(np.array([i * 37]), np.array([j]), np.array([i % 5]))[0])
                for i in range(40) for j in range(20)]
    assert data == pytest.approx(expected, abs=1e-12)
