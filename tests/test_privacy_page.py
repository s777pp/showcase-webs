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

    def test_public_multilingual_policy_without_scripts_or_cookie(self):
        for lang, title in [('en', 'Privacy policy'), ('ru', 'Политика конфиденциальности'),
                            ('de', 'Datenschutz'), ('tr', 'Gizlilik'), ('fr', 'confidentialité'), ('uk', 'конфіденційності'),
                            ('es', 'privacidad'), ('pt', 'privacidade')]:
            response = self.client.get(f'/{lang}/privacy')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['content-language'], lang)
            self.assertEqual(response.headers['cache-control'], 'no-cache')
            self.assertNotIn('set-cookie', response.headers)
            self.assertIn(title, response.text)
            self.assertIn('SteamShowcase Helper', response.text)
            self.assertIn('90', response.text)
            if lang == 'en':
                self.assertIn('Limited Use', response.text)
                self.assertIn('loyalty Web API token', response.text)
            markup = PolicyMarkup()
            markup.feed(response.text)
            self.assertFalse(markup.scripts)
            self.assertEqual(len(markup.ids), len(set(markup.ids)))
            self.assertTrue(set(markup.anchors).issubset(markup.ids))

    def test_default_alias_and_untrusted_language(self):
        for url in ['/privacy', '/privacy/', '/privacy?lang=../../.env', '/privacy?lang=<script>']:
            response = self.client.get(url, follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertEqual(response.headers['location'], '/en/privacy' + (response.headers['location'].split('/en/privacy', 1)[1] if response.headers['location'].startswith('/en/privacy?') else ''))

    def test_browser_language_redirects_and_localized_pages(self):
        cases = [('de-DE,de;q=0.9', '/de/app'), ('tr-TR,tr;q=0.9', '/tr/app'), ('fr-FR', '/fr/app'), ('uk-UA', '/uk/app'),
                 ('es-ES', '/es/app'), ('pt-BR', '/pt/app'), ('ja-JP', '/en/app')]
        for header, expected in cases:
            response = self.client.get('/app', headers={'Accept-Language': header}, follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertEqual(response.headers['location'], expected)
        for lang in ('en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'):
            for path in ('', '/app', '/gallery', '/profile'):
                response = self.client.get(f'/{lang}{path}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['content-language'], lang)

    def test_footer_links_and_cache_keys(self):
        static = Path(__file__).resolve().parents[1] / 'static'
        for page in ['index.html', 'app.html']:
            self.assertIn('data-privacy-link', (static / page).read_text(encoding='utf-8'))
        for page in ['index.html', 'app.html', 'gallery.html', 'profile.html', 'profile-view.html']:
            source = (static / page).read_text(encoding='utf-8')
            self.assertIn('ss-shell.js?v=20260910-analytics1', source)
            self.assertIn('analytics.js?v=20260910a', source)
            self.assertIn('locales-extra.js?v=20260909-languages8', source)
            self.assertIn('i18n.js?v=20260909-languages4', source)
        for page in ['profile.html', 'profile-view.html']:
            self.assertIn('id="ssFootHost"', (static / page).read_text(encoding='utf-8'))

    def test_analytics_dashboard_is_not_cached_or_indexed(self):
        response = self.client.get('/admin/analytics')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'private, no-store')
        self.assertIn('noindex,nofollow', response.text)


if __name__ == '__main__':
    unittest.main()
