"""Picture from emoticons" (smweb/emoticon_colors.py, POST /api/infobox/emoticons, static/js/infobox-emoji.js)."""

import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from smweb import emoticon_colors, middleware
from smweb.routers import infobox as infobox_router

ROOT = Path(__file__).resolve().parents[1]


def _png(color=(255, 0, 0, 255), size=18, left_clear=False):
    image = Image.new("RGBA", (size, size), color)
    if left_clear:
        for x in range(size // 3):
            for y in range(size):
                image.putpixel((x, y), (0, 0, 0, 0))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def test_names_are_cleaned_and_deduplicated():
    raw = [":steamhappy:", "ːsteamsadː", "steamhappy", "bad name", "<x>", "a" * 61, 7, None, "ok_1-2"]
    assert emoticon_colors.clean_names(raw) == ["steamhappy", "steamsad", "ok_1-2"]
    assert emoticon_colors.clean_names("not a list") == []


def test_grid_colors_weigh_by_alpha():
    cells = emoticon_colors.grid_colors(_png((10, 200, 30, 255), left_clear=True))
    assert len(cells) == 9
    # Left column is fully transparent: no coverage; the rest is the solid colour.
    assert cells[0][3] == 0 and cells[3][3] == 0 and cells[6][3] == 0
    assert cells[1] == [10, 200, 30, 255]
    # Other sizes are scaled to Steam's 18 px first.
    assert emoticon_colors.grid_colors(_png((0, 0, 255, 255), size=54))[4] == [0, 0, 255, 255]


def test_colors_cache_hits_misses_and_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(emoticon_colors, "_CACHE", tmp_path / "emo")
    calls = []

    def fake(name):
        calls.append(name)
        if name == "gone":
            return "missing", None
        if name == "flaky":
            return "error", None
        return "ok", emoticon_colors.grid_colors(_png())

    monkeypatch.setattr(emoticon_colors, "_download", fake)
    first = emoticon_colors.colors(["red", "gone", "flaky"])
    assert set(first["items"]) == {"red"} and first["missing"] == ["gone"] and first["failed"] == ["flaky"]
    calls.clear()
    second = emoticon_colors.colors(["red", "gone", "flaky"])
    # Found and missing names come from the cache; a failure is asked again.
    assert calls == ["flaky"]
    assert set(second["items"]) == {"red"} and second["missing"] == ["gone"]
    # A missing name is checked again after a day.
    record = json.loads((tmp_path / "emo" / "gone.json").read_text())
    record["t"] -= emoticon_colors.MISSING_TTL + 1
    (tmp_path / "emo" / "gone.json").write_text(json.dumps(record))
    calls.clear()
    emoticon_colors.colors(["gone"])
    assert calls == ["gone"]


def test_route(monkeypatch, tmp_path):
    monkeypatch.setattr(emoticon_colors, "_CACHE", tmp_path / "emo")
    monkeypatch.setattr(emoticon_colors, "_download", lambda name: ("ok", emoticon_colors.grid_colors(_png())))
    app = FastAPI()
    app.include_router(infobox_router.router)
    client = TestClient(app)
    ok = client.post("/api/infobox/emoticons", json={"names": [":a1:", "b2"]})
    assert ok.status_code == 200 and set(ok.json()["items"]) == {"a1", "b2"}
    assert client.post("/api/infobox/emoticons", json={"names": ["bad name"]}).status_code == 400
    assert client.post("/api/infobox/emoticons", content=b"nope").status_code == 400
    many = [f"e{i}" for i in range(emoticon_colors.MAX_NAMES + 1)]
    assert client.post("/api/infobox/emoticons", json={"names": many}).json()["code"] == "too_many"


def test_rate_rule():
    rules = dict((prefix, (limit, window)) for prefix, limit, window in middleware.RateLimitMiddleware.RULES)
    assert rules["/api/infobox/emoticons"] == (30, 60)


def _node(script):
    prelude = "const E=require(%s);" % json.dumps(str(ROOT / "static" / "js" / "infobox-emoji.js"))
    return json.loads(subprocess.run(["node", "-e", prelude + script], capture_output=True, text=True, encoding="utf-8", check=True).stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_engine_matches_colours_and_keeps_the_limit():
    data = _node(r"""
      const solid = c => Array(9).fill([...c, 255]);
      const items = [{name: 'r', cells: solid([255, 0, 0])}, {name: 'b', cells: solid([0, 0, 255])},
                     {name: 'green_with_a_long_name', cells: solid([0, 200, 0])}, {name: 'g', cells: solid([40, 160, 40])}];
      const P = E.palette(items);
      const w = 6, h = 3, px = new Uint8ClampedArray(w * h * 4);
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) px.set(x < 3 ? [255, 0, 0, 255] : [0, 0, 255, 255], (y * w + x) * 4);
      const r = E.solve(E.samples(px, 2, 1), 2, 1, P, 0, false);
      const green = (c, rr) => { const o = new Uint8ClampedArray(c * 3 * rr * 3 * 4); for (let i = 0; i < o.length; i += 4) o.set([0, 200, 0, 255], i); return E.samples(o, c, rr); };
      const exact = E.fit(green, 4, 1, P, 1000, false);
      const tight = E.fit(green, 10, 1, P, 10 * 10 * 5, false);
      const out = {picks: [...r.picks].map(i => P.names[i]), text: E.text(r, P), exact: E.text(exact, P).split('\n')[0],
                   tight: {cols: tight.cols, chars: tight.chars, shorter: tight.shorter, shrunk: tight.shrunk},
                   parse: [E.parse('[":steamhappy:",":a_b:"]'), E.parse('x ːfooːːbarː :baz: :baz:')]};
      console.log(JSON.stringify(out));
    """)
    assert data["picks"] == ["r", "b"]
    assert data["text"] == "ːrːːbː"
    # Plenty of room: the exact colour wins even with a long name.
    assert data["exact"] == "ːgreen_with_a_long_nameː" * 4
    # Tight budget: shorter names are preferred and the result never passes the budget.
    assert data["tight"]["chars"] <= 500 and data["tight"]["shorter"]
    assert data["parse"] == [["steamhappy", "a_b"], ["foo", "bar", "baz"]]
