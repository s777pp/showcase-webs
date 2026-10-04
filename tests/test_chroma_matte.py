"""Chroma keying of characters on solid backdrops (smweb/chroma_matte.py + static/js/chroma-matte.js)."""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from smweb import chroma_matte as cm

ROOT = Path(__file__).resolve().parents[1]


def character(backdrop, body, outline, eye, size=(160, 200), shift=0):
    """A figure with an outline, an eye of the backdrop colour and an arm that closes a big pocket."""
    image = Image.new("RGBA", size, backdrop + (255,))
    draw = ImageDraw.Draw(image)
    draw.ellipse((40 + shift, 20, 120 + shift, 100), fill=body, outline=outline, width=4)        # head
    draw.ellipse((66 + shift, 49, 74 + shift, 57), fill=eye, outline=outline, width=2)           # small eye
    draw.rectangle((55 + shift, 100, 105 + shift, 185), fill=body, outline=outline, width=4)     # body
    draw.rectangle((105 + shift, 110, 150 + shift, 118), fill=body, outline=outline, width=3)    # arm out
    draw.rectangle((142 + shift, 110, 150 + shift, 175), fill=body, outline=outline, width=3)    # arm down
    draw.rectangle((105 + shift, 167, 150 + shift, 175), fill=body, outline=outline, width=3)    # arm back -> pocket
    return image


def alpha_at(result, x, y):
    return int(np.asarray(result)[y, x, 3])


def key_one(image, mode="auto", **kw):
    return cm.key_frames([image], mode, **kw)[0]


@pytest.mark.parametrize("backdrop,body,outline,eye", [
    ((255, 255, 255), (230, 120, 60), (0, 0, 0), (255, 255, 255)),     # white backdrop, black outline, white eye
    ((0, 0, 0), (90, 140, 230), (255, 255, 255), (0, 0, 0)),           # the reverse
    ((0, 177, 64), (200, 80, 160), (20, 20, 20), (0, 177, 64)),        # green screen
    ((255, 102, 204), (60, 200, 120), (10, 10, 40), (255, 102, 204)),  # any colour: pink
    ((128, 128, 128), (250, 220, 90), (30, 30, 30), (128, 128, 128)),  # grey
])
def test_backdrop_goes_details_inside_stay(backdrop, body, outline, eye):
    result = key_one(character(backdrop, body, outline, eye))
    assert alpha_at(result, 3, 3) == 0 and alpha_at(result, 156, 196) == 0          # backdrop
    assert alpha_at(result, 80, 140) == 255                                          # body
    # A spot of the backdrop colour inside the figure: kept for white/grey/black keys (eyes,
    # highlights); a saturated key colour is never part of a figure, so it goes too.
    saturated = cm._key_saturation(backdrop) >= 40
    assert alpha_at(result, 70, 53) == (0 if saturated else 255)
    assert alpha_at(result, 125, 140) == 0                                           # big pocket by the arm is removed
    assert alpha_at(result, 42, 60) == 255                                           # outline stays


def test_pockets_can_be_kept():
    result = key_one(character((255, 255, 255), (230, 120, 60), (0, 0, 0), (255, 255, 255)), holes=False)
    assert alpha_at(result, 125, 140) == 255


def test_photo_without_a_solid_backdrop_is_left_alone():
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 255, (120, 160, 4), dtype=np.uint8)
    noise[..., 3] = 255
    result = key_one(Image.fromarray(noise, "RGBA"))
    assert np.array_equal(result, noise)


def test_cutout_is_left_alone():
    image = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((10, 10, 40, 40), fill=(255, 0, 0, 255))
    assert np.array_equal(key_one(image), np.asarray(image))


def test_soft_edge_has_no_backdrop_halo():
    image = Image.new("RGBA", (120, 120), (0, 177, 64, 255))
    ImageDraw.Draw(image).ellipse((20, 20, 100, 100), fill=(220, 40, 40, 255))
    small = image.resize((60, 60), Image.Resampling.LANCZOS)  # anti-aliased rim mixes red and green
    result = np.asarray(key_one(small)).astype(int)
    rim = (result[..., 3] > 0) & (result[..., 3] < 255)
    assert rim.any()
    # Un-mixed and despilled: the rim is not greener than it is red.
    assert (result[rim, 1] <= result[rim, 0]).mean() > 0.9


def test_clip_uses_one_backdrop_and_does_not_flicker():
    rng = np.random.default_rng(7)
    frames = []
    for index in range(8):
        frame = np.asarray(character((250, 250, 250), (230, 120, 60), (0, 0, 0), (250, 250, 250)), dtype=np.int16).copy()
        # GIF-like noise on the backdrop that changes every frame
        frame[..., :3] += rng.integers(-9, 10, frame[..., :3].shape, dtype=np.int16)
        frames.append(Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), "RGBA"))
    keyed = cm.key_frames(frames, "auto")
    alphas = np.stack([np.asarray(frame)[..., 3] for frame in keyed]).astype(int)
    # The figure does not move: its alpha must be (almost) identical in every frame.
    changing = (alphas.max(axis=0) - alphas.min(axis=0)) > 24
    assert changing.mean() < 0.002
    assert alphas[:, 3, 3].max() == 0 and alphas[:, 140, 80].min() == 255


def test_explicit_colour_wins_over_a_wrong_guess():
    image = character((255, 255, 255), (230, 120, 60), (0, 0, 0), (255, 255, 255))
    # Pretend the border measured something else: an explicit white still keys white.
    model = cm.resolve("#ffffff", cm.Model(key=(10, 200, 30), spread=0, coverage=1))
    out, _ = cm.apply(np.asarray(image), model)
    assert out[3, 3, 3] == 0 and out[140, 80, 3] == 255


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_browser_and_server_cut_the_same_matte(tmp_path):
    cases = [
        ("auto", character((255, 255, 255), (230, 120, 60), (0, 0, 0), (255, 255, 255))),
        ("auto", character((0, 177, 64), (200, 80, 160), (20, 20, 20), (0, 177, 64)).resize((120, 150), Image.Resampling.LANCZOS)),
        ("black", character((0, 0, 0), (90, 140, 230), (255, 255, 255), (0, 0, 0))),
    ]
    payload = []
    for mode, image in cases:
        array = np.asarray(image, dtype=np.uint8)
        payload.append({"mode": mode, "w": array.shape[1], "h": array.shape[0], "data": array.ravel().tolist()})
    (tmp_path / "in.json").write_text(json.dumps(payload))
    script = tmp_path / "run.js"
    script.write_text(
        "const fs=require('fs');require(%s);\n"
        "const cases=JSON.parse(fs.readFileSync(%s,'utf8'));\n"
        "const out=cases.map(c=>{const img={data:Uint8ClampedArray.from(c.data),width:c.w,height:c.h};"
        "const model=SMChroma.resolve(c.mode,SMChroma.estimate([img]));SMChroma.apply(img,model,{});return Array.from(img.data)});\n"
        "fs.writeFileSync(%s,JSON.stringify(out));\n" % (
            json.dumps(str(ROOT / "static/js/chroma-matte.js")), json.dumps(str(tmp_path / "in.json")),
            json.dumps(str(tmp_path / "out.json"))))
    subprocess.run(["node", str(script)], check=True)
    browser = json.loads((tmp_path / "out.json").read_text())
    for (mode, image), js in zip(cases, browser):
        server = key_one(image, mode).astype(int)
        js = np.array(js, dtype=int).reshape(server.shape)
        alpha_gap = np.abs(server[..., 3] - js[..., 3])
        assert (alpha_gap > 8).mean() < 0.002, mode
        visible = server[..., 3] > 32
        assert np.abs(server[visible, :3] - js[visible, :3]).max() <= 6, mode


def test_intro_frame_on_another_colour_is_keyed_by_its_own_backdrop():
    frames = [character((255, 255, 255), (230, 120, 60), (0, 0, 0), (255, 255, 255))]
    frames += [character((0, 177, 64), (230, 120, 60), (0, 0, 0), (230, 120, 60)) for _ in range(6)]
    keyed = cm.key_frames(frames, "auto")
    assert all(alpha_at(frame, 3, 3) == 0 for frame in keyed)
    assert all(alpha_at(frame, 80, 140) == 255 for frame in keyed)
