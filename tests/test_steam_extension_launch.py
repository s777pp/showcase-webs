import unittest
from pathlib import Path


class SteamExtensionLaunchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.html = (root / "static" / "app.html").read_text(encoding="utf-8")
        cls.script = (root / "static" / "js" / "steam-extension-status.js").read_text(encoding="utf-8")

    def test_steam_tab_has_all_three_quick_modes_and_launch_button(self):
        self.assertIn('id="steamExtensionUpload"', self.html)
        for mode in ("workshop", "featured", "split"):
            self.assertIn(f'data-steam-upload-mode="{mode}"', self.html)

    def test_quick_launch_reuses_existing_extension_protocol(self):
        self.assertIn("type: 'START_STEAM_UPLOAD'", self.script)
        self.assertIn("mode === 'split' ? 'artwork' : mode", self.script)
        for expected_name in ("part_1", "part_5", "featured_630", "center_506", "side_100"):
            self.assertIn(expected_name, self.script)


if __name__ == "__main__":
    unittest.main()
