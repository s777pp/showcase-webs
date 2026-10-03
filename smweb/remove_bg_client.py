"""Small, bounded background-removal client used by Builder jobs.

Providers (each one is used only when its credentials are set):

* ``modal``     our own BiRefNet service (``modal_bg_remove.py``, ``MODAL_BG_REMOVE_URL`` +
                ``MODAL_PROXY_TOKEN_*``). First call after a pause waits for a GPU (~20-45 s).
* ``iloveapi``  iLoveAPI ``removebackgroundimage`` (``ILOVEAPI_PUBLIC_KEY``; 250 free images a month).
                It returns a 256-colour PNG, so only its alpha is used and the colours come
                from the source image.
* ``problembo`` Problembo ``background-removal`` (``PROBLEMBO_API_TOKEN``, paid per image).
* ``removebg``  remove.bg (``REMOVE_BG_API_KEY``, paid per image).

The user may pick a provider in the Builder; the remaining configured providers are then
tried in ``BG_REMOVE_ORDER`` (default modal,iloveapi,problembo,removebg) when the chosen one
is down, busy or over its monthly cap (``BG_REMOVE_MONTHLY_<NAME>``). ``BG_REMOVE_FALLBACK=0``
turns the fallback off. A bad image never moves on to the next provider.

Provider credentials never leave the server. This module accepts only one decoded still
image and returns one validated PNG so animated media cannot turn into dozens of
provider calls.
"""
from __future__ import annotations

import io
import logging
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps, UnidentifiedImageError


API_URL = "https://api.remove.bg/v1.0/removebg"
ILOVEAPI_URL = "https://api.ilovepdf.com/v1"
PROBLEMBO_URL = "https://problembo.com/apis/v1/client"
MAX_INPUT_BYTES = 22 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
# A transparent PNG result is documented up to 10 MP by remove.bg; the same cap keeps
# every provider's output and our re-encoding bounded.
MAX_PIXELS = 10_000_000
_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
LOGGER = logging.getLogger("sm.bg_remove")

PROVIDERS = ("modal", "iloveapi", "problembo", "removebg")
# Monthly caps protect the bills: iLoveAPI's free plan is 250 images, remove.bg's free plan 50.
DEFAULT_MONTHLY = {"modal": 5000, "iloveapi": 240, "problembo": 100, "removebg": 50}
# Codes that mean "this provider cannot do it right now"; anything else is about the image.
_FALLBACK_CODES = {"provider_unavailable", "provider_busy", "invalid_result", "not_configured", "provider_limit"}


class RemoveBgError(RuntimeError):
    """A provider-safe error with a stable code for the browser UI."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _unavailable() -> RemoveBgError:
    return RemoveBgError("provider_unavailable", "AI background removal is temporarily unavailable")


def _busy() -> RemoveBgError:
    return RemoveBgError("provider_busy", "Background removal is busy. Try again later")


# ---------------------------------------------------------------- configuration

def _modal_settings() -> tuple[str, str, str] | None:
    base = _env("MODAL_BG_REMOVE_URL").rstrip("/")
    token_id, token_secret = _env("MODAL_PROXY_TOKEN_ID"), _env("MODAL_PROXY_TOKEN_SECRET")
    parsed = urlparse(base)
    host = (parsed.hostname or "").lower()
    if not (token_id and token_secret) or parsed.scheme != "https":
        return None
    if not (host.endswith(".modal.run") or host.endswith(".modal.direct")):
        return None
    return base, token_id, token_secret


def ready(name: str) -> bool:
    if name == "modal":
        return _modal_settings() is not None
    if name == "iloveapi":
        return bool(_env("ILOVEAPI_PUBLIC_KEY"))
    if name == "problembo":
        return bool(_env("PROBLEMBO_API_TOKEN"))
    if name == "removebg":
        return bool(_env("REMOVE_BG_API_KEY"))
    return False


def order() -> list[str]:
    raw = _env("BG_REMOVE_ORDER") or ",".join(PROVIDERS)
    names: list[str] = []
    for name in raw.lower().replace(" ", "").split(","):
        if name in PROVIDERS and name not in names:
            names.append(name)
    return names


def providers() -> list[str]:
    """Configured providers in fallback order."""
    return [name for name in order() if ready(name)]


def provider() -> str:
    """The provider tried first in automatic mode, or "" when none is configured."""
    names = providers()
    return names[0] if names else ""


def configured() -> bool:
    return bool(providers())


def chain(preferred: str | None = None) -> list[str]:
    """Providers to try for one request: the user's choice first, then the fallbacks."""
    names = providers()
    if preferred in names:
        names.remove(preferred)
        names.insert(0, preferred)
    if _env("BG_REMOVE_FALLBACK") in {"0", "false", "no", "off"}:
        names = names[:1]
    return names


def monthly_cap(name: str) -> int:
    legacy = _env("REMOVE_BG_GLOBAL_MONTHLY") if name == "removebg" else ""
    raw = _env(f"BG_REMOVE_MONTHLY_{name.upper()}") or legacy
    try:
        return max(0, int(raw)) if raw else DEFAULT_MONTHLY[name]
    except ValueError:
        return DEFAULT_MONTHLY[name]


def _take_budget(name: str) -> bool:
    """Count one image against the provider's calendar-month cap."""
    try:
        import redis_store as rs
    except Exception:
        return True
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    allowed, _ = rs.rate_limit(f"bg-provider:{name}:{month}", monthly_cap(name), 32 * 86400,
                               fail_closed=True, fixed_bucket=True)
    return allowed


# ---------------------------------------------------------------- shared helpers

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


def _download(url: str, allowed_suffixes: tuple[str, ...], headers: dict | None = None) -> bytes:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise RemoveBgError("invalid_result", "The background-removal result is invalid")
    if allowed_suffixes and not any(host == s.lstrip(".") or host.endswith(s) for s in allowed_suffixes):
        raise RemoveBgError("invalid_result", "The background-removal result is invalid")
    with requests.get(url, headers=headers or {}, timeout=(10, 90), allow_redirects=False, stream=True) as response:
        if response.status_code != 200:
            raise _unavailable()
        return _read_bounded(response)


def _unzip_single(body: bytes) -> bytes:
    if body[:2] != b"PK":
        return body
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            names = [n for n in archive.namelist() if not n.endswith("/")]
            if not names or archive.getinfo(names[0]).file_size > MAX_OUTPUT_BYTES:
                raise ValueError("bad archive")
            return archive.read(names[0])
    except (zipfile.BadZipFile, ValueError, KeyError) as exc:
        raise RemoveBgError("invalid_result", "The background-removal result is invalid") from exc


def _source_rgba(data: bytes) -> Image.Image:
    with Image.open(io.BytesIO(data)) as source:
        return ImageOps.exif_transpose(source).convert("RGBA")


def _finalize(source: bytes, result: bytes) -> bytes:
    """Return a transparent PNG. Palette results or results of another size keep only
    their alpha; the colours then come from the source image."""
    try:
        with Image.open(io.BytesIO(result)) as image:
            if int(getattr(image, "n_frames", 1) or 1) != 1:
                raise ValueError("unexpected result")
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_PIXELS:
                raise ValueError("invalid dimensions")
            has_alpha = "A" in image.getbands() or (image.mode == "P" and "transparency" in image.info)
            if not has_alpha:
                raise ValueError("result has no transparency channel")
            original = _source_rgba(source)
            if image.format == "PNG" and image.mode in {"RGBA", "LA"} and image.size == original.size:
                image.verify()
                return result
            alpha = image.convert("RGBA").getchannel("A")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise RemoveBgError("invalid_result", "The background-removal result is invalid") from exc
    if alpha.size != original.size:
        alpha = alpha.resize(original.size, Image.Resampling.LANCZOS)
    if original.getextrema()[3][0] < 255:
        from PIL import ImageChops
        alpha = ImageChops.multiply(alpha, original.getchannel("A"))
    original.putalpha(alpha)
    clear = Image.new("RGBA", original.size, (0, 0, 0, 0))
    original = Image.composite(original, clear, alpha.point(lambda v: 255 if v else 0))
    out = io.BytesIO()
    original.save(out, format="PNG", compress_level=6)
    return out.getvalue()


# ---------------------------------------------------------------- providers

def _removebg(data: bytes, filename: str, media_type: str) -> bytes:
    try:
        with requests.post(
            API_URL,
            headers={"X-Api-Key": _env("REMOVE_BG_API_KEY"), "Accept": "image/png"},
            files={"image_file": (filename, data, media_type)},
            data={"size": "auto", "format": "png", "type": "auto"},
            timeout=(10, 120),
            allow_redirects=False,
            stream=True,
        ) as response:
            if response.status_code == 429:
                raise _busy()
            if response.status_code != 200:
                raise _unavailable()
            return _read_bounded(response)
    except RemoveBgError:
        raise
    except requests.RequestException as exc:
        raise _unavailable() from exc


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
                raise _busy()
            if response.status_code != 200:
                raise _unavailable()
            return _read_bounded(response)
    except RemoveBgError:
        raise
    except requests.RequestException as exc:
        raise _unavailable() from exc


_ilove_token: dict = {"value": "", "until": 0.0}


def _ilove_auth(refresh: bool = False) -> dict:
    now = time.time()
    if refresh or not _ilove_token["value"] or _ilove_token["until"] <= now:
        response = requests.post(f"{ILOVEAPI_URL}/auth", data={"public_key": _env("ILOVEAPI_PUBLIC_KEY")},
                                 timeout=(10, 30), allow_redirects=False)
        if response.status_code != 200:
            raise _unavailable()
        token = str((response.json() or {}).get("token") or "")
        if not token:
            raise _unavailable()
        # Signed tokens live one hour.
        _ilove_token.update(value=token, until=now + 50 * 60)
    return {"Authorization": "Bearer " + _ilove_token["value"]}


def _iloveapi(data: bytes, filename: str) -> bytes:
    region = _env("ILOVEAPI_REGION").lower() or "eu"
    if region not in {"eu", "us", "fr", "de", "pl", "in", "sg"}:
        region = "eu"
    try:
        headers = _ilove_auth()
        start = requests.get(f"{ILOVEAPI_URL}/start/removebackgroundimage/{region}", headers=headers,
                             timeout=(10, 30), allow_redirects=False)
        if start.status_code == 401:
            headers = _ilove_auth(refresh=True)
            start = requests.get(f"{ILOVEAPI_URL}/start/removebackgroundimage/{region}", headers=headers,
                                 timeout=(10, 30), allow_redirects=False)
        if start.status_code == 429:
            raise _busy()
        if start.status_code != 200:
            raise _unavailable()
        started = start.json() or {}
        server, task = str(started.get("server") or "").lower(), str(started.get("task") or "")
        # The task server comes from their answer: only their own hosts are accepted.
        if not task or not (server.endswith(".iloveimg.com") or server.endswith(".ilovepdf.com")) or "/" in server:
            raise _unavailable()
        upload = requests.post(f"https://{server}/v1/upload", headers=headers, data={"task": task},
                               files={"file": (filename, data)}, timeout=(10, 120), allow_redirects=False)
        if upload.status_code != 200:
            raise _unavailable()
        server_filename = str((upload.json() or {}).get("server_filename") or "")
        process = requests.post(
            f"https://{server}/v1/process", headers=headers, timeout=(10, 180), allow_redirects=False,
            json={"task": task, "tool": "removebackgroundimage",
                  "files": [{"server_filename": server_filename, "filename": filename}]},
        )
        if process.status_code == 400:
            raise RemoveBgError("invalid_image", "The selected file is not a valid image")
        if process.status_code != 200 or (process.json() or {}).get("status") != "TaskSuccess":
            raise _unavailable()
        return _unzip_single(_download(f"https://{server}/v1/download/{task}", (".iloveimg.com", ".ilovepdf.com"), headers))
    except RemoveBgError:
        raise
    except (requests.RequestException, ValueError) as exc:
        raise _unavailable() from exc


def _problembo_key(response) -> str:
    """Their error code: top-level "errorKey" in practice, {"error": {"key"}} in the docs.
    Short and free of user data, safe to log."""
    try:
        body = response.json() or {}
        return str(body.get("errorKey") or (body.get("error") or {}).get("key") or "")[:60]
    except (ValueError, AttributeError):
        return ""


# Problembo support (2026-10-03): tasks go to ONE endpoint, POST /apis/v1/client/tasks, with the task
# type in the body. Their site stores tasks as {"protoType": "com.problembo.proto.Pr<Name>Request",
# "payload": {...}} (task history code), so that envelope is the default. The older per-service path
# answered PARSE_TASK to every shape and stays only for PROBLEMBO_BG_BODY=probe.
_PB_REQUEST = "com.problembo.proto.PrBackgroundRemovalRequest"


def _pb_images(fid: str, name: str) -> dict:
    return {"images": [{"fileId": fid, "origName": name}]}


_PROBLEMBO_BODIES = {
    "envelope": ("tasks", lambda fid, name: {"protoType": _PB_REQUEST, "payload": _pb_images(fid, name)}),
    "envelope_task": ("tasks", lambda fid, name: {"protoType": "com.problembo.proto.BackgroundRemovalClientTaskPr",
                                                  "payload": _pb_images(fid, name)}),
    "envelope_contract": ("tasks", lambda fid, name: {"contractId": "background-removal", "payload": _pb_images(fid, name)}),
    "envelope_flat": ("tasks", lambda fid, name: {"contractId": "background-removal", **_pb_images(fid, name)}),
    "images": ("background-removal/tasks", lambda fid, name: {"images": [{"fileId": fid}]}),
    "sourceImageFileIds": ("background-removal/tasks", lambda fid, name: {"sourceImageFileIds": [fid]}),
}
_problembo_body: dict = {"name": ""}


def _problembo_body_order() -> list[str]:
    """One shape per request (PROBLEMBO_BG_BODY, default "envelope"); PROBLEMBO_BG_BODY=probe tries them all."""
    forced = _env("PROBLEMBO_BG_BODY") or "envelope"
    if forced != "probe":
        return [forced] if forced in _PROBLEMBO_BODIES else ["envelope"]
    names = list(_PROBLEMBO_BODIES)
    if _problembo_body["name"] in names:
        names.remove(_problembo_body["name"])
        names.insert(0, _problembo_body["name"])
    return names


def _problembo_step(step: str, response) -> None:
    detail = ""
    if response.status_code >= 400:
        # Their validation message names the field they did not like; links are cut out.
        import re
        try:
            detail = re.sub(r"https?://\S+", "<url>", str(response.text or ""))[:300]
        except Exception:
            detail = ""
    LOGGER.info("problembo %s -> HTTP %s %s %s", step, response.status_code, _problembo_key(response), detail)


def _problembo(data: bytes, filename: str, media_type: str = "image/png") -> bytes:
    headers = {"Authorization": "Bearer " + _env("PROBLEMBO_API_TOKEN")}
    deadline = time.time() + max(30, int(_env("PROBLEMBO_TIMEOUT_SECONDS") or 150))
    try:
        slot = requests.post(f"{PROBLEMBO_URL}/files/upload-url-for-src", headers=headers, timeout=(10, 30),
                             json={"origFileName": filename, "fileSizeBytes": str(len(data))}, allow_redirects=False)
        _problembo_step("upload-url", slot)
        if slot.status_code == 429:
            raise _busy()
        if slot.status_code != 200:
            raise _unavailable()
        slot_data = slot.json() or {}
        file_id, upload_url = str(slot_data.get("fileId") or ""), str(slot_data.get("uploadUrl") or "")
        if not file_id or urlparse(upload_url).scheme != "https":
            raise _unavailable()
        # The upload URL is presigned for this file: send the type and the Content-Disposition
        # they returned, otherwise the stored object is not recognised as an image.
        put_headers = {"Content-Type": media_type}
        if slot_data.get("contentDisposition"):
            put_headers["Content-Disposition"] = str(slot_data["contentDisposition"])[:300]
        put = requests.put(upload_url, data=data, headers=put_headers, timeout=(10, 120), allow_redirects=False)
        LOGGER.info("problembo upload -> HTTP %s", put.status_code)
        if put.status_code not in (200, 201, 204):
            raise _unavailable()
        done = requests.post(f"{PROBLEMBO_URL}/files/upload-complete", headers=headers, json={"fileId": file_id},
                             timeout=(10, 30), allow_redirects=False)
        _problembo_step("upload-complete", done)
        if done.status_code not in (200, 201, 204):
            raise _unavailable()
        created = None
        for shape in _problembo_body_order():
            path, build = _PROBLEMBO_BODIES[shape]
            created = requests.post(f"{PROBLEMBO_URL}/{path}", headers=headers, timeout=(10, 30),
                                    json=build(file_id, filename), allow_redirects=False)
            _problembo_step(f"create-task[{shape}]", created)
            if created.status_code == 200:
                _problembo_body["name"] = shape
                break
            if _problembo_key(created) != "PARSE_TASK":
                break
        if created.status_code == 429:
            raise _busy()
        if created.status_code != 200:
            # A 400 here is about our request or their account far more often than about the image,
            # so the next provider gets a chance; only their explicit file error blames the image.
            if _problembo_key(created) == "INVALID_INPUT_FILE":
                raise RemoveBgError("invalid_image", "The selected file is not a valid image")
            raise _unavailable()
        task_id = str((created.json() or {}).get("taskId") or "")
        if not task_id or "/" in task_id:
            raise _unavailable()
        while True:
            state = requests.get(f"{PROBLEMBO_URL}/tasks/{task_id}", headers=headers, timeout=(10, 30),
                                 allow_redirects=False)
            if state.status_code != 200:
                _problembo_step("task", state)
                raise _unavailable()
            body = state.json() or {}
            status = str(body.get("status") or "")
            if status == "END_SUCCESS":
                results = ((body.get("result") or {}).get("taskResult") or [])
                url = str((results[0] or {}).get("url") or "") if results else ""
                # The result lives on their storage (a Storj gateway today).
                hosts = tuple(h if h.startswith(".") else "." + h for h in
                              (_env("PROBLEMBO_RESULT_HOSTS") or "storjshare.io,problembo.com").replace(" ", "").split(",") if h)
                return _download(url, hosts)
            if status.startswith("END_"):
                key = str(((body.get("error") or {}).get("key")) or "")[:60]
                LOGGER.info("problembo task -> %s %s", status, key)
                if key == "INVALID_INPUT_FILE":
                    raise RemoveBgError("invalid_image", "The selected file is not a valid image")
                raise _unavailable()
            if time.time() > deadline:
                raise _busy()
            time.sleep(2)
    except RemoveBgError:
        raise
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        raise _unavailable() from exc


# ---------------------------------------------------------------- entry points

def remove_background_with(data: bytes, source_name: str = "image.png",
                           preferred: str | None = None) -> tuple[bytes, str]:
    """Cut one still image out of its background. Returns (transparent PNG, provider used)."""
    suffix, media_type = _validated_source(data)
    names = chain(preferred)
    if not names:
        raise RemoveBgError("not_configured", "AI background removal is temporarily unavailable")
    filename = (Path(source_name).stem[:80] or "image") + suffix
    last: RemoveBgError | None = None
    for name in names:
        try:
            if not _take_budget(name):
                raise RemoveBgError("provider_limit", "Background-removal limit reached. Try again later")
            if name == "modal":
                raw = _modal(data, media_type)
            elif name == "iloveapi":
                raw = _iloveapi(data, filename)
            elif name == "problembo":
                raw = _problembo(data, filename, media_type)
            else:
                raw = _removebg(data, filename, media_type)
            return _finalize(data, raw), name
        except RemoveBgError as exc:
            # Only a provider problem moves on to the next provider; a bad image would fail there too.
            if exc.code not in _FALLBACK_CODES:
                raise
            last = exc
    if last and last.code == "provider_limit":
        raise RemoveBgError("remove_bg_limit", "Background-removal limit reached. Try again later")
    raise last or _unavailable()


def remove_background(data: bytes, source_name: str = "image.png", preferred: str | None = None) -> bytes:
    """Cut one still image out of its background and return a bounded transparent PNG."""
    return remove_background_with(data, source_name, preferred)[0]
