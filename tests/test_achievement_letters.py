"""Achievement letters tab (#tab-letters): catalogue builder rules and the page wiring (2026-10-09)."""
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_achievement_letters as builder  # noqa: E402


def test_letter_names_are_recognised():
    assert builder.letter_of("A") == ("letter", "A")
    assert builder.letter_of("a!") == ("letter", "A")
    assert builder.letter_of("Letter Q") == ("letter", "Q")
    assert builder.letter_of("[z]") == ("letter", "Z")
    assert builder.letter_of("7") == ("digit", "7")
    assert builder.letter_of("Number 3") == ("digit", "3")
    assert builder.letter_of("П") == ("letter", "П")
    assert builder.letter_of("Буква Ж") == ("letter", "Ж")
    assert builder.letter_of("[ё]") == ("letter", "Ё")
    assert builder.letter_of("!") == ("symbol", "!")
    assert builder.letter_of("Space") == ("symbol", " ")
    for name in ("AB", "Ace", "Level 1 complete", "Spacebar", "", None):
        assert builder.letter_of(name) is None


def _icon(background, letter=(255, 255, 255)):
    image = Image.new("RGB", (64, 64), background)
    ImageDraw.Draw(image).rectangle((22, 10, 42, 54), fill=letter)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=95)
    return out.getvalue()


def test_icon_colours(monkeypatch):
    class Answer:
        def __init__(self, data): self.data = data
        def read(self): return self.data
        def __enter__(self): return self
        def __exit__(self, *a): return False

    samples = {"red": (220, 30, 40), "green": (30, 190, 70), "blue": (30, 80, 230), "pink": (230, 40, 160),
               "yellow": (235, 210, 30), "purple": (140, 50, 220)}
    for expected, rgb in samples.items():
        monkeypatch.setattr(builder.urllib.request, "urlopen", lambda req, timeout, d=_icon(rgb): Answer(d))
        assert builder.icon_color(1, "x") == expected, expected
    monkeypatch.setattr(builder.urllib.request, "urlopen", lambda req, timeout: Answer(_icon((12, 12, 16))))
    assert builder.icon_color(1, "x") == "white"          # white letter on a dark tile
    monkeypatch.setattr(builder.urllib.request, "urlopen", lambda req, timeout: Answer(_icon((10, 10, 12), (40, 40, 44))))
    assert builder.icon_color(1, "x") == "black"


def test_catalogue_shape_when_built():
    path = ROOT / "static" / "assets" / "achievements" / "letters.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["cdn"].startswith("https://") and data["sets"]
    for item in data["sets"][:20]:
        assert len(item["letters"]) >= builder.MIN_LETTERS
        for variants in item["letters"].values():
            assert 1 <= len(variants) <= builder.MAX_VARIANTS
            icon, percent, title, color = variants[0]
            assert len(icon) == 40 and (percent is None or 0 <= percent <= 100) and color in builder.COLORS + ("",)


def test_tab_is_wired():
    app = (ROOT / "static" / "app.html").read_text(encoding="utf-8")
    assert 'data-tab="letters" data-i="nav_letters"' in app and '<section class="tab" id="tab-letters">' in app
    assert "achievement-letters.js?v=" in app and "achievement-letters.css?v=" in app
    js = (ROOT / "static" / "js" / "achievement-letters.js").read_text(encoding="utf-8")
    for needle in ("colorOk", "paintGallery", "paintEditor", "setColor", "letters.json", "APPLY_ACHIEVEMENT_LETTERS"):
        assert needle in js
    assert "var SLOTS = 7;" in js and "input.maxLength = SLOTS" in js   # Steam's Achievement Showcase holds 7 icons
    assert (ROOT / "static" / "img" / "tool-icons" / "letters.svg").is_file()
