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


def test_landing_has_structured_data_without_a_product_offer(client):
    text = client.get("/ru/").text
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S).group(1)
    graph = json.loads(block)["@graph"]
    app = next(item for item in graph if item["@type"] == "WebApplication")
    # No Offer: Google read the price as a product and asked for reviews / returns / shipping (2026-10-10).
    assert app["inLanguage"] == "ru" and "offers" not in app and app["isAccessibleForFree"] is True
    assert '"Offer"' not in block and '"Product"' not in block
    assert "оформите профиль Steam" in app["description"]


def test_guides_and_privacy_keep_their_titles_and_get_previews(client):
    guide = client.get("/de/guides").text
    title, descriptions, og = _head(guide)
    assert og["og:title"] == title and len(descriptions) == 1 and og["og:locale"] == "de_DE"
    privacy = client.get("/ru/privacy").text
    title, _descriptions, og = _head(privacy)
    assert title.startswith("Политика конфиденциальности") and og["og:title"] == title


def test_author_page_names_the_author(client, monkeypatch):
    import auth_db
    monkeypatch.setattr(auth_db, "get_public_profile", lambda name: {"profile_visibility": "public"})
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


def test_www_host_redirects_permanently_to_the_main_host(monkeypatch):
    from starlette.responses import PlainTextResponse
    from smweb.middleware import WwwRedirectMiddleware
    monkeypatch.setenv("APP_URL", "https://showcasemaker.com")
    inner = FastAPI()
    inner.add_api_route("/{path:path}", lambda path: PlainTextResponse("ok"))
    client = TestClient(WwwRedirectMiddleware(inner))
    response = client.get("https://www.showcasemaker.com/ru/app?x=1", follow_redirects=False)
    assert response.status_code == 301 and response.headers["location"] == "https://showcasemaker.com/ru/app?x=1"
    assert client.get("https://showcasemaker.com/ru/app").text == "ok"
    assert client.get("https://ru.showcasemaker.com/ru/").text == "ok"


def test_plain_http_on_the_main_host_goes_to_https(monkeypatch):
    """Yandex 2026-10-10: http://showcasemaker.com/ served pages. Cloudflare's Cf-Visitor tells the visitor's scheme."""
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    from fastapi.testclient import TestClient
    from smweb.middleware import WwwRedirectMiddleware
    monkeypatch.setenv("APP_URL", "https://showcasemaker.com")
    inner = FastAPI()
    inner.add_api_route("/{path:path}", lambda path: PlainTextResponse("ok"))
    client = TestClient(WwwRedirectMiddleware(inner))
    plain = client.get("http://showcasemaker.com/ru/?a=1", headers={"cf-visitor": '{"scheme":"http"}'}, follow_redirects=False)
    assert plain.status_code == 301 and plain.headers["location"] == "https://showcasemaker.com/ru/?a=1"
    secure = client.get("http://showcasemaker.com/ru/", headers={"cf-visitor": '{"scheme":"https"}'})
    assert secure.text == "ok"                     # nginx -> app is plain http, the visitor's scheme decides
    assert client.get("http://showcasemaker.com/ru/").text == "ok"          # no Cloudflare header: left alone
    mirror = client.get("http://ru.showcasemaker.com/ru/", headers={"cf-visitor": '{"scheme":"http"}'})
    assert mirror.text == "ok"
    monkeypatch.setenv("APP_URL", "http://127.0.0.1:8091")
    local = TestClient(WwwRedirectMiddleware(inner))
    assert local.get("http://127.0.0.1/ru/", headers={"cf-visitor": '{"scheme":"http"}'}).text == "ok"


def test_head_works_for_pages_robots_and_sitemap():
    """Crawlers check with HEAD; FastAPI GET routes used to answer 405 (Yandex: "no Sitemap used")."""
    from fastapi.responses import PlainTextResponse
    from smweb.middleware import HeadAsGetMiddleware
    app = FastAPI()
    app.include_router(pages.router)
    app.add_api_route("/api/thing", lambda: PlainTextResponse("x"))
    client = TestClient(HeadAsGetMiddleware(app))
    for path in ("/ru/", "/robots.txt", "/sitemap.xml"):
        get = client.get(path)
        head = client.head(path)
        assert head.status_code == get.status_code == 200, path
        assert head.content == b"" and head.headers.get("content-type") == get.headers.get("content-type")
    assert client.head("/api/thing").status_code == 405        # /api/ keeps its own HEAD rules
    assert client.get("/api/thing").text == "x"


def test_favicon_and_icon_links(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200 and response.headers["content-type"] == "image/x-icon"
    for name in ("index.html", "app.html", "privacy-ru.html", "guide.html"):
        source = (STATIC / name).read_text(encoding="utf-8")
        assert '<link rel="icon" href="/favicon.ico" sizes="48x48">' in source and "icon-256.png\"/>" not in source
    assert (STATIC / "img" / "favicon" / "favicon-192.png").is_file()


def test_unknown_public_profile_is_a_404(client, monkeypatch):
    import auth_db
    monkeypatch.setattr(auth_db, "get_public_profile", lambda name: None if name == "profile" else
                        {"profile_visibility": "private" if name == "hidden" else "public"})
    assert client.get("/ru/profile/profile").status_code == 404
    assert client.get("/ru/profile/saba").status_code == 200
    hidden = client.get("/ru/profile/hidden")
    assert hidden.status_code == 200 and hidden.headers["x-robots-tag"] == "noindex, follow"


def test_tabs_get_the_bare_mark_by_theme_while_html_keeps_the_tile():
    script = (STATIC / "js" / "favicon-theme.js").read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in script and "/static/img/favicon/tab-' + (dark ? 'dark' : 'light') + '.png" in script
    for name in ("tab-dark.png", "tab-light.png"):
        assert (STATIC / "img" / "favicon" / name).is_file()
    for page in STATIC.glob("*.html"):
        source = page.read_text(encoding="utf-8")
        if page.name.startswith("privacy-"):
            assert "<script" not in source              # privacy pages stay script-free (navy tile in the tab)
            continue
        assert "favicon-theme.js" in source and '<link rel="icon" href="/favicon.ico" sizes="48x48">' in source, page.name
