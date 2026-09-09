import time
import tempfile
import unittest
from pathlib import Path

import auth_db
from smweb.routers.builder import _validated_project


class BuilderProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = (auth_db.USING_POSTGRES, auth_db.DB, auth_db._SCHEMA_READY)
        auth_db.USING_POSTGRES = False
        auth_db.DB = Path(self.temp.name) / "users.db"
        auth_db._SCHEMA_READY = False
        connection = auth_db._conn()
        connection.execute(
            "INSERT INTO users(email,password_hash,is_pro,email_verified,created_at) VALUES (?,?,?,?,?)",
            ("builder@example.invalid", "test", 0, 1, time.time()),
        )
        connection.commit()
        self.user_id = int(connection.execute("SELECT id FROM users").fetchone()["id"])
        connection.close()

    def tearDown(self):
        auth_db.USING_POSTGRES, auth_db.DB, auth_db._SCHEMA_READY = self.previous
        self.temp.cleanup()

    def test_free_project_expires_and_pro_project_does_not(self):
        free = auth_db.save_builder_project(
            self.user_id, "free", "Free", "workshop", {"layers": []}, is_pro=False
        )
        pro = auth_db.save_builder_project(
            self.user_id, "pro", "Pro", "split", {"layers": []}, is_pro=True
        )
        self.assertGreater(free["expires_at"], time.time() + 6 * 86400)
        self.assertIsNone(pro["expires_at"])
        self.assertEqual([item["id"] for item in auth_db.builder_projects_for_user(self.user_id)],
                         ["pro", "free"])

    def test_free_export_is_one_per_utc_day(self):
        self.assertEqual(auth_db.consume_builder_render(self.user_id, is_pro=False), (True, 0))
        self.assertEqual(auth_db.consume_builder_render(self.user_id, is_pro=False), (False, 0))
        self.assertEqual(auth_db.consume_builder_render(self.user_id, is_pro=True), (True, None))

    def test_project_validation_rejects_untrusted_sources(self):
        project = _validated_project({
            "mode": "split",
            "width": 606,
            "height": 1000,
            "layers": [{"id": "x", "type": "character", "src": "javascript:alert(1)"}],
        })
        self.assertEqual(project["layers"][0]["src"], "")
        self.assertEqual(project["mode"], "split")
        with self.assertRaises(ValueError):
            _validated_project({"layers": [{"type": "script"}]})

    def test_builder_layer_controls_are_validated(self):
        project = _validated_project({
            "layers": [{
                "type": "effect", "effect": "unknown", "color": "red",
                "chromaTolerance": 999, "chromaFeather": -8,
                "fontSize": "invalid", "animation": "spin",
            }],
        })
        layer = project["layers"][0]
        self.assertEqual(layer["effect"], "particle")
        self.assertEqual(layer["color"], "#52d5ff")
        self.assertEqual(layer["chromaTolerance"], 120)
        self.assertEqual(layer["chromaFeather"], 0)
        self.assertEqual(layer["fontSize"], 64)
        self.assertEqual(layer["animation"], "none")

    def test_builder_markup_exposes_compact_controls(self):
        root = Path(__file__).resolve().parents[1]
        markup = (root / "static" / "app.html").read_text(encoding="utf-8")
        script = (root / "static" / "js" / "showcase-builder.js").read_text(encoding="utf-8")
        self.assertNotIn("builder-file-button", markup)
        self.assertIn('id="builderChromaTolerance"', markup)
        self.assertIn('id="builderChromaFeather"', markup)
        self.assertIn('id="builderEffectColor"', markup)
        self.assertIn('id="builderFontPreview"', markup)
        self.assertIn('<option value="Unbounded">Unbounded</option>', markup)
        self.assertIn("applyChroma", script)
        self.assertIn("builderEffectColor", script)
        self.assertIn("ctx.translate(-canvas.width/2,-canvas.height/2)", script)
        self.assertIn("syncFontPreview", script)


if __name__ == "__main__":
    unittest.main()
