"""Durable, privacy-bounded content used by the operator control centre.

The module intentionally stores support metadata, notices and catalogue rules,
never uploaded source media, session cookies or provider credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import auth_db


CATALOG_FILE = Path(auth_db.DATA) / "steam_catalog_controls.json"
_catalog_lock = threading.RLock()
_TICKET_STATUSES = {"new", "working", "resolved", "closed"}
_ANNOUNCEMENT_LEVELS = {"info", "success", "warning"}
_ANNOUNCEMENT_AUDIENCES = {"all", "guests", "users", "pro"}


def _json_dict(value: str | None) -> dict:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def create_ticket(*, user_id: int | None, email: str, message: str, page: str, context: dict | None) -> dict:
    text = str(message or "").strip()
    if len(text) < 10 or len(text) > 2000:
        raise ValueError("Message must contain 10–2000 characters")
    page = str(page or "").split("?", 1)[0][:160]
    if not page.startswith("/") or any(ch in page for ch in "\r\n\t"):
        page = "/"
    source = context if isinstance(context, dict) else {}
    clean_context = {
        "language": str(source.get("language") or "")[:12],
        "viewport": str(source.get("viewport") or "")[:32],
        "browser": str(source.get("browser") or "")[:120],
        "job_id": str(source.get("job_id") or "")[:64],
    }
    ticket_id = secrets.token_hex(8)
    now = time.time()
    connection = auth_db._conn()
    try:
        connection.execute(
            """INSERT INTO support_tickets
               (id,user_id,email,message,page,context_json,status,admin_note,created_at,updated_at)
               VALUES (?,?,?,?,?,?,'new','',?,?)""",
            (ticket_id, int(user_id) if user_id else None, str(email or "")[:254], text, page,
             json.dumps(clean_context, ensure_ascii=False), now, now),
        )
        connection.commit()
    finally:
        connection.close()
    return {"ok": True, "ticket_id": ticket_id}


def tickets(status: str = "open", limit: int = 100) -> list[dict]:
    limit = max(1, min(250, int(limit or 100)))
    status = str(status or "open")
    where, params = "", []
    if status == "open":
        where, params = "WHERE t.status IN ('new','working')", []
    elif status in _TICKET_STATUSES:
        where, params = "WHERE t.status=?", [status]
    connection = auth_db._conn()
    try:
        rows = connection.execute(
            f"""SELECT t.id,t.user_id,t.email,t.message,t.page,t.context_json,t.status,
                       t.admin_note,t.created_at,t.updated_at,u.display_name,u.profile_username
                FROM support_tickets t LEFT JOIN users u ON u.id=t.user_id
                {where} ORDER BY t.updated_at DESC LIMIT ?""",
            [*params, limit],
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["context"] = _json_dict(item.pop("context_json", "{}"))
            result.append(item)
        return result
    finally:
        connection.close()


def update_ticket(ticket_id: str, status: str, note: str = "") -> dict:
    status = str(status or "")
    if status not in _TICKET_STATUSES:
        raise ValueError("Invalid ticket status")
    connection = auth_db._conn()
    try:
        cursor = connection.execute(
            "UPDATE support_tickets SET status=?,admin_note=?,updated_at=? WHERE id=?",
            (status, str(note or "").strip()[:2000], time.time(), str(ticket_id or "")),
        )
        connection.commit()
        if cursor.rowcount < 1:
            raise LookupError("Ticket not found")
    finally:
        connection.close()
    return {"ok": True}


def announcements(*, active_only: bool = False, audience: str = "all") -> list[dict]:
    now = time.time()
    where, params = "", []
    if active_only:
        where = "WHERE enabled=1 AND (starts_at IS NULL OR starts_at<=?) AND (ends_at IS NULL OR ends_at>?)"
        params = [now, now]
    connection = auth_db._conn()
    try:
        rows = connection.execute(
            f"""SELECT id,title_ru,title_en,body_ru,body_en,level,audience,enabled,
                       starts_at,ends_at,created_at,updated_at
                FROM admin_announcements {where} ORDER BY updated_at DESC""",
            params,
        ).fetchall()
        items = [dict(row) for row in rows]
    finally:
        connection.close()
    if active_only:
        allowed = {"all"}
        if audience in {"users", "pro"}:
            allowed.add("users")
        if audience == "pro":
            allowed.add("pro")
        if audience == "guests":
            allowed.add("guests")
        items = [item for item in items if item.get("audience") in allowed]
    for item in items:
        item["enabled"] = bool(item.get("enabled"))
    return items


def save_announcement(payload: dict) -> dict:
    announcement_id = str(payload.get("id") or secrets.token_hex(8))
    if not all(ch in "0123456789abcdef" for ch in announcement_id.lower()) or not 8 <= len(announcement_id) <= 40:
        raise ValueError("Invalid announcement id")
    level = str(payload.get("level") or "info")
    audience = str(payload.get("audience") or "all")
    if level not in _ANNOUNCEMENT_LEVELS or audience not in _ANNOUNCEMENT_AUDIENCES:
        raise ValueError("Invalid announcement options")
    title_ru = str(payload.get("title_ru") or "").strip()[:100]
    title_en = str(payload.get("title_en") or "").strip()[:100]
    body_ru = str(payload.get("body_ru") or "").strip()[:500]
    body_en = str(payload.get("body_en") or "").strip()[:500]
    if not body_ru and not body_en:
        raise ValueError("Announcement text is required")
    now = time.time()
    starts_at = float(payload["starts_at"]) if payload.get("starts_at") not in (None, "") else None
    ends_at = float(payload["ends_at"]) if payload.get("ends_at") not in (None, "") else None
    if starts_at and ends_at and ends_at <= starts_at:
        raise ValueError("End must be later than start")
    connection = auth_db._conn()
    try:
        exists = connection.execute("SELECT id,created_at FROM admin_announcements WHERE id=?", (announcement_id,)).fetchone()
        if exists:
            connection.execute(
                """UPDATE admin_announcements SET title_ru=?,title_en=?,body_ru=?,body_en=?,level=?,
                   audience=?,enabled=?,starts_at=?,ends_at=?,updated_at=? WHERE id=?""",
                (title_ru, title_en, body_ru, body_en, level, audience, int(payload.get("enabled") is not False),
                 starts_at, ends_at, now, announcement_id),
            )
        else:
            connection.execute(
                """INSERT INTO admin_announcements
                   (id,title_ru,title_en,body_ru,body_en,level,audience,enabled,starts_at,ends_at,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (announcement_id, title_ru, title_en, body_ru, body_en, level, audience,
                 int(payload.get("enabled") is not False), starts_at, ends_at, now, now),
            )
        connection.commit()
    finally:
        connection.close()
    return {"ok": True, "id": announcement_id}


def delete_announcement(announcement_id: str) -> dict:
    connection = auth_db._conn()
    try:
        cursor = connection.execute("DELETE FROM admin_announcements WHERE id=?", (str(announcement_id or ""),))
        connection.commit()
        if cursor.rowcount < 1:
            raise LookupError("Announcement not found")
    finally:
        connection.close()
    return {"ok": True}


def _catalog_source() -> dict:
    try:
        value = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def _write_catalog(value: dict) -> None:
    CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="steam-controls-", suffix=".json", dir=str(CATALOG_FILE.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o640)
        os.replace(temporary, CATALOG_FILE)
    finally:
        Path(temporary).unlink(missing_ok=True)


def catalog_key(item: dict) -> str:
    identity = str(item.get("buy_url") or item.get("image") or item.get("name") or "").strip()
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20] if identity else ""


def catalog_rules() -> list[dict]:
    with _catalog_lock:
        source = _catalog_source()
    return sorted((dict(value, key=key) for key, value in source.items() if isinstance(value, dict)), key=lambda x: x.get("updated_at", 0), reverse=True)


def save_catalog_rule(payload: dict) -> dict:
    identity = str(payload.get("identity") or "").strip()[:1000]
    name = str(payload.get("name") or identity or "Steam item").strip()[:120]
    if not identity:
        raise ValueError("Steam item URL or image URL is required")
    parsed = urlparse(identity)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Only an http(s) Steam or image URL is allowed")
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    rule = {"identity": identity, "name": name, "hidden": bool(payload.get("hidden")),
            "featured": bool(payload.get("featured")), "note": str(payload.get("note") or "")[:240],
            "updated_at": time.time()}
    with _catalog_lock:
        source = _catalog_source()
        source[key] = rule
        _write_catalog(source)
    return {"ok": True, "key": key}


def delete_catalog_rule(key: str) -> dict:
    with _catalog_lock:
        source = _catalog_source()
        if str(key) not in source:
            raise LookupError("Catalog rule not found")
        source.pop(str(key), None)
        _write_catalog(source)
    return {"ok": True}


def apply_catalog_rules(items: list[dict]) -> list[dict]:
    with _catalog_lock:
        rules = _catalog_source()
    output = []
    for source in items:
        item = dict(source)
        key = catalog_key(item)
        rule = rules.get(key) if key else None
        if rule and rule.get("hidden"):
            continue
        item["featured"] = bool(rule and rule.get("featured"))
        output.append(item)
    output.sort(key=lambda item: (not item.get("featured"),))
    return output


def backup_snapshot() -> dict:
    configured = Path(os.environ.get("BACKUP_DIR") or (Path(auth_db.DATA).parent / "backups"))
    files = []
    try:
        if configured.is_dir():
            for path in configured.iterdir():
                if path.is_file() and path.suffix.lower() in {".sql", ".dump", ".gz", ".zip", ".tar"}:
                    stat = path.stat()
                    files.append({"name": path.name[:180], "size": stat.st_size, "updated_at": stat.st_mtime})
    except OSError:
        files = []
    files.sort(key=lambda item: item["updated_at"], reverse=True)
    latest = files[0] if files else None
    age_hours = (time.time() - latest["updated_at"]) / 3600 if latest else None
    state = "ok" if latest and age_hours <= 36 else ("warn" if latest else "down")
    return {"state": state, "directory": str(configured), "latest": latest,
            "age_hours": round(age_hours, 1) if age_hours is not None else None,
            "files": files[:20], "restore_verified": False,
            "note": "Факт восстановления нужно проверять отдельно на тестовой базе."}
