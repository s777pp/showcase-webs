import unittest
import tempfile
from pathlib import Path

from PIL import Image

from smweb.routers.seamless_loop import _media
from smweb.loop_jobs import _build_sequence


class SeamlessLoopTests(unittest.TestCase):
    def test_media_is_detected_by_magic_not_filename(self):
        self.assertEqual(_media(b"GIF89a" + b"x" * 20), (".gif", "gif"))
        self.assertEqual(_media(b"\x00\x00\x00\x18ftypisom" + b"x" * 20), (".mp4", "video"))
        self.assertIsNone(_media(b"not animated media"))

    def test_webm_and_avi_are_accepted(self):
        self.assertEqual(_media(b"\x1aE\xdf\xa3" + b"x" * 20), (".webm", "video"))
        self.assertEqual(_media(b"RIFFxxxxAVI " + b"x" * 20), (".avi", "video"))

    def test_frame_builder_produces_blend_and_pingpong_sequences(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            frames = []
            for index in range(8):
                frame = root / f"raw_{index}.png"
                Image.new("RGB", (4, 4), (index * 20, 0, 0)).save(frame)
                frames.append(frame)
            self.assertEqual(_build_sequence(frames, root / "blend", "blend", 2), 6)
            self.assertEqual(_build_sequence(frames, root / "pingpong", "pingpong", 2), 14)


if __name__ == "__main__":
    unittest.main()
