import unittest

from smweb.routers.seamless_loop import _media


class SeamlessLoopTests(unittest.TestCase):
    def test_media_is_detected_by_magic_not_filename(self):
        self.assertEqual(_media(b"GIF89a" + b"x" * 20), (".gif", "gif"))
        self.assertEqual(_media(b"\x00\x00\x00\x18ftypisom" + b"x" * 20), (".mp4", "video"))
        self.assertIsNone(_media(b"not animated media"))

    def test_webm_and_avi_are_accepted(self):
        self.assertEqual(_media(b"\x1aE\xdf\xa3" + b"x" * 20), (".webm", "video"))
        self.assertEqual(_media(b"RIFFxxxxAVI " + b"x" * 20), (".avi", "video"))


if __name__ == "__main__":
    unittest.main()
