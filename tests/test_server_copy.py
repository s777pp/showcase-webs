"""Page text in the page language already in the server HTML (smweb/server_copy.py, 2026-10-09)."""
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb import server_copy
from smweb.routers import pages

SAMPLE = """<html><head><title>Process</title></head><body>
<h1 data-i="x">Process</h1><p class="a" title="Process">  Process  </p>
<script>var t = "Process";</script><code>Process</code><span data-no-translate>Process <b>Process</b></span>
<svg><text>Process</text></svg><img alt="Process"><br/>Fish &amp; Chips<p>Unknown</p></body></html>"""


def test_only_text_between_tags_changes(monkeypatch):
    monkeypatch.setattr(server_copy, "_map", lambda language: {"/": {"Process": "Обработка", "Fish & Chips": "Рыба <и> чипсы"}})
    out = server_copy.translate(SAMPLE, "ru", "/")
    assert '<h1 data-i="x">Обработка</h1>' in out
    assert '<p class="a" title="Process">  Обработка  </p>' in out          # spacing kept, attribute untouched
    assert 'var t = "Process";' in out and "<code>Process</code>" in out
    assert "<span data-no-translate>Process <b>Process</b></span>" in out
    assert "<svg><text>Process</text></svg>" in out and 'alt="Process"' in out
    assert "<title>Process</title>" in out and "Рыба &lt;и&gt; чипсы" in out and "<p>Unknown</p>" in out
    assert re.findall(r"<[^>]+>", out) == re.findall(r"<[^>]+>", SAMPLE)    # markup is identical
    assert server_copy.translate(SAMPLE, "en", "/") == SAMPLE
    monkeypatch.setenv("SERVER_COPY", "0")
    assert server_copy.translate(SAMPLE, "ru", "/") == SAMPLE


def test_maps_exist_for_every_language_and_page():
    for language in ("ru", "uk", "de", "tr", "fr", "es", "pt"):
        table = server_copy._map(language)
        assert len(table.get("/", {})) > 100 and len(table.get("/app", {})) > 150, language
    assert server_copy._map("ru")["/"]["Revitalized"] == "Без рутины"


def test_pages_are_served_in_the_page_language():
    app = FastAPI()
    app.include_router(pages.router)
    client = TestClient(app)
    ru = client.get("/ru/").text
    assert '<span data-i="h1a">Steam-витрины.</span>' in ru
    assert 'data-editor-copy="run">Подготовить витрину</button>' in client.get("/ru/app").text
    assert '<span data-i="h1a">Steam-Vitrinen.</span>' in client.get("/de/").text
    assert '<span data-i="h1a">Steam showcases.</span>' in client.get("/en/").text
