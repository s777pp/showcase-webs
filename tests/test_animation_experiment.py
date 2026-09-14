import asyncio
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urlencode

from PIL import Image, ImageDraw
from pydantic import ValidationError

from smweb.animation_experiment import (
    DAILY_LIMIT, MAX_INPUT_BYTES, DailyLimitReached, Submission,
    SubmissionConflict, assess_motion, chroma_channel, claim_submission,
    execute_once, keys, motion_prompts, prepare_image, segmentation_key,
    SegmentationRequest,
)
from smweb.modal_animation_client import AnimationClient, AnimationServiceError


def payload(request_id="a" * 32, **overrides):
    query = urlencode({"X-Amz-Algorithm": "AWS4-HMAC-SHA256", "X-Amz-Signature": "b" * 64,
                       "X-Amz-Credential": "private-credential", "X-Amz-Date": "20260914T120000Z",
                       "X-Amz-Expires": "7200"})
    source, result = keys(request_id)
    base = "https://" + "c" * 32 + ".r2.cloudflarestorage.com/private-bucket/"
    return {"request_id": request_id, "source_url": base + source + "?" + query,
            "result_url": base + result + "?" + query, **overrides}


class MemoryRecords:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def put(self, key, value, *, skip_if_exists=False):
        if skip_if_exists and key in self.data:
            return False
        self.data[key] = value
        return True


class AnimationInputTests(unittest.TestCase):
    def test_exact_private_storage_paths_only(self):
        good = payload()
        self.assertEqual(Submission(**good).preset, "alive")
        for url in ("http://127.0.0.1/private", good["source_url"].replace("/source.png", "/other.png"),
                    good["source_url"].replace("https://", "https://name:secret@"),
                    good["source_url"].replace(".r2.cloudflarestorage.com", ".r2.cloudflarestorage.com.evil.test"),
                    good["source_url"] + "#fragment", good["source_url"] + "&X-Amz-Expires=60"):
            with self.subTest(url_type=url[:25]), self.assertRaises(ValidationError):
                Submission(**{**good, "source_url": url})

    def test_options_and_result_cannot_escape_request(self):
        for overrides in ({"result_url": payload("f" * 32)["result_url"]}, {"quality": "unlimited"},
                          {"preset": "custom"}, {"prompt": "ignored"}, {"seed": -1},
                          {"matte": "invalid"}, {"intensity": "unlimited"}, {"num_inference_steps": 9999}):
            with self.subTest(overrides=list(overrides)), self.assertRaises(ValidationError):
                Submission(**payload(**overrides))

    def test_fingerprint_ignores_expiring_signature_not_motion(self):
        first = Submission(**payload())
        refreshed = payload()
        refreshed["source_url"] = refreshed["source_url"].replace("b" * 64, "d" * 64)
        self.assertEqual(first.fingerprint(), Submission(**refreshed).fingerprint())
        self.assertNotEqual(first.fingerprint(), Submission(**payload(preset="water")).fingerprint())
        self.assertNotEqual(first.fingerprint(), Submission(**payload(intensity="strong")).fingerprint())

    def test_segmentation_request_is_bound_to_its_private_source(self):
        request_id="d"*32;query=urlencode({"X-Amz-Algorithm":"AWS4-HMAC-SHA256","X-Amz-Signature":"e"*64,"X-Amz-Credential":"private","X-Amz-Date":"20260914T120000Z","X-Amz-Expires":"600"})
        url="https://"+"c"*32+".r2.cloudflarestorage.com/private-bucket/"+segmentation_key(request_id)+"?"+query
        request=SegmentationRequest(request_id=request_id,source_url=url,targets=['hair','cloth'])
        self.assertEqual(request.targets,['hair','cloth'])
        with self.assertRaises(ValidationError):
            SegmentationRequest(request_id=request_id,source_url=url.replace('/source.png','/other.png'),targets=['hair'])
        with self.assertRaises(ValidationError):
            SegmentationRequest(request_id=request_id,source_url=url,targets=['hair','hair'])


class AnimationMotionTests(unittest.TestCase):
    def test_prompt_requests_visible_motion_not_frozen_pose(self):
        image = Image.new("RGB", (128, 128), "gray")
        prompt, negative = motion_prompts(Submission(**payload()), image)
        self.assertIn("head tilt", prompt)
        self.assertNotIn("minimal motion", prompt)
        self.assertNotIn("pose unchanged", prompt)
        self.assertIn("static image", negative)

    def test_breeze_works_with_short_hair_and_intensity_is_distinct(self):
        image = Image.new("RGB", (128, 128), "gray")
        gentle = motion_prompts(Submission(**payload(preset="breeze", intensity="gentle")), image)[0]
        strong = motion_prompts(Submission(**payload(preset="breeze", intensity="strong")), image)[0]
        self.assertIn("hair is short", gentle)
        self.assertNotEqual(gentle, strong)

    def test_custom_prompt_is_preserved(self):
        text = "Ocean waves flow continuously."
        prompt = motion_prompts(Submission(**payload(preset="custom", prompt=text)), Image.new("RGB", (128, 128)))[0]
        self.assertIn(text, prompt)
        self.assertNotIn("blinks", prompt)

    def test_chroma_detection_is_conservative(self):
        self.assertEqual(chroma_channel(Image.new("RGB", (128, 128), "lime")), 1)
        self.assertEqual(chroma_channel(Image.new("RGB", (128, 128), "blue")), 2)
        self.assertIsNone(chroma_channel(Image.new("RGB", (128, 128), "gray")))

    def test_static_and_global_brightness_are_not_motion(self):
        frames = []
        for brightness in range(30, 110, 4):
            image = Image.new("RGB", (128, 128), (brightness,) * 3)
            ImageDraw.Draw(image).rectangle((30, 30, 90, 90), fill=(brightness + 100,) * 3)
            frames.append(image)
        self.assertEqual(assess_motion([frames[0]] * 81, frames[0])["status"], "low_motion")
        self.assertEqual(assess_motion(frames, frames[0])["status"], "low_motion")

    def test_moving_object_is_detected_and_sampling_is_bounded(self):
        frames = []
        for index in range(81):
            image = Image.new("RGB", (128, 128))
            x = (index * 3) % 80
            ImageDraw.Draw(image).rectangle((x, 30, x + 40, 90), fill="white")
            frames.append(image)
        report = assess_motion(frames, frames[0])
        self.assertEqual(report["status"], "motion_detected")
        self.assertLessEqual(report["sampled_frames"], 21)

    def test_chroma_brightness_changes_do_not_count_as_foreground_motion(self):
        frames = []
        for green in range(100, 250, 7):
            image = Image.new("RGB", (128, 128), (0, green, 0))
            ImageDraw.Draw(image).rectangle((30, 30, 90, 90), fill="gray")
            frames.append(image)
        report = assess_motion(frames, frames[0])
        self.assertTrue(report["chroma_excluded"])
        self.assertEqual(report["status"], "low_motion")

    def test_insufficient_frames_or_foreground_is_inconclusive(self):
        image = Image.new("RGB", (128, 128), "gray")
        self.assertEqual(assess_motion([image], image)["status"], "inconclusive")
        green = Image.new("RGB", (128, 128), "lime")
        self.assertEqual(assess_motion([green] * 10, green)["status"], "inconclusive")


class AnimationExecutionTests(unittest.TestCase):
    def setUp(self):
        self.data = {}
        def put(key, value, *, skip_if_exists=False):
            if skip_if_exists and key in self.data:
                return False
            self.data[key] = value
            return True
        self.records = SimpleNamespace(get=self.data.get, put=put)
        self.payload = Submission(**payload())

    def test_completed_execution_is_not_generated_twice(self):
        generate = Mock(return_value={"status": "done", "motion": {"status": "low_motion"}})
        for _ in range(2):
            result = execute_once(self.payload, self.records, generate, lambda: 100)
            self.assertEqual(result["status"], "done")
        generate.assert_called_once()

    def test_crashed_execution_is_fenced_before_model_loading(self):
        self.data["execution:" + self.payload.request_id] = {"stage": "load_model", "started_at": 90}
        generate = Mock()
        result = execute_once(self.payload, self.records, generate, lambda: 100)
        self.assertEqual(result["code"], "execution_not_repeated")
        generate.assert_not_called()

    def test_errors_do_not_leak_urls_or_retry(self):
        generate = Mock(side_effect=RuntimeError("PRIVATE_SIGNED_URL"))
        with patch("builtins.print") as printer:
            first = execute_once(self.payload, self.records, generate, lambda: 100)
            second = execute_once(self.payload, self.records, generate, lambda: 101)
        self.assertEqual(first, second)
        self.assertNotIn("PRIVATE_SIGNED_URL", str(printer.call_args_list))
        generate.assert_called_once()

    def test_progress_is_recorded_without_payload(self):
        def generate(payload, progress):
            progress("generate", step=5, total=30)
            state = self.data["execution:" + payload.request_id]
            self.assertEqual(state["step"], 5)
            self.assertNotIn("source_url", state)
            return {"status": "done"}
        with patch("builtins.print"):
            execute_once(self.payload, self.records, generate, lambda: 100)

class AnimationPreparedImageTests(unittest.TestCase):
    def test_image_preserves_proportions_and_does_not_stretch(self):
        raw = io.BytesIO()
        Image.new("RGB", (200, 600), "red").save(raw, format="PNG")
        image = prepare_image(raw.getvalue())
        self.assertEqual(image.mode, "RGB")
        self.assertLessEqual(max(image.size), 1280)
        self.assertEqual(image.width % 32, 0)
        self.assertEqual(image.height % 32, 0)
        self.assertAlmostEqual(image.width / image.height, 1 / 3, delta=.04)
        self.assertEqual(image.getpixel((image.width // 2, image.height // 2)), (255, 0, 0))

    def test_transparent_input_has_explicit_matte(self):
        raw = io.BytesIO()
        Image.new("RGBA", (128, 128), (255, 0, 0, 0)).save(raw, format="PNG")
        image = prepare_image(raw.getvalue(), "#123456")
        self.assertEqual(image.getpixel((100, 100)), (18, 52, 86))

    def test_invalid_large_and_animated_media_rejected(self):
        animation = io.BytesIO()
        Image.new("RGB", (128, 128), "red").save(animation, format="GIF")
        for raw in (b"not image", b"x" * (MAX_INPUT_BYTES + 1), animation.getvalue()):
            with self.assertRaises(ValueError):
                prepare_image(raw)
        image = io.BytesIO()
        Image.new("RGB", (20, 20), "red").save(image, format="PNG")
        with self.assertRaises(ValueError):
            prepare_image(image.getvalue())


class AnimationSubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_repeat_spawns_once(self):
        records, spawn = MemoryRecords(), AsyncMock(return_value="fc-test")
        submission = Submission(**payload())
        self.assertEqual(await claim_submission(submission, records, spawn, 1789387200), "fc-test")
        self.assertEqual(await claim_submission(submission, records, spawn, 1789387201), "fc-test")
        self.assertEqual(spawn.await_count, 1)
        with self.assertRaises(SubmissionConflict):
            await claim_submission(Submission(**payload(preset="water")), records, spawn, 1789387202)

    async def test_concurrent_repeat_cannot_spawn_twice(self):
        records = MemoryRecords()
        started, release = asyncio.Event(), asyncio.Event()

        async def spawn(data):
            started.set()
            await release.wait()
            return "fc-test"

        submission = Submission(**payload())
        first = asyncio.create_task(claim_submission(submission, records, spawn, 1789387200))
        await started.wait()
        with self.assertRaises(SubmissionConflict):
            await claim_submission(submission, records, spawn, 1789387200)
        release.set()
        self.assertEqual(await first, "fc-test")

    async def test_daily_limit_and_next_utc_day(self):
        records, spawn = MemoryRecords(), AsyncMock(return_value="fc-test")
        for index in range(DAILY_LIMIT):
            await claim_submission(Submission(**payload(f"{index:032x}")), records, spawn, 1789387200)
        with self.assertRaises(DailyLimitReached):
            await claim_submission(Submission(**payload("e" * 32)), records, spawn, 1789387200)
        self.assertEqual(spawn.await_count, DAILY_LIMIT)
        await claim_submission(Submission(**payload("f" * 32)), records, spawn, 1789387200 + 86400)
        self.assertEqual(spawn.await_count, DAILY_LIMIT + 1)

    async def test_uncertain_spawn_is_not_retried(self):
        records, spawn = MemoryRecords(), AsyncMock(side_effect=RuntimeError("PRIVATE_URL"))
        submission = Submission(**payload())
        for _ in range(2):
            with self.assertRaises(SubmissionConflict) as caught:
                await claim_submission(submission, records, spawn, 1789387200)
            self.assertNotIn("PRIVATE_URL", str(caught.exception))
        self.assertEqual(spawn.await_count, 1)
        self.assertEqual(records.data["request:" + submission.request_id]["state"], "unknown")


class AnimationClientTests(unittest.TestCase):
    env = {"MODAL_ANIMATE_URL": "https://owner--animation-api.modal.run",
           "MODAL_PROXY_TOKEN_ID": "wk-private", "MODAL_PROXY_TOKEN_SECRET": "ws-private"}

    def test_endpoint_rejected_before_credentials_sent(self):
        for url in ("https://evil.example", "https://owner--api.modal.run@evil.example",
                    "https://name:pass@owner--api.modal.run", "https://owner--api.modal.run/path",
                    "https://owner--api.modal.run?url=secret", "https://["):
            with patch.dict("os.environ", {**self.env, "MODAL_ANIMATE_URL": url}), self.assertRaises(AnimationServiceError):
                AnimationClient()

    @patch("smweb.modal_animation_client.requests.request")
    def test_no_redirects_and_safe_error(self, request):
        request.return_value = Mock(status_code=422, text="PRIVATE_URL")
        with patch.dict("os.environ", self.env):
            with self.assertRaises(AnimationServiceError) as caught:
                AnimationClient().submit(payload())
        self.assertNotIn("PRIVATE_URL", str(caught.exception))
        self.assertNotIn("ws-private", str(caught.exception))
        self.assertFalse(request.call_args.kwargs["allow_redirects"])


@unittest.skipUnless(importlib.util.find_spec("modal"), "Optional Modal SDK not installed")
class AnimationAPITests(unittest.TestCase):
    def setUp(self):
        import modal_animate
        from fastapi.testclient import TestClient
        self.module = modal_animate
        self.client = TestClient(modal_animate.create_api())

    def test_health_does_not_spawn_gpu(self):
        with patch.object(self.module, "animate") as gpu:
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["daily_limit"], DAILY_LIMIT)
        self.assertEqual(response.json()["protocol_version"], 5)
        gpu.spawn.aio.assert_not_called()

    def test_validation_does_not_echo_signed_url(self):
        response = self.client.post("/submit", json={**payload(), "seed": -1})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private-credential", response.text)
        self.assertNotIn("X-Amz", response.text)

    def test_segmentation_uses_cpu_function_not_animation_gpu(self):
        request_id="d"*32;query=urlencode({"X-Amz-Algorithm":"AWS4-HMAC-SHA256","X-Amz-Signature":"e"*64,"X-Amz-Credential":"private","X-Amz-Date":"20260914T120000Z","X-Amz-Expires":"600"})
        url="https://"+"c"*32+".r2.cloudflarestorage.com/private-bucket/"+segmentation_key(request_id)+"?"+query
        cpu=SimpleNamespace(remote=SimpleNamespace(aio=AsyncMock(return_value={'request_id':request_id,'protocol_version':5,'model':'CIDAS/clipseg-rd64-refined','masks':[]})))
        with patch.object(self.module,'segment_regions',cpu),patch.object(self.module,'animate') as gpu:
            response=self.client.post('/segment',json={'request_id':request_id,'source_url':url,'targets':['hair']})
        self.assertEqual(response.status_code,200);cpu.remote.aio.assert_awaited_once();gpu.spawn.aio.assert_not_called()

    def test_submit_and_poll_pending(self):
        memory = MemoryRecords()
        fake_records = SimpleNamespace(get=SimpleNamespace(aio=memory.get), put=SimpleNamespace(aio=memory.put))
        gpu = SimpleNamespace(spawn=SimpleNamespace(aio=AsyncMock(return_value=SimpleNamespace(object_id="fc-test"))))
        with patch.object(self.module, "records", fake_records), patch.object(self.module, "animate", gpu):
            first = self.client.post("/submit", json=payload())
            second = self.client.post("/submit", json=payload())
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(gpu.spawn.aio.await_count, 1)
            call = SimpleNamespace(get=SimpleNamespace(aio=AsyncMock(side_effect=TimeoutError)))
            with patch.object(self.module.modal.FunctionCall, "from_id", return_value=call):
                response = self.client.get("/result/" + "a" * 32)
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json()["status"], "running")

    def test_poll_reports_progress_without_private_input(self):
        memory = MemoryRecords()
        request_id = "a" * 32
        memory.data["request:" + request_id] = {"created_at": __import__("time").time(), "state": "submitted", "call_id": "fc-test"}
        memory.data["execution:" + request_id] = {"stage": "generate", "step": 10, "total": 30, "source_url": "PRIVATE_URL"}
        fake = SimpleNamespace(get=SimpleNamespace(aio=memory.get))
        call = SimpleNamespace(get=SimpleNamespace(aio=AsyncMock(side_effect=TimeoutError)))
        with patch.object(self.module, "records", fake), patch.object(self.module.modal.FunctionCall, "from_id", return_value=call):
            response = self.client.get("/result/" + request_id)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["step"], 10)
        self.assertNotIn("PRIVATE_URL", response.text)

    def test_cancel_only_mapped_experiment_call(self):
        memory = MemoryRecords()
        request_id = "a" * 32
        memory.data["request:" + request_id] = {"call_id": "fc-this-experiment"}
        fake = SimpleNamespace(get=SimpleNamespace(aio=memory.get), put=SimpleNamespace(aio=memory.put))
        call = SimpleNamespace(cancel=SimpleNamespace(aio=AsyncMock()))
        with patch.object(self.module, "records", fake), patch.object(self.module.modal.FunctionCall, "from_id", return_value=call) as lookup:
            response = self.client.post("/cancel/" + request_id)
        self.assertEqual(response.json()["status"], "cancelled")
        lookup.assert_called_once_with("fc-this-experiment")
        call.cancel.aio.assert_awaited_once_with(terminate_containers=True)
        self.assertTrue(memory.data["cancel:" + request_id])
        self.assertEqual(memory.data["execution:" + request_id]["output"]["code"], "cancelled")

    def test_unknown_cancel_does_not_touch_gpu(self):
        fake = SimpleNamespace(get=SimpleNamespace(aio=AsyncMock(return_value=None)))
        with patch.object(self.module, "records", fake), patch.object(self.module.modal.FunctionCall, "from_id") as lookup:
            response = self.client.post("/cancel/" + "a" * 32)
        self.assertEqual(response.status_code, 404)
        lookup.assert_not_called()


class AnimationDownloadTests(unittest.TestCase):
    def test_download_does_not_overwrite_and_closes_stream(self):
        from scripts.test_modal_animation import save_result
        data = b"\x00\x00\x00\x18ftypisom" + b"test" * 10
        storage = Mock()
        storage.PRIVATE_BUCKET = "private"
        storage.client.return_value.get_object.return_value = {"Body": io.BytesIO(data), "ContentLength": len(data)}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test.mp4"
            save_result(storage, "a" * 32, output)
            self.assertEqual(output.read_bytes(), data)
            storage.client.return_value.get_object.return_value["Body"] = io.BytesIO(data)
            with self.assertRaises(FileExistsError):
                save_result(storage, "a" * 32, output)
            self.assertEqual(output.read_bytes(), data)

    def test_invalid_output_new_file_removed(self):
        from scripts.test_modal_animation import save_result
        storage = Mock()
        storage.client.return_value.get_object.return_value = {"Body": io.BytesIO(b"not video"), "ContentLength": 9}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test.mp4"
            with self.assertRaises(ValueError):
                save_result(storage, "a" * 32, output)
            self.assertFalse(output.exists())


class AnimationCommandTests(unittest.TestCase):
    def test_old_service_rejected_before_upload(self):
        from scripts.test_modal_animation import main, SafeTestError
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "input.png"
            Image.new("RGB", (128, 128), "red").save(image)
            with patch("smweb.modal_animation_client.AnimationClient") as client, \
                 patch("smweb.object_store.configured", return_value=True), \
                 patch("smweb.object_store.presigned_get_url", return_value=payload()["source_url"]), \
                 patch("smweb.object_store.presigned_put_url", return_value=payload()["result_url"]), \
                 patch("scripts.test_modal_animation.uuid.uuid4", return_value=SimpleNamespace(hex="a" * 32)), \
                 patch("smweb.object_store.put_bytes") as upload, patch("builtins.print"):
                client.return_value.health.return_value = {"experiment": True}
                with self.assertRaises(SafeTestError):
                    main(["--image", str(image), "--confirm-cost", "--env-file", str(Path(directory) / ".env")])
            upload.assert_not_called()
            client.return_value.submit.assert_not_called()

    def test_weak_motion_warns_without_retry(self):
        from scripts.test_modal_animation import main
        with tempfile.TemporaryDirectory() as directory:
            with patch("smweb.modal_animation_client.AnimationClient") as client, \
                 patch("smweb.object_store.configured", return_value=True), \
                 patch("smweb.object_store.delete"), patch("scripts.test_modal_animation.save_result"), \
                 patch("builtins.print") as printer:
                client.return_value.result.return_value = (True, {"status": "done", "motion": {"status": "low_motion"}})
                main(["--resume", "a" * 32, "--output", str(Path(directory) / "result.mp4")])
            self.assertIn("weak foreground motion", str(printer.call_args_list))
            client.return_value.submit.assert_not_called()

    def test_default_is_local_only(self):
        from scripts.test_modal_animation import main
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "input.png"
            Image.new("RGB", (128, 128), "red").save(image)
            with patch("smweb.modal_animation_client.AnimationClient") as client, \
                 patch("smweb.object_store.put_bytes") as upload, patch("builtins.print"):
                self.assertEqual(main(["--image", str(image), "--env-file", str(Path(directory) / ".env")]), 0)
            client.assert_not_called()
            upload.assert_not_called()

    def test_resume_does_not_submit_a_new_gpu_task(self):
        from scripts.test_modal_animation import main
        with tempfile.TemporaryDirectory() as directory:
            with patch("smweb.modal_animation_client.AnimationClient") as client, \
                 patch("smweb.object_store.configured", return_value=True), \
                 patch("smweb.object_store.delete") as cleanup, \
                 patch("smweb.object_store.put_bytes") as upload, \
                 patch("scripts.test_modal_animation.save_result") as save, patch("builtins.print"):
                client.return_value.result.return_value = (True, {"status": "done"})
                self.assertEqual(main(["--resume", "a" * 32, "--output", str(Path(directory) / "result.mp4"),
                                       "--env-file", str(Path(directory) / ".env")]), 0)
            client.return_value.submit.assert_not_called()
            upload.assert_not_called()
            save.assert_called_once()
            self.assertEqual(cleanup.call_count, 2)
            self.assertTrue(all(call.kwargs["public"] is False for call in cleanup.call_args_list))


if __name__ == "__main__":
    unittest.main()
