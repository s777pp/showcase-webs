import io
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from smweb import remove_bg_client
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

    def json(self):
        import json
        return json.loads(self.body)


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


_NONE = {"MODAL_BG_REMOVE_URL": "", "MODAL_PROXY_TOKEN_ID": "", "MODAL_PROXY_TOKEN_SECRET": "", 
         "ILOVEAPI_PUBLIC_KEY": "", "PROBLEMBO_API_TOKEN": "", "REMOVE_BG_API_KEY": "",
         "BG_REMOVE_ORDER": "", "BG_REMOVE_FALLBACK": ""}
_MODAL = {**_NONE, "MODAL_BG_REMOVE_URL": "https://team--showcasemaker-bg-remove-api.modal.run",
          "MODAL_PROXY_TOKEN_ID": "wk-test", "MODAL_PROXY_TOKEN_SECRET": "ws-test"}
_ALL = {**_MODAL, "ILOVEAPI_PUBLIC_KEY": "pub", "PROBLEMBO_API_TOKEN": "pb", "REMOVE_BG_API_KEY": "rb"}


def _palette_png(size=(8, 6)) -> bytes:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    for x in range(size[0] // 2):
        for y in range(size[1]):
            image.putpixel((x, y), (255, 255, 255, 255))
    out = io.BytesIO()
    image.convert("P", palette=Image.Palette.ADAPTIVE).save(out, format="PNG", transparency=0)
    return out.getvalue()


def _colour_jpeg(size=(8, 6)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, (200, 40, 90)).save(out, format="JPEG", quality=100)
    return out.getvalue()


class _Json(_Response):
    def __init__(self, status_code: int, payload=None, body: bytes = b""):
        super().__init__(status_code, body)
        self.payload = payload or {}

    def json(self):
        return self.payload


class ProviderChainTests(unittest.TestCase):
    def setUp(self):
        remove_bg_client._ilove_token.update(value="", until=0)
        patcher = patch("smweb.remove_bg_client._take_budget", return_value=True)
        self.budget = patcher.start()
        self.addCleanup(patcher.stop)

    def test_chain_order_choice_and_switch_off(self):
        with patch.dict("os.environ", _ALL, clear=False):
            self.assertEqual(remove_bg_client.chain(), ["modal", "iloveapi", "problembo", "removebg"])
            self.assertEqual(remove_bg_client.chain("problembo"), ["problembo", "modal", "iloveapi", "removebg"])
            self.assertEqual(remove_bg_client.chain("unknown"), ["modal", "iloveapi", "problembo", "removebg"])
        with patch.dict("os.environ", {**_ALL, "BG_REMOVE_ORDER": "iloveapi,modal"}, clear=False):
            self.assertEqual(remove_bg_client.providers(), ["iloveapi", "modal"])
        with patch.dict("os.environ", {**_ALL, "BG_REMOVE_FALLBACK": "0"}, clear=False):
            self.assertEqual(remove_bg_client.chain("removebg"), ["removebg"])
        for url in ("http://team--x.modal.run", "https://evil.example.com", ""):
            with patch.dict("os.environ", {**_MODAL, "MODAL_BG_REMOVE_URL": url}, clear=False):
                self.assertFalse(remove_bg_client.configured(), url)

    @patch("smweb.remove_bg_client.requests.post")
    def test_posts_raw_image_to_modal_with_proxy_token(self, post: Mock):
        post.return_value = _Response(200, _png())
        with patch.dict("os.environ", _MODAL, clear=False):
            self.assertEqual(remove_bg_client.remove_background_with(_png("RGB"), "a.png"), (_png(), "modal"))
        args, kwargs = post.call_args
        self.assertEqual(args[0], _MODAL["MODAL_BG_REMOVE_URL"] + "/remove")
        self.assertEqual(kwargs["headers"]["Modal-Key"], "wk-test")
        self.assertEqual(kwargs["headers"]["Modal-Secret"], "ws-test")
        self.assertEqual(kwargs["data"], _png("RGB"))
        self.assertFalse(kwargs["allow_redirects"])

    @patch("smweb.remove_bg_client.requests.post")
    def test_modal_errors_map_to_safe_codes(self, post: Mock):
        with patch.dict("os.environ", _MODAL, clear=False):
            for status, body, code in ((422, b'{"ok":false,"code":"image_too_large"}', "image_too_large"),
                                       (422, b'{"detail":"x"}', "invalid_image"),
                                       (503, b"modal internals", "provider_unavailable")):
                post.return_value = _Response(status, body)
                with self.assertRaises(RemoveBgError) as caught:
                    remove_background(_png())
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn("modal internals", str(caught.exception))

    @patch("smweb.remove_bg_client.requests.post")
    def test_next_provider_only_when_the_previous_is_down(self, post: Mock):
        env = {**_MODAL, "REMOVE_BG_API_KEY": "k", "BG_REMOVE_ORDER": "modal,removebg"}
        post.side_effect = [_Response(503), _Response(200, _png())]
        with patch.dict("os.environ", env, clear=False):
            self.assertEqual(remove_bg_client.remove_background_with(_png()), (_png(), "removebg"))
        self.assertEqual(post.call_args_list[1].args[0], API_URL)
        post.reset_mock(side_effect=True)
        post.return_value = _Response(422, b'{"ok":false,"code":"image_only"}')
        with patch.dict("os.environ", env, clear=False):
            with self.assertRaises(RemoveBgError):
                remove_background(_png())
        self.assertEqual(post.call_count, 1, "a bad image is not sent to the next (paid) provider")

    @patch("smweb.remove_bg_client.requests.post")
    def test_provider_over_its_monthly_cap_is_skipped(self, post: Mock):
        env = {**_MODAL, "REMOVE_BG_API_KEY": "k", "BG_REMOVE_ORDER": "modal,removebg"}
        self.budget.side_effect = lambda name: name != "modal"
        post.return_value = _Response(200, _png())
        with patch.dict("os.environ", env, clear=False):
            self.assertEqual(remove_bg_client.remove_background_with(_png())[1], "removebg")
        self.budget.side_effect = lambda name: False
        with patch.dict("os.environ", env, clear=False):
            with self.assertRaises(RemoveBgError) as caught:
                remove_background(_png())
        self.assertEqual(caught.exception.code, "remove_bg_limit")

    @patch("smweb.remove_bg_client.requests.get")
    @patch("smweb.remove_bg_client.requests.post")
    def test_iloveapi_flow_keeps_only_its_alpha(self, post: Mock, get: Mock):
        post.side_effect = [
            _Json(200, {"token": "jwt"}),                                  # auth
            _Json(200, {"server_filename": "f.jpg"}),                       # upload
            _Json(200, {"status": "TaskSuccess"}),                          # process
        ]
        get.side_effect = [
            _Json(200, {"server": "api4g.iloveimg.com", "task": "t1"}),    # start
            _Response(200, _palette_png()),                                 # download
        ]
        with patch.dict("os.environ", {**_NONE, "ILOVEAPI_PUBLIC_KEY": "pub"}, clear=False):
            png, used = remove_bg_client.remove_background_with(_colour_jpeg(), "a.jpg")
        self.assertEqual(used, "iloveapi")
        self.assertEqual(post.call_args_list[0].kwargs["data"], {"public_key": "pub"})
        self.assertTrue(post.call_args_list[1].args[0].startswith("https://api4g.iloveimg.com/"))
        result = Image.open(io.BytesIO(png))
        self.assertEqual(result.mode, "RGBA")
        r, g, b, a = result.getpixel((1, 1))
        self.assertEqual(a, 255)
        self.assertGreater(r, 150, "colour comes from the source, not from the white mask")
        self.assertLess(g, 90)
        self.assertEqual(result.getpixel((7, 1))[3], 0)

    @patch("smweb.remove_bg_client.requests.get")
    @patch("smweb.remove_bg_client.requests.post")
    def test_iloveapi_foreign_task_server_is_refused(self, post: Mock, get: Mock):
        post.side_effect = [_Json(200, {"token": "jwt"})]
        get.side_effect = [_Json(200, {"server": "evil.example.com", "task": "t1"})]
        with patch.dict("os.environ", {**_NONE, "ILOVEAPI_PUBLIC_KEY": "pub"}, clear=False):
            with self.assertRaises(RemoveBgError) as caught:
                remove_background(_colour_jpeg())
        self.assertEqual(caught.exception.code, "provider_unavailable")
        self.assertEqual(post.call_count, 1, "nothing is uploaded to a host outside iLoveAPI")

    @patch("smweb.remove_bg_client.time.sleep")
    @patch("smweb.remove_bg_client.requests.put")
    @patch("smweb.remove_bg_client.requests.get")
    @patch("smweb.remove_bg_client.requests.post")
    def test_problembo_flow(self, post: Mock, get: Mock, put: Mock, _sleep: Mock):
        post.side_effect = [
            _Json(200, {"fileId": "f1.png", "uploadUrl": "https://upload.example.net/x",
                        "contentDisposition": "inline; filename=a.png"}),
            _Json(200, {}),
            _Json(200, {"taskId": "task-1"}),
        ]
        put.return_value = _Json(200)
        get.side_effect = [
            _Json(200, {"taskId": "task-1", "status": "RUNNING"}),
            _Json(200, {"taskId": "task-1", "taskType": "background_removal", "status": "SUCCEEDED",
                        "result": {"items": [{"kind": "IMAGE", "filename": "background-removed.png",
                                              "url": "https://storage.example.com/t/r.png?signature=x"}]}}),
            _Response(200, _png()),
        ]
        with patch.dict("os.environ", {**_NONE, "PROBLEMBO_API_TOKEN": "pb"}, clear=False):
            png, used = remove_bg_client.remove_background_with(_png("RGB"), "a.png")
        self.assertEqual((png, used), (_png(), "problembo"))
        self.assertEqual(post.call_args_list[2].args[0], remove_bg_client.PROBLEMBO_URL + "/background-removal/tasks")
        self.assertEqual(post.call_args_list[2].kwargs["json"], {"sourceImages": [{"fileId": "f1.png"}], "idempotencyKey": "f1.png"})
        self.assertEqual(get.call_args_list[0].args[0], remove_bg_client.PROBLEMBO_URL + "/operations/task-1")
        self.assertEqual(post.call_args_list[0].kwargs["headers"]["Authorization"], "Bearer pb")
        self.assertEqual(put.call_args.kwargs["headers"]["Content-Type"], "image/png")
        self.assertEqual(put.call_args.kwargs["headers"]["Content-Disposition"], "inline; filename=a.png")

    @patch("smweb.remove_bg_client.time.sleep")
    @patch("smweb.remove_bg_client.requests.put")
    @patch("smweb.remove_bg_client.requests.get")
    @patch("smweb.remove_bg_client.requests.post")
    def test_problembo_result_host_is_checked(self, post: Mock, get: Mock, put: Mock, _sleep: Mock):
        post.side_effect = [_Json(200, {"fileId": "f1", "uploadUrl": "https://u.example.net/x"}), _Json(200, {}),
                            _Json(200, {"taskId": "t"})]
        put.return_value = _Json(200)
        get.side_effect = [_Json(200, {"status": "SUCCEEDED", "result": {"items": [{"kind": "IMAGE", "url": "https://127.0.0.1/r.png"}]}})]
        with patch.dict("os.environ", {**_NONE, "PROBLEMBO_API_TOKEN": "pb"}, clear=False):
            with self.assertRaises(RemoveBgError) as caught:
                remove_background(_png("RGB"))
        self.assertEqual(caught.exception.code, "invalid_result")
        self.assertEqual(get.call_count, 1, "the result is not fetched from an IP address")

    @patch("smweb.remove_bg_client.time.sleep")
    @patch("smweb.remove_bg_client.requests.put")
    @patch("smweb.remove_bg_client.requests.get")
    @patch("smweb.remove_bg_client.requests.post")
    def test_problembo_failed_operation_moves_to_the_next_provider(self, post: Mock, get: Mock, put: Mock, _sleep: Mock):
        post.side_effect = [_Json(200, {"fileId": "f1", "uploadUrl": "https://u.example.net/x"}), _Json(200, {}),
                            _Json(200, {"taskId": "t"}), _Response(200, _png())]
        put.return_value = _Json(200)
        get.side_effect = [_Json(200, {"status": "FAILED"})]
        env = {**_NONE, "PROBLEMBO_API_TOKEN": "pb", "REMOVE_BG_API_KEY": "rb", "BG_REMOVE_ORDER": "problembo,removebg"}
        with patch.dict("os.environ", env, clear=False):
            self.assertEqual(remove_bg_client.remove_background_with(_png("RGB"), "a.png"), (_png(), "removebg"))


class BuilderProviderRouteTests(unittest.TestCase):
    def test_providers_route_lists_only_configured_services_and_job_keeps_choice(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import redis_store as rs
        from smweb.routers import builder

        app = FastAPI()
        app.include_router(builder.router)
        client = TestClient(app)
        # A Free account removes a background once a week (tests/test_free_limits.py); not what this test is about.
        with patch.object(builder.free_limits, "consume", return_value=True), \
             patch.object(builder, "_user", lambda request: ({"id": 9}, None)),              patch.dict("os.environ", {**_NONE, "ILOVEAPI_PUBLIC_KEY": "pub", "REMOVE_BG_API_KEY": "rb"}, clear=False):
            data = client.get("/api/builder/remove-background/providers").json()
            self.assertEqual([p["id"] for p in data["providers"]], ["iloveapi", "removebg"])
            self.assertTrue(data["fallback"])
            with patch.object(builder._remove_pool, "submit") as submit:
                res = client.post("/api/builder/remove-background",
                                  json={"url": "/api/builder/assets/" + "a" * 32 + ".png", "provider": "removebg"})
            self.assertEqual(res.status_code, 200, res.text)
            self.assertEqual(rs.job_get(res.json()["job_id"])["provider"], "removebg")
            submit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
