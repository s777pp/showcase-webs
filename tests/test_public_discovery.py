from xml.etree import ElementTree

from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb.routers.pages import router
from smweb.locales import SUPPORTED_LANGUAGES


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_sitemap_only_contains_public_pages_that_exist():
    response = client.get('/sitemap.xml')
    assert response.status_code == 200
    root = ElementTree.fromstring(response.content)
    urls = [n.text for n in root.findall('{*}url/{*}loc')]
    assert len(urls) == len(SUPPORTED_LANGUAGES) * 4
    assert len(urls) == len(set(urls))
    for url in urls:
        assert '/profile' not in url and '/api/' not in url
        assert client.get(url.removeprefix('https://showcasemaker.com')).status_code == 200


def test_robots_and_private_editor_indexing():
    assert 'Sitemap: https://showcasemaker.com/sitemap.xml' in client.get('/robots.txt').text
    assert client.get('/admin/analytics').headers['x-robots-tag'] == 'noindex, nofollow'
    assert client.get('/ru/profile').headers['x-robots-tag'] == 'noindex, nofollow'
