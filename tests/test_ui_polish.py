"""Front-end pass of 2026-10-07: 404 page, shared polish stylesheet, small contracts."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
SHELL_PAGES = ["index", "app", "gallery", "profile", "profile-view", "account", "news", "support", "extension",
               "guide", "billing-claim", "404"]


def test_polish_stylesheet_is_last_on_every_shell_page():
    keys = set()
    for name in SHELL_PAGES:
        html = (STATIC / f"{name}.html").read_text(encoding="utf-8")
        head = html.split("</head>", 1)[0]
        links = re.findall(r'href="/static/css/([^"?]+)\?v=([^"]+)"', head)
        assert links and links[-1][0] == "ui-polish.css", f"{name}: ui-polish.css must be the last stylesheet"
        keys.add(links[-1][1])
    assert len(keys) == 1, "one cache key for ui-polish.css on every page"


def test_unknown_addresses_get_the_site_404_page():
    import main
    client = TestClient(main.app)
    page = client.get("/ru/kakaya-to-staraya-ssylka", headers={"Accept": "text/html"})
    assert page.status_code == 404 and page.headers["content-type"].startswith("text/html")
    assert '<html lang="ru"' in page.text and 'name="robots" content="noindex"' in page.text
    assert 'rel="canonical"' not in page.text
    german = client.get("/de/nichts", headers={"Accept": "text/html"})
    assert '<html lang="de"' in german.text
    guide = client.get("/ru/guides/no-such-guide", headers={"Accept": "text/html"})
    assert guide.status_code == 404 and "nf__card" in guide.text
    # API clients and assets keep JSON.
    assert client.get("/api/definitely-missing", headers={"Accept": "text/html"}).headers["content-type"].startswith("application/json")
    assert client.get("/ru/kakaya-to-staraya-ssylka").headers["content-type"].startswith("application/json")
    assert client.get("/static/definitely-missing.css", headers={"Accept": "text/html"}).status_code == 404


def test_disabled_buttons_and_embedded_editor_rules_exist():
    css = (STATIC / "css/ui-polish.css").read_text(encoding="utf-8")
    assert ":disabled{" in css and "opacity:1!important" in css
    assert "html.profile-embedded" in css and ".sm-consent" in css
    analytics = (STATIC / "js/analytics.js").read_text(encoding="utf-8")
    assert "window.self !== window.top" in analytics, "no second consent banner inside the embedded profile editor"


def test_builder_consolas_uses_the_system_font_first():
    css = (STATIC / "css/showcase-builder.css").read_text(encoding="utf-8")
    assert "src:local('Consolas'),url('/static/steam-mockup/fonts/consolas.ttf')" in css
