"""Small DB-API compatibility layer for the PostgreSQL production backend.

The application historically used sqlite3 directly and therefore uses ``?``
placeholders and ``cursor.lastrowid`` throughout auth_db.py.  Rewriting every
call site at once would be risky, so this module presents the tiny subset of
the sqlite API the application uses while executing against psycopg.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from psycopg import IntegrityError
from psycopg.pq import TransactionStatus
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _translate(sql: str) -> tuple[str, bool]:
    """Translate the small SQLite dialect used by auth_db.py.

    Returns (sql, wants_lastrowid).  The only REPLACE statement in the app is
    for used_codes, whose primary key is ``code``.
    """
    text = sql.strip()
    upper = text.upper()
    if upper.startswith("PRAGMA "):
        return "", False
    if upper.startswith("ALTER TABLE "):
        # Production schema migrations are centralized in schema_pg.sql.
        # Legacy defensive ALTER probes would otherwise run on every request.
        return "", False
    if upper.startswith("BEGIN IMMEDIATE"):
        return "BEGIN", False
    if upper.startswith("INSERT OR REPLACE INTO USED_CODES"):
        text = re.sub(r"(?is)^INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", text)
        text += " ON CONFLICT (code) DO UPDATE SET user_id=EXCLUDED.user_id, used_at=EXCLUDED.used_at"
    elif upper.startswith("INSERT OR IGNORE INTO"):
        text = re.sub(r"(?is)^INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", text)
        text += " ON CONFLICT DO NOTHING"

    wants_id = bool(
        re.match(r"(?is)^INSERT\s+INTO\s+(gallery|gallery_comments|profile_showcases)\b", text)
        and " RETURNING " not in text.upper()
    )
    if wants_id:
        text = text.rstrip().rstrip(";") + " RETURNING id"
    return text.replace("?", "%s"), wants_id


class Cursor:
    def __init__(self, cursor: Any, lastrowid: int | None = None):
        self._cursor = cursor
        self.lastrowid = lastrowid

    @property
    def rowcount(self) -> int:
        return int(self._cursor.rowcount or 0)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class Connection:
    def __init__(self, pool: ConnectionPool):
        self._pool = pool
        self._conn = pool.getconn()

    def execute(self, sql: str, params: tuple | list = ()) -> Cursor:
        translated, wants_id = _translate(sql)
        if not translated:
            return Cursor(self._conn.cursor(row_factory=dict_row))
        # psycopg opens a transaction on the preceding DELETE/SELECT already;
        # SQLite call sites may still issue BEGIN IMMEDIATE explicitly.
        if translated == "BEGIN" and self._conn.info.transaction_status != TransactionStatus.IDLE:
            return Cursor(self._conn.cursor(row_factory=dict_row))
        cur = self._conn.cursor(row_factory=dict_row)
        try:
            cur.execute(translated, tuple(params))
            last_id = None
            if wants_id:
                row = cur.fetchone()
                last_id = int(row["id"]) if row else None
            return Cursor(cur, last_id)
        except IntegrityError as exc:
            # PostgreSQL marks the whole transaction failed after a constraint
            # violation.  Existing auth code expects it can catch the SQLite
            # error and continue querying on the same connection.
            self._conn.rollback()
            raise sqlite3.IntegrityError(str(exc)) from exc
        except Exception:
            # Several legacy call sites intentionally probe optional columns
            # and continue on failure. Keep the pooled connection usable.
            self._conn.rollback()
            raise

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is None:
            return
        try:
            if conn.info.transaction_status != TransactionStatus.IDLE:
                conn.rollback()
        except Exception:
            pass
        try:
            self._pool.putconn(conn)
        except Exception:
            pass

    def __del__(self) -> None:
        """Last-resort return to the pool.

        Most auth_db.py helpers call close() explicitly but not from a finally
        block, so an exception raised between _conn() and close() would retire a
        pooled connection permanently.  Ten of those exhaust the pool and every
        later request blocks for the pool timeout instead of answering.
        """
        try:
            self.close()
        except Exception:
            pass

    # Allow `with auth_db._conn() as c:` at future call sites.
    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def pool(database_url: str) -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is None:
            _pool = ConnectionPool(
                conninfo=database_url,
                min_size=1,
                max_size=int(os.environ.get("PG_POOL_MAX", "10")),
                timeout=10,
                # Without a check, every connection pooled before a PostgreSQL
                # restart is handed out dead and each request fails until the
                # pool happens to notice.
                check=ConnectionPool.check_connection,
                max_lifetime=1800,
                max_idle=300,
                kwargs={"autocommit": False, "row_factory": dict_row},
                open=True,
            )
    return _pool


def connect(database_url: str) -> Connection:
    return Connection(pool(database_url))


def initialize(database_url: str, schema_path: Path) -> None:
    """Apply the idempotent production schema before serving traffic."""
    schema = schema_path.read_text(encoding="utf-8")
    p = pool(database_url)
    with p.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema)
        conn.commit()
