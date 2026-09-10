"""First-party, privacy-conscious product analytics.

The module deliberately exposes two operations: record an allowlisted event and
build an aggregate report. Callers never handle SQL, identifiers or retention.
Raw IP addresses, user agents, e-mail addresses and media names are not stored.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import auth_db


LOGGER = logging.getLogger("sm.analytics")
RETENTION_DAYS = max(30, min(365, int(os.environ.get("ANALYTICS_RETENTION_DAYS") or 90)))

PUBLIC_EVENTS = frozenset({
    "home_view",
    "tool_open",
    "file_added",
    "process_failed",
    "extension_launch_clicked",
    "extension_launch_confirmed",
})
SERVER_EVENTS = frozenset({
    "process_success",
    "process_failed",
    "zip_download",
    "registration_success",
    "pro_activated",
})
ALL_EVENTS = PUBLIC_EVENTS | SERVER_EVENTS

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_SAFE_SESSION = re.compile(r"^[A-Fa-f0-9-]{20,80}$")
_last_cleanup = 0.0
_cleanup_lock = threading.Lock()


def _open_connection():
    """Internal adapter seam used by tests and the production DB backend."""
    return auth_db._conn()


def _digest(kind: str, value: str) -> str:
    key = (os.environ.get("SECRET_KEY") or "local-analytics-development-key").encode("utf-8")
    return hmac.new(key, f"{kind}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def user_hash(user_id: int | str) -> str:
    """Stable pseudonymous key used to export or erase one user's events."""
    return _digest("user", str(int(user_id)))


def _clean(value: Any, default: str = "") -> str:
    text = str(value or "").strip().lower()[:64]
    return text if _SAFE_TOKEN.fullmatch(text) else default


def _language(value: Any) -> str:
    language = str(value or "").strip().lower().split("-", 1)[0]
    return language if language in {"ru", "en", "de", "tr", "fr", "uk", "es", "pt"} else "other"


def _path(value: Any) -> str:
    text = str(value or "").split("?", 1)[0].strip()[:160]
    if not text.startswith("/") or any(ch in text for ch in "\r\n\t"):
        return ""
    parts = [part for part in text.split("/") if part]
    if parts and parts[0].lower() in {"ru", "en", "de", "tr", "fr", "uk", "es", "pt"}:
        parts = parts[1:]
    if not parts:
        return "/"
    first = parts[0].lower()
    if first in {"profile", "preview"} and len(parts) > 1:
        return f"/{first}/:item"
    if first == "admin":
        return "/admin"
    return f"/{first}" if _SAFE_TOKEN.fullmatch(first) else ""


def request_context(request: Any) -> dict[str, str]:
    """Return the only request fields analytics may persist."""
    raw_session = str(request.headers.get("x-sm-analytics-session") or "").strip()
    session_hash = _digest("session", raw_session) if _SAFE_SESSION.fullmatch(raw_session) else ""
    explicit_language = request.headers.get("x-sm-language") or ""
    path = str(getattr(getattr(request, "url", None), "path", "") or "")
    if not explicit_language:
        first = path.strip("/").split("/", 1)[0]
        explicit_language = first or request.headers.get("accept-language") or ""
    return {"session_hash": session_hash, "language": _language(explicit_language), "path": _path(path)}


def _maybe_cleanup(now: float) -> None:
    global _last_cleanup
    if now - _last_cleanup < 3600:
        return
    with _cleanup_lock:
        if now - _last_cleanup < 3600:
            return
        _last_cleanup = now
        connection = None
        try:
            connection = _open_connection()
            connection.execute("DELETE FROM analytics_events WHERE created_at<?", (now - RETENTION_DAYS * 86400,))
            connection.commit()
        except Exception:
            LOGGER.exception("analytics cleanup failed")
            if connection:
                connection.rollback()
        finally:
            if connection:
                connection.close()


def record(
    event_name: str,
    *,
    request: Any | None = None,
    session_id: str = "",
    session_hash: str = "",
    user_id: int | str | None = None,
    language: str = "",
    path: str = "",
    properties: dict[str, Any] | None = None,
    event_key: str = "",
    now: float | None = None,
) -> bool:
    """Record one event without allowing analytics failure to affect the product."""
    event_name = _clean(event_name)
    if event_name not in ALL_EVENTS:
        return False
    current = float(now if now is not None else time.time())
    context = request_context(request) if request is not None else {}
    if _SAFE_SESSION.fullmatch(str(session_id or "").strip()):
        session_hash = _digest("session", str(session_id).strip())
    else:
        session_hash = session_hash if re.fullmatch(r"[a-f0-9]{32}", session_hash or "") else context.get("session_hash", "")
    language = _language(language or context.get("language"))
    path = _path(path or context.get("path"))
    props = properties if isinstance(properties, dict) else {}
    clean_props = {
        "tool": _clean(props.get("tool")),
        "mode": _clean(props.get("mode")),
        "method": _clean(props.get("method")),
        "reason": _clean(props.get("reason")),
        "file_type": _clean(props.get("file_type")),
        "size_bucket": _clean(props.get("size_bucket")),
    }
    try:
        value_int = max(0, min(2_147_483_647, int(props.get("value") or 0)))
    except (TypeError, ValueError):
        value_int = 0
    try:
        user_hash = _digest("user", str(int(user_id))) if user_id not in (None, "") else ""
    except (TypeError, ValueError):
        user_hash = ""
    event_key = str(event_key or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_.:-]{16,128}", event_key):
        event_key = secrets.token_hex(16)
    day_key = datetime.fromtimestamp(current, timezone.utc).strftime("%Y-%m-%d")
    connection = None
    try:
        connection = _open_connection()
        connection.execute(
            """INSERT OR IGNORE INTO analytics_events
               (event_key,event_name,session_hash,user_hash,language,path,tool,mode,method,reason,file_type,size_bucket,value_int,day_key,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event_key, event_name, session_hash or None, user_hash or None,
                language, path, clean_props["tool"], clean_props["mode"],
                clean_props["method"], clean_props["reason"], clean_props["file_type"],
                clean_props["size_bucket"], value_int, day_key, current,
            ),
        )
        connection.commit()
    except Exception:
        LOGGER.exception("analytics record failed event=%s", event_name)
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            connection.close()
    _maybe_cleanup(current)
    return True


def report(days: int = 30, *, now: float | None = None) -> dict[str, Any]:
    """Return an aggregate report; never return individual event rows."""
    days = max(1, min(90, int(days or 30)))
    current = float(now if now is not None else time.time())
    _maybe_cleanup(current)
    since = current - days * 86400
    connection = _open_connection()
    try:
        totals_rows = connection.execute(
            """SELECT event_name, COUNT(*) AS total,
                      COUNT(DISTINCT session_hash) AS unique_sessions
               FROM analytics_events WHERE created_at>=?
               GROUP BY event_name""",
            (since,),
        ).fetchall()
        daily_rows = connection.execute(
            """SELECT day_key,event_name,COUNT(*) AS total
               FROM analytics_events WHERE created_at>=?
               GROUP BY day_key,event_name ORDER BY day_key""",
            (since,),
        ).fetchall()
        tool_rows = connection.execute(
            """SELECT tool,COUNT(*) AS total,COUNT(DISTINCT session_hash) AS unique_sessions
               FROM analytics_events WHERE created_at>=? AND event_name='tool_open' AND tool!=''
               GROUP BY tool ORDER BY total DESC""",
            (since,),
        ).fetchall()
        failure_rows = connection.execute(
            """SELECT reason,COUNT(*) AS total FROM analytics_events
               WHERE created_at>=? AND event_name='process_failed'
               GROUP BY reason ORDER BY total DESC""",
            (since,),
        ).fetchall()
        language_rows = connection.execute(
            """SELECT language,COUNT(DISTINCT session_hash) AS visitors
               FROM analytics_events WHERE created_at>=? AND event_name='home_view'
               GROUP BY language ORDER BY visitors DESC""",
            (since,),
        ).fetchall()
        mode_rows = connection.execute(
            """SELECT mode,COUNT(*) AS total FROM analytics_events
               WHERE created_at>=? AND event_name='process_success' AND mode!=''
               GROUP BY mode ORDER BY total DESC""",
            (since,),
        ).fetchall()
        performance_rows = connection.execute(
            """SELECT mode,AVG(value_int) AS average_ms FROM analytics_events
               WHERE created_at>=? AND event_name='process_success' AND value_int>0
               GROUP BY mode ORDER BY average_ms DESC""",
            (since,),
        ).fetchall()
    finally:
        connection.close()

    totals = {str(row["event_name"]): {"total": int(row["total"] or 0), "unique": int(row["unique_sessions"] or 0)} for row in totals_rows}
    by_day: dict[str, dict[str, int]] = defaultdict(dict)
    for row in daily_rows:
        by_day[str(row["day_key"])][str(row["event_name"])] = int(row["total"] or 0)
    funnel_names = [
        "home_view", "tool_open", "file_added", "process_success", "zip_download",
        "extension_launch_confirmed", "registration_success", "pro_activated",
    ]
    funnel = []
    previous = 0
    for index, name in enumerate(funnel_names):
        item = totals.get(name, {"total": 0, "unique": 0})
        count = item["unique"] or item["total"]
        conversion = 100.0 if index == 0 else (round(count / previous * 100, 1) if previous else 0.0)
        funnel.append({"event": name, "count": count, "conversion": conversion})
        previous = count
    return {
        "ok": True,
        "days": days,
        "retention_days": RETENTION_DAYS,
        "generated_at": current,
        "totals": totals,
        "funnel": funnel,
        "daily": [{"day": day, "events": events} for day, events in sorted(by_day.items())],
        "tools": [dict(row) for row in tool_rows],
        "failures": [dict(row) for row in failure_rows],
        "languages": [dict(row) for row in language_rows],
        "modes": [dict(row) for row in mode_rows],
        "performance": [dict(row) for row in performance_rows],
    }
