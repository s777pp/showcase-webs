import io
import unittest

from PIL import Image

import processor
from smweb.steam_readiness import Candidate, analyze_group, apply_safe_fixes, inspect_file


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

    def test_split_geometry_mismatch_is_reported_without_red_size_verdict(self):
        files = [
            Candidate("center_506.png", png_bytes((506, 200))),
            Candidate("side_100.png", png_bytes((101, 200))),
        ]
        report = analyze_group("Files", files, "split")
        geometry = next(check for check in report["checks"] if check["id"] == "geometry")
        self.assertEqual(geometry["state"], "fail")
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["failures"], 1)
        self.assertEqual(report["warnings"], 0)

    def test_missing_hex_is_warning(self):
        report = inspect_file(Candidate("featured_630.png", png_bytes((630, 200), hex21=False)))
        self.assertIn("hex21_missing", {issue["code"] for issue in report["issues"]})

        group = analyze_group("Files", [Candidate("featured_630.png", png_bytes((630, 200), hex21=False))], "featured")
        self.assertEqual(group["status"], "ready")
        self.assertEqual(group["failures"], 0)
        self.assertEqual(group["warnings"], 1)

    def test_gif_metadata_survives_hex21_trailer(self):
        report = inspect_file(Candidate("part_1.gif", gif_bytes(durations=(80, 120, 100))))
        self.assertEqual(report["format"], "GIF")
        self.assertTrue(report["animated"])
        self.assertEqual(report["frames"], 3)
        self.assertEqual(report["duration_ms"], 300)

    def test_workshop_parts_wider_than_minimum_are_ready(self):
        files = [Candidate(f"part_{index}.png", png_bytes((180 + index, 100))) for index in range(1, 6)]
        report = analyze_group("Files", files, "workshop")
        geometry = next(check for check in report["checks"] if check["id"] == "geometry")
        self.assertEqual(geometry["state"], "pass")

    def test_long_animation_is_a_recommendation(self):
        report = analyze_group(
            "Files",
            [Candidate("featured_630.gif", gif_bytes((630, 100), durations=(4100, 4100)))],
            "featured",
        )
        animation = next(check for check in report["checks"] if check["id"] == "animation")
        self.assertEqual(animation["state"], "warn")
        self.assertEqual(report["failures"], 0)

    def test_safe_fix_normalizes_workshop_names_and_hex(self):
        source = [Candidate(f"tile-{index}.png", png_bytes((180, 100), hex21=False)) for index in range(1, 6)]
        mode, fixed = apply_safe_fixes(source, "workshop")
        self.assertEqual(mode, "workshop")
        self.assertEqual([item.name for item in fixed], [f"part_{index}.png" for index in range(1, 6)])
        self.assertTrue(all(item.data.endswith(b"\x21") for item in fixed))
        self.assertEqual(analyze_group("Files", fixed, "workshop")["status"], "ready")

    def test_oversized_auxiliary_is_warning_but_set_stays_ready(self):
        files = [Candidate(f"part_{index}.png", png_bytes((150, 100))) for index in range(1, 6)]
        auxiliary = Candidate("full_with_bars.png", png_bytes((750, 100)) + b"x" * (5 * 1024 * 1024))
        report = analyze_group("Files", files + [auxiliary], "workshop")
        aux_report = next(item for item in report["files"] if item["auxiliary"])
        self.assertEqual(report["status"], "ready")
        self.assertTrue(all(issue["severity"] == "warn" for issue in aux_report["issues"]))
        self.assertIn("auxiliary_not_for_upload", [issue["code"] for issue in aux_report["issues"]])

    def test_oversized_primary_is_the_red_not_ready_verdict(self):
        files = [Candidate(f"part_{index}.png", png_bytes((150, 100))) for index in range(1, 6)]
        files[2] = Candidate("part_3.png", png_bytes((150, 100)) + b"x" * (5 * 1024 * 1024))
        report = analyze_group("Files", files, "workshop")
        self.assertEqual(report["status"], "fail")


if __name__ == "__main__":
    unittest.main()
