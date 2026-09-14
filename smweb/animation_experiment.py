"""Private image-animation experiment: bounded inputs and exactly-once submission.

GPU/model dependencies belong to modal_animate.py, not to the site's
production environment. Website integration is gated by an owner allowlist.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import warnings
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlsplit

from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field, model_validator
from smweb.animation_selection import MotionSelection, selection_prompts

MODEL_ID = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
MODEL_REVISION = "b8fff7315c768468a5333511427288870b2e9635"
PREFIX = "animation-experiment"
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 80 * 1024 * 1024
DAILY_LIMIT = 5
FPS = 24
PROTOCOL_VERSION = 4
PROFILES = {"draft": (81, 30), "quality": (121, 50)}
PRESETS = {
    "alive": "The character comes alive: visible natural breathing, a natural blink, a small relaxed head tilt and gentle shoulder movement. Hair and loose clothing respond to the movement.",
    "breathing": "Visible rhythmic breathing moves the chest and shoulders. The character blinks naturally and makes a small relaxed head movement.",
    "breeze": "A breeze continuously sways the hair and loose clothing. The character breathes, blinks naturally and makes a small head movement, even if the hair is short.",
    "water": "Continuous visible ripples travel across the water and reflections flow with them. The surrounding solid objects remain stationary.",
    "smoke": "Smoke continuously curls, rises and drifts with visible changing shapes. Existing glowing lights gently pulse. Solid objects remain stationary.",
}
INTENSITIES = {
    "gentle": "Small but clearly visible, smooth movement throughout the video. ",
    "normal": "Clearly visible fluid animation throughout the video, with moderate movement. ",
    "strong": "Expressive, clearly visible movement throughout the video without large displacement. ",
}
BASE_PROMPT = "Animate the supplied image. Preserve the character identity, drawing style, proportions and scene composition. Locked static camera, no zoom, no pan. "
NEGATIVE_PROMPT = "static image, frozen character, no motion, camera movement, zoom, scene cut, distorted face, deformed hands, extra limbs, flicker, new objects, subtitles, watermark"


def keys(request_id: str) -> tuple[str, str]:
    if not re.fullmatch(r"[a-f0-9]{32}", request_id):
        raise ValueError("Invalid request id")
    return f"{PREFIX}/{request_id}/source.png", f"{PREFIX}/{request_id}/result.mp4"


def signed_location(url: str, key: str) -> tuple[str, str]:
    """Allow only direct presigned R2 URLs for this request's exact objects."""
    try:
        parsed = urlsplit(url)
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        query = dict(pairs)
        valid = (
            len(url) <= 4096 and parsed.scheme == "https"
            and re.fullmatch(r"[a-f0-9]{32}\.r2\.cloudflarestorage\.com", parsed.hostname or "")
            and not parsed.username and not parsed.password and parsed.port in (None, 443)
            and not parsed.fragment and len(query) == len(pairs)
            and query.get("X-Amz-Algorithm") == "AWS4-HMAC-SHA256"
            and re.fullmatch(r"[a-fA-F0-9]{64}", query.get("X-Amz-Signature", ""))
            and query.get("X-Amz-Credential") and query.get("X-Amz-Date")
            and 60 <= int(query.get("X-Amz-Expires", "0")) <= 7200
            and re.fullmatch(r"/[a-z0-9][a-z0-9.-]{1,62}/" + re.escape(key), parsed.path)
        )
        if valid:
            return parsed.hostname, parsed.path
    except (ValueError, TypeError):
        pass
    raise ValueError("Invalid private storage URL")


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    source_url: str = Field(max_length=4096)
    result_url: str = Field(max_length=4096)
    preset: str = "alive"
    intensity: str = "normal"
    quality: str = "draft"
    prompt: str = Field(default="", max_length=1000)
    seed: int = Field(default=42, ge=0, le=2147483647)
    matte: str = Field(default="#061019", pattern=r"^#[a-fA-F0-9]{6}$")
    selection: MotionSelection | None = None

    @model_validator(mode="after")
    def validate_options(self):
        source_key, result_key = keys(self.request_id)
        source = signed_location(self.source_url, source_key)
        result = signed_location(self.result_url, result_key)
        if source[0] != result[0] or source[1].split("/")[1] != result[1].split("/")[1]:
            raise ValueError("Storage locations must match")
        if self.quality not in PROFILES or self.preset not in (*PRESETS, "custom") or self.intensity not in INTENSITIES:
            raise ValueError("Invalid animation option")
        if (self.preset == "custom") != bool(self.prompt.strip()):
            raise ValueError("Use a nonempty prompt only with the custom preset")
        return self

    def fingerprint(self) -> str:
        values = self.model_dump()
        for field in ("source_url", "result_url"):
            parsed = urlsplit(values[field])
            values[field] = parsed.hostname + parsed.path
        return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def prepare_image(raw: bytes, matte: str = "#061019", *, canonical: bool = False) -> Image.Image:
    """Decode static images only; fit into the model canvas without stretching."""
    if not raw or len(raw) > MAX_INPUT_BYTES or not re.fullmatch(r"#[a-fA-F0-9]{6}", matte):
        raise ValueError("Invalid or oversized image")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in ("PNG", "JPEG", "WEBP") or getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Use a static PNG, JPEG or WebP image")
                width, height = source.size
                ratio_limit = 3.2 if canonical else 3
                if min(width, height) < 64 or width * height > 16_000_000 or not 1/ratio_limit <= width/height <= ratio_limit:
                    raise ValueError("Image dimensions are outside the experiment limits")
                image = ImageOps.exif_transpose(source).convert("RGBA")
        background = Image.new("RGBA", image.size, matte)
        background.alpha_composite(image)
        image = background.convert("RGB")
        if canonical:
            # Website paints on this fitted canvas. Re-fitting changes its ratio
            # through rounding and moves brush coordinates relative to the image.
            if max(image.size) > 1280 or image.width * image.height > 1280 * 704 or any(side % 32 for side in image.size):
                raise ValueError("Invalid canonical image canvas")
            return image
    except (ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise
    except Exception:
        raise ValueError("Could not decode image") from None
    ratio = image.width / image.height
    height = math.sqrt((1280 * 704) / ratio)
    width = height * ratio
    scale = min(1.0, 1280 / max(width, height))
    size = (max(32, int(width * scale) // 32 * 32), max(32, int(height * scale) // 32 * 32))
    return ImageOps.pad(image, size, method=Image.Resampling.LANCZOS, color=matte)


def chroma_channel(image: Image.Image) -> int | None:
    """Conservative corner-based detection; does not alter the user's image."""
    import numpy as np
    sample = np.asarray(image.convert("RGB").resize((64, 64)), dtype=float)
    corners = np.concatenate([sample[:8, :8].reshape(-1, 3), sample[:8, -8:].reshape(-1, 3),
                              sample[-8:, :8].reshape(-1, 3), sample[-8:, -8:].reshape(-1, 3)])
    for channel in (1, 2):
        others = np.delete(corners, channel, axis=1).max(axis=1)
        if ((corners[:, channel] > 80) & (corners[:, channel] - others > 45)).mean() > .85:
            return channel
    return None


def motion_prompts(payload: Submission, image: Image.Image) -> tuple[str, str]:
    if payload.selection is not None:
        prompt, negative = selection_prompts(payload.selection, payload.intensity)
    else:
        prompt = BASE_PROMPT + INTENSITIES[payload.intensity]
        prompt += payload.prompt.strip() if payload.preset == "custom" else PRESETS[payload.preset]
        negative = NEGATIVE_PROMPT
    channel = chroma_channel(image)
    if channel is not None:
        prompt += " Keep the existing flat " + ("green" if channel == 1 else "blue") + " screen background uniform and stationary."
    return prompt, negative


def assess_motion(video, image: Image.Image) -> dict:
    """Cheap warning heuristic, not a semantic judgement or an automatic retry.

    Sample at most 21 frames, exclude an obvious chroma background and subtract
    global brightness drift so a changing flat background is not 'animation'.
    """
    import numpy as np
    size = (128, max(32, round(128 * image.height / image.width)))
    source = np.asarray(image.convert("RGB").resize(size), dtype=float)
    mask = np.ones(source.shape[:2], dtype=bool)
    channel = chroma_channel(image)
    if channel is not None:
        other = np.delete(source, channel, axis=2).max(axis=2)
        mask &= ~((source[:, :, channel] > 80) & (source[:, :, channel] - other > 35))
    if mask.sum() < 64:
        return {"status": "inconclusive", "reason": "insufficient_foreground"}
    samples = []
    indices = np.unique(np.linspace(0, len(video) - 1, min(21, len(video))).astype(int))
    for index in indices:
        frame = video[index]
        if not isinstance(frame, Image.Image):
            array = np.asarray(frame)
            if np.issubdtype(array.dtype, np.floating):
                array = np.clip(array * 255, 0, 255)
            frame = Image.fromarray(array.astype("uint8"))
        pixels = np.asarray(frame.convert("L").resize(size), dtype=float)[mask]
        samples.append(pixels - pixels.mean())
    if len(samples) < 2:
        return {"status": "inconclusive", "reason": "insufficient_frames"}
    values = np.asarray(samples)
    variation = values.std(axis=0)
    activity = float((variation > 3).mean() * 100)
    deviation = float(variation.mean())
    speed = float((np.abs(np.diff(values, axis=0)).mean(axis=1) / np.diff(indices)).mean())
    weak = (deviation < 2 and activity < 12) or speed < .5
    return {"status": "low_motion" if weak else "motion_detected",
            "foreground_variation": round(deviation, 3), "active_pixels_percent": round(activity, 2),
            "change_per_frame": round(speed, 3),
            "sampled_frames": len(samples), "chroma_excluded": channel is not None}


def execute_once(payload: Submission, records, generate, now) -> dict:
    """A persisted execution fence prevents expensive replay after a GPU crash.

    This cannot fence crashes before function entry. Interrupted executions are
    not automatically retried, even when Modal reschedules the same input.
    """
    key = f"execution:{payload.request_id}"
    initial = {"stage": "starting", "started_at": now(), "updated_at": now()}
    if not records.put(key, initial, skip_if_exists=True):
        previous = records.get(key) or {}
        return previous.get("output") or {"status": "error", "code": "execution_not_repeated"}

    def progress(stage, **values):
        records.put(key, {**initial, "stage": stage, "updated_at": now(), **values})
        print(f"[animation {payload.request_id}] {stage} {values}", flush=True)

    try:
        output = generate(payload, progress)
    except Exception as error:
        # Exception messages may contain signed URLs; only the class is logged.
        print(f"[animation {payload.request_id}] failed ({type(error).__name__})", flush=True)
        output = {"status": "error", "code": "generation_failed"}
    records.put(key, {**initial, "stage": output["status"], "updated_at": now(), "output": output})
    return output


class SubmissionConflict(RuntimeError):
    pass


class DailyLimitReached(RuntimeError):
    pass


async def claim_submission(payload: Submission, records, spawn, now: float) -> str:
    """Atomic reservation prevents double GPU spawns, including uncertain errors.

    records implements Modal Dict's get/put(skip_if_exists=True) async methods.
    Never release a reservation after an ambiguous spawn failure.
    """
    key = f"request:{payload.request_id}"
    initial = {"fingerprint": payload.fingerprint(), "created_at": now, "state": "starting"}
    if not await records.put(key, initial, skip_if_exists=True):
        record = await records.get(key)
        if record and record.get("fingerprint") == initial["fingerprint"] and record.get("call_id"):
            return record["call_id"]
        raise SubmissionConflict("Request already reserved; check its status")
    day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    for slot in range(DAILY_LIMIT):
        if await records.put(f"budget:{day}:{slot}", payload.request_id, skip_if_exists=True):
            break
    else:
        await records.put(key, {**initial, "state": "limit"})
        raise DailyLimitReached("Daily experiment limit reached")
    try:
        call_id = await spawn(payload.model_dump())
        await records.put(key, {**initial, "state": "submitted", "call_id": call_id})
    except Exception:
        await records.put(key, {**initial, "state": "unknown"})
        raise SubmissionConflict("Submission outcome unknown; do not resubmit automatically") from None
    return call_id
