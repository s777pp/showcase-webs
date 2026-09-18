import gzip
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "static" / "index.html"
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

    def test_landing_page_loads_the_runtime_and_shows_attribution(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn(
            'data-model="https://media.showcasemaker.com/site-assets/models/saba-0.1.vrm?v=20260918-r2-1"',
            html,
        )
        self.assertIn('data-model-fallback="/static/models/saba-0.1.vrm?v=20260915-saba1"', html)
        self.assertIn('/static/js/hero-vrm.js?v=20260918-reaction4', html)
        self.assertIn('/static/css/hero-vrm.css?v=20260918-reaction1', html)
        self.assertIn('rel="modulepreload" href="/static/js/hero-vrm.js?v=20260918-reaction4"', html)
        self.assertIn('rel="modulepreload" href="/static/vendor/vrm-runtime.module.js?v=20260915-saba2"', html)
        self.assertIn(
            'rel="preload" href="https://media.showcasemaker.com/site-assets/models/saba-0.1.vrm?v=20260918-r2-1"',
            html,
        )
        self.assertIn('fetchpriority="high"', html)
        self.assertIn('3D model:</span> SABA_0.1', html)
        self.assertIn(
            'https://hub.vroid.com/en/characters/8524332363497057331/models/524490645277532236',
            html,
        )

    def test_click_reaction_bundles_sound_and_brand_hearts(self):
        source = (ROOT / "static" / "js" / "hero-vrm.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "hero-vrm.css").read_text(encoding="utf-8")

        self.assertTrue(AUDIO.is_file())
        self.assertGreater(AUDIO.stat().st_size, 10_000)
        self.assertIn("/static/audio/hero-cute-reaction.mp3?v=20260918-2", source)
        self.assertIn("const REACTION_SOUND_VOLUME = .22;", source)
        self.assertIn("canvas.addEventListener('click', playReactionAudio)", source)
        self.assertIn("burstReactionHearts(event)", source)
        self.assertIn(".creator-scene__reaction-hearts", css)
        self.assertIn("#55d9ff", source)

    def test_runtime_is_self_hosted(self):
        bundle = ROOT / "static" / "vendor" / "vrm-runtime.module.js"
        self.assertTrue(bundle.is_file())
        self.assertGreater(bundle.stat().st_size, 100_000)
        source = (ROOT / "static" / "js" / "hero-vrm.js").read_text(encoding="utf-8")
        self.assertIn("/static/vendor/vrm-runtime.module.js", source)
        self.assertNotIn("cdn.", source)

    def test_humanoid_motion_clips_are_bundled(self):
        source = (ROOT / "static" / "js" / "hero-vrm.js").read_text(encoding="utf-8")
        motion_pack = ROOT / "static" / "animations" / "saba" / "opensourceavatars.motionpack.json.gz"
        reaction_motion = ROOT / "static" / "animations" / "saba" / "Goodbye.vrma"
        self.assertTrue(motion_pack.is_file())
        self.assertGreater(motion_pack.stat().st_size, 100_000)
        self.assertTrue(reaction_motion.is_file())
        self.assertGreater(reaction_motion.stat().st_size, 100_000)
        self.assertIn("opensourceavatars.motionpack.json.gz", source)
        with gzip.open(motion_pack, "rt", encoding="utf-8") as stream:
            packed_keys = {clip["key"] for clip in json.load(stream)["clips"]}
        self.assertEqual(packed_keys, {"bored", "looking"})
        for active_motion in ("bored", "looking"):
            self.assertIn(f"'{active_motion}'", source)
        for removed_motion in ("crossJumps", "offensiveIdle", "textingWhileStanding"):
            self.assertNotIn(f"'{removed_motion}'", source)

    def test_mascot_tracks_the_entire_viewport_and_has_a_safe_fallback(self):
        source = (ROOT / "static" / "js" / "hero-vrm.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "hero-vrm.css").read_text(encoding="utf-8")
        html = INDEX.read_text(encoding="utf-8")

        self.assertIn("window.addEventListener('pointermove', setPointer", source)
        self.assertIn('const fallbackUrl = host.dataset.modelFallback', source)
        self.assertIn('return loader.loadAsync(fallbackUrl)', source)
        self.assertIn("const yaw = smoothPointer.x * .24", source)
        self.assertIn("applyIdlePose(vrm)", source)
        self.assertIn("THREE.LoopRepeat", source)
        self.assertNotIn("/static/animations/saba/Relax.vrma", source)
        self.assertIn("/static/animations/saba/Goodbye.vrma", source)
        self.assertIn("reaction: { happy: .85 }", source)
        self.assertIn("playMotion(action, 'once', 'goodbye'", source)
        self.assertIn("window.requestIdleCallback(warmReaction", source)
        self.assertNotIn("const reactionMotionPromise", source)
        self.assertIn("fetchAmbientMotionPack()", source)
        self.assertIn("createAmbientMotionActions(ambientPack, mixer, vrm, gazeBoneNames)", source)
        self.assertIn("'bored',", source)
        self.assertIn("previousMotion.crossFadeTo(action, blendSeconds, true)", source)
        self.assertIn("bored: { repeats: 6, holdSeconds: 32", source)
        self.assertIn("playMotion(entry.action, 'repeat'", source)
        self.assertIn("selectIntroMotion(ambientMotions, requestedPreview)", source)
        self.assertIn("sessionStorage.getItem('showcaseHeroMotionIndex')", source)
        self.assertIn("sceneRoot.dataset.heroMotion = key", source)
        self.assertIn("if (nextMotionAt && now >= nextMotionAt) playAmbient(now)", source)
        self.assertIn("if (!AMBIENT_MOTION_KEYS.has(sourceClip.key)) return []", source)
        self.assertIn("const targetY = size.y * .687", source)
        self.assertIn("const visibleHeight = size.y * .741", source)
        self.assertNotIn("/static/animations/saba/Thinking.vrma", source)
        self.assertIn(".has-js .creator-scene__character", css)
        self.assertIn(".is-vrm-fallback .creator-scene__character", css)
        self.assertIn("width: 116%", css)
        self.assertIn("overflow: visible !important", css)
        self.assertIn("z-index: 10", css)
        self.assertIn("top: -14%", css)
        self.assertIn("height: 121%", css)
        self.assertIn("clip-path: inset(0 0 6% 0)", css)
        self.assertIn(".page-home .hero-studio::after", css)
        self.assertLess(
            html.index("document.documentElement.classList.add('has-js')"),
            html.index('href="/static/css/hero-vrm.css'),
        )

    def test_large_vrm_assets_are_served_immutable_without_changing_the_model(self):
        nginx = (ROOT / "nginx" / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("location ^~ /static/models/", nginx)
        self.assertIn("location ^~ /static/animations/", nginx)
        self.assertIn('Cache-Control "public, max-age=31536000, immutable"', nginx)
        self.assertIn('CDN-Cache-Control "public, max-age=31536000, immutable"', nginx)


if __name__ == "__main__":
    unittest.main()
