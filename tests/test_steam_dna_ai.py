import json
import unittest
from unittest.mock import Mock, patch

from smweb import steam_dna_ai as ai
from smweb.steam_dna import build_profile_dna


class SteamDnaAiTests(unittest.TestCase):
    def snapshot(self):
        return {
            "steamid": "76561198000000000",
            "profileurl": "https://steamcommunity.com/id/private-input",
            "name": "Signal User",
            "games": [
                {"name": "First Game", "playtime_forever": 6000},
                {"name": "Second Game", "playtime_forever": 1200},
            ],
            "recent_games": [{"name": "First Game"}],
            "showcase_instances": [{"type": "artwork", "title": "My art", "images": ["https://steamuserimages.example/a.jpg"]}],
            "stats_map": {"artwork": 14, "screenshots": 80},
            "level": 20,
        }

    def interpretation(self):
        return {
            "title": "Neon Pathfinder",
            "summary": "A focused library with a clear center of gravity.",
            "play_style": "Long sessions cluster around a small core.",
            "collector_style": "The library is selective rather than broad.",
            "visual_direction": "Use cyan rings, a dark field and slow orbital motion.",
            "motto": "FOLLOW THE BRIGHTEST SIGNAL",
            "signal_notes": {key: "Explanation based on the visible profile data." for key in ai._SIGNALS},
        }

    def test_payload_is_strict_localized_and_excludes_identifiers(self):
        dna = build_profile_dna(self.snapshot(), user_id=5)
        with patch.dict("os.environ", {"GROQ_API_KEY": "test", "GROQ_DNA_MODEL": "openai/gpt-oss-20b"}):
            payload = ai.build_payload(dna, self.snapshot(), "ru")
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertFalse(payload["store"])
        self.assertIn("Russian", payload["instructions"])
        self.assertNotIn("76561198000000000", payload["input"])
        self.assertNotIn("steamcommunity.com", payload["input"])
        self.assertNotIn("Signal User", payload["input"])
        self.assertIn('"type": "artwork"', payload["input"])
        self.assertIn('"artwork": 14', payload["input"])
        self.assertNotIn("steamuserimages.example", payload["input"])

    def test_success_returns_copy_and_updates_builder_text(self):
        snapshot = self.snapshot()
        dna = build_profile_dna(snapshot, user_id=5)
        data = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(self.interpretation())}]}]}
        response = Mock(status_code=200)
        response.iter_content.return_value = [json.dumps(data).encode()]
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}), patch.object(ai.requests, "post", return_value=context) as post:
            result = ai.enrich_profile_dna(dna, snapshot, "en")
        self.assertEqual(result["title"], "Neon Pathfinder")
        self.assertEqual(post.call_args.args[0], "https://api.groq.com/openai/v1/responses")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])
        for variant in dna["projects"]:
            layers = variant["project"]["layers"]
            self.assertTrue(any(item.get("text") == "NEON PATHFINDER" for item in layers))
            self.assertTrue(any(item.get("text") == "FOLLOW THE BRIGHTEST SIGNAL" for item in layers))

    def test_provider_failure_has_safe_exception(self):
        snapshot = self.snapshot()
        dna = build_profile_dna(snapshot, user_id=5)
        response = Mock(status_code=500)
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}), patch.object(ai.requests, "post", return_value=context):
            with self.assertRaises(ai.SteamDnaAiUnavailable):
                ai.enrich_profile_dna(dna, snapshot, "en")


if __name__ == "__main__":
    unittest.main()
