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

    def test_api_requires_login_and_queues_live_public_profile(self):
        app = FastAPI()
        app.include_router(steam_dna_router.router)
        client = TestClient(app)
        with patch.object(steam_dna_router, "_auth_user", return_value=None):
            response = client.post("/api/steam-dna/analyze", json={"url": "https://steamcommunity.com/id/example"})
        self.assertEqual(response.status_code, 401)
        with (
            patch.object(steam_dna_router, "_auth_user", return_value={"id": 7, "is_pro": False}),
            patch.object(steam_dna_router.auth_db, "effective_pro", return_value=False),
            patch.object(steam_dna_router.rs, "rate_limit", return_value=(True, 11)),
            patch.object(steam_dna_router.rs, "steam_dna_cache_get", return_value=None),
            patch.object(steam_dna_router.rs, "job_find_active", return_value=None),
            patch.object(steam_dna_router.rs, "redis_ok", return_value=True),
            patch.object(steam_dna_router.rs, "worker_alive", return_value=True),
            patch.object(steam_dna_router.rs, "job_create") as create,
            patch.dict("os.environ", {"WORKER_MODE": "external"}),
        ):
            response = client.post(
                "/api/steam-dna/analyze",
                json={"url": "https://steamcommunity.com/id/example", "mode": "featured", "language": "ru"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["queued"])
        payload = create.call_args.args[1]
        self.assertEqual(payload["kind"], "steam_dna")
        self.assertEqual(payload["mode"], "featured")
        self.assertEqual(payload["language"], "ru")
        self.assertTrue(payload["url"].startswith("https://steamcommunity.com/id/example"))

    def test_api_rejects_non_steam_url_and_returns_cached_result_without_quota(self):
        app = FastAPI()
        app.include_router(steam_dna_router.router)
        client = TestClient(app)
        cached = build_profile_dna(self.snapshot(), mode="workshop")
        with patch.object(steam_dna_router, "_auth_user", return_value={"id": 7}):
            invalid = client.post("/api/steam-dna/analyze", json={"url": "https://example.com/profile"})
        self.assertEqual(invalid.status_code, 400)
        with (
            patch.object(steam_dna_router, "_auth_user", return_value={"id": 7}),
            patch.object(steam_dna_router.rs, "steam_dna_cache_get", return_value=cached),
            patch.object(steam_dna_router.rs, "rate_limit") as quota,
        ):
            response = client.post(
                "/api/steam-dna/analyze", json={"url": "https://steamcommunity.com/profiles/76561198000000000"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["cached"])
        self.assertEqual(response.json()["dna"]["seed"], cached["seed"])
        quota.assert_not_called()

    def test_status_is_private_to_job_owner(self):
        app = FastAPI()
        app.include_router(steam_dna_router.router)
        client = TestClient(app)
        job = {"kind": "steam_dna", "user_id": 7, "status": "done", "pct": 100, "stage": "done", "result": {"seed": "abc"}}
        with patch.object(steam_dna_router, "_auth_user", return_value={"id": 7}), patch.object(steam_dna_router.rs, "job_get", return_value=job):
            response = client.get("/api/steam-dna/status/0123456789abcdef01234567")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["dna"]["seed"], "abc")
        with patch.object(steam_dna_router, "_auth_user", return_value={"id": 8}), patch.object(steam_dna_router.rs, "job_get", return_value=job):
            response = client.get("/api/steam-dna/status/0123456789abcdef01234567")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
