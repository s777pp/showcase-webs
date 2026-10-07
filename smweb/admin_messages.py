"""Messages from the site owner to users (2026-10-07, owner: "send users messages they notice at once").

The admin console ("Сообщения") writes one ``notifications`` row per recipient with kind
``admin_message``, so the bell, "mark read", export and account deletion work unchanged.
``meta`` carries the message id, the English copy and ``popup``: while such a row is unread,
``/api/notifications/unread`` returns it and ``site-bell.js`` shows it as a window over the page
(on the next page load, or within a minute in an open tab). Closing the window marks it read.

Audiences: ``users`` (ids, e-mails, nicknames or SteamID64 typed by the owner), ``all``,
``pro``, ``free``. A broadcast is one ``INSERT ... SELECT``. The history lives in
``admin_messages``; read counts come from the rows (index on ``group_key``). A message can be
recalled: its unread and read rows are deleted. Rows of these messages stay 30 days
(``notify._cleanup``), the history 365 days.
"""
from __future__ import annotations

import json
import re
import secrets
import time

import auth_db

KIND = "admin_message"
AUDIENCES = ("users", "all", "pro", "free")
KEEP_SECONDS = 30 * 86400
HISTORY_SECONDS = 365 * 86400
TITLE_MAX = 120
BODY_MAX = 1500
MAX_TARGETS = 200


def _pro_sql(now: float) -> tuple[str, list]:
    return "(COALESCE(u.is_pro,0)=1 AND (u.pro_until IS NULL OR u.pro_until>?))", [now]


def _audience_where(audience: str, now: float) -> tuple[str, list]:
    if audience == "pro":
        return _pro_sql(now)
    if audience == "free":
        sql, params = _pro_sql(now)
        return f"NOT {sql}", params
    return "1=1", []


def clean_link(value: str) -> str:
    """Site paths ("/app#loop") or https links only."""
    link = str(value or "").strip()[:300]
    if not link:
        return ""
    if link.startswith("/") and not link.startswith("//"):
        return link
    if re.match(r"^https://[^\s/]+", link, re.I):
        return link
    raise ValueError("Ссылка должна начинаться с / (страница сайта) или https://")


def _text(value, limit: int) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()[:limit]


def resolve_targets(raw) -> tuple[list[int], list[str]]:
    """Ids, e-mails, nicknames or SteamID64 (comma, space or line separated) -> user ids + not found."""
    if isinstance(raw, list):
        parts = [str(item) for item in raw]
    else:
        parts = re.split(r"[\s,;]+", str(raw or ""))
    parts = [p.strip() for p in parts if p.strip()][:MAX_TARGETS]
    found: list[int] = []
    missing: list[str] = []
    c = auth_db._conn()
    try:
        for part in parts:
            key = part.lower().lstrip("@")
            row = None
            if key.isdigit() and len(key) < 15:
                row = c.execute("SELECT id FROM users WHERE id=?", (int(key),)).fetchone()
            elif key.isdigit():
                row = c.execute("SELECT id FROM users WHERE steam_id=?", (key,)).fetchone()
            elif "@" in key:
                row = c.execute("SELECT id FROM users WHERE lower(email)=?", (key,)).fetchone()
            else:
                row = c.execute("""SELECT id FROM users WHERE lower(COALESCE(profile_username,''))=?
                                   OR lower(COALESCE(display_name,''))=? ORDER BY id LIMIT 1""", (key, key)).fetchone()
            if row:
                if int(row["id"]) not in found:
                    found.append(int(row["id"]))
            else:
                missing.append(part)
    finally:
        c.close()
    return found, missing


def count(audience: str, targets=None) -> dict:
    """How many accounts a message would reach (shown before sending)."""
    audience = audience if audience in AUDIENCES else "users"
    if audience == "users":
        ids, missing = resolve_targets(targets)
        return {"ok": True, "count": len(ids), "missing": missing}
    where, params = _audience_where(audience, time.time())
    c = auth_db._conn()
    try:
        n = c.execute(f"SELECT COUNT(*) AS n FROM users u WHERE {where}", params).fetchone()["n"]
    finally:
        c.close()
    return {"ok": True, "count": int(n or 0), "missing": []}


def send(body: dict) -> dict:
    audience = str(body.get("audience") or "users")
    if audience not in AUDIENCES:
        raise ValueError("Неизвестная аудитория")
    title_ru = _text(body.get("title_ru"), TITLE_MAX)
    text_ru = _text(body.get("body_ru"), BODY_MAX)
    title_en = _text(body.get("title_en"), TITLE_MAX)
    text_en = _text(body.get("body_en"), BODY_MAX)
    if not title_ru:
        raise ValueError("Нужен заголовок на русском")
    if (text_en or title_en) and not title_en:
        raise ValueError("Для английской версии нужен заголовок")
    link = clean_link(body.get("link"))
    popup = body.get("popup") is not False
    message_id = secrets.token_hex(6)
    meta = {"msg": message_id, "popup": popup}
    if title_en:
        meta["en"] = {"title": title_en, "body": text_en}
    payload = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    now = time.time()
    group_key = f"msg:{message_id}"
    missing: list[str] = []
    target_label = ""
    c = auth_db._conn()
    try:
        if audience == "users":
            ids, missing = resolve_targets(body.get("targets"))
            if not ids:
                raise ValueError("Не найден ни один получатель" + (": " + ", ".join(missing[:5]) if missing else ""))
            for uid in ids:
                c.execute("""INSERT INTO notifications(user_id, kind, body, is_read, created_at, title, link, meta_json, group_key)
                             VALUES (?,?,?,0,?,?,?,?,?)""", (uid, KIND, text_ru, now, title_ru, link, payload, group_key))
            recipients = len(ids)
            target_label = ",".join(str(uid) for uid in ids)[:2000]
        else:
            where, params = _audience_where(audience, now)
            cur = c.execute(f"""INSERT INTO notifications(user_id, kind, body, is_read, created_at, title, link, meta_json, group_key)
                                SELECT u.id, CAST(? AS TEXT), CAST(? AS TEXT), 0, ?, CAST(? AS TEXT),
                                       CAST(? AS TEXT), CAST(? AS TEXT), CAST(? AS TEXT) FROM users u WHERE {where}""",
                            [KIND, text_ru, now, title_ru, link, payload, group_key, *params])
            recipients = max(0, int(cur.rowcount or 0))
        c.execute("""INSERT INTO admin_messages(id, created_at, audience, targets, title_ru, body_ru, title_en, body_en, link, popup, recipients)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (message_id, now, audience, target_label, title_ru, text_ru, title_en, text_en, link, 1 if popup else 0, recipients))
        c.commit()
    finally:
        c.close()
    return {"ok": True, "id": message_id, "recipients": recipients, "missing": missing}


def history(limit: int = 50) -> list[dict]:
    c = auth_db._conn()
    try:
        c.execute("DELETE FROM admin_messages WHERE created_at<?", (time.time() - HISTORY_SECONDS,))
        c.commit()
        rows = [dict(r) for r in c.execute("SELECT * FROM admin_messages ORDER BY created_at DESC LIMIT ?",
                                           (max(1, min(int(limit), 200)),)).fetchall()]
        for row in rows:
            stats = c.execute("SELECT COUNT(*) AS n, SUM(is_read) AS r FROM notifications WHERE group_key=?",
                              (f"msg:{row['id']}",)).fetchone()
            row["delivered"] = int(stats["n"] or 0)
            row["read"] = int(stats["r"] or 0)
            row["popup"] = bool(row.get("popup"))
    finally:
        c.close()
    return rows


def recall(message_id: str) -> int:
    """Remove a sent message from every bell (read or not). Returns the removed row count."""
    message_id = re.sub(r"[^0-9a-f]", "", str(message_id or ""))[:24]
    if not message_id:
        return 0
    c = auth_db._conn()
    try:
        exists = c.execute("SELECT 1 FROM admin_messages WHERE id=?", (message_id,)).fetchone()
        if not exists:
            raise LookupError("Сообщение не найдено")
        cur = c.execute("DELETE FROM notifications WHERE group_key=?", (f"msg:{message_id}",))
        removed = max(0, int(cur.rowcount or 0))
        c.execute("UPDATE admin_messages SET recalled_at=? WHERE id=?", (time.time(), message_id))
        c.commit()
    finally:
        c.close()
    return removed


def popup_for(user_id: int) -> dict | None:
    """The newest unread message that should open as a window, for /api/notifications/unread."""
    c = auth_db._conn()
    try:
        rows = c.execute("""SELECT id, title, body, link, meta_json, created_at FROM notifications
                            WHERE user_id=? AND is_read=0 AND kind=? ORDER BY created_at DESC LIMIT 5""",
                         (int(user_id), KIND)).fetchall()
    finally:
        c.close()
    for row in rows:
        try:
            meta = json.loads(row["meta_json"] or "{}")
        except (TypeError, ValueError):
            meta = {}
        if isinstance(meta, dict) and meta.get("popup"):
            return {"id": int(row["id"]), "title": row["title"] or "", "body": row["body"] or "",
                    "link": row["link"] or "", "meta": meta, "created_at": row["created_at"]}
    return None
