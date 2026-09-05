import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import steam_browser_import
import steam_catalog
import steam_profile_guard


PROFILE_HTML = """
<html><body class="profile_page">
<script>g_rgProfileData = {"steamid":"76561199542622738","personaname":"Browser User"};</script>
<div class="playerAvatarAutoSizeInner"><img src="https://avatars.steamstatic.com/test_full.jpg"></div>
<span class="actual_persona_name">Browser User</span>
<div class="profile_summary">Rendered profile</div>
<div class="friendPlayerLevelNum">42</div>
<div class="profile_customization">
  <div class="profile_customization_header">Artwork Showcase</div>
  <img src="https://steamuserimages-a.akamaihd.net/ugc/art.jpg">
</div>
</body></html>
"""


class BrowserImportTests(unittest.TestCase):
    def test_only_public_steam_profile_urls_are_allowed(self):
        self.assertEqual(
            steam_browser_import._public_profile_url("https://steamcommunity.com/id/n1t1337"),
            "https://steamcommunity.com/id/n1t1337?l=english",
        )
        with self.assertRaises(steam_browser_import.BrowserImportError):
            steam_browser_import._public_profile_url("https://example.com/id/n1t1337")
        with self.assertRaises(steam_browser_import.BrowserImportError):
            steam_browser_import._public_profile_url("https://steamcommunity.com/market")

    def test_credentials_are_encoded_inside_cdp_endpoint(self):
        env = {
            "BRIGHTDATA_BROWSER_USERNAME": "zone:user",
            "BRIGHTDATA_BROWSER_PASSWORD": "p@ss/word",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            endpoint = steam_browser_import._endpoint()
        self.assertEqual(endpoint, "wss://zone%3Auser:p%40ss%2Fword@brd.superproxy.io:9222")

    def test_rendered_html_reuses_existing_profile_parser(self):
        with mock.patch.object(steam_catalog.steam_browser_import, "configured", return_value=True), \
             mock.patch.object(steam_catalog.steam_browser_import, "fetch_html", return_value=PROFILE_HTML), \
             mock.patch.object(steam_catalog, "_profile_fetch") as direct:
            result = steam_catalog._load_profile("https://steamcommunity.com/id/n1t1337")
        self.assertTrue(result["ok"])
        self.assertEqual(result["profile"]["steamid"], "76561199542622738")
        self.assertEqual(result["profile"]["name"], "Browser User")
        self.assertEqual(result["profile"]["level"], 42)
        self.assertEqual(result["profile"]["showcase_order"], ["artwork"])
        direct.assert_not_called()

    def test_browser_connection_error_never_exposes_credentials(self):
        playwright = mock.MagicMock()
        playwright.__enter__.return_value.chromium.connect_over_cdp.side_effect = RuntimeError(
            "cannot connect wss://zone-user:top-secret@brd.superproxy.io:9222"
        )
        fake_api = mock.MagicMock()
        fake_api.sync_playwright.return_value = playwright
        env = {
            "BRIGHTDATA_BROWSER_USERNAME": "zone-user",
            "BRIGHTDATA_BROWSER_PASSWORD": "top-secret",
        }
        with mock.patch.dict(os.environ, env, clear=False), \
             mock.patch.dict("sys.modules", {"playwright.sync_api": fake_api}):
            with self.assertRaises(steam_browser_import.BrowserImportError) as caught:
                steam_browser_import.fetch_html("https://steamcommunity.com/id/n1t1337")
        self.assertNotIn("top-secret", str(caught.exception))
        self.assertNotIn("wss://", str(caught.exception))

    def test_browser_import_bypasses_direct_steam_global_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profiles.sqlite3"
            db = sqlite3.connect(path)
            db.execute("CREATE TABLE gate (id INTEGER PRIMARY KEY, until REAL)")
            db.execute("INSERT INTO gate VALUES (1, ?)", (time.time() + 3600,))
            db.commit()
            db.close()
            result = steam_profile_guard.run(
                path, "profile", lambda: {"ok": True, "profile": {}},
                use_global_gate=False,
            )
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
