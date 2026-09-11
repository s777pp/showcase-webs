import unittest
from unittest.mock import patch

from smweb import steam_dna_jobs


class SteamDnaJobTests(unittest.TestCase):
    def test_live_job_builds_ai_result_and_caches_it(self):
        profile = {
            "steamid": "76561198000000000", "name": "Live User", "level": 12,
            "games": [{"name": "Game", "playtime_forever": 600}],
            "showcase_instances": [{"type": "artwork"}, {"type": "workshop"}],
        }
        interpretation = {
            "title": "Live Signal", "summary": "Summary", "play_style": "Play",
            "collector_style": "Collection", "visual_direction": "Visual", "motto": "LIVE",
            "signal_notes": {key: "Note" for key in ("focus", "variety", "mastery", "history", "activity", "collector")},
        }
        updates = []
        with (
            patch.object(steam_dna_jobs.steam_catalog, "profile", return_value={"ok": True, "profile": profile, "sync_mode": "browser_api"}),
            patch.object(steam_dna_jobs, "_merge_steam_api", side_effect=lambda value: value),
            patch.object(steam_dna_jobs.steam_dna_ai, "configured", return_value=True),
            patch.object(steam_dna_jobs.steam_dna_ai, "enrich_profile_dna", return_value=interpretation),
            patch.object(steam_dna_jobs.rs, "job_update", side_effect=lambda jid, **kw: updates.append(kw)),
            patch.object(steam_dna_jobs.rs, "steam_dna_cache_set") as cache,
        ):
            steam_dna_jobs.run("job", {"url": "https://steamcommunity.com/id/live", "mode": "split", "language": "en", "cache_key": "key"})
        done = updates[-1]
        self.assertEqual(done["status"], "done")
        self.assertEqual(done["result"]["live_profile"]["showcases"], 2)
        self.assertTrue(done["result"]["ai"]["used"])
        self.assertEqual(done["result"]["project"]["mode"], "split")
        cache.assert_called_once()

    def test_provider_error_is_safe_job_error(self):
        updates = []
        with (
            patch.object(steam_dna_jobs.steam_catalog, "profile", return_value={"ok": False, "code": "steam_private", "error": "private"}),
            patch.object(steam_dna_jobs.rs, "job_update", side_effect=lambda jid, **kw: updates.append(kw)),
        ):
            steam_dna_jobs.run("job", {"url": "https://steamcommunity.com/id/private"})
        self.assertEqual(updates[-1]["status"], "error")
        self.assertEqual(updates[-1]["code"], "steam_private")


if __name__ == "__main__":
    unittest.main()
