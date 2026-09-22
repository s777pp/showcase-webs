import io
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from smweb.remove_bg_client import API_URL, RemoveBgError, remove_background


def _png(mode="RGBA") -> bytes:
    output = io.BytesIO()
    Image.new(mode, (8, 6), (30, 120, 200, 90) if mode == "RGBA" else (30, 120, 200)).save(
        output, format="PNG"
    )
    return output.getvalue()


def _animated_gif() -> bytes:
    output = io.BytesIO()
    frames = [Image.new("RGB", (4, 4), color) for color in ("red", "blue")]
    frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:], duration=50, loop=0)
    return output.getvalue()


class _Response:
    def __init__(self, status_code: int, body: bytes = b""):
        self.status_code = status_code
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, _chunk_size):
        yield self.body


class RemoveBgClientTests(unittest.TestCase):
    @patch("smweb.remove_bg_client.requests.post")
    def test_sends_one_bounded_still_image_and_accepts_transparent_png(self, post: Mock):
        post.return_value = _Response(200, _png())
        with patch.dict("os.environ", {"REMOVE_BG_API_KEY": "test-secret"}, clear=False):
            result = remove_background(_png("RGB"), "portrait.png")

        self.assertEqual(result, _png())
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], API_URL)
        self.assertEqual(kwargs["headers"]["X-Api-Key"], "test-secret")
        self.assertEqual(kwargs["data"], {"size": "auto", "format": "png", "type": "auto"})
        self.assertEqual(kwargs["files"]["image_file"][0], "portrait.png")
        self.assertEqual(kwargs["timeout"], (10, 120))
        self.assertFalse(kwargs["allow_redirects"])

    @patch("smweb.remove_bg_client.requests.post")
    def test_requires_server_side_key_before_provider_call(self, post: Mock):
        with patch.dict("os.environ", {"REMOVE_BG_API_KEY": ""}, clear=False):
            with self.assertRaises(RemoveBgError) as caught:
                remove_background(_png())
        self.assertEqual(caught.exception.code, "not_configured")
        post.assert_not_called()

    @patch("smweb.remove_bg_client.requests.post")
    def test_rejects_animated_and_unsupported_media_before_provider_call(self, post: Mock):
        with patch.dict("os.environ", {"REMOVE_BG_API_KEY": "test-secret"}, clear=False):
            for payload in (_animated_gif(), b"not an image"):
                with self.assertRaises(RemoveBgError) as caught:
                    remove_background(payload)
                self.assertIn(caught.exception.code, {"image_only", "invalid_image"})
        post.assert_not_called()

    @patch("smweb.remove_bg_client.requests.post")
    def test_maps_provider_failures_to_safe_codes(self, post: Mock):
        with patch.dict("os.environ", {"REMOVE_BG_API_KEY": "test-secret"}, clear=False):
            for status, code in ((429, "provider_busy"), (402, "provider_unavailable"),
                                 (500, "provider_unavailable")):
                post.return_value = _Response(status, b"provider secret diagnostic")
                with self.assertRaises(RemoveBgError) as caught:
                    remove_background(_png())
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn("provider secret diagnostic", str(caught.exception))

    @patch("smweb.remove_bg_client.requests.post")
    def test_rejects_provider_png_without_transparency(self, post: Mock):
        post.return_value = _Response(200, _png("RGB"))
        with patch.dict("os.environ", {"REMOVE_BG_API_KEY": "test-secret"}, clear=False):
            with self.assertRaises(RemoveBgError) as caught:
                remove_background(_png())
        self.assertEqual(caught.exception.code, "invalid_result")


if __name__ == "__main__":
    unittest.main()
