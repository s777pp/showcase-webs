from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image, ImageDraw

import processor


class WorkshopGroupEncodingTests(unittest.TestCase):
    @staticmethod
    def _gif_timeline(path: Path) -> tuple[tuple[int, int], int, int]:
        repaired = path.with_name(path.stem + "_readable.gif")
        data = path.read_bytes()
        repaired.write_bytes(data[:-1] + b"\x3b")
        durations = []
        with Image.open(repaired) as image:
            size = image.size
            index = 0
            while True:
                try:
                    image.seek(index)
                except EOFError:
                    break
                durations.append(int(image.info.get("duration", 0) or 0))
                index += 1
        return size, len(durations), sum(durations)

    def test_frame_sets_share_names_count_and_dimensions(self):
        if not processor.find_ffmpeg():
            self.skipTest("FFmpeg is not installed")
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            source = tmp / "source.gif"
            frames = []
            for index in range(6):
                frame = Image.new("RGB", (500, 240), (8, 15, 24))
                draw = ImageDraw.Draw(frame)
                draw.rectangle((index * 20, 20, index * 20 + 70, 210), fill=(20 + index * 30, 180, 240))
                frames.append(frame)
            frames[0].save(
                source,
                save_all=True,
                append_images=frames[1:],
                duration=100,
                loop=0,
            )

            work = tmp / "work"
            work.mkdir()
            full, parts, count = processor._prepare_workshop_frame_sets(
                source, work, fps=10, width=750,
            )

            full_names = [path.name for path in sorted(full.glob("frame_*.png"))]
            self.assertEqual(count, len(full_names))
            self.assertGreater(count, 1)
            for part in parts:
                part_files = sorted(part.glob("frame_*.png"))
                self.assertEqual([path.name for path in part_files], full_names)
                with Image.open(part_files[0]) as image:
                    self.assertEqual(image.width, 150)

    def test_group_uses_highest_common_gifski_quality(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            frame_dirs = []
            for index in range(5):
                frame_dir = tmp / f"frames_{index}"
                frame_dir.mkdir()
                frame_dirs.append(frame_dir)
            destinations = [tmp / f"part_{index}.gif" for index in range(5)]
            attempts = []

            def fake_encode(frame_dir, destination, fps, quality=100):
                panel = int(frame_dir.name.rsplit("_", 1)[1])
                attempts.append((panel, fps, quality))
                size = 900 if quality <= 80 or panel < 4 else 1200
                destination.write_bytes(f"q={quality:03d};".encode("ascii") + b"x" * size)
                return True

            with mock.patch.object(processor, "find_gifski", return_value="gifski"), mock.patch.object(
                processor, "_gifski_from_frames", side_effect=fake_encode
            ):
                selected = processor._encode_workshop_frame_group(
                    frame_dirs, destinations, fps=18, encoder="gifski", max_mb=0.001,
                )

            self.assertEqual(selected, {"encoder": "gifski", "quality": 80, "fps": 18})
            self.assertEqual({path.read_bytes()[:6] for path in destinations}, {b"q=080;"})
            for quality in {quality for _, _, quality in attempts}:
                used_panels = {panel for panel, _, q in attempts if q == quality}
                self.assertEqual(used_panels, {0, 1, 2, 3, 4})

    def test_video_workshop_skips_shared_five_mb_intermediate(self):
        expected = {"part_1.gif": Path("part_1.gif")}
        with tempfile.TemporaryDirectory() as raw_tmp:
            output = Path(raw_tmp) / "output"
            with mock.patch.object(processor, "process_gif_workshop", return_value=expected) as process, mock.patch.object(
                processor, "media_to_gif"
            ) as media_to_gif:
                result = processor.process_video_workshop(
                    Path("source.mp4"), output, fps=20, width=750,
                    duration=8, encoder="gifski",
                )

            self.assertEqual(result, expected)
            media_to_gif.assert_not_called()
            self.assertEqual(process.call_args.args[:2], (Path("source.mp4"), output))
            self.assertEqual(process.call_args.kwargs["fps"], 20)
            self.assertEqual(process.call_args.kwargs["width"], 750)
            self.assertEqual(process.call_args.kwargs["duration"], 8)

    def test_public_workshop_outputs_have_one_timeline(self):
        if not processor.find_ffmpeg() or not processor.find_gifski():
            self.skipTest("FFmpeg and gifski are required")
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            source = tmp / "moving.gif"
            source_frames = []
            for frame_index in range(12):
                frame = Image.new("RGB", (750, 260), (7, 14, 23))
                draw = ImageDraw.Draw(frame)
                for panel in range(5):
                    left = panel * 150
                    x = left + 8 + frame_index * 8
                    draw.rectangle((x, 30 + panel * 4, x + 28, 220), fill=(30 + panel * 35, 120 + frame_index * 8, 240))
                source_frames.append(frame)
            source_frames[0].save(
                source,
                save_all=True,
                append_images=source_frames[1:],
                duration=80,
                loop=0,
            )

            output = tmp / "output"
            result = processor.process_gif_workshop(
                source, output, encoder="gifski", fps=12, width=750,
            )
            timelines = [self._gif_timeline(result[f"part_{index}.gif"]) for index in range(1, 6)]

            self.assertEqual({size for size, _, _ in timelines}, {(150, 260)})
            self.assertEqual(len({frames for _, frames, _ in timelines}), 1)
            self.assertEqual(len({duration for _, _, duration in timelines}), 1)
            self.assertTrue(all(result[f"part_{index}.gif"].stat().st_size <= 5 * 1024 * 1024 for index in range(1, 6)))

    def test_fit_fallback_reduces_fps_for_the_whole_group(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            output = tmp / "output"
            attempted_fps = []

            def fake_prepare(source, work, fps, width, **kwargs):
                full = work / "full_frames"
                full.mkdir()
                (full / "frame_0001.png").write_bytes(b"frame")
                parts = []
                for index in range(5):
                    part = work / f"part_{index}"
                    part.mkdir()
                    parts.append(part)
                return full, parts, 1

            def fake_group(frame_dirs, destinations, fps, encoder, **kwargs):
                attempted_fps.append(fps)
                if fps == 20:
                    raise processor._WorkshopGroupFitError("too large")
                for destination in destinations:
                    destination.write_bytes(b"GIF89a;")
                return {"encoder": "gifski", "quality": 100, "fps": fps}

            def fake_full(frame_dir, destination, fps, quality=100):
                destination.write_bytes(b"GIF89a;")
                return True

            def fake_bars(source, destination, *args, **kwargs):
                destination.write_bytes(b"GIF89a;")

            with mock.patch.object(processor, "_prepare_workshop_frame_sets", side_effect=fake_prepare), mock.patch.object(
                processor, "_encode_workshop_frame_group", side_effect=fake_group
            ), mock.patch.object(processor, "_gifski_from_frames", side_effect=fake_full), mock.patch.object(
                processor, "_gif_full_with_bars_workshop", side_effect=fake_bars
            ), mock.patch.object(processor, "apply_hex21_file"):
                processor.process_gif_workshop(
                    tmp / "source.gif", output, encoder="gifski", fps=20, width=750,
                )

            self.assertEqual(attempted_fps, [20, 18])


if __name__ == "__main__":
    unittest.main()
