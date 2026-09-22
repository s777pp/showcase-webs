"""Small, bounded remove.bg client used by Builder background-removal jobs.

The provider credential never leaves the server.  This module intentionally
accepts only one decoded still image and returns one validated PNG so animated
media cannot accidentally turn into dozens of paid API calls.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import requests
from PIL import Image, UnidentifiedImageError


API_URL = "https://api.remove.bg/v1.0/removebg"
MAX_INPUT_BYTES = 22 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
# remove.bg accepts larger inputs for some formats, but a transparent PNG result
# is documented up to 10 MP. Reject larger sources instead of silently reducing
# resolution or spending a credit on a request that cannot preserve the source.
MAX_PIXELS = 10_000_000
_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


class RemoveBgError(RuntimeError):
    """A provider-safe error with a stable code for the browser UI."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def configured() -> bool:
    return bool((os.environ.get("REMOVE_BG_API_KEY") or "").strip())


def _validated_source(data: bytes) -> tuple[str, str]:
    if not data or len(data) > MAX_INPUT_BYTES:
        raise RemoveBgError("image_too_large", "The image must be no larger than 22 MB")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = str(image.format or "").upper()
            width, height = image.size
            frames = int(getattr(image, "n_frames", 1) or 1)
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise RemoveBgError("invalid_image", "The selected file is not a valid image") from exc
    if image_format not in _FORMATS:
        raise RemoveBgError("image_only", "AI background removal supports PNG, JPG and WebP images only")
    if frames != 1:
        raise RemoveBgError("image_only", "AI background removal supports still images only")
    if width < 1 or height < 1 or width * height > MAX_PIXELS:
        raise RemoveBgError("image_too_large", "The image resolution is too large")
    suffix = ".jpg" if image_format == "JPEG" else "." + image_format.lower()
    return suffix, _FORMATS[image_format]


def remove_background(data: bytes, source_name: str = "image.png") -> bytes:
    """Send one still image to remove.bg and return a bounded transparent PNG."""
    suffix, media_type = _validated_source(data)
    key = (os.environ.get("REMOVE_BG_API_KEY") or "").strip()
    if not key:
        raise RemoveBgError("not_configured", "AI background removal is temporarily unavailable")
    filename = (Path(source_name).stem[:80] or "image") + suffix
    try:
        with requests.post(
            API_URL,
            headers={"X-Api-Key": key, "Accept": "image/png"},
            files={"image_file": (filename, data, media_type)},
            data={"size": "auto", "format": "png", "type": "auto"},
            timeout=(10, 120),
            allow_redirects=False,
            stream=True,
        ) as response:
            if response.status_code == 429:
                raise RemoveBgError("provider_busy", "Background removal is busy. Try again later")
            if response.status_code != 200:
                raise RemoveBgError("provider_unavailable", "AI background removal is temporarily unavailable")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_OUTPUT_BYTES:
                    raise RemoveBgError("invalid_result", "The background-removal result is too large")
                chunks.append(chunk)
    except RemoveBgError:
        raise
    except requests.RequestException as exc:
        raise RemoveBgError("provider_unavailable", "AI background removal is temporarily unavailable") from exc

    result = b"".join(chunks)
    try:
        with Image.open(io.BytesIO(result)) as image:
            if image.format != "PNG" or int(getattr(image, "n_frames", 1) or 1) != 1:
                raise ValueError("unexpected result")
            if "A" not in image.getbands():
                raise ValueError("result has no transparency channel")
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_PIXELS:
                raise ValueError("invalid dimensions")
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise RemoveBgError("invalid_result", "The background-removal result is invalid") from exc
    return result
