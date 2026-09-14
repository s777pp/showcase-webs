"""Deploy explicitly: python -m modal deploy modal_animate.py.

Private experiment, not a public site feature. No R2 secrets are sent to Modal.
"""
import modal
from smweb.animation_selection import isolate_video

from smweb.animation_experiment import (
    DAILY_LIMIT, FPS, INTENSITIES, MAX_INPUT_BYTES, MAX_OUTPUT_BYTES,
    MODEL_ID, MODEL_REVISION, PRESETS, PROFILES, PROTOCOL_VERSION,
    SEGMENTATION_MODEL_ID, SEGMENTATION_MODEL_REVISION, SegmentationRequest,
    DailyLimitReached, Submission, SubmissionConflict, assess_motion,
    claim_submission, execute_once, motion_prompts, prepare_image,
)

app = modal.App("showcasemaker-animate-experiment")
records = modal.Dict.from_name("showcasemaker-animate-experiment-v1", create_if_missing=True)


def download_model():
    from huggingface_hub import snapshot_download
    snapshot_download(MODEL_ID, revision=MODEL_REVISION, local_dir="/opt/animation-model",
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])


def download_segmentation_model():
    from huggingface_hub import snapshot_download
    snapshot_download(SEGMENTATION_MODEL_ID, revision=SEGMENTATION_MODEL_REVISION,
                      local_dir="/opt/clipseg",
                      allow_patterns=["*.json", "*.safetensors", "*.txt"])


web_image = (modal.Image.debian_slim(python_version="3.11")
             .pip_install("fastapi==0.115.6", "pydantic==2.10.6", "Pillow==11.3.0")
             .add_local_python_source("smweb", copy=True))
gpu_image = (modal.Image.debian_slim(python_version="3.11")
             .apt_install("ffmpeg")
             .pip_install("torch==2.8.0", "diffusers==0.36.0", "transformers==4.57.3",
                          "accelerate==1.12.0", "huggingface-hub==0.36.0", "safetensors==0.7.0",
                          "sentencepiece==0.2.1", "ftfy==6.3.1", "Pillow==11.3.0",
                          "requests==2.32.5", "pydantic==2.10.6",
                          "imageio==2.37.2", "imageio-ffmpeg==0.6.0", "numpy==2.2.6")
             .add_local_python_source("smweb", copy=True)
             .run_function(download_model))
segment_image = (modal.Image.debian_slim(python_version="3.11")
                 .pip_install("torch==2.8.0", "transformers==4.57.3",
                              "huggingface-hub==0.36.0", "safetensors==0.7.0",
                              "Pillow==11.3.0", "requests==2.32.5",
                              "pydantic==2.10.6", "numpy==2.2.6")
                 .add_local_python_source("smweb", copy=True)
                 .run_function(download_segmentation_model))
_pipeline = None
_segment_processor = None
_segment_model = None


SEGMENT_PROMPTS = {
    "hair": ("anime character hair", "loose hair strands and hair tips"),
    "cloth": ("character clothing and fabric", "shirt dress sleeves and loose cloth"),
    "breathing": ("character shirt and upper body clothing", "chest clothing fabric and folds"),
    "eyes": ("anime character eyes and eyelids", "eyes and eyelashes"),
}
SEGMENT_RULES = {
    "hair": (.30, .55, .46),
    "cloth": (.28, .52, .56),
    "breathing": (.30, .58, .22),
    "eyes": (.24, .70, .055),
}


def _transparent_mask(mask) -> str:
    import base64
    import io
    import numpy as np
    from PIL import Image

    alpha = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    output = Image.new("RGBA", alpha.size, (255, 255, 255, 0))
    output.putalpha(alpha)
    buffer = io.BytesIO()
    output.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@app.function(image=segment_image, cpu=4, memory=8192,
              min_containers=0, max_containers=1, scaledown_window=60,
              timeout=180, startup_timeout=180, retries=0)
def segment_regions(data: dict) -> dict:
    """Text-guided CPU masks. This never loads or invokes the video model."""
    import io
    import numpy as np
    import requests
    import torch
    from PIL import Image, ImageFilter
    from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor

    global _segment_processor, _segment_model
    payload = SegmentationRequest.model_validate(data)
    with requests.get(payload.source_url, stream=True, allow_redirects=False,
                      timeout=(10, 60)) as response:
        if response.status_code != 200:
            raise ValueError("Segmentation source unavailable")
        content = io.BytesIO()
        for chunk in response.iter_content(65536):
            if content.tell() + len(chunk) > MAX_INPUT_BYTES:
                raise ValueError("Segmentation source too large")
            content.write(chunk)
    image = prepare_image(content.getvalue(), canonical=True)
    if _segment_processor is None or _segment_model is None:
        _segment_processor = CLIPSegProcessor.from_pretrained("/opt/clipseg", local_files_only=True)
        _segment_model = CLIPSegForImageSegmentation.from_pretrained("/opt/clipseg", local_files_only=True)
        _segment_model.eval()

    prompts, owners = [], []
    for target in payload.targets:
        for prompt in SEGMENT_PROMPTS[target]:
            prompts.append(prompt)
            owners.append(target)
    inputs = _segment_processor(text=prompts, images=[image] * len(prompts),
                                padding=True, return_tensors="pt")
    with torch.inference_mode():
        probabilities = _segment_model(**inputs).logits.sigmoid().cpu().numpy()

    scores = {}
    for target in payload.targets:
        positions = [index for index, owner in enumerate(owners) if owner == target]
        scores[target] = np.max(probabilities[positions], axis=0)

    candidates, strengths = {}, {}
    for target, score in scores.items():
        fixed, relative, maximum_area = SEGMENT_RULES[target]
        peak = float(score.max())
        threshold = max(fixed, peak * relative)
        candidate = score >= threshold
        if candidate.mean() > maximum_area:
            threshold = max(threshold, float(np.quantile(score, 1 - maximum_area)))
            candidate = score >= threshold
        candidates[target] = candidate
        strengths[target] = np.clip((score - threshold) / max(.001, peak - threshold), 0, 1)

    # A pixel belongs to one semantic region only. Eyes receive a small boost so
    # they are not swallowed by the surrounding hair mask.
    if len(payload.targets) > 1:
        stack = np.stack([strengths[target] + (.12 if target == "eyes" else 0)
                          for target in payload.targets])
        winners = stack.argmax(axis=0)
        for index, target in enumerate(payload.targets):
            candidates[target] &= winners == index

    masks = []
    for target in payload.targets:
        raw = candidates[target]
        if raw.sum() < 12:
            masks.append({"target": target, "found": False,
                          "confidence": round(float(scores[target].max()), 3)})
            continue
        mask = Image.fromarray((raw.astype(np.uint8) * 255), mode="L")
        mask = mask.filter(ImageFilter.MedianFilter(3))
        if target == "eyes":
            mask = mask.filter(ImageFilter.MaxFilter(3))
        else:
            mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
        binary = np.asarray(mask) >= 128
        confidence = float(scores[target][binary].mean()) if binary.any() else 0.0
        compact = mask.resize((256, 256), Image.Resampling.NEAREST)
        compact_binary = np.asarray(compact) >= 128
        masks.append({"target": target, "found": bool(compact_binary.any()),
                      "width": int(compact.width), "height": int(compact.height),
                      "png": _transparent_mask(compact_binary),
                      "confidence": round(min(1.0, confidence), 3)})
    return {"request_id": payload.request_id, "protocol_version": PROTOCOL_VERSION,
            "model": SEGMENTATION_MODEL_ID, "masks": masks}


@app.function(image=gpu_image, gpu="L40S", cpu=4, memory=49152,
              min_containers=0, max_containers=1, scaledown_window=30,
              timeout=1200, startup_timeout=300, retries=0)
def animate(data: dict) -> dict:
    import time
    # Reserve BEFORE importing/loading torch and the model: Modal can replay a
    # crashed input even with retries=0. A replay must not start another GPU run.
    return execute_once(Submission.model_validate(data), records, generate_video, time.time)


def generate_video(payload: Submission, progress) -> dict:
    import io
    import tempfile
    from pathlib import Path

    import requests
    import torch
    from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
    from diffusers.utils import export_to_video

    global _pipeline
    try:
        progress("download")
        with requests.get(payload.source_url, stream=True, allow_redirects=False, timeout=(10, 60)) as response:
            if response.status_code != 200:
                return {"status": "error", "code": "source_unavailable"}
            content = io.BytesIO()
            for chunk in response.iter_content(65536):
                if content.tell() + len(chunk) > MAX_INPUT_BYTES:
                    return {"status": "error", "code": "image_too_large"}
                content.write(chunk)
        image = prepare_image(content.getvalue(), payload.matte, canonical=payload.selection is not None)
        if _pipeline is None:
            progress("load_model")
            vae = AutoencoderKLWan.from_pretrained("/opt/animation-model", subfolder="vae",
                                                  torch_dtype=torch.float32, local_files_only=True)
            # TI2V-5B needs expanded timesteps and does not use the 14B CLIP image encoder.
            pipeline = WanImageToVideoPipeline.from_pretrained(
                "/opt/animation-model", vae=vae, image_encoder=None, image_processor=None,
                expand_timesteps=True, torch_dtype=torch.bfloat16, local_files_only=True,
            )
            pipeline.enable_model_cpu_offload()
            pipeline.vae.enable_tiling()
            pipeline.set_progress_bar_config(disable=True)
            _pipeline = pipeline
        frames, steps = PROFILES[payload.quality]
        prompt, negative = motion_prompts(payload, image)
        progress("generate", step=0, total=steps)

        def step_finished(pipeline, step, timestep, callback_kwargs):
            if step == 0 or (step + 1) % 5 == 0 or step + 1 == steps:
                progress("generate", step=step + 1, total=steps)
            return callback_kwargs

        with torch.inference_mode():
            video = _pipeline(image=image, prompt=prompt, negative_prompt=negative,
                              width=image.width, height=image.height, num_frames=frames,
                              num_inference_steps=steps, guidance_scale=5.0,
                              generator=torch.Generator(device="cuda").manual_seed(payload.seed),
                              callback_on_step_end=step_finished).frames[0]
        progress("isolate")
        video = isolate_video(video, image, payload.selection)
        progress("check_motion")
        motion = assess_motion(video, image)
        progress("encode")
        with tempfile.TemporaryDirectory(prefix="animation-") as directory:
            result = Path(directory) / "result.mp4"
            export_to_video(video, str(result), fps=FPS, macro_block_size=1)
            size = result.stat().st_size
            if not 0 < size <= MAX_OUTPUT_BYTES:
                return {"status": "error", "code": "output_too_large"}
            with result.open("rb") as stream:
                progress("upload")
                response = requests.put(payload.result_url, data=stream,
                                        headers={"Content-Type": "video/mp4"},
                                        allow_redirects=False, timeout=(10, 120))
            if not 200 <= response.status_code < 300:
                return {"status": "error", "code": "upload_failed"}
        return {"status": "done", "width": image.width, "height": image.height,
                "frames": frames, "fps": FPS, "bytes": size, "seed": payload.seed,
                "preset": payload.preset, "intensity": payload.intensity,
                "quality": payload.quality, "motion": motion,
                "masked": bool(payload.selection and payload.selection.lock_outside)}
    except torch.cuda.OutOfMemoryError:
        _pipeline = None
        torch.cuda.empty_cache()
        return {"status": "error", "code": "gpu_memory"}
    except Exception as error:
        # Neither signed URLs nor pipeline/HTTP exception bodies leave this boundary.
        print(f"[animation {payload.request_id}] failed ({type(error).__name__})", flush=True)
        return {"status": "error", "code": "generation_failed"}


def create_api():
    import time
    from fastapi import FastAPI, HTTPException
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    service = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    class AsyncRecords:
        async def get(self, key):
            return await records.get.aio(key)

        async def put(self, key, value, *, skip_if_exists=False):
            return await records.put.aio(key, value, skip_if_exists=skip_if_exists)

    @service.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse({"detail": "Invalid animation request"}, status_code=422)

    @service.get("/health")
    async def health():
        return {"experiment": True, "model": MODEL_ID, "daily_limit": DAILY_LIMIT,
                "presets": list(PRESETS), "intensities": list(INTENSITIES),
                "fps": FPS, "protocol_version": PROTOCOL_VERSION}

    @service.post("/segment")
    async def segment(payload: SegmentationRequest):
        try:
            result = await segment_regions.remote.aio(payload.model_dump())
            if not isinstance(result, dict) or result.get("request_id") != payload.request_id:
                raise ValueError("Invalid segmentation result")
            return result
        except Exception as error:
            print(f"[segmentation {payload.request_id}] failed ({type(error).__name__})", flush=True)
            raise HTTPException(502, "Segmentation failed") from None

    @service.post("/submit")
    async def submit(payload: Submission):
        async def spawn(data):
            call = await animate.spawn.aio(data)
            return call.object_id
        try:
            call_id = await claim_submission(payload, AsyncRecords(), spawn, time.time())
        except DailyLimitReached:
            raise HTTPException(429, "Daily experiment limit reached") from None
        except SubmissionConflict:
            raise HTTPException(409, "Request reserved; check status, do not automatically resubmit") from None
        return {"request_id": payload.request_id, "call_id": call_id}

    @service.get("/result/{request_id}")
    async def result(request_id: str):
        from smweb.animation_experiment import keys
        try:
            keys(request_id)
        except ValueError:
            raise HTTPException(400, "Invalid request id") from None
        record = await records.get.aio(f"request:{request_id}")
        if not record:
            raise HTTPException(404, "Unknown request")
        if time.time() - record["created_at"] > 86400:
            raise HTTPException(410, "Experiment request expired")
        if record["state"] == "limit":
            raise HTTPException(429, "Daily experiment limit reached")
        if not record.get("call_id"):
            # An ambiguous submission is not proof that no GPU task was spawned.
            return JSONResponse({"status": record["state"]}, status_code=202)
        if await records.get.aio(f"cancel:{request_id}"):
            return {"status": "error", "code": "cancelled"}
        execution = await records.get.aio(f"execution:{request_id}") or {}
        if execution.get("output"):
            return execution["output"]
        try:
            output = await modal.FunctionCall.from_id(record["call_id"]).get.aio(timeout=0)
        except TimeoutError:
            progress = {key: execution[key] for key in ("stage", "step", "total", "started_at", "updated_at") if key in execution}
            return JSONResponse({"status": "running", **progress}, status_code=202)
        except Exception:
            return {"status": "error", "code": "remote_task_failed"}
        return output

    @service.post("/cancel/{request_id}")
    async def cancel(request_id: str):
        from smweb.animation_experiment import keys
        try:
            keys(request_id)
        except ValueError:
            raise HTTPException(400, "Invalid request id") from None
        record = await records.get.aio(f"request:{request_id}")
        if not record or not record.get("call_id"):
            raise HTTPException(404, "No cancellable request")
        execution = await records.get.aio(f"execution:{request_id}") or {}
        if execution.get("output"):
            return {"status": "already_finished"}
        # Only the call mapped to this experiment request, never an arbitrary call.
        # Fence its next execution before terminating a running GPU container.
        await records.put.aio(f"execution:{request_id}",
                              {"output": {"status": "error", "code": "cancelled"}}, skip_if_exists=True)
        await records.put.aio(f"cancel:{request_id}", True)
        try:
            await modal.FunctionCall.from_id(record["call_id"]).cancel.aio(terminate_containers=True)
        except Exception:
            raise HTTPException(503, "Cancellation uncertain; inspect the animation app dashboard") from None
        return {"status": "cancelled"}

    return service


@app.function(image=web_image, min_containers=0, max_containers=1, timeout=240)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    return create_api()
