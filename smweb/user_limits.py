"""Per-account operational limit overrides.

Only explicit integer limits are stored. Missing values always fall back to the
normal product configuration, so removing an override restores standard rules.
"""
from __future__ import annotations

import time

import auth_db


def get(user_id: int | None) -> dict:
    if not user_id:
        return {"free_daily_limit": None, "max_jobs": None, "note": "", "updated_at": None}
    connection = auth_db._conn()
    try:
        row = connection.execute(
            "SELECT free_daily_limit,max_jobs,note,updated_at FROM user_limit_overrides WHERE user_id=?",
            (int(user_id),),
        ).fetchone()
        return dict(row) if row else {"free_daily_limit": None, "max_jobs": None, "note": "", "updated_at": None}
    finally:
        connection.close()


def integer(user_id: int | None, key: str, fallback: int) -> int:
    if key not in {"free_daily_limit", "max_jobs"}:
        return int(fallback)
    value = get(user_id).get(key)
    try:
        return int(value) if value is not None else int(fallback)
    except (TypeError, ValueError):
        return int(fallback)


def set_limits(user_id: int, *, free_daily_limit=None, max_jobs=None, note: str = "") -> dict:
    uid = int(user_id)
    free_value = None if free_daily_limit in (None, "") else max(1, min(1000, int(free_daily_limit)))
    jobs_value = None if max_jobs in (None, "") else max(1, min(20, int(max_jobs)))
    connection = auth_db._conn()
    try:
        if not connection.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone():
            raise LookupError("Account not found")
        exists = connection.execute("SELECT user_id FROM user_limit_overrides WHERE user_id=?", (uid,)).fetchone()
        if exists:
            connection.execute(
                "UPDATE user_limit_overrides SET free_daily_limit=?,max_jobs=?,note=?,updated_at=? WHERE user_id=?",
                (free_value, jobs_value, str(note or "")[:240], time.time(), uid),
            )
        else:
            connection.execute(
                "INSERT INTO user_limit_overrides(user_id,free_daily_limit,max_jobs,note,updated_at) VALUES (?,?,?,?,?)",
                (uid, free_value, jobs_value, str(note or "")[:240], time.time()),
            )
        connection.commit()
    finally:
        connection.close()
    return get(uid)


def clear(user_id: int) -> None:
    connection = auth_db._conn()
    try:
        connection.execute("DELETE FROM user_limit_overrides WHERE user_id=?", (int(user_id),))
        connection.commit()
    finally:
        connection.close()
