import json
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb import guides
from smweb.routers import pages


def _client():
    app = FastAPI()
    app.include_router(pages.router)
    return TestClient(app)


def test_guides_render_in_every_language_with_howto_markup_and_links():
    client = _client()
    for language in guides.GUIDE_LANGUAGES:
        hub = client.get(f"/{language}/guides")
        assert hub.status_code == 200 and "X-Robots-Tag" not in hub.headers
        for slug, versions in guides.GUIDES.items():
            assert f"/{language}/guides/{slug}" in hub.text
            page = client.get(f"/{language}/guides/{slug}")
            assert page.status_code == 200
            assert f'<html lang="{language}"' in page.text
            assert versions[language]["title"].replace('"', "&quot;").split("(")[0].strip()[:30] in page.text
            data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page.text).group(1))
            assert data["@type"] == "HowTo" and len(data["step"]) == len(versions[language]["steps"])
            assert f'hreflang="ru" href="https://showcasemaker.com/ru/guides/{slug}"' in page.text
            assert f'hreflang="de" href="https://showcasemaker.com/de/guides/{slug}"' in page.text
            # The extension is offered once, after the manual steps, linking to its page in the same language.
            assert page.text.count('class="guide__ext"') == 1
            assert f'href="/{language}/extension"' in page.text or 'href="/extension"' in page.text


def test_every_language_has_its_own_text_and_is_indexed():
    for language in ("de", "tr", "fr", "uk", "es", "pt"):
        page = _client().get(f"/{language}/guides/steam-workshop-showcase")
        assert page.status_code == 200 and "X-Robots-Tag" not in page.headers
        own = guides.GUIDES["steam-workshop-showcase"][language]["steps"][0][0]
        assert own != guides.GUIDES["steam-workshop-showcase"]["en"]["steps"][0][0]
        assert own.replace("’", "&#x27;")[:12] in page.text or own[:12] in page.text
    assert _client().get("/en/guides/unknown").status_code == 404


def test_sitemap_lists_guides():
    body = _client().get("/sitemap.xml").text
    assert "https://showcasemaker.com/ru/guides/steam-artwork-showcase-split" in body
    assert "https://showcasemaker.com/pt/guides/steam-workshop-showcase" in body
