"""AI animation (beta, 2026-10-10): a still art comes alive through MiniMax H3 on fal.ai.

Owner request: "like steamprofile.io, people write simple prompts such as 'animated hair and breathing'". A bench on
the owner's art (output/ai-bench) picked MiniMax H3: it accepts suggestive anime art with fal's checker off (Wan 3.0
and Seedance refused it), keeps the first frame, honours an end frame (= the start, so the clip loops) and costs
about $0.30 per 5 s 768P clip; moderation refusals are not billed.

Flow (one job of kind ``ai_animate`` on the ``gpu`` queue, smweb/ai_animate_jobs.py):
  prompt (mode + motion chips + the visitor's own wish, rewritten into English by Gemini when it is configured)
  -> fal queue API with the picture as a data URI and the same picture as the end frame
  -> ``render``: frames at the clip's own size, the original still background composited back where nothing moves
     (as steamprofile does: a sharp background and a lighter GIF), the best loop of the chosen length (2/3/5 s) with
     a short cross-fade, then an MP4 (for Process) and a GIF that fits Steam's 5 MB.

Money guards: Pro only while in beta, ``AI_ANIMATE_PRO_DAILY`` per account and ``AI_ANIMATE_GLOBAL_DAILY`` for the
whole site per UTC day (``take`` / ``give_back``: a failed or refused animation gives its use back). Without
``FAL_KEY`` the tool reports itself unavailable. The fal key never leaves the server and is never logged.
"""
from __future__ import annotations

import base64
import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import processor as proc
import redis_store as rs
from smweb import process_control

LOG = logging.getLogger(__name__)

ENDPOINT = (os.environ.get("AI_ANIMATE_ENDPOINT") or "minimax/h3/image-to-video").strip()
QUEUE_URL = "https://queue.fal.run/"
MAX_INPUT_SIDE = 1536          # the picture sent to the model
MAX_OUTPUT_SIDE = 1080         # frames we work with (MP4 size)
GIF_WIDTH = 630                # Steam shows showcases 630 px wide
LENGTHS = {2: 24, 3: 20, 5: 16}  # seconds -> GIF frame rate (shorter loops can afford more frames in 5 MB)
MODES = ("lively", "calm")
MOTIONS = ("hair", "breath", "blink", "gaze", "wind", "glow")
WISH_MAX = 200
POLL_SECONDS = 4
TIMEOUT_SECONDS = 600


class Refused(Exception):
    """The model's content checker refused the picture (not billed by fal; the use is given back)."""


def configured() -> bool:
    return bool(_key())


def _key() -> str:
    return (os.environ.get("FAL_KEY") or "").strip()


# ---------------------------------------------------------------- prompt
_BASE = ("Anime illustration brought to life. The character keeps exactly the same pose, body, face and outfit. "
         "Static camera: no zoom, no pan, no cut, no new objects. The background stays still. Smooth seamless loop.")
_MODE = {
    "lively": "Lively natural motion: her long hair flows in a breeze, she breathes and moves softly in place.",
    "calm": ("Only a gentle idle motion. Her face and expression do not change; if her mouth is closed it stays closed "
             "and she keeps the same smile; her eyes keep looking the same way."),
}
_MOTION = {
    "hair": "The hair sways gently.",
    "breath": "The chest rises and falls slowly as she breathes.",
    "blink": "She blinks once, naturally.",
    "gaze": "Her eyes shift slightly, then return.",
    "wind": "A light wind moves the hair and the loose parts of the clothes.",
    "glow": "Soft light shimmers over the picture.",
}


def clean_wish(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:WISH_MAX]


def build_prompt(mode: str, motions: list[str], wish_en: str = "") -> str:
    mode = mode if mode in MODES else "calm"
    parts = [_BASE, _MODE[mode]]
    parts += [_MOTION[m] for m in motions if m in _MOTION]
    if wish_en:
        parts.append("Also: " + wish_en.rstrip(".") + ".")
    return " ".join(parts)


def rewrite_wish(wish: str) -> str:
    """The visitor's own words (any language) as one short English motion instruction.

    Gemini when GEMINI_API_KEY is set; otherwise the text goes as is (the model reads several languages).
    Anything that would change the picture itself is dropped by the instruction to Gemini.
    """
    wish = clean_wish(wish)
    if not wish:
        return ""
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        return wish
    model = (os.environ.get("GEMINI_MODEL") or "gemini-3.6-flash").strip()
    instruction = ("Rewrite the user's wish for an image-to-video model as ONE short English sentence that describes only "
                   "motion of things already in the picture (hair, eyes, breathing, clothes, light, particles). "
                   "Drop requests to change the character, outfit, pose, camera or to add objects. "
                   "Answer with the sentence only. Wish: ")
    try:
        import requests
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": instruction + wish}]}],
                  "generationConfig": {"maxOutputTokens": 80, "temperature": 0.2}},
            timeout=(5, 20))
        response.raise_for_status()
        parts = response.json()["candidates"][0]["content"]["parts"]
        text = clean_wish(" ".join(str(p.get("text") or "") for p in parts))
        return text or wish
    except Exception:
        LOG.info("ai_animate: wish rewrite failed, sending it as is")
        return wish


# ---------------------------------------------------------------- daily limits (with refunds)
_LOCAL: dict[str, int] = {}
_LOCAL_LOCK = threading.Lock()


def pro_daily() -> int:
    try:
        return max(0, int(os.environ.get("AI_ANIMATE_PRO_DAILY") or 3))
    except ValueError:
        return 3


def global_daily() -> int:
    try:
        return max(0, int(os.environ.get("AI_ANIMATE_GLOBAL_DAILY") or 30))
    except ValueError:
        return 30


def _day(now: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if now is None else now, tz=timezone.utc).strftime("%Y%m%d")


def _bump(key: str, delta: int) -> int:
    r = rs._r()
    if r:
        try:
            value = int(r.incrby(key, delta))
            if delta > 0 and value == delta:
                r.expire(key, 2 * 86400)
            return value
        except Exception:
            LOG.warning("ai_animate: redis counter failed, using the local one")
    with _LOCAL_LOCK:
        _LOCAL[key] = _LOCAL.get(key, 0) + delta
        return _LOCAL[key]


def _read(key: str) -> int:
    r = rs._r()
    if r:
        try:
            return int(r.get(key) or 0)
        except Exception:
            pass
    with _LOCAL_LOCK:
        return _LOCAL.get(key, 0)


def _keys(uid: int, day: str) -> tuple[str, str]:
    return f"sm:aianim:{day}:u:{uid}", f"sm:aianim:{day}:all"


def used_today(uid: int) -> dict:
    user_key, all_key = _keys(uid, _day())
    return {"used": _read(user_key), "limit": pro_daily(), "site_used": _read(all_key), "site_limit": global_daily()}


def take(uid: int, exempt: bool = False) -> tuple[dict | None, str]:
    """Reserve one animation for today. Returns (ticket, "") or (None, "user" | "site")."""
    day = _day()
    user_key, all_key = _keys(uid, day)
    if not exempt and _bump(user_key, 1) > pro_daily():
        _bump(user_key, -1)
        return None, "user"
    if _bump(all_key, 1) > global_daily():
        _bump(all_key, -1)
        if not exempt:
            _bump(user_key, -1)
        return None, "site"
    return {"day": day, "uid": int(uid), "user": not exempt}, ""


def give_back(ticket: dict | None) -> None:
    if not ticket:
        return
    user_key, all_key = _keys(int(ticket["uid"]), str(ticket["day"]))
    if ticket.get("user"):
        _bump(user_key, -1)
    _bump(all_key, -1)


# ---------------------------------------------------------------- fal
def data_uri(path: Path) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        if max(image.size) > MAX_INPUT_SIDE:
            image.thumbnail((MAX_INPUT_SIDE, MAX_INPUT_SIDE), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=93)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def request_body(image: str, prompt: str) -> dict:
    return {"image_url": image, "end_image_url": image, "prompt": prompt, "duration": 5, "resolution": "768P",
            "enable_safety_checker": False, "prompt_expansion_mode": "disabled"}


def _refusal(payload) -> bool:
    text = str(payload)
    return "content_policy_violation" in text or "content checker" in text or "partner_validation_failed" in text


def _http(method: str, url: str, json_body: dict | None = None, timeout: float = 60):
    import requests
    return requests.request(method, url, json=json_body, timeout=timeout,
                            headers={"Authorization": f"Key {_key()}", "Content-Type": "application/json"})


def generate(image_path: Path, prompt: str, dest: Path, jid: str = "", progress=None) -> dict:
    """Run the model; save the MP4 to ``dest``. Raises Refused, process_control.JobCancelled or RuntimeError."""
    if not configured():
        raise RuntimeError("AI animation is not configured (FAL_KEY)")
    started = time.time()
    sent = _http("POST", QUEUE_URL + ENDPOINT, request_body(data_uri(image_path), prompt), timeout=90)
    if sent.status_code == 422 and _refusal(sent.text):
        raise Refused("moderated")
    if sent.status_code >= 400:
        raise RuntimeError(f"AI service answered {sent.status_code}")
    info = sent.json()
    status_url, response_url, cancel_url = info["status_url"], info["response_url"], info.get("cancel_url")
    while True:
        if jid and process_control.cancelled(jid):
            if cancel_url:
                try:
                    _http("PUT", cancel_url, timeout=20)
                except Exception:
                    pass
            raise process_control.JobCancelled("Job cancelled")
        if time.time() - started > TIMEOUT_SECONDS:
            raise RuntimeError("AI animation timed out")
        state = _http("GET", status_url, timeout=30)
        status = state.json().get("status") if state.status_code < 400 else ""
        if progress:
            progress(status, time.time() - started)
        if status == "COMPLETED":
            break
        time.sleep(POLL_SECONDS)
    result = _http("GET", response_url, timeout=60)
    if result.status_code == 422 and _refusal(result.text):
        raise Refused("moderated")
    if result.status_code >= 400:
        raise RuntimeError(f"AI service answered {result.status_code}")
    video = (result.json().get("video") or {}).get("url")
    if not video:
        raise RuntimeError("AI service returned no video")
    import requests
    with requests.get(video, timeout=120, stream=True) as download:
        download.raise_for_status()
        with open(dest, "wb") as handle:
            for chunk in download.iter_content(1 << 16):
                handle.write(chunk)
    return {"seconds": round(time.time() - started, 1)}


# ---------------------------------------------------------------- render
def _small(frame: np.ndarray, width: int = 160) -> np.ndarray:
    h, w = frame.shape[:2]
    image = Image.fromarray(frame).resize((width, max(1, round(h * width / w))), Image.BILINEAR)
    return np.asarray(image, dtype=np.float32)


def pick_loop(small: list[np.ndarray], length: int) -> tuple[int, int]:
    """Start and end (exclusive) of the ``length``-frame window whose last frame is closest to its first.
    A window covering the whole clip is returned unchanged."""
    n = len(small)
    if length >= n:
        return 0, n
    best, best_start = None, 0
    for start in range(0, n - length + 1):
        end = start + length - 1
        diff = float(np.abs(small[end] - small[start]).mean())
        if best is None or diff < best:
            best, best_start = diff, start
    return best_start, best_start + length


def crossfade_loop(frames: list[np.ndarray], fade: int) -> list[np.ndarray]:
    """Blend the last ``fade`` frames into the first ones so the loop has no jump (the result is shorter by fade)."""
    n = len(frames)
    if fade < 1 or n < 3 * fade:
        return frames
    blended = []
    for j in range(fade):
        a = (j + 1) / fade
        blended.append(np.clip((1 - a) * frames[n - fade + j].astype(np.float32) + a * frames[j].astype(np.float32),
                               0, 255).astype(np.uint8))
    return frames[fade:n - fade] + blended


def motion_mask(small: list[np.ndarray], size: tuple[int, int]) -> np.ndarray:
    """0..1 mask of what moves anywhere in the clip, grown and feathered, at ``size``."""
    first = small[0]
    motion = np.zeros(first.shape[:2], np.float32)
    for frame in small[1:]:
        motion = np.maximum(motion, np.abs(frame - first).mean(axis=2))
    mask = Image.fromarray(np.clip((motion - 6) * 12, 0, 255).astype(np.uint8)).resize(size, Image.BILINEAR)
    mask = mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(6))
    return np.asarray(mask, dtype=np.float32)[..., None] / 255


def render(video: Path, source: Path, out_dir: Path, seconds: int = 3, keep_background: bool = True,
           jid: str = "", stem: str = "animation") -> dict:
    """MP4 + GIF (<= 5 MB) of the best ``seconds`` loop. Returns paths and numbers."""
    seconds = seconds if seconds in LENGTHS else 3
    fps = LENGTHS[seconds]
    ffmpeg = proc.find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable")
    work = Path(tempfile.mkdtemp(prefix="sm_aianim_", dir=str(out_dir)))
    try:
        raw_dir = work / "raw"
        raw_dir.mkdir()
        scale = f"scale='min({MAX_OUTPUT_SIDE},iw)':'min({MAX_OUTPUT_SIDE},ih)':force_original_aspect_ratio=decrease"
        process_control.run([ffmpeg, "-y", "-v", "error", "-i", str(video), "-vf",
                             f"fps={fps},{scale},scale=trunc(iw/2)*2:trunc(ih/2)*2", str(raw_dir / "f_%04d.png")],
                            check=True, capture_output=True, job_id=jid or None)
        paths = sorted(raw_dir.glob("f_*.png"))
        if len(paths) < 4:
            raise RuntimeError("The animation has too few frames")
        frames = [np.asarray(Image.open(p).convert("RGB")) for p in paths]
        h, w = frames[0].shape[:2]
        small = [_small(f) for f in frames]
        # The loop: a window of the chosen length that comes back to its start, then a short cross-fade.
        want = min(len(frames), seconds * fps + max(2, fps // 4))
        start, end = pick_loop(small, want)
        frames, small = frames[start:end], small[start:end]
        steps = [float(np.abs(small[i + 1] - small[i]).mean()) for i in range(len(small) - 1)]
        seam_before = float(np.abs(small[-1] - small[0]).mean())
        fade = max(2, fps // 4) if seam_before > 1.2 * (np.mean(steps) if steps else 0) else 0
        frames = crossfade_loop(frames, fade)
        process_control.checkpoint(jid or None)
        moving = 100.0
        if keep_background:
            with Image.open(source) as picture:
                still = np.asarray(picture.convert("RGB").resize((w, h), Image.LANCZOS), dtype=np.float32)
            mask = motion_mask([_small(f) for f in frames], (w, h))
            moving = round(float((mask[..., 0] > 0.5).mean()) * 100, 1)
            frames = [np.clip(mask * f.astype(np.float32) + (1 - mask) * still, 0, 255).astype(np.uint8) for f in frames]
        full_dir, gif_dir = work / "full", work / "gif"
        full_dir.mkdir()
        gif_dir.mkdir()
        gif_size = (GIF_WIDTH, max(2, round(h * GIF_WIDTH / w / 2) * 2)) if w > GIF_WIDTH else (w, h)
        for index, frame in enumerate(frames, 1):
            image = Image.fromarray(frame)
            image.save(full_dir / f"frame_{index:04d}.png", compress_level=1)
            (image.resize(gif_size, Image.LANCZOS) if gif_size != (w, h) else image).save(
                gif_dir / f"frame_{index:04d}.png", compress_level=1)
        mp4 = out_dir / f"{stem}.mp4"
        process_control.run([ffmpeg, "-y", "-v", "error", "-framerate", str(fps), "-i", str(full_dir / "frame_%04d.png"),
                             "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                             "-movflags", "+faststart", str(mp4)], check=True, capture_output=True, job_id=jid or None)
        gif = out_dir / f"{stem}.gif"
        chosen = proc.fit_frames_to_gif(gif_dir, gif, fps=fps, max_mb=proc.MAX_STEAM_MB)
        if not chosen:
            proc.media_to_gif(mp4, gif, fps=fps, width=gif_size[0], duration=float(seconds) + 1, encoder="gifski")
            proc.ensure_under_mb(gif, max_mb=proc.MAX_STEAM_MB)
        return {"mp4": str(mp4), "gif": str(gif), "fps": fps, "frames": len(frames), "width": w, "height": h,
                "gif_width": gif_size[0], "gif_height": gif_size[1], "gif_bytes": gif.stat().st_size,
                "mp4_bytes": mp4.stat().st_size, "seam_before": round(seam_before, 2), "crossfade": fade,
                "moving_pct": moving}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def probe_video(path: Path) -> bool:
    """True when FFmpeg can read at least one frame (a guard before rendering)."""
    ffmpeg = proc.find_ffmpeg()
    if not ffmpeg:
        return False
    done = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "null", "-"],
                          capture_output=True)
    return done.returncode == 0
