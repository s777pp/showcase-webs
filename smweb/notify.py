"""Site-wide notifications (2026-10-01).

Rows live in ``notifications``. The browser renders the text in the visitor's language
from ``kind`` + ``meta`` (see ``ss-shell.js`` NOTIFY_COPY); ``title``/``body`` keep a
plain Russian fallback for older clients. ``group_key`` makes repeated events update
one row instead of piling up (download digests, Pro reminders, one row per job).

Kinds: like, comment, reply (gallery, written by auth_db), downloads, support_reply,
job_done, job_error, pro_expiring, pro_expired. News are not stored per user: the bell
reads published posts and ``users.news_seen_at`` (smweb/news.py).
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time

import auth_db

LOG = logging.getLogger(__name__)
KEEP_SECONDS = 7 * 86400          # owner: "a week is enough for now"
DOWNLOAD_WINDOW = 4 * 3600        # downloads are summed per 4 hours (owner: every 3-5 h)
_periodic_lock = threading.Lock()
_last_periodic = 0.0

# Jobs whose success is worth a notification: they take minutes, the user has often left.
LONG_JOBS = {"upscale", "seamless_loop", "workshop_studio", "steam_profile_import", "profile_insight", "steam_dna"}
JOB_LINKS = {
    "process": "/app", "workshop_studio": "/app#workshop", "compose": "/app#compose", "upscale": "/app#upscale",
    "seamless_loop": "/app#loop", "steam_profile_import": "/profile", "profile_insight": "/app#doctor",
    "steam_dna": "/app#dna", "builder_bg_remove": "/app#builder",
}


def add(user_id: int, kind: str, *, title: str = "", body: str = "", link: str = "", meta: dict | None = None,
        group_key: str | None = None, actor_id: int | None = None, item_id: int | None = None) -> None:
    """Insert a notification, or refresh the unread row with the same ``group_key``."""
    if not user_id:
        return
    now = time.time()
    payload = json.dumps(meta or {}, ensure_ascii=False, separators=(",", ":"))
    c = auth_db._conn()
    try:
        if group_key:
            row = c.execute("SELECT id FROM notifications WHERE user_id=? AND group_key=? ORDER BY id DESC LIMIT 1",
                            (int(user_id), group_key)).fetchone()
            if row:
                c.execute("""UPDATE notifications SET kind=?, title=?, body=?, link=?, meta_json=?, is_read=0, created_at=?
                             WHERE id=?""", (kind, title[:200], body[:500], link[:300], payload, now, int(row["id"])))
                c.commit()
                return
        c.execute("""INSERT INTO notifications(user_id, kind, actor_id, item_id, body, is_read, created_at, title, link, meta_json, group_key)
                     VALUES (?,?,?,?,?,0,?,?,?,?,?)""",
                  (int(user_id), kind, actor_id, item_id, body[:500], now, title[:200], link[:300], payload, group_key))
        c.commit()
    except Exception:
        LOG.debug("notification insert failed", exc_info=True)
    finally:
        c.close()


def _user_id(user_key) -> int | None:
    value = str(user_key or "")
    return int(value) if value.isdigit() else None


# ---------------------------------------------------------------- jobs
def error_code(job: dict) -> str:
    """A short reason code the browser turns into a plain-language explanation."""
    from smweb import job_diagnostics
    text = job_diagnostics._text(job)
    if re.search(r"private|приват", text, re.I):
        return "steam_private"
    if re.search(r"HTTP 429|Too Many Requests|rate.?limit", text, re.I):
        return "steam_busy"
    if re.search(r"not.?found|404|profile_unavailable|does not exist", text, re.I) and job.get("kind") == "steam_profile_import":
        return "steam_not_found"
    matched = job_diagnostics.classify(text)
    code = matched[0] if matched else "unknown"
    if code in {"ffmpeg_missing", "gifski", "memory", "disk", "worker", "ffmpeg_failed", "empty_output", "timeout"}:
        return "server"
    if code == "steam_profile":
        return "steam_unavailable"
    return code


def job_finished(job_id: str, fields: dict) -> None:
    """Called from redis_store.job_update for done/error. One row per job (group key)."""
    status = fields.get("status")
    if status not in ("done", "error"):
        return
    try:
        import redis_store as rs
        job = rs.job_get(job_id) or {}
    except Exception:
        return
    job = {**job, **fields}
    user_id = _user_id(job.get("user_key"))
    kind = str(job.get("kind") or "process")
    if not user_id:
        return
    if status == "done" and kind not in LONG_JOBS:
        return
    link = JOB_LINKS.get(kind, "/app")
    if status == "done":
        add(user_id, "job_done", title="Задача готова", link=link, meta={"tool": kind, "job": job_id},
            group_key=f"job:{job_id}")
    else:
        code = error_code(job)
        add(user_id, "job_error", title="Не удалось выполнить задачу", link=link,
            meta={"tool": kind, "job": job_id, "code": code}, group_key=f"job:{job_id}")


# ---------------------------------------------------------------- gallery downloads
def gallery_downloaded(item_id: int) -> None:
    """Sum downloads of one work into a single row per 4-hour window."""
    c = auth_db._conn()
    try:
        item = c.execute("SELECT user_id, title FROM gallery WHERE id=?", (int(item_id),)).fetchone()
    finally:
        c.close()
    if not item or not item["user_id"]:
        return
    window = int(time.time() // DOWNLOAD_WINDOW)
    key = f"dl:{int(item_id)}:{window}"
    c = auth_db._conn()
    try:
        row = c.execute("SELECT meta_json FROM notifications WHERE user_id=? AND group_key=?", (int(item["user_id"]), key)).fetchone()
    finally:
        c.close()
    count = 1
    if row:
        try:
            count = int(json.loads(row["meta_json"] or "{}").get("count") or 0) + 1
        except (TypeError, ValueError):
            count = 1
    add(int(item["user_id"]), "downloads", title="Твою работу скачали", link=f"/gallery?item={int(item_id)}",
        meta={"count": count, "work": str(item["title"] or "")[:60]}, group_key=key, item_id=int(item_id))


# ---------------------------------------------------------------- Pro reminders + retention
def _pro_reminders(now: float) -> None:
    c = auth_db._conn()
    try:
        rows = c.execute("SELECT id, pro_until FROM users WHERE pro_until IS NOT NULL AND pro_until>? AND pro_until<?",
                         (now - 86400, now + 3 * 86400 + 600)).fetchall()
    finally:
        c.close()
    for row in rows:
        until, left = float(row["pro_until"]), float(row["pro_until"]) - now
        stage = None
        if left <= 0:
            stage = "ended"
        elif left <= 15 * 60:
            stage = "15m"
        elif left <= 86400:
            stage = "1d" if left > 3 * 3600 else None
        elif left <= 3 * 86400:
            stage = "3d"
        if not stage:
            continue
        # One reminder per stage of one subscription (the key holds its end time).
        kind = "pro_expired" if stage == "ended" else "pro_expiring"
        key = f"pro:{stage}:{int(until)}"
        c = auth_db._conn()
        try:
            exists = c.execute("SELECT 1 FROM notifications WHERE user_id=? AND group_key=?", (int(row["id"]), key)).fetchone()
        finally:
            c.close()
        if not exists:
            add(int(row["id"]), kind, title="Pro", link="/?activate=1", meta={"stage": stage, "until": until}, group_key=key)


def _cleanup(now: float) -> None:
    c = auth_db._conn()
    try:
        c.execute("DELETE FROM notifications WHERE created_at<?", (now - KEEP_SECONDS,))
        c.commit()
    finally:
        c.close()


def maybe_periodic(interval: float = 600) -> None:
    """Pro reminders and the 7-day cleanup, at most every ``interval`` seconds."""
    global _last_periodic
    now = time.time()
    if now - _last_periodic < interval or not _periodic_lock.acquire(blocking=False):
        return
    try:
        _last_periodic = now
        _pro_reminders(now)
        _cleanup(now)
    except Exception:
        LOG.debug("notification maintenance failed", exc_info=True)
    finally:
        _periodic_lock.release()
