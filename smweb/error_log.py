"""Server errors kept in the database (2026-10-01).

Docker logs disappear whenever a container is recreated (every deploy), so the
owner could not see what had failed before an update. Every ERROR log record of
the app and the worker (with its traceback) and every unexplained HTTP 500 is
stored in ``server_errors``, grouped by a fingerprint: the same bug is one row
with a counter. The admin console lists them ("Ошибки сайта"); a new error, or
one that comes back after being marked resolved, is sent to the owner's bot.

Nothing here may raise or log at ERROR level: it runs inside ``logging``.
Writes go through a small queue and a background thread, so a request never
waits for the database because something failed.
"""
from __future__ import annotations

import contextvars
import hashlib
import logging
import os
import queue
import re
import sys
import threading
import time
import traceback
from pathlib import Path

KEEP_DAYS = 14
MAX_ROWS = 500
TRACE_LIMIT = 6000
# 502/503 are deliberate answers (Steam unreachable, maintenance, "busy"), not bugs.
IGNORED_STATUSES = {502, 503}
FIELDS = ("id", "source", "kind", "title", "location", "logger", "method", "path", "status", "message",
          "trace", "request_id", "count", "first_seen", "last_seen", "resolved_at")

_REQUEST: contextvars.ContextVar[dict | None] = contextvars.ContextVar("sm_error_request", default=None)
_QUEUE: "queue.Queue[dict]" = queue.Queue(maxsize=500)
_LOCAL = threading.local()
_SOURCE = "app"
_STARTED = False
_LOG = logging.getLogger(__name__)
_PROJECT = str(Path(__file__).resolve().parent.parent)


# ---------------------------------------------------------------- helpers
def _scrub(text: str, limit: int) -> str:
    try:
        from smweb.job_diagnostics import scrub
        value = scrub(text)
    except Exception:
        value = re.sub(r"https?://\S+", "[url]", str(text or ""))
    return value.replace(_PROJECT, "").strip()[:limit]


def _shape(text: str) -> str:
    """Stable form of a message/path for grouping: ids and numbers do not split a bug."""
    value = re.sub(r"[0-9a-f]{12,}", "<id>", str(text or ""), flags=re.I)
    value = re.sub(r"\d+", "#", value)
    return value[:300]


def _frame(tb) -> str:
    """Innermost frame of our own code (file:line in function), else the innermost one."""
    frames = traceback.extract_tb(tb) if tb else []
    own = [f for f in frames if f.filename.startswith(_PROJECT) and "site-packages" not in f.filename]
    pick = (own or frames)[-1] if (own or frames) else None
    if not pick:
        return ""
    name = pick.filename.replace(_PROJECT, "").lstrip("\\/").replace("\\", "/")
    if "site-packages" in name:
        name = "site-packages" + name.split("site-packages", 1)[1]
    return f"{name}:{pick.lineno} in {pick.name}"


def _fingerprint(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8", "replace")).hexdigest()[:20]


# ---------------------------------------------------------------- capture
def capture_record(record: logging.LogRecord) -> None:
    """Turn one ERROR log record into a queued entry (called by the logging handler)."""
    ctx = _REQUEST.get()
    exc = record.exc_info[1] if record.exc_info else None
    if exc is not None and getattr(exc, "_sm_error_logged", False):
        return  # the same exception logged twice (route + global handler): count it once
    message = _scrub(record.getMessage(), 1000)
    if exc is not None:
        try:
            exc._sm_error_logged = True
        except Exception:
            pass
        location = _frame(record.exc_info[2])
        first = (str(exc).splitlines() or [""])[0]
        title = _scrub(f"{type(exc).__name__}: {first}" if first else type(exc).__name__, 240)
        trace = _scrub("".join(traceback.format_exception(*record.exc_info)), TRACE_LIMIT)
        fingerprint = _fingerprint("exc", type(exc).__name__, location or _shape(first))
    else:
        location = f"{record.pathname.replace(_PROJECT, '').lstrip(chr(92) + '/')}:{record.lineno}".replace("\\", "/")
        title, trace = message[:240], ""
        fingerprint = _fingerprint("log", record.name, _shape(record.msg if isinstance(record.msg, str) else message))
    if ctx is not None:
        ctx["logged"] = True
        method, path, request_id = ctx.get("method", ""), ctx.get("path", ""), _request_id(ctx)
    else:
        method, path, request_id = getattr(exc, "_sm_request", None) or ("", "", "")
    _enqueue({"id": fingerprint, "kind": "exception" if exc is not None else "log", "title": title,
              "location": location, "logger": record.name, "message": message, "trace": trace,
              "method": method, "path": _scrub(path, 300), "status": None, "request_id": request_id})


def capture_http(method: str, path: str, status: int, request_id: str = "") -> None:
    """A 5xx answer that no ERROR log explained (e.g. a route returned 500 itself)."""
    _enqueue({"id": _fingerprint("http", method, _shape(path), str(status)), "kind": "http",
              "title": f"HTTP {status} без записи в логе", "location": "", "logger": "", "message": "",
              "trace": "", "method": method, "path": _scrub(path, 300), "status": int(status),
              "request_id": request_id})


def _request_id(ctx: dict | None) -> str:
    if not ctx:
        return ""
    state = (ctx.get("scope") or {}).get("state") or {}
    try:
        return str(state.get("request_id") or "")[:40]
    except Exception:
        return ""


def _enqueue(item: dict) -> None:
    item["source"] = _SOURCE
    item["at"] = time.time()
    try:
        _QUEUE.put_nowait(item)
    except queue.Full:
        pass  # a storm of errors: the first 500 are enough to see the problem


# ---------------------------------------------------------------- storage
def _store(item: dict) -> tuple[bool, bool, int]:
    """Insert or bump one group. Returns (new, reopened, count)."""
    import auth_db
    c = auth_db._conn()
    try:
        row = c.execute("SELECT count, resolved_at FROM server_errors WHERE id=?", (item["id"],)).fetchone()
        values = (item["source"], item["kind"], item["title"], item["location"], item["logger"], item["method"],
                  item["path"], item["status"], item["message"], item["trace"], item["request_id"])
        if row:
            c.execute("UPDATE server_errors SET source=?, kind=?, title=?, location=?, logger=?, method=?, path=?, "
                      "status=?, message=?, trace=?, request_id=?, count=count+1, last_seen=?, resolved_at=NULL "
                      "WHERE id=?", (*values, item["at"], item["id"]))
            new, reopened, count = False, row["resolved_at"] is not None, int(row["count"] or 0) + 1
        else:
            c.execute("INSERT INTO server_errors (id, source, kind, title, location, logger, method, path, status, "
                      "message, trace, request_id, count, first_seen, last_seen) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)", (item["id"], *values, item["at"], item["at"]))
            new, reopened, count = True, False, 1
        c.commit()
        return new, reopened, count
    finally:
        c.close()


def _telegram(item: dict, reopened: bool) -> None:
    from smweb import admin_notify
    if not admin_notify.configured():
        return
    allowed, _ = admin_notify._throttled(f"srv-error:{item['id']}", 3600)
    if not allowed:
        return
    import html
    where = " ".join(x for x in (item.get("method"), item.get("path")) if x) or item.get("source", "")
    head = "🔁 <b>Ошибка сайта вернулась</b>" if reopened else "🛑 <b>Новая ошибка сайта</b>"
    base = (os.environ.get("APP_URL") or "").rstrip("/")
    link = f"\n{base}/admin/analytics#errors" if base.startswith("https://") else ""
    admin_notify.send(f"{head} ({html.escape(item['source'])})\n<code>{html.escape(item['title'])[:400]}</code>\n"
                      f"Где: {html.escape(where)[:200]}"
                      + (f"\nКод: {html.escape(item['location'])[:200]}" if item.get("location") else "") + link)


def _process(item: dict) -> None:
    _LOCAL.busy = True
    try:
        new, reopened, _ = _store(item)
        if new or reopened:
            _telegram(item, reopened)
    except Exception:
        pass  # the table may not exist yet or the DB is down: never loop back into logging
    finally:
        _LOCAL.busy = False


def flush() -> int:
    """Write everything queued now (tests, shutdown). Returns how many entries were written."""
    done = 0
    while True:
        try:
            item = _QUEUE.get_nowait()
        except queue.Empty:
            return done
        _process(item)
        done += 1


def _writer() -> None:
    while True:
        item = _QUEUE.get()
        _process(item)


# ---------------------------------------------------------------- admin
def _row(row) -> dict:
    item = dict(row)
    item["count"] = int(item.get("count") or 0)
    return item


def listing(status: str = "open", limit: int = 200) -> dict:
    import auth_db
    where = {"open": "WHERE resolved_at IS NULL", "resolved": "WHERE resolved_at IS NOT NULL"}.get(status, "")
    c = auth_db._conn()
    try:
        rows = c.execute(f"SELECT {','.join(FIELDS)} FROM server_errors {where} ORDER BY last_seen DESC LIMIT ?",
                         (max(1, min(500, int(limit))),)).fetchall()
        open_count = c.execute("SELECT COUNT(*) AS n FROM server_errors WHERE resolved_at IS NULL").fetchone()["n"]
        day = c.execute("SELECT COALESCE(SUM(count),0) AS n FROM server_errors WHERE last_seen>?",
                        (time.time() - 86400,)).fetchone()["n"]
    finally:
        c.close()
    return {"items": [_row(r) for r in rows], "open": int(open_count or 0), "recent": int(day or 0)}


def resolve(error_id: str | None = None) -> int:
    """Mark one group (or every open one when error_id is None) as resolved."""
    import auth_db
    c = auth_db._conn()
    try:
        if error_id:
            cur = c.execute("UPDATE server_errors SET resolved_at=? WHERE id=? AND resolved_at IS NULL",
                            (time.time(), str(error_id)[:40]))
        else:
            cur = c.execute("UPDATE server_errors SET resolved_at=? WHERE resolved_at IS NULL", (time.time(),))
        c.commit()
        return int(cur.rowcount or 0)
    finally:
        c.close()


def delete_resolved() -> int:
    import auth_db
    c = auth_db._conn()
    try:
        cur = c.execute("DELETE FROM server_errors WHERE resolved_at IS NOT NULL")
        c.commit()
        return int(cur.rowcount or 0)
    finally:
        c.close()


def cleanup() -> None:
    """Forget groups not seen for KEEP_DAYS and keep at most MAX_ROWS (job cleaner calls it)."""
    import auth_db
    c = auth_db._conn()
    try:
        c.execute("DELETE FROM server_errors WHERE last_seen<?", (time.time() - KEEP_DAYS * 86400,))
        extra = c.execute("SELECT COUNT(*) AS n FROM server_errors").fetchone()["n"] - MAX_ROWS
        if extra > 0:
            c.execute("DELETE FROM server_errors WHERE id IN (SELECT id FROM server_errors ORDER BY last_seen ASC LIMIT ?)",
                      (int(extra),))
        c.commit()
    finally:
        c.close()


# ---------------------------------------------------------------- wiring
class _Handler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if getattr(_LOCAL, "busy", False) or record.name == __name__:
            return
        _LOCAL.busy = True
        try:
            capture_record(record)
        except Exception:
            pass
        finally:
            _LOCAL.busy = False


class ErrorCaptureMiddleware:
    """Outermost ASGI layer: request context for the log handler + unexplained 5xx answers."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        ctx = {"method": scope.get("method", ""), "path": scope.get("path", ""), "scope": scope, "logged": False}
        token = _REQUEST.set(ctx)
        seen = {"status": 0}

        async def watch(message):
            if message.get("type") == "http.response.start":
                seen["status"] = int(message.get("status") or 0)
            await send(message)

        try:
            await self.app(scope, receive, watch)
        except BaseException as exc:
            # Starlette's global handler runs outside this layer: keep the request on the exception.
            try:
                exc._sm_request = (ctx["method"], ctx["path"], _request_id(ctx))
            except Exception:
                pass
            raise
        finally:
            _REQUEST.reset(token)
            status = seen["status"]
            if status >= 500 and status not in IGNORED_STATUSES and not ctx["logged"]:
                capture_http(ctx["method"], ctx["path"], status, _request_id(ctx))


def install(source: str) -> None:
    """Attach the handler to the root logger and start the writer (app and worker)."""
    global _SOURCE, _STARTED
    _SOURCE = source
    if _STARTED or os.environ.get("ERROR_LOG", "1") == "0" or "pytest" in sys.modules:
        return
    _STARTED = True
    handler = _Handler(level=logging.ERROR)
    logging.getLogger().addHandler(handler)
    threading.Thread(target=_writer, daemon=True, name="error-log").start()
