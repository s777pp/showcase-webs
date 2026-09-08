import unittest
from html.parser import HTMLParser
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb.routers.pages import router


class PolicyMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.anchors = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'a' and attrs.get('href', '').startswith('#'):
            self.anchors.append(attrs['href'][1:])
        if tag == 'script':
            self.scripts.append(attrs)


class PrivacyPageTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_public_bilingual_policy_without_scripts_or_cookie(self):
        for lang, title in [('en', 'Privacy policy'), ('ru', 'Политика конфиденциальности')]:
            response = self.client.get('/privacy', params={'lang': lang})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['content-language'], lang)
            self.assertEqual(response.headers['cache-control'], 'no-cache')
            self.assertNotIn('set-cookie', response.headers)
            self.assertIn(title, response.text)
            self.assertIn('SteamShowcase Helper', response.text)
            self.assertIn('Limited Use', response.text)
            self.assertIn('loyalty Web API token', response.text)
            markup = PolicyMarkup()
            markup.feed(response.text)
            self.assertFalse(markup.scripts)
            self.assertEqual(len(markup.ids), len(set(markup.ids)))
            self.assertTrue(set(markup.anchors).issubset(markup.ids))

    def test_default_alias_and_untrusted_language(self):
        for url in ['/privacy', '/privacy/', '/privacy?lang=../../.env', '/privacy?lang=<script>']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn('<html lang="en">', response.text)
            self.assertNotIn('<script>', response.text)

    def test_footer_links_and_cache_keys(self):
        static = Path(__file__).resolve().parents[1] / 'static'
        for page in ['index.html', 'app.html']:
            self.assertIn('data-privacy-link', (static / page).read_text(encoding='utf-8'))
        for page in ['index.html', 'app.html', 'gallery.html', 'profile.html', 'profile-view.html']:
            self.assertIn('ss-shell.js?v=20260908-auth-code', (static / page).read_text(encoding='utf-8'))
        for page in ['profile.html', 'profile-view.html']:
            self.assertIn('id="ssFootHost"', (static / page).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
