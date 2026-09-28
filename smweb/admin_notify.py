"""Telegram notifications for the site owner, sent through the shop bot.

Uses ADMIN_BOT_TOKEN (the same bot the owner administers) and ADMIN_BOT_CHAT_ID.
Messages go out on a background thread and never raise: a notification must
not break the request or job that triggered it.  Noisy events are throttled
with Redis so a burst of failures becomes one message with a count.
"""
from __future__ import annotations

import html
import json
import os
import shutil
import threading
import time
import urllib.request

_last_disk_check = 0.0


def configured() -> bool:
    return bool((os.environ.get("ADMIN_BOT_TOKEN") or "").strip() and
                (os.environ.get("ADMIN_BOT_CHAT_ID") or "").strip())


def _post(text: str, buttons: list[list[dict]] | None) -> None:
    token = (os.environ.get("ADMIN_BOT_TOKEN") or "").strip()
    payload = {"chat_id": (os.environ.get("ADMIN_BOT_CHAT_ID") or "").strip(), "text": text[:4000],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request, timeout=8).read()
    except Exception as exc:  # the owner simply misses one message
        print(f"[notify] telegram send failed: {type(exc).__name__}", flush=True)


def send(text: str, buttons: list[list[dict]] | None = None) -> None:
    if configured():
        threading.Thread(target=_post, args=(text, buttons), daemon=True, name="admin-notify").start()


def _throttled(key: str, window: int) -> tuple[bool, int]:
    """(send now?, events suppressed since the previous message)."""
    import redis_store as rs
    r = rs._r()
    if not r:
        return True, 0
    try:
        if r.set(f"sm:notify:{key}:gate", "1", nx=True, ex=window):
            skipped = int(r.getset(f"sm:notify:{key}:skipped", 0) or 0)
            return True, skipped
        r.incr(f"sm:notify:{key}:skipped")
        return False, 0
    except Exception:
        return True, 0


def ticket_created(ticket_id: str, email: str, message: str, page: str) -> None:
    text = (f"📩 <b>Новое обращение</b>\n"
            f"От: {html.escape(email or 'без почты')}\nСтраница: {html.escape(page or '/')}\n\n"
            f"{html.escape(message)[:3000]}")
    send(text, [[{"text": "✍️ Ответить", "callback_data": f"tk:{ticket_id}"},
                 {"text": "✅ Закрыть", "callback_data": f"tkc:{ticket_id}"}]])


def job_failed(job_id: str, fields: dict) -> None:
    if not configured():
        return
    allowed, skipped = _throttled("job-error", 600)
    if not allowed:
        return
    try:
        import redis_store as rs
        job = rs.job_get(job_id) or {}
    except Exception:
        job = {}
    kind = job.get("kind") or "process"
    detail = fields.get("error_detail") or fields.get("error") or job.get("error") or ""
    extra = f"\n\n+ ещё {skipped} за прошлые 10 минут" if skipped else ""
    send(f"❗ <b>Ошибка обработки</b> ({html.escape(str(kind))})\n"
         f"<code>{html.escape(str(detail))[:600]}</code>\nЗадание: <code>{html.escape(job_id)}</code>{extra}")


def paid_import_used(profile_url: str) -> None:
    allowed, skipped = _throttled("brightdata", 6 * 3600)
    if allowed:
        more = f" (+{skipped} за 6 часов)" if skipped else ""
        send("💸 Импорт профиля ушёл в платный Bright Data: сервер и ретранслятор не смогли загрузить "
             f"профиль{more}.\n{html.escape(profile_url)}")


def check_disk(path: str) -> None:
    """At most hourly; warns when the data disk has under 10 % or 5 GB free."""
    global _last_disk_check
    if time.time() - _last_disk_check < 3600 or not configured():
        return
    _last_disk_check = time.time()
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return
    free_gb = usage.free / 1024 ** 3
    if usage.free / usage.total < .10 or free_gb < 5:
        allowed, _ = _throttled("disk", 12 * 3600)
        if allowed:
            send(f"💾 <b>Мало места на сервере</b>: свободно {free_gb:.1f} ГБ из {usage.total / 1024 ** 3:.0f} ГБ.")
