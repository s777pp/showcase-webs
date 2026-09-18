import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HomeLoaderTests(unittest.TestCase):
    def test_loader_is_mounted_before_home_content(self):
        html = (ROOT / 'static' / 'index.html').read_text(encoding='utf-8')
        self.assertIn("classList.add('home-is-loading')", html)
        self.assertLess(html.index('id="homeLoader"'), html.index('<div class="shell">'))
        self.assertIn('/static/css/home-loader.css?v=20260918a', html)
        self.assertIn('/static/js/home-loader.js?v=20260918a', html)

    def test_loader_waits_for_page_fonts_and_hero(self):
        source = (ROOT / 'static' / 'js' / 'home-loader.js').read_text(encoding='utf-8')
        self.assertIn("window.addEventListener('load', markPageReady", source)
        self.assertIn('document.fonts.ready', source)
        self.assertIn("document.addEventListener('showcasemaker:hero-ready'", source)
        self.assertIn('window.setTimeout(finish, 45000)', source)

    def test_vrm_settles_success_and_fallback(self):
        source = (ROOT / 'static' / 'js' / 'hero-vrm.js').read_text(encoding='utf-8')
        self.assertIn("settleHeroLoad('ready')", source)
        self.assertIn("settleHeroLoad('fallback')", source)
        self.assertIn("new CustomEvent('showcasemaker:hero-ready'", source)


if __name__ == '__main__':
    unittest.main()
