"""Deploy explicitly: python -m modal deploy modal_animate.py.

Private experiment, not a public site feature. No R2 secrets are sent to Modal.
"""
import modal
from smweb.animation_selection import isolate_video

from smweb.animation_experiment import (
    DAILY_LIMIT, FPS, INTENSITIES, MAX_INPUT_BYTES, MAX_OUTPUT_BYTES,
    MODEL_ID, MODEL_REVISION, PRESETS, PROFILES, PROTOCOL_VERSION,
    DailyLimitReached, Submission, SubmissionConflict, assess_motion,
    claim_submission, execute_once, motion_prompts, prepare_image,
)

app = modal.App("showcasemaker-animate-experiment")
records = modal.Dict.from_name("showcasemaker-animate-experiment-v1", create_if_missing=True)


def download_model():
    from huggingface_hub import snapshot_download
    snapshot_download(MODEL_ID, revision=MODEL_REVISION, local_dir="/opt/animation-model",
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"])


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
_pipeline = None


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


@app.function(image=web_image, min_containers=0, max_containers=1, timeout=60)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    return create_api()
