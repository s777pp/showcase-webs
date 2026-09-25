"""Landing hero: licensed VRM, sitting pose, gaze, click reaction and assets."""
import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "static" / "index.html"
MODULE = ROOT / "static" / "js" / "home-vrm.js"
CSS = ROOT / "static" / "css" / "home.css"
MODEL = ROOT / "static" / "models" / "saba-0.1.vrm"
AUDIO = ROOT / "static" / "audio" / "hero-cute-reaction.mp3"


class HeroVrmTests(unittest.TestCase):
    def test_model_file_matches_the_licensed_source_asset(self):
        self.assertTrue(MODEL.is_file())
        self.assertEqual(MODEL.stat().st_size, 21_101_700)
        self.assertEqual(
            hashlib.sha256(MODEL.read_bytes()).hexdigest().upper(),
            "E130883AD1C3A24382EC750F8934EA4859101F4EB1B225869B1A900AB53C0E07",
        )

    def test_landing_loads_runtime_model_and_attribution(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn('data-model="https://media.showcasemaker.com/site-assets/models/saba-0.1.vrm?v=20260918-r2-1"', html)
        self.assertIn('data-model-fallback="/static/models/saba-0.1.vrm?v=20260915-saba1"', html)
        self.assertIn('<script type="module" src="/static/js/home-vrm.js?v=', html)
        self.assertIn('rel="modulepreload" href="/static/vendor/vrm-runtime.module.js?v=20260915-saba2"', html)
        self.assertIn('3D model:</span> SABA_0.1', html)
        self.assertIn("https://hub.vroid.com/en/characters/8524332363497057331/models/524490645277532236", html)
        # The old standing-hero stack must not come back by accident.
        for removed in ("hero-vrm.js", "index.js", "index.css", "creator-os.css"):
            self.assertNotIn(removed, html)

    def test_runtime_is_self_hosted(self):
        bundle = ROOT / "static" / "vendor" / "vrm-runtime.module.js"
        self.assertTrue(bundle.is_file())
        source = MODULE.read_text(encoding="utf-8")
        self.assertIn("/static/vendor/vrm-runtime.module.js", source)
        self.assertNotIn("cdn.", source)

    def test_sitting_pose_gaze_and_gentle_reaction(self):
        source = MODULE.read_text(encoding="utf-8")
        for bone in ("hips", "rightUpperLeg", "rightLowerLeg", "leftUpperLeg", "leftLowerLeg",
                     "rightUpperArm", "leftUpperArm", "head"):
            self.assertIn(f"  {bone}: [", source)
        self.assertIn("window.addEventListener('pointermove', setPointer", source)
        self.assertIn("hitZone.addEventListener('pointerdown', react", source)
        self.assertNotIn("Raycaster", source)  # per-move 3D hit tests caused stutter
        self.assertIn("hitZone.addEventListener('click', playReactionAudio)", source)
        self.assertIn("const REACTION_SOUND_VOLUME = 0.05;", source)
        self.assertIn("const REACTION_FACE = { happy: 0.38", source)
        self.assertIn("burstReactionHearts(event)", source)
        self.assertTrue(AUDIO.is_file() and AUDIO.stat().st_size > 10_000)
        self.assertIn(".home-reaction i", CSS.read_text(encoding="utf-8"))

    def test_safe_fallbacks_and_local_only_tuning(self):
        source = MODULE.read_text(encoding="utf-8")
        self.assertIn("return loader.loadAsync(fallbackUrl)", source)
        self.assertIn("if (saveData || !hasWebGL())", source)
        self.assertIn("prefers-reduced-motion: reduce", source)
        self.assertIn("if (isLocalPreview())", source)
        self.assertIn("window.location.hostname === '127.0.0.1'", source)

    def test_hero_assets_are_optimized_and_present(self):
        html = INDEX.read_text(encoding="utf-8")
        folder = ROOT / "static" / "img" / "home"
        # Responsive background: every width in AVIF and WebP, the browser picks one.
        for width in (1000, 1280, 1920, 2560, 3840):
            for ext, limit in (("avif", 900_000), ("webp", 1_300_000)):
                name = f"fon-{width}.{ext}"
                self.assertTrue((folder / name).is_file(), name)
                self.assertLess((folder / name).stat().st_size, limit, name)
                self.assertIn(f"/static/img/home/{name}", html)
        for name in ("card-cuts.webp", "card-upscale.webp", "card-anim.webp"):
            self.assertTrue((folder / name).is_file(), name)
            self.assertLess((folder / name).stat().st_size, 60_000, name)
            self.assertIn(f"/static/img/home/{name}", html)
        self.assertIn('id="heroVrmHit"', html)


class LandingBlocksTests(unittest.TestCase):
    def test_restored_blocks_are_present_and_isolated(self):
        html = INDEX.read_text(encoding="utf-8")
        for anchor in ('id="features"', 'id="pricing"', 'id="formatsTrack"', 'id="ctaReg"', 'data-buy-key="1"'):
            self.assertIn(anchor, html)
        blocks = html[html.index('<div class="home-blocks">'):html.index('</main>')]
        # Classes are prefixed so legacy redesign.css rules (.section, .mock-frame, ...) cannot restyle them.
        for legacy in ('class="section', 'class="mock-frame', 'class="c3-card', 'class="q-card'):
            self.assertNotIn(legacy, blocks)
        css = (ROOT / "static" / "css" / "home-blocks.css").read_text(encoding="utf-8")
        self.assertIn(".home-blocks .hb-c3-card", css)
        self.assertIn("/static/css/home-blocks.css?v=", html)
        for icon in ("chrome.svg", "edge.svg"):
            self.assertTrue((ROOT / "static" / "img" / "browser-icons" / icon).is_file())


class LandingPolishTests(unittest.TestCase):
    def test_reveal_background_and_assistant_lift(self):
        js = (ROOT / "static" / "js" / "home.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "home-blocks.css").read_text(encoding="utf-8")
        chat = (ROOT / "static" / "js" / "support-chat.js").read_text(encoding="utf-8")
        chat_css = (ROOT / "static" / "css" / "support-chat.css").read_text(encoding="utf-8")
        self.assertIn("function initReveal()", js)
        self.assertIn("IntersectionObserver", js)
        self.assertIn('[data-hb-reveal].is-in', css)
        self.assertIn("@keyframes hb-drift-a", css)
        self.assertIn('class="hb-aurora"', INDEX.read_text(encoding="utf-8"))
        self.assertIn("--support-lift", chat)
        self.assertIn("var(--support-lift,0px)", chat_css)

    def test_extension_nav_and_telegram_brand_mark(self):
        shell = (ROOT / "static" / "ss-shell.js").read_text(encoding="utf-8")
        self.assertIn("href: '/extension'", shell)
        self.assertNotIn('ss-shop__icon--telegram">➤', shell)
        self.assertIn('fill="#229ED9"', shell)
        self.assertIn('fill="#229ED9"', (ROOT / "static" / "app.html").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "static" / "extension.html").is_file())


class LandingOverlayTests(unittest.TestCase):
    def test_popups_are_restyled_only_on_the_landing(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn("/static/css/home-overlays.css?v=", html)
        css = (ROOT / "static" / "css" / "home-overlays.css").read_text(encoding="utf-8")
        for selector in (".ss-auth__card", ".ss-activation__card", ".ss-lang__menu", ".sm-consent",
                         ".studio-chat-panel", ".studio-support-choice__card", ".ss-drawer", ".studio-ticket-form"):
            self.assertIn("html body.page-home " + selector, css)
        # Every rule stays scoped to the landing page.
        import re
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        for block in re.findall(r"([^{}]+)\{", css):
            for selector in block.split(","):
                selector = selector.strip()
                if selector and not selector.startswith(("@", "from", "to")):
                    self.assertTrue(selector.startswith("html body.page-home"), selector)


if __name__ == "__main__":
    unittest.main()
