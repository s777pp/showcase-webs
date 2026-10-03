"""Modal GPU service for ShowcaseMaker AI background removal (BiRefNet).

Deploy from the repository root with::

    py -m modal deploy modal_bg_remove.py

Smoke test without deploying (prints cold/warm timings)::

    py -m modal run modal_bg_remove.py --path static/img/samples/sample-art.webp

The HTTP API is protected by a Modal Proxy Token (the same token the upscale
service uses). The OVH worker posts the image bytes and receives a transparent
PNG; the service never sees R2 keys, user ids or any other credentials.

Model: BiRefNet general (MIT licence), the ONNX export rembg publishes; the
weights are baked into the image at build time. rembg itself is NOT used at
runtime: importing it compiles pymatting with numba, which cost ~100 s on every
cold start. The pre/post-processing below is the same as rembg's BiRefNet session.
"""
# No "from __future__ import annotations": FastAPI resolves the route annotations at runtime
# and Request is imported inside api(), so a string annotation turned it into a query parameter.
import io
import os
import time

import modal


APP_NAME = "showcasemaker-bg-remove"
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-general-epoch_244.onnx"
MODEL_MD5 = "7a35a0141cbbc80de11d9c9a28f52697"
MODEL_PATH = "/models/birefnet-general.onnx"
INPUT_SIZE = 1024
MAX_INPUT_BYTES = 22 * 1024 * 1024
MAX_PIXELS = 10_000_000

runtime = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl")
    .pip_install(
        "fastapi[standard]==0.115.6",
        "numpy==2.3.5",
        "Pillow==12.1.0",
        # CUDA 12 + cuDNN 9 come as pip wheels and are loaded by preload_dlls().
        "onnxruntime-gpu[cuda,cudnn]==1.23.2",
        # The newest cuDNN (9.27) fails on T4 ("HEURISTIC_QUERY_FAILED") and onnxruntime
        # silently falls back to CPU. 9.8 is the version this onnxruntime was built with.
        "nvidia-cudnn-cu12==9.8.0.87",
    )
    .env({"OMP_NUM_THREADS": "2"})
    .run_commands(
        "mkdir -p /models",
        f"curl -fL --retry 4 --retry-delay 2 -o {MODEL_PATH} {MODEL_URL}",
        f"echo '{MODEL_MD5}  {MODEL_PATH}' | md5sum -c -",
    )
)

app = modal.App(APP_NAME)


@app.cls(
    image=runtime,
    gpu=os.environ.get("BG_REMOVE_GPU", "T4"),
    timeout=180,
    min_containers=0,
    max_containers=2,
    scaledown_window=60,
)
class Remover:
    @modal.enter()
    def load(self) -> None:
        import onnxruntime as ort
        from PIL import Image

        started = time.perf_counter()
        ort.preload_dlls()
        # The default EXHAUSTIVE cuDNN search benchmarks every convolution on the first run;
        # the heuristic pick is close enough and keeps the first image fast.
        cuda = ("CUDAExecutionProvider", {"cudnn_conv_algo_search": "HEURISTIC"})
        self.session = ort.InferenceSession(MODEL_PATH, providers=[cuda, "CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.providers = list(self.session.get_providers())
        loaded = time.perf_counter()
        self._mask(Image.new("RGB", (64, 64), "white"))  # warm-up: CUDA kernels, cuDNN plans
        print(f"[bg-remove] providers={self.providers} load={loaded - started:.1f}s "
              f"warmup={time.perf_counter() - loaded:.1f}s")

    def _mask(self, rgb):
        """Alpha mask in the source size (same maths as rembg's BiRefNet session)."""
        import numpy as np
        from PIL import Image

        im = np.asarray(rgb.resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.LANCZOS), dtype=np.float32)
        im = im / max(float(im.max()), 1e-6)
        im = (im - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
        tensor = np.ascontiguousarray(im.transpose(2, 0, 1)[None], dtype=np.float32)
        pred = self.session.run(None, {self.input_name: tensor})[0][0, 0]
        pred = 1.0 / (1.0 + np.exp(-pred))
        low, high = float(pred.min()), float(pred.max())
        pred = (pred - low) / max(high - low, 1e-6)
        mask = Image.fromarray((pred * 255).astype("uint8"), mode="L")
        return mask.resize(rgb.size, Image.Resampling.LANCZOS)

    def _cut(self, data: bytes) -> bytes:
        from PIL import Image, ImageChops, ImageOps

        if not data or len(data) > MAX_INPUT_BYTES:
            raise ValueError("image_too_large")
        with Image.open(io.BytesIO(data)) as source:
            if int(getattr(source, "n_frames", 1) or 1) != 1:
                raise ValueError("image_only")
            if source.width * source.height > MAX_PIXELS:
                raise ValueError("image_too_large")
            image = ImageOps.exif_transpose(source).convert("RGBA")
        mask = self._mask(image.convert("RGB"))
        # Keep the source's own transparency (a PNG that was already partly cut out).
        if image.getextrema()[3][0] < 255:
            mask = ImageChops.multiply(mask, image.getchannel("A"))
        image.putalpha(mask)  # true colours + alpha (rembg's default darkens soft edges)
        # Fully transparent pixels carry no colour: smaller PNG, nothing hidden in the "empty" area.
        image = Image.composite(image, Image.new("RGBA", image.size, (0, 0, 0, 0)), mask.point(lambda v: 255 if v else 0))
        out = io.BytesIO()
        image.save(out, format="PNG", compress_level=6)
        return out.getvalue()

    @modal.method()
    def cut(self, data: bytes) -> dict:
        started = time.perf_counter()
        try:
            png = self._cut(data)
        except ValueError as exc:
            code = str(exc) if str(exc) in {"image_too_large", "image_only"} else "invalid_image"
            return {"ok": False, "code": code}
        except Exception as exc:
            print(f"[bg-remove] failed: {type(exc).__name__}: {str(exc)[:300]}")
            return {"ok": False, "code": "invalid_image"}
        elapsed = time.perf_counter() - started
        print(f"[bg-remove] cut {elapsed:.2f}s")
        return {"ok": True, "png": png, "ms": int(elapsed * 1000)}


web_runtime = modal.Image.debian_slim(python_version="3.12").pip_install("fastapi[standard]==0.115.6")


# The HTTP front runs on a cheap CPU container, so /health (the admin status page) never wakes a GPU.
@app.function(image=web_runtime, min_containers=0, max_containers=2, scaledown_window=30, timeout=200)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, Response

    web = FastAPI(title="ShowcaseMaker background removal", docs_url=None, redoc_url=None, openapi_url=None)

    @web.get("/health")
    async def health():
        return {"ok": True, "model": "birefnet-general"}

    @web.post("/remove")
    async def remove_route(request: Request):
        data = await request.body()
        if not data or len(data) > MAX_INPUT_BYTES:
            return JSONResponse({"ok": False, "code": "image_too_large"}, status_code=422)
        result = await Remover().cut.remote.aio(data)
        if not result.get("ok"):
            return JSONResponse({"ok": False, "code": result.get("code") or "invalid_image"}, status_code=422)
        return Response(result["png"], media_type="image/png", headers={"X-Elapsed-Ms": str(result.get("ms") or 0)})

    return web


@app.local_entrypoint()
def main(path: str = "static/img/samples/sample-art.webp", out: str = ""):
    import tempfile

    out = out or os.path.join(tempfile.gettempdir(), "bg_remove_test.png")
    with open(path, "rb") as handle:
        data = handle.read()
    remover = Remover()
    for attempt in ("cold", "warm", "warm"):
        started = time.time()
        result = remover.cut.remote(data)
        assert result["ok"], result
        png = result["png"]
        print(f"{attempt}: {time.time() - started:.1f}s")
    with open(out, "wb") as handle:
        handle.write(png)
    print(f"wrote {out} ({len(png)} bytes)")
