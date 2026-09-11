import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb.routers.builder import _validated_project
from smweb.routers import steam_dna as steam_dna_router
from smweb.steam_dna import build_profile_dna


class SteamDnaTests(unittest.TestCase):
    def snapshot(self):
        return {
            "steamid": "76561198000000000",
            "name": "Signal User",
            "avatar": "https://avatars.steamstatic.com/example_full.jpg",
            "background": "https://shared.cloudflare.steamstatic.com/store_item_assets/example.jpg",
            "level": 42,
            "timecreated": 1262304000,
            "games": [
                {"appid": 10, "name": "Focused Game", "playtime_forever": 72000},
                {"appid": 20, "name": "Second Game", "playtime_forever": 12000},
                {"appid": 30, "name": "Third Game", "playtime_forever": 6000},
            ],
            "recent_games": [{"appid": 10, "playtime_2weeks": 900}],
            "stats_map": {"games": 180, "screenshots": 250, "workshop": 30},
            "badges": [{"title": "Badge"}] * 12,
            "showcase_instances": [{"type": "artwork"}],
        }

    def test_result_is_deterministic_bounded_and_builder_compatible(self):
        first = build_profile_dna(self.snapshot(), user_id=7, mode="split")
        second = build_profile_dna(self.snapshot(), user_id=7, mode="split")
        self.assertEqual(first["seed"], second["seed"])
        self.assertEqual(first["signals"], second["signals"])
        self.assertEqual(len(first["palette"]), 3)
        self.assertTrue(all(0 <= value <= 1 for value in first["signals"].values()))
        project = _validated_project(first["project"])
        self.assertEqual(project["mode"], "split")
        self.assertEqual(project["width"], 606)
        self.assertEqual([layer["type"] for layer in project["layers"]].count("dna"), 1)
        self.assertTrue(project["layers"][0]["src"].startswith("/api/steam/proxy-image?"))

    def test_profile_changes_produce_a_new_identity(self):
        first = build_profile_dna(self.snapshot())
        changed = self.snapshot()
        changed["steamid"] = "76561198000000001"
        changed["games"] = [{"appid": 99, "name": "Only Game", "playtime_forever": 120}]
        second = build_profile_dna(changed)
        self.assertNotEqual(first["seed"], second["seed"])
        self.assertNotEqual(first["signals"], second["signals"])

    def test_invalid_mode_falls_back_to_workshop(self):
        result = build_profile_dna(self.snapshot(), mode="unknown")
        self.assertEqual(result["project"]["mode"], "workshop")
        self.assertEqual(result["project"]["width"], 750)

    def test_api_requires_login_and_uses_private_snapshot(self):
        app = FastAPI()
        app.include_router(steam_dna_router.router)
        client = TestClient(app)
        with patch.object(steam_dna_router, "_auth_user", return_value=None):
            response = client.post("/api/steam-dna/analyze", json={"mode": "featured"})
        self.assertEqual(response.status_code, 401)
        with (
            patch.object(steam_dna_router, "_auth_user", return_value={"id": 7}),
            patch.object(steam_dna_router.rs, "rate_limit", return_value=(True, 11)),
            patch.object(steam_dna_router.auth_db, "get_steam_profile_snapshot", return_value=self.snapshot()),
            patch.object(steam_dna_router.steam_dna_ai, "configured", return_value=False),
        ):
            response = client.post("/api/steam-dna/analyze", json={"mode": "featured"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["dna"]["project"]["mode"], "featured")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_api_adds_ai_interpretation_without_replacing_signals(self):
        app = FastAPI()
        app.include_router(steam_dna_router.router)
        client = TestClient(app)
        interpretation = {
            "title": "Signal Cartographer", "summary": "Readable summary",
            "play_style": "Focused pattern", "collector_style": "Broad library",
            "visual_direction": "Cyan map lines", "motto": "MAP YOUR SIGNAL",
            "signal_notes": {key: "Clear note" for key in ("focus", "variety", "mastery", "history", "activity", "collector")},
        }
        with (
            patch.object(steam_dna_router, "_auth_user", return_value={"id": 7, "is_pro": False}),
            patch.object(steam_dna_router.rs, "rate_limit", return_value=(True, 2)),
            patch.object(steam_dna_router.auth_db, "get_steam_profile_snapshot", return_value=self.snapshot()),
            patch.object(steam_dna_router.steam_dna_ai, "configured", return_value=True),
            patch.object(steam_dna_router.steam_dna_ai, "enrich_profile_dna", return_value=interpretation),
        ):
            response = client.post("/api/steam-dna/analyze", json={"mode": "workshop", "language": "ru"})
        body = response.json()["dna"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["interpretation"]["title"], "Signal Cartographer")
        self.assertTrue(body["ai"]["used"])
        self.assertEqual(set(body["signals"]), {"focus", "variety", "mastery", "history", "activity", "collector"})


if __name__ == "__main__":
    unittest.main()
