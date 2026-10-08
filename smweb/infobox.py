"""Community templates for Steam's "Custom Info Box" showcase (owner, 2026-10-08: "a place with ready info box
templates"). The site's own templates live in static/js/infobox.js; this module stores the ones visitors publish.

A template is plain BBCode text exactly as it goes into Steam (no HTML is ever stored or rendered from it: the
browser escapes it and draws only the BBCode it knows). Authors confirm they have the rights; the owner can hide a
template from the admin API. Table ``infobox_templates`` exists in both schemas.
"""
from __future__ import annotations

import re
import secrets
import time

import auth_db

CATEGORIES = ("about", "frames", "games", "quotes", "art", "other")
TITLE_MAX = 60
BODY_MAX = 8000          # Steam's info box limit as reported by the community
PER_USER_MAX = 50


def clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:TITLE_MAX]


def clean_body(value: str) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    # Control characters other than line breaks and tabs have no place in Steam text.
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text).strip("\n")[:BODY_MAX]


def _public(row: dict) -> dict:
    return {
        "id": row["id"], "title": row["title"], "body": row["body"], "category": row["category"],
        "uses": int(row.get("uses") or 0), "created_at": row["created_at"],
        "author": row.get("display_name") or row.get("profile_username") or "Author",
        "username": row.get("profile_username") or "", "user_id": int(row["user_id"]),
    }


def listing(category: str = "", sort: str = "new", limit: int = 24, offset: int = 0) -> tuple[list[dict], int]:
    limit = max(1, min(48, int(limit or 24)))
    offset = max(0, int(offset or 0))
    where, params = ["t.status='published'"], []
    if category in CATEGORIES:
        where.append("t.category=?")
        params.append(category)
    order = "t.uses DESC, t.created_at DESC" if sort == "popular" else "t.created_at DESC"
    c = auth_db._conn()
    try:
        total = c.execute(f"SELECT COUNT(*) AS n FROM infobox_templates t WHERE {' AND '.join(where)}", params).fetchone()
        rows = c.execute(
            "SELECT t.*, u.display_name, u.profile_username FROM infobox_templates t "
            f"LEFT JOIN users u ON u.id=t.user_id WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?",
            params + [limit, offset]).fetchall()
        return [_public(dict(row)) for row in rows], int(dict(total)["n"])
    finally:
        c.close()


def create(user_id: int, title: str, body: str, category: str) -> dict:
    title, body = clean_title(title), clean_body(body)
    if not title or not body.strip():
        raise ValueError("empty")
    category = category if category in CATEGORIES else "other"
    c = auth_db._conn()
    try:
        count = dict(c.execute("SELECT COUNT(*) AS n FROM infobox_templates WHERE user_id=? AND status='published'",
                               (int(user_id),)).fetchone())["n"]
        if int(count) >= PER_USER_MAX:
            raise ValueError("too_many")
        row = {"id": secrets.token_hex(8), "user_id": int(user_id), "title": title, "body": body,
               "category": category, "uses": 0, "status": "published", "created_at": time.time()}
        c.execute("INSERT INTO infobox_templates (id,user_id,title,body,category,uses,status,created_at) "
                  "VALUES (?,?,?,?,?,?,?,?)", tuple(row.values()))
        c.commit()
        return row
    finally:
        c.close()


def used(template_id: str) -> None:
    c = auth_db._conn()
    try:
        c.execute("UPDATE infobox_templates SET uses=uses+1 WHERE id=? AND status='published'", (str(template_id),))
        c.commit()
    finally:
        c.close()


def remove(template_id: str, user_id: int | None = None) -> bool:
    """Delete an author's own template, or hide any template (user_id None = the owner's admin action)."""
    c = auth_db._conn()
    try:
        if user_id is None:
            cur = c.execute("UPDATE infobox_templates SET status='hidden' WHERE id=?", (str(template_id),))
        else:
            cur = c.execute("DELETE FROM infobox_templates WHERE id=? AND user_id=?", (str(template_id), int(user_id)))
        c.commit()
        return bool(cur.rowcount)
    finally:
        c.close()
