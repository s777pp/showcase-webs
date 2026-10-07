"""Cutting a file sent to the owner's Telegram bot (owner, 2026-10-08: "like the Process tab, pictures and GIFs,
showcase type and an optional frame, no Builder").

The bot calls the private /api/bot-admin/cut/* routes (smweb/routers/bot_admin.py, BOT_ADMIN_SECRET) with the file
it downloaded from Telegram. The job is an ordinary Process job (same payload, same worker, same pipeline as the
site's "Prepare a file" tab), owned by ``tg:<telegram id>`` so only that chat can read its status and ZIP.

Limits are the site's: a Telegram user whose account (telegram_billing.account_for) has Pro cuts without a daily
limit, everyone else gets FREE_LIMIT files a day, counted per Telegram id (the bot has no visitor IP). The ZIP
holds only the Steam files, like the site by default, so the free watermark (drawn on the optional preview only)
never appears in it.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import time
from pathlib import Path

import processor as proc
import redis_store as rs
from smweb import analytics, gumroad_billing, square_fx, telegram_billing
from smweb.core import FREE_LIMIT, JOBS, MAX_UPLOAD_MB, _day
from smweb.jobs import _job_pool, _job_set, _run_process_job_from_payload, _worker_mode

_TG_ID = re.compile(r"^\d{3,20}$")
MODES = ("workshop", "featured", "split")
# Frame presets offered by the bot; the same options the Process tab sends.
FRAMES: dict[str, dict | None] = {
    "none": None,
    "line": {"style": "solid", "color": "#ffffff", "width": 2},
    "neon": {"style": "neon", "color": "#1fc9f1", "color2": "#8a62ff", "width": 3},
    "rgb": {"style": "rgb", "color": "#1fc9f1", "color2": "#8a62ff", "width": 3, "speed": 1},
}
ACTIVE_JOBS_FREE = 1
ACTIVE_JOBS_PRO = 2


def owner(tg_id: str) -> str:
    return f"tg:{tg_id}"


def valid_tg(tg_id: str) -> bool:
    return bool(_TG_ID.match(str(tg_id or "")))


def _is_pro(tg_id: str) -> bool:
    user_id = telegram_billing.account_for(tg_id)
    return bool(user_id and gumroad_billing.pro_state(user_id).get("pro"))


def quota(tg_id: str) -> dict:
    """{"pro", "limit", "used", "left"}; limit/left are -1 for Pro."""
    if _is_pro(tg_id):
        return {"pro": True, "limit": -1, "used": 0, "left": -1}
    used = int(rs.quota_get(owner(tg_id), _day()) or 0)
    limit = int(os.environ.get("TELEGRAM_CUT_DAILY") or FREE_LIMIT)
    return {"pro": False, "limit": limit, "used": used, "left": max(0, limit - used)}


def start(tg_id: str, name: str, data: bytes, mode: str, frame: str) -> tuple[int, dict]:
    """Queue a cut. Returns (HTTP status, JSON body)."""
    if not valid_tg(tg_id):
        return 400, {"ok": False, "code": "tg_id", "msg": "Bad Telegram id"}
    mode = mode if mode in MODES else "workshop"
    frame = frame if frame in FRAMES else "none"
    if not data:
        return 400, {"ok": False, "code": "empty", "msg": "Empty file"}
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        return 413, {"ok": False, "code": "too_big", "msg": f"File is over {MAX_UPLOAD_MB} MB"}
    key = owner(tg_id)
    if not rs.start_lock("tgcut:" + tg_id, ttl=30):
        return 429, {"ok": False, "code": "busy", "msg": "Previous file is still starting"}
    try:
        q = quota(tg_id)
        if rs.job_count_user(key) >= (ACTIVE_JOBS_PRO if q["pro"] else ACTIVE_JOBS_FREE):
            return 429, {"ok": False, "code": "active", "msg": "A file is already being cut"}
        if not q["pro"] and q["left"] <= 0:
            return 429, {"ok": False, "code": "limit", "msg": "Daily limit reached", "limit": q["limit"], "left": 0}
        jid = secrets.token_hex(12)
        job_dir = JOBS / jid
        job_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name or "file")[:80] or "file"
        path = job_dir / f"00_{safe}"
        path.write_bytes(data)
        preset = FRAMES[frame]
        width = int(preset["width"]) if preset else 0
        opts = {
            "modes": [mode],
            # Free branding goes only on the optional preview, which the bot never asks for.
            "text": "" if q["pro"] else "ShowcaseMaker", "opacity": 0.0 if q["pro"] else 0.5,
            "color": "#ffffff", "corner": "bl", "scale": 1.0, "wm_x": None, "wm_y": None, "wm_font": "Fineday",
            "do_ac": False,
            "outline_width": width,
            "outline_color": preset["color"] if preset else "#ffffff",
            "outline_fx": square_fx.normalize_frame(dict(preset, target="squares")) if preset else None,
            "size_i": 750, "grade": None, "fps": 12, "enc": "gifski",
            "encode_profile": proc.normalize_encode_profile("standard"),
            "extras": [],
            "steam_check": False,
            "_analytics": {"session_hash": "", "language": "telegram", "user_id": None,
                           "file_type": Path(safe).suffix.lower().lstrip("."), "size_bucket": ""},
        }
        files_meta = [{"name": safe, "path": str(path), "rotation": 0.0, "size": len(data),
                       "sha256": hashlib.sha256(data).hexdigest()}]
        external = _worker_mode() == "external" and rs.redis_ok() and rs.worker_alive()
        payload = {"kind": "process", "queue": "media", "status": "queued", "pct": 1, "stage": "queued",
                   "user_key": key, "files": files_meta, "opts": opts, "created": time.time(), "source": "telegram"}
        rs.job_create(jid, payload, enqueue=external)
        _job_set(jid, status="queued", pct=1, stage="queued", created=time.time(), user_key=key)
        analytics.record("process_started", session_hash="", user_id=None, language="other",
                         properties={"mode": mode, "file_type": opts["_analytics"]["file_type"], "source": "telegram"},
                         event_key=f"process:{jid}:started")
        if not q["pro"]:
            rs.quota_inc(key, _day(), 1)                 # charged once the job exists (the lock keeps this atomic)
        if not external:
            _job_pool.submit(_run_process_job_from_payload, jid, payload)
        return 200, {"ok": True, "job_id": jid, "pro": q["pro"],
                     "left": -1 if q["pro"] else max(0, q["left"] - 1), "limit": q["limit"]}
    finally:
        rs.start_unlock("tgcut:" + tg_id)


def job_for(tg_id: str, job_id: str) -> dict | None:
    """The job, only if this Telegram user started it."""
    if not valid_tg(tg_id) or not re.fullmatch(r"[0-9a-f]{24}", str(job_id or "")):
        return None
    job = rs.job_get(job_id)
    if not job or str(job.get("user_key") or "") != owner(tg_id):
        return None
    return job


def describe(job_id: str, job: dict) -> dict:
    """What the bot needs to show progress (the same numbers as the site's status endpoint)."""
    from smweb import job_diagnostics
    from smweb.routers.process import _process_eta
    out = {"status": job.get("status"), "pct": int(job.get("pct") or 0), "stage": job.get("stage") or ""}
    out.update(_process_eta(job_id, job))
    if job.get("status") == "error":
        # A category, never the raw text (it may carry paths); the bot words it.
        out.update(job_diagnostics.public_error(job.get("error")))
    if job.get("status") == "done":
        out["files"] = [item.get("name") for item in (job.get("listed") or [])][:20]
    return out
