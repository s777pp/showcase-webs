"""Monocular depth for the "Depth" (2.5D parallax) effect of the Process tab (owner, 2026-10-08).

Model: Depth Anything V2 Small (Apache-2.0), the ONNX export of onnx-community/depth-anything-v2-small, baked into the
image by the Dockerfile (sha256 pinned) at DEPTH_MODEL_PATH. It runs on the CPU through onnxruntime in ~0.1-0.5 s at
518 px, so no GPU service is involved. Output: relative inverse depth, larger = nearer; ``estimate`` returns it
normalised to 0..1 at the picture's own size. ``processor.depth_displacement`` turns it into the map both the
renderer and the browser preview use.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

import numpy as np
from PIL import Image

MODEL_NAME = "depth_anything_v2_small.onnx"


def _default_model_path() -> Path:
    """DEPTH_MODEL_PATH, else the Docker image's copy, else <project>/models/ for local runs
    (scripts/get_depth_model.py downloads it there; /models/ is kept out of git and releases)."""
    configured = os.environ.get("DEPTH_MODEL_PATH")
    if configured:
        return Path(configured)
    for candidate in (Path("/app/models") / MODEL_NAME, Path(__file__).resolve().parents[1] / "models" / MODEL_NAME):
        if candidate.is_file():
            return candidate
    return Path("/app/models") / MODEL_NAME


MODEL_PATH = _default_model_path()
INPUT_SIDE = 518            # the model's training size; both sides must be multiples of 14
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
_lock = threading.Lock()
_session = None


def available() -> bool:
    return MODEL_PATH.is_file()


def _get_session():
    global _session
    with _lock:
        if _session is None:
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = max(1, (os.cpu_count() or 2) - 1)
            _session = ort.InferenceSession(str(MODEL_PATH), sess_options=options, providers=["CPUExecutionProvider"])
        return _session


def estimate(image: Image.Image) -> np.ndarray:
    """Depth of ``image`` as float32 0..1 (1 = nearest), same width/height as the image."""
    if not available():
        raise RuntimeError("depth model is not installed")
    alpha = None
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        cover = np.asarray(rgba.getchannel("A"), dtype=np.float32) / 255.0
        if cover.min() < 1.0:
            # A cut-out (the Builder's Character layer): the model sees it on neutral grey, and whatever is
            # transparent is pushed to the far plane afterwards, so particles pass around the figure.
            alpha = cover
            grey = Image.new("RGBA", rgba.size, (128, 128, 128, 255))
            image = Image.alpha_composite(grey, rgba)
    rgb = image.convert("RGB")
    width, height = rgb.size
    scale = INPUT_SIDE / max(width, height)
    w = max(14, int(round(width * scale / 14)) * 14)
    h = max(14, int(round(height * scale / 14)) * 14)
    x = np.asarray(rgb.resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32) / 255.0
    x = ((x - _MEAN) / _STD).transpose(2, 0, 1)[None].astype(np.float32)
    session = _get_session()
    out = session.run(None, {session.get_inputs()[0].name: x})[0][0]
    low, high = np.percentile(out, 1), np.percentile(out, 99)
    depth = np.clip((out - low) / max(1e-6, high - low), 0, 1).astype(np.float32)
    depth = np.asarray(Image.fromarray(depth).resize((width, height), Image.Resampling.BILINEAR), dtype=np.float32)
    if alpha is not None:
        depth = depth * alpha
    return depth
