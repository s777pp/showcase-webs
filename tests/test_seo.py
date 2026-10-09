"""Search snippets and link previews in the page language (smweb/seo.py, 2026-10-09)."""
import html
import json
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb import seo
from smweb.core import STATIC
from smweb.locales import SUPPORTED_LANGUAGES
from smweb.routers import pages


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(pages.router)
    return TestClient(app)


def _head(text):
    title = html.unescape(re.search(r"<title>([^<]*)</title>", text).group(1))
    descriptions = re.findall(r'<meta name="description" content="([^"]*)"', text)
    og = dict((key, html.unescape(value)) for key, value in re.findall(r'<meta property="(og:[a-z:_]+)" content="([^"]*)"', text))
    return title, [html.unescape(d) for d in descriptions], og


def test_every_page_has_copy_in_every_language_within_snippet_length():
    for page, versions in seo.PAGES.items():
        assert set(versions) == set(SUPPORTED_LANGUAGES), page
        for language, (title, description) in versions.items():
            assert len(title) <= 70, (page, language, title)
            assert 40 <= len(description) <= 170 or page in ("support", "account", "profile"), (page, language)
            assert "Showcase Maker" in title


@pytest.mark.parametrize("path,page", [("/", "home"), ("/app", "app"), ("/gallery", "gallery"), ("/extension", "extension")])
def test_pages_serve_their_own_language(client, path, page):
    for language in SUPPORTED_LANGUAGES:
        response = client.get(f"/{language}{path}" if path != "/" else f"/{language}/")
        assert response.status_code == 200
        title, descriptions, og = _head(response.text)
        expected_title, expected_description = seo.PAGES[page][language]
        assert title == expected_title
        assert descriptions == [expected_description]          # exactly one description
        assert og["og:title"] == expected_title and og["og:description"] == expected_description
        assert og["og:locale"] == seo.OG_LOCALE[language]
        assert og["og:image"].endswith(f"/static/img/og/og-{language}.jpg")
        assert og["og:url"].startswith(f"https://showcasemaker.com/{language}")
        assert '<meta name="sm-seo" content="1">' in response.text
        assert response.text.count("<title>") == 1


def test_landing_has_structured_data_with_the_free_offer(client):
    text = client.get("/ru/").text
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S).group(1)
    graph = json.loads(block)["@graph"]
    app = next(item for item in graph if item["@type"] == "WebApplication")
    assert app["inLanguage"] == "ru" and app["offers"]["price"] == "0"
    assert "оформите профиль Steam" in app["description"]


def test_guides_and_privacy_keep_their_titles_and_get_previews(client):
    guide = client.get("/de/guides").text
    title, descriptions, og = _head(guide)
    assert og["og:title"] == title and len(descriptions) == 1 and og["og:locale"] == "de_DE"
    privacy = client.get("/ru/privacy").text
    title, _descriptions, og = _head(privacy)
    assert title.startswith("Политика конфиденциальности") and og["og:title"] == title


def test_author_page_names_the_author(client):
    text = client.get("/ru/profile/saba%20chan").text
    title, _d, og = _head(text)
    assert title.startswith("saba chan — Витрины Steam автора")


def test_preview_pictures_exist_for_every_language():
    for language in SUPPORTED_LANGUAGES:
        path = STATIC / "img" / "og" / f"og-{language}.jpg"
        assert path.is_file() and path.stat().st_size < 300_000


def test_page_scripts_do_not_overwrite_the_server_title():
    for name in ("home.js", "community-gallery.js", "extension-guide.js", "app.js", "profile.js"):
        source = (STATIC / "js" / name).read_text(encoding="utf-8")
        assert 'meta[name="sm-seo"]' in source, name
