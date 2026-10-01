"""Support conversations (2026-10-01).

A ticket (``support_tickets``) now has a thread in ``support_messages``: the user's first
message, replies from support (admin console or the owner's Telegram bot) and the user's
follow-ups. A reply from support notifies the user on the site (signed-in tickets) and
is e-mailed when the ticket has an e-mail address. Telegram-only contacts are answered by
the owner in Telegram itself; the site thread still keeps the text.
"""
from __future__ import annotations

import html
import time

import auth_db
from smweb import admin_content

TEXT_MIN, TEXT_MAX = 2, 2000


def _ticket(ticket_id: str) -> dict | None:
    c = auth_db._conn()
    try:
        row = c.execute("SELECT id,user_id,email,message,page,context_json,status,created_at,updated_at "
                        "FROM support_tickets WHERE id=?", (str(ticket_id or ""),)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["context"] = admin_content._json_dict(item.pop("context_json", "{}"))
        return item
    finally:
        c.close()


def messages(ticket: dict) -> list[dict]:
    """The thread, starting with the original message (stored on the ticket itself)."""
    c = auth_db._conn()
    try:
        rows = c.execute("SELECT id, author, body, created_at FROM support_messages WHERE ticket_id=? ORDER BY created_at, id",
                         (ticket["id"],)).fetchall()
    finally:
        c.close()
    first = {"id": 0, "author": "user", "body": ticket.get("message") or "", "created_at": ticket.get("created_at")}
    return [first, *[dict(r) for r in rows]]


def _add(ticket_id: str, author: str, body: str, status: str) -> None:
    now = time.time()
    c = auth_db._conn()
    try:
        c.execute("INSERT INTO support_messages(ticket_id, author, body, created_at) VALUES (?,?,?,?)",
                  (ticket_id, author, body, now))
        c.execute("UPDATE support_tickets SET status=?, updated_at=? WHERE id=?", (status, now, ticket_id))
        c.commit()
    finally:
        c.close()


def _clean(text: str) -> str:
    text = str(text or "").strip()
    if not TEXT_MIN <= len(text) <= TEXT_MAX:
        raise ValueError(f"Сообщение должно быть от {TEXT_MIN} до {TEXT_MAX} символов")
    return text


def reply_from_support(ticket_id: str, text: str, status: str = "resolved") -> dict:
    """Store the answer, notify the user on the site and e-mail it when possible."""
    ticket = _ticket(ticket_id)
    if not ticket:
        raise LookupError("Ticket not found")
    text = _clean(text)
    if status not in ("working", "resolved", "closed"):
        status = "resolved"
    _add(ticket["id"], "support", text, status)
    if ticket.get("user_id"):
        from smweb import notify
        notify.add(int(ticket["user_id"]), "support_reply", title="Ответ поддержки", body=text[:200],
                   link=f"/support?t={ticket['id']}", meta={"ticket": ticket["id"]}, group_key=f"support:{ticket['id']}")
    emailed = False
    email = str(ticket.get("email") or "").strip()
    if email:
        try:
            import mailer
            from smweb.core import APP_URL
            link = (APP_URL or "https://showcasemaker.com").rstrip("/") + f"/support?t={ticket['id']}"
            body_html = (f"<p>{html.escape(text).replace(chr(10), '<br>')}</p>"
                         + (f"<p><a href=\"{html.escape(link)}\">Открыть переписку на сайте</a></p>" if ticket.get("user_id") else "")
                         + f"<hr><p style='color:#888'>Ваше обращение:<br>{html.escape(str(ticket.get('message') or ''))}</p>")
            emailed, _msg = mailer.send_email(email, "Ответ поддержки Showcase Maker", text, body_html)
        except Exception:
            emailed = False
    telegram = str((ticket.get("context") or {}).get("telegram") or "")
    return {"ok": True, "emailed": bool(emailed), "has_email": bool(email), "telegram": telegram,
            "notified": bool(ticket.get("user_id"))}


def user_tickets(user_id: int) -> list[dict]:
    c = auth_db._conn()
    try:
        rows = c.execute("""SELECT t.id, t.message, t.status, t.created_at, t.updated_at,
                                   (SELECT COUNT(*) FROM support_messages m WHERE m.ticket_id=t.id AND m.author='support') AS replies
                            FROM support_tickets t WHERE t.user_id=? ORDER BY t.updated_at DESC LIMIT 50""",
                         (int(user_id),)).fetchall()
        return [{**dict(r), "message": str(r["message"] or "")[:160], "replies": int(r["replies"] or 0)} for r in rows]
    finally:
        c.close()


def user_thread(ticket_id: str, user_id: int) -> dict | None:
    ticket = _ticket(ticket_id)
    if not ticket or int(ticket.get("user_id") or 0) != int(user_id):
        return None
    return {"id": ticket["id"], "status": ticket["status"], "created_at": ticket["created_at"],
            "updated_at": ticket["updated_at"], "messages": messages(ticket)}


def reply_from_user(ticket_id: str, user_id: int, text: str) -> dict:
    ticket = _ticket(ticket_id)
    if not ticket or int(ticket.get("user_id") or 0) != int(user_id):
        raise LookupError("Ticket not found")
    if ticket.get("status") == "closed":
        raise ValueError("Обращение закрыто. Создай новое, если вопрос остался.")
    text = _clean(text)
    _add(ticket["id"], "user", text, "new")
    try:
        from smweb import admin_notify
        admin_notify.send(f"💬 <b>Ответ в обращении #{html.escape(ticket['id'])}</b>\n"
                          f"От: {html.escape(str(ticket.get('email') or 'пользователь'))}\n\n{html.escape(text)[:3000]}",
                          [[{"text": "✍️ Ответить", "callback_data": f"tk:{ticket['id']}"}]])
    except Exception:
        pass
    return {"ok": True}


def admin_threads(ticket_ids: list[str]) -> dict[str, list[dict]]:
    """Replies per ticket for the admin console (the first message is on the ticket)."""
    if not ticket_ids:
        return {}
    c = auth_db._conn()
    try:
        marks = ",".join("?" * len(ticket_ids))
        rows = c.execute(f"SELECT ticket_id, author, body, created_at FROM support_messages WHERE ticket_id IN ({marks}) "
                         "ORDER BY created_at, id", list(ticket_ids)).fetchall()
    finally:
        c.close()
    out: dict[str, list[dict]] = {}
    for row in rows:
        out.setdefault(row["ticket_id"], []).append({"author": row["author"], "body": row["body"], "created_at": row["created_at"]})
    return out
