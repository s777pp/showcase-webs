import io
import unittest

from PIL import Image

import processor
from smweb.steam_readiness import Candidate, analyze_group, inspect_file


def png_bytes(size=(150, 100), hex21=True):
    buffer = io.BytesIO()
    Image.new("RGB", size, (25, 110, 155)).save(buffer, format="PNG")
    data = buffer.getvalue()
    return processor.apply_hex21(data) if hex21 else data


def gif_bytes(size=(150, 100), durations=(100, 100), hex21=True):
    frames = [Image.new("RGB", size, (20 + index * 20, 80, 140)) for index in range(len(durations))]
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=list(durations), loop=0)
    data = buffer.getvalue()
    return processor.apply_hex21(data) if hex21 else data


class SteamReadinessTests(unittest.TestCase):
    def test_generated_workshop_set_is_ready(self):
        files = [Candidate(f"demo_workshop/part_{index}.png", png_bytes()) for index in range(1, 6)]
        report = analyze_group("demo_workshop", files)
        self.assertEqual(report["mode"], "workshop")
        self.assertEqual(report["status"], "ready")
        self.assertTrue(all(check["state"] == "pass" for check in report["checks"]))

    def test_split_geometry_mismatch_fails(self):
        files = [
            Candidate("center_506.png", png_bytes((506, 200))),
            Candidate("side_100.png", png_bytes((101, 200))),
        ]
        report = analyze_group("Files", files, "split")
        geometry = next(check for check in report["checks"] if check["id"] == "geometry")
        self.assertEqual(geometry["state"], "fail")
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["failures"], 1)
        self.assertEqual(report["warnings"], 0)

    def test_missing_hex_is_warning(self):
        report = inspect_file(Candidate("featured_630.png", png_bytes((630, 200), hex21=False)))
        self.assertIn("hex21_missing", {issue["code"] for issue in report["issues"]})

        group = analyze_group("Files", [Candidate("featured_630.png", png_bytes((630, 200), hex21=False))], "featured")
        self.assertEqual(group["status"], "warn")
        self.assertEqual(group["failures"], 0)
        self.assertEqual(group["warnings"], 1)

    def test_gif_metadata_survives_hex21_trailer(self):
        report = inspect_file(Candidate("part_1.gif", gif_bytes(durations=(80, 120, 100))))
        self.assertEqual(report["format"], "GIF")
        self.assertTrue(report["animated"])
        self.assertEqual(report["frames"], 3)
        self.assertEqual(report["duration_ms"], 300)


if __name__ == "__main__":
    unittest.main()
