"""Small, bounded background-removal client used by Builder jobs.

Two providers: our own BiRefNet service on Modal (``modal_bg_remove.py``,
``MODAL_BG_REMOVE_URL``) and remove.bg (``REMOVE_BG_API_KEY``).
``BG_REMOVE_PROVIDER`` = auto (default: Modal when configured, otherwise
remove.bg), ``modal``, ``removebg`` or a list such as ``modal,removebg``
(the next provider is tried only when the previous one is down; never by default,
so a Modal outage cannot quietly spend paid remove.bg credits).

Provider credentials never leave the server. This module accepts only one
decoded still image and returns one validated PNG so animated media cannot
turn into dozens of provider calls.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from urllib.parse import urlparse

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


def _removebg_key() -> str:
    return (os.environ.get("REMOVE_BG_API_KEY") or "").strip()


def _modal_settings() -> tuple[str, str, str] | None:
    base = (os.environ.get("MODAL_BG_REMOVE_URL") or "").strip().rstrip("/")
    token_id = (os.environ.get("MODAL_PROXY_TOKEN_ID") or "").strip()
    token_secret = (os.environ.get("MODAL_PROXY_TOKEN_SECRET") or "").strip()
    parsed = urlparse(base)
    host = (parsed.hostname or "").lower()
    if not (token_id and token_secret) or parsed.scheme != "https":
        return None
    if not (host.endswith(".modal.run") or host.endswith(".modal.direct")):
        return None
    return base, token_id, token_secret


def providers() -> list[str]:
    """Providers to try, in order."""
    ready = {"modal": _modal_settings() is not None, "removebg": bool(_removebg_key())}
    choice = (os.environ.get("BG_REMOVE_PROVIDER") or "auto").strip().lower()
    if choice in ("", "auto"):
        return [name for name in ("modal", "removebg") if ready[name]][:1]
    names: list[str] = []
    for name in choice.replace(" ", "").split(","):
        if ready.get(name) and name not in names:
            names.append(name)
    return names


def provider() -> str:
    """The main provider ("modal", "removebg") or "" when none is configured."""
    names = providers()
    return names[0] if names else ""


def configured() -> bool:
    return bool(providers())


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


def _read_bounded(response) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_OUTPUT_BYTES:
            raise RemoveBgError("invalid_result", "The background-removal result is too large")
        chunks.append(chunk)
    return b"".join(chunks)


def _removebg(data: bytes, filename: str, media_type: str) -> bytes:
    try:
        with requests.post(
            API_URL,
            headers={"X-Api-Key": _removebg_key(), "Accept": "image/png"},
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
            return _read_bounded(response)
    except RemoveBgError:
        raise
    except requests.RequestException as exc:
        raise RemoveBgError("provider_unavailable", "AI background removal is temporarily unavailable") from exc


def _modal(data: bytes, media_type: str) -> bytes:
    settings = _modal_settings()
    if not settings:
        raise RemoveBgError("not_configured", "AI background removal is temporarily unavailable")
    base, token_id, token_secret = settings
    try:
        # A cold GPU container needs ~20-45 s before the first image; a warm one ~2 s.
        with requests.post(
            f"{base}/remove",
            headers={"Modal-Key": token_id, "Modal-Secret": token_secret,
                     "Content-Type": media_type, "Accept": "image/png"},
            data=data,
            timeout=(10, 170),
            allow_redirects=False,
            stream=True,
        ) as response:
            if response.status_code == 422:
                try:
                    code = str(response.json().get("code") or "")
                except ValueError:
                    code = ""
                if code == "image_too_large":
                    raise RemoveBgError(code, "The image resolution is too large")
                if code == "image_only":
                    raise RemoveBgError(code, "AI background removal supports still images only")
                raise RemoveBgError("invalid_image", "The selected file is not a valid image")
            if response.status_code == 429:
                raise RemoveBgError("provider_busy", "Background removal is busy. Try again later")
            if response.status_code != 200:
                raise RemoveBgError("provider_unavailable", "AI background removal is temporarily unavailable")
            return _read_bounded(response)
    except RemoveBgError:
        raise
    except requests.RequestException as exc:
        raise RemoveBgError("provider_unavailable", "AI background removal is temporarily unavailable") from exc


def remove_background(data: bytes, source_name: str = "image.png") -> bytes:
    """Cut one still image out of its background and return a bounded transparent PNG."""
    suffix, media_type = _validated_source(data)
    names = providers()
    if not names:
        raise RemoveBgError("not_configured", "AI background removal is temporarily unavailable")
    filename = (Path(source_name).stem[:80] or "image") + suffix
    for index, name in enumerate(names):
        try:
            if name == "modal":
                return _validated_result(_modal(data, media_type))
            return _validated_result(_removebg(data, filename, media_type))
        except RemoveBgError as exc:
            # Only a provider outage moves on to the next provider; a bad image would fail there too.
            if index == len(names) - 1 or exc.code not in {"provider_unavailable", "provider_busy", "invalid_result"}:
                raise
    raise RemoveBgError("not_configured", "AI background removal is temporarily unavailable")


def _validated_result(result: bytes) -> bytes:
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
