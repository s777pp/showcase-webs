"""IndexNow announcements and sitemap <lastmod> (2026-10-09)."""
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_db
from smweb import indexnow
from smweb.routers import pages


@pytest.fixture()
def data(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "DATA", tmp_path)
    monkeypatch.setenv("SECRET_KEY", "indexnow-test-secret-0123456789abcdef")
    monkeypatch.delenv("INDEXNOW_KEY", raising=False)
    return tmp_path


def _client():
    app = FastAPI()
    app.include_router(pages.router)
    return TestClient(app)


def test_key_is_stable_valid_and_served_as_a_file(data):
    key = indexnow.key()
    assert key == indexnow.key() and re.fullmatch(r"[0-9a-f]{32}", key)
    client = _client()
    response = client.get(f"/{key}.txt")
    assert response.status_code == 200 and response.text == key
    assert client.get("/0123456789abcdef.txt").status_code == 404
    assert "Sitemap:" in client.get("/robots.txt").text          # robots.txt is not shadowed


def test_own_key_from_env(data, monkeypatch):
    monkeypatch.setenv("INDEXNOW_KEY", "my-key-1234")
    assert indexnow.key() == "my-key-1234"
    monkeypatch.setenv("INDEXNOW_KEY", "bad key!")
    assert indexnow.key() != "bad key!"


def test_only_production_announces_and_never_under_tests(monkeypatch):
    monkeypatch.delenv("INDEXNOW", raising=False)
    monkeypatch.setenv("APP_URL", "https://showcasemaker.com")
    assert indexnow.enabled() is False                          # pytest guard
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert indexnow.enabled() is True
    monkeypatch.setenv("APP_URL", "http://127.0.0.1:8091")
    assert indexnow.enabled() is False
    monkeypatch.setenv("INDEXNOW", "1")
    assert indexnow.enabled() is True
    monkeypatch.setenv("APP_URL", "https://showcasemaker.com")
    monkeypatch.setenv("INDEXNOW", "0")
    assert indexnow.enabled() is False


def test_first_run_sends_everything_then_only_changes(data, monkeypatch):
    sent = []
    entries = [("https://showcasemaker.com/en/", 100.0), ("https://showcasemaker.com/ru/", 200.0),
               ("https://showcasemaker.com/en/news", None)]
    monkeypatch.setattr(pages, "sitemap_entries", lambda: list(entries))
    monkeypatch.setattr(indexnow, "submit", lambda urls: sent.append(list(urls)) or True)
    assert indexnow.run_once() == 3 and len(sent[0]) == 3
    assert indexnow.run_once() == 0 and len(sent) == 1
    entries[0] = ("https://showcasemaker.com/en/", 300.0)
    assert indexnow.run_once() == 1 and sent[-1] == ["https://showcasemaker.com/en/"]


def test_failed_submit_is_retried_next_time(data, monkeypatch):
    monkeypatch.setattr(pages, "sitemap_entries", lambda: [("https://showcasemaker.com/en/", 100.0)])
    monkeypatch.setattr(indexnow, "submit", lambda urls: False)
    assert indexnow.run_once() == 0
    monkeypatch.setattr(indexnow, "submit", lambda urls: True)
    assert indexnow.run_once() == 1


def test_submit_posts_own_urls_to_both_engines(data, monkeypatch):
    calls = []

    class Answer:
        status = 202
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.data))
        return Answer()

    monkeypatch.setattr(indexnow.urllib.request, "urlopen", fake_urlopen)
    assert indexnow.submit(["https://showcasemaker.com/ru/", "https://evil.example/x", "https://showcasemaker.com/ru/"])
    assert [url for url, _ in calls] == list(indexnow.ENDPOINTS)
    body = calls[0][1].decode()
    assert '"urlList": ["https://showcasemaker.com/ru/"]' in body and indexnow.key() in body


def test_sitemap_has_lastmod_dates():
    body = _client().get("/sitemap.xml").text
    assert re.search(r"<loc>https://showcasemaker.com/ru/guides/steam-showcase-sizes</loc>"
                     r"<lastmod>\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00</lastmod>", body)
    assert body.count("<lastmod>") >= body.count("<url>") - 2       # only an empty news hub may lack a date
