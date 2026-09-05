"""Modal GPU service for ShowcaseMaker image, GIF and video upscaling.

Deploy from the repository root with::

    py -m modal deploy modal_upscale.py

The HTTP API is protected by a Modal Proxy Token.  It never receives R2
credentials: the OVH worker supplies short-lived, single-object presigned URLs.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlparse

import modal


APP_NAME = "showcasemaker-upscale"
MAX_INPUT_BYTES = 40 * 1024 * 1024
MAX_VIDEO_SECONDS = 30.0
MAX_VIDEO_FRAMES = 900
MAX_INPUT_PIXELS = 1280 * 720

MODEL_URLS = {
    "general_x2": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
    "general_x4": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "anime_x4": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
}

runtime = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "curl", "libgl1", "libglib2.0-0")
    .pip_install(
        "fastapi[standard]==0.115.6",
        "requests==2.32.3",
        "numpy==1.26.4",
        "Pillow==11.1.0",
        "opencv-python-headless==4.10.0.84",
        "torch==2.1.2",
        "torchvision==0.16.2",
        "addict==2.4.0",
        "future==1.0.0",
        "lmdb==1.5.1",
        "PyYAML==6.0.2",
        "scipy==1.14.1",
        "tqdm==4.67.1",
        "yapf==0.43.0",
    )
    # basicsr 1.4.2 imports a torchvision module removed in newer releases.
    # The pinned torchvision still exposes the implementation under transforms.functional.
    .run_commands(
        # Their legacy setup.py requests a CUDA toolkit independently of
        # PyTorch. Installing without dependency resolution avoids conflicting
        # CUDA 13 wheels; every runtime dependency we use is pinned above.
        "python -m pip install --no-deps basicsr==1.4.2 realesrgan==0.3.0",
        "python - <<'PY'\n"
        "from pathlib import Path\n"
        "p=Path('/usr/local/lib/python3.11/site-packages/basicsr/data/degradations.py')\n"
        "s=p.read_text()\n"
        "s=s.replace('torchvision.transforms.functional_tensor', 'torchvision.transforms.functional')\n"
        "p.write_text(s)\n"
        "PY",
        "mkdir -p /models",
        *[
            f"curl -fL --retry 4 --retry-delay 2 -o /models/{name}.pth {url}"
            for name, url in MODEL_URLS.items()
        ],
    )
)

web_runtime = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi[standard]==0.115.6"
)

app = modal.App(APP_NAME)
calls = modal.Dict.from_name("showcasemaker-upscale-calls", create_if_missing=True)


def _safe_r2_url(value: str) -> str:
    """Allow only HTTPS presigned URLs pointing at Cloudflare R2."""
    parsed = urlparse(str(value or ""))
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host.endswith(".r2.cloudflarestorage.com"):
        raise ValueError("Only Cloudflare R2 presigned URLs are accepted")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials are not accepted")
    return value


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "command failed")[-2000:]
        raise RuntimeError(detail)


def _probe_video(path: Path) -> tuple[float, float, int, int]:
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,avg_frame_rate:format=duration",
            "-of", "json", str(path),
        ],
        check=False, capture_output=True, text=True,
    )
    if completed.returncode:
        raise ValueError("Video metadata could not be read")
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams") or []
    if not streams:
        raise ValueError("No video stream found")
    stream = streams[0]
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    duration = float((payload.get("format") or {}).get("duration") or 0)
    try:
        fps = float(Fraction(str(stream.get("avg_frame_rate") or "0/1")))
    except Exception:
        fps = 0.0
    if width <= 0 or height <= 0 or fps <= 0 or duration <= 0:
        raise ValueError("Incomplete video metadata")
    if width * height > MAX_INPUT_PIXELS:
        raise ValueError("Video input exceeds 1280x720")
    if duration > MAX_VIDEO_SECONDS + 0.25:
        raise ValueError("Video is longer than 30 seconds")
    if duration * fps > MAX_VIDEO_FRAMES + 1:
        raise ValueError("Video contains more than 900 frames")
    return duration, fps, width, height


def _build_upsampler(preset: str, scale: int):
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    if preset == "anime":
        model_scale = 4
        model_key = "anime_x4"
        model = RRDBNet(3, 3, 64, 6, 32, scale=4)
    elif scale == 2:
        model_scale = 2
        model_key = "general_x2"
        model = RRDBNet(3, 3, 64, 23, 32, scale=2)
    else:
        model_scale = 4
        model_key = "general_x4"
        model = RRDBNet(3, 3, 64, 23, 32, scale=4)
    return RealESRGANer(
        scale=model_scale,
        model_path=f"/models/{model_key}.pth",
        model=model,
        tile=384,
        tile_pad=16,
        pre_pad=0,
        half=True,
    )


def _upscale_frames(source_dir: Path, target_dir: Path, upsampler, scale: int) -> int:
    import cv2

    target_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted(source_dir.glob("*.png"))
    if not frames:
        raise ValueError("No frames decoded")
    for frame in frames:
        image = cv2.imread(str(frame), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError(f"Could not decode frame {frame.name}")
        output, _ = upsampler.enhance(image, outscale=scale)
        if not cv2.imwrite(str(target_dir / frame.name), output):
            raise RuntimeError(f"Could not write frame {frame.name}")
    return len(frames)


def _process_still(source: Path, output: Path, upsampler, scale: int) -> None:
    import cv2

    image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError("Image could not be decoded")
    if image.shape[0] * image.shape[1] > 20_000_000:
        raise ValueError("Image exceeds 20 megapixels")
    result, _ = upsampler.enhance(image, outscale=scale)
    if not cv2.imwrite(str(output), result):
        raise RuntimeError("Upscaled image could not be encoded")


def _process_gif(source: Path, output: Path, upsampler, scale: int, work: Path) -> int:
    from PIL import Image

    decoded = work / "gif-in"
    encoded = work / "gif-out"
    decoded.mkdir()
    durations: list[int] = []
    with Image.open(source) as image:
        frame_count = int(getattr(image, "n_frames", 1))
        if frame_count > MAX_VIDEO_FRAMES:
            raise ValueError("GIF contains more than 900 frames")
        if image.width * image.height > MAX_INPUT_PIXELS:
            raise ValueError("GIF input exceeds 1280x720")
        for index in range(frame_count):
            image.seek(index)
            durations.append(max(20, int(image.info.get("duration") or 100)))
            image.convert("RGBA").save(decoded / f"{index:08d}.png")
    _upscale_frames(decoded, encoded, upsampler, scale)
    frames = [Image.open(path).convert("RGBA") for path in sorted(encoded.glob("*.png"))]
    if not frames:
        raise ValueError("GIF contains no frames")
    first, rest = frames[0], frames[1:]
    first.save(
        output, save_all=True, append_images=rest, duration=durations,
        loop=0, disposal=2, optimize=False,
    )
    for frame in frames:
        frame.close()
    return len(frames)


def _process_video(source: Path, output: Path, upsampler, scale: int, work: Path) -> tuple[int, float]:
    duration, fps, _, _ = _probe_video(source)
    decoded = work / "video-in"
    encoded = work / "video-out"
    decoded.mkdir()
    # A constant-frame-rate output is deliberate: it keeps the frame/audio
    # timeline stable and avoids passing user-controlled filter expressions.
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-vf", f"fps={fps:.6f}", "-frames:v", str(MAX_VIDEO_FRAMES),
        str(decoded / "%08d.png"),
    ])
    count = _upscale_frames(decoded, encoded, upsampler, scale)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-framerate", f"{fps:.6f}", "-i", str(encoded / "%08d.png"),
        "-i", str(source), "-map", "0:v:0", "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(output),
    ])
    return count, duration


@app.function(
    image=runtime,
    gpu="L4",
    timeout=3600,
    startup_timeout=600,
    min_containers=0,
    max_containers=2,
    buffer_containers=0,
    scaledown_window=60,
    memory=(4096, 16384),
)
def upscale_job(payload: dict) -> dict:
    import requests

    started = time.monotonic()
    source_url = _safe_r2_url(payload.get("source_url"))
    result_url = _safe_r2_url(payload.get("result_url"))
    media_kind = str(payload.get("media_kind") or "")
    preset = str(payload.get("preset") or "general")
    scale = int(payload.get("scale") or 2)
    if media_kind not in {"image", "gif", "video"}:
        raise ValueError("Unsupported media kind")
    if preset not in {"general", "anime"} or scale not in {2, 4}:
        raise ValueError("Unsupported upscale settings")
    if media_kind == "video" and scale != 2:
        raise ValueError("Video upscale supports 2x only")

    work = Path(tempfile.mkdtemp(prefix="showcasemaker-upscale-"))
    try:
        suffix = {"image": ".png", "gif": ".gif", "video": ".mp4"}[media_kind]
        source = work / f"source{Path(str(payload.get('filename') or suffix)).suffix or suffix}"
        with requests.get(source_url, stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()
            declared = int(response.headers.get("Content-Length") or 0)
            if declared > MAX_INPUT_BYTES:
                raise ValueError("Input exceeds 40 MB")
            total = 0
            with source.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_INPUT_BYTES:
                        raise ValueError("Input exceeds 40 MB")
                    handle.write(chunk)

        upsampler = _build_upsampler(preset, scale)
        if media_kind == "image":
            output = work / "upscaled.png"
            _process_still(source, output, upsampler, scale)
            content_type = "image/png"
            frame_count = 1
            duration = 0.0
        elif media_kind == "gif":
            output = work / "upscaled.gif"
            frame_count = _process_gif(source, output, upsampler, scale, work)
            content_type = "image/gif"
            duration = 0.0
        else:
            output = work / "upscaled.mp4"
            frame_count, duration = _process_video(source, output, upsampler, scale, work)
            content_type = "video/mp4"

        output_size = output.stat().st_size
        with output.open("rb") as handle:
            uploaded = requests.put(result_url, data=handle, timeout=(15, 600))
        uploaded.raise_for_status()
        return {
            "ok": True,
            "content_type": content_type,
            "size": output_size,
            "frames": frame_count,
            "duration": duration,
            "elapsed": round(time.monotonic() - started, 3),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.function(image=web_runtime, min_containers=0, max_containers=2, scaledown_window=30)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field

    web = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    class Submit(BaseModel):
        # Accept both the current hex job IDs and IDs created by the earlier
        # token_urlsafe implementation during a rolling VPS/Modal deployment.
        request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{20,80}$")
        source_url: str
        result_url: str
        filename: str = Field(max_length=160)
        media_kind: str
        preset: str = "general"
        scale: int = 2

    @web.get("/health")
    async def health():
        return {"ok": True, "service": APP_NAME}

    @web.post("/submit")
    async def submit(payload: Submit):
        data = payload.model_dump()
        _safe_r2_url(data["source_url"])
        _safe_r2_url(data["result_url"])
        existing = calls.get(data["request_id"])
        if existing:
            return {"ok": True, "call_id": existing["call_id"], "duplicate": True}
        call = await upscale_job.spawn.aio(data)
        calls[data["request_id"]] = {"call_id": call.object_id, "created": int(time.time())}
        return {"ok": True, "call_id": call.object_id}

    @web.get("/result/{call_id}")
    async def result(call_id: str):
        if not call_id.startswith("fc-") or len(call_id) > 100:
            raise HTTPException(status_code=400, detail="Invalid call id")
        call = modal.FunctionCall.from_id(call_id)
        try:
            value = await call.get.aio(timeout=0)
            return value
        except TimeoutError:
            return JSONResponse({"ok": True, "status": "running"}, status_code=202)
        except modal.exception.OutputExpiredError:
            raise HTTPException(status_code=410, detail="Result expired")

    return web


@app.local_entrypoint()
def main():
    """Small authenticated deployment smoke test without starting a GPU."""
    print(f"Deploy with: modal deploy {Path(__file__).name}")
