import unittest
from unittest.mock import Mock, patch

from smweb import modal_upscale_client
from smweb import object_store
from smweb.routers.media import _upscale_media


class ModalUpscaleTests(unittest.TestCase):
    def test_media_magic_does_not_trust_filename(self):
        self.assertEqual(_upscale_media(b"\x89PNG\r\n\x1a\nrest")[0], "image")
        self.assertEqual(_upscale_media(b"GIF89arest")[0], "gif")
        self.assertEqual(_upscale_media(b"\x00\x00\x00\x18ftypisomrest")[0], "video")
        self.assertIsNone(_upscale_media(b"<script>not media</script>"))

    @patch("smweb.object_store.client")
    def test_presigned_download_is_private_and_bounded(self, client):
        fake = Mock()
        fake.generate_presigned_url.return_value = "https://example.invalid/signed"
        client.return_value = fake
        url = object_store.presigned_get_url(
            "upscale/result/job.mp4", expires=999999,
            download_name='bad\n"name.mp4', media_type="video/mp4",
        )
        self.assertEqual(url, "https://example.invalid/signed")
        kwargs = fake.generate_presigned_url.call_args.kwargs
        self.assertEqual(kwargs["ExpiresIn"], 86400)
        self.assertEqual(kwargs["Params"]["Bucket"], object_store.PRIVATE_BUCKET)
        self.assertEqual(kwargs["Params"]["ResponseContentType"], "video/mp4")
        self.assertNotIn("\n", kwargs["Params"]["ResponseContentDisposition"])

    def test_modal_client_rejects_untrusted_endpoint(self):
        with patch.object(modal_upscale_client, "BASE_URL", "https://attacker.example"), \
             patch.object(modal_upscale_client, "TOKEN_ID", "wk-test"), \
             patch.object(modal_upscale_client, "TOKEN_SECRET", "ws-test"):
            self.assertFalse(modal_upscale_client.configured())

    def test_modal_validation_error_is_useful_without_leaking_input(self):
        response = Mock()
        response.ok = False
        response.status_code = 422
        response.json.return_value = {
            "detail": [{
                "loc": ["body", "request_id"],
                "msg": "String should match pattern",
                "type": "string_pattern_mismatch",
                "input": "secret-signed-url-or-value",
            }]
        }
        with self.assertRaises(modal_upscale_client.ModalUpscaleHTTPError) as caught:
            modal_upscale_client._raise_safe_http_error(response)
        message = str(caught.exception)
        self.assertIn("HTTP 422", message)
        self.assertIn("body.request_id", message)
        self.assertNotIn("secret-signed-url-or-value", message)


if __name__ == "__main__":
    unittest.main()


def test_cancelled_upscale_stops_the_gpu_call(monkeypatch):
    import redis_store as rs
    from smweb import upscale_jobs
    from smweb import modal_upscale_client as client
    monkeypatch.setattr(rs, "_r", lambda: None)
    monkeypatch.setattr(client, "configured", lambda: True)
    monkeypatch.setattr(upscale_jobs.object_store, "presigned_get_url", lambda key, expires: "https://r2/get")
    monkeypatch.setattr(upscale_jobs.object_store, "presigned_put_url", lambda key, expires: "https://r2/put")
    monkeypatch.setattr(upscale_jobs, "POLL_SECONDS", 0)
    jid = "c" * 32
    rs.job_create(jid, {"status": "queued", "kind": "upscale"}, enqueue=False)
    cancelled_calls = []
    monkeypatch.setattr(client, "submit", lambda payload: "fc-test")
    monkeypatch.setattr(client, "cancel", lambda call_id: cancelled_calls.append(call_id) or True)

    def result(call_id):
        rs.job_cancel(jid)  # the user presses "Cancel" while the GPU is working
        return False, {}
    monkeypatch.setattr(client, "result", result)
    upscale_jobs.run(jid, {"source_key": "uploads/a.png", "result_key": "results/a.png", "kind": "upscale"})
    assert cancelled_calls == ["fc-test"]
    assert rs.job_get(jid)["status"] == "cancelled"


def test_upscale_cancelled_in_the_queue_never_reaches_modal(monkeypatch):
    import redis_store as rs
    from smweb import upscale_jobs
    from smweb import modal_upscale_client as client
    monkeypatch.setattr(rs, "_r", lambda: None)
    monkeypatch.setattr(client, "configured", lambda: True)
    jid = "d" * 32
    rs.job_create(jid, {"status": "queued", "kind": "upscale"}, enqueue=False)
    rs.job_cancel(jid)
    monkeypatch.setattr(client, "submit", lambda payload: (_ for _ in ()).throw(AssertionError("submitted")))
    upscale_jobs.run(jid, {"source_key": "uploads/a.png", "result_key": "results/a.png"})
    assert rs.job_get(jid)["status"] == "cancelled"
