#!/usr/bin/env python3
"""Copy SQLite users.db → PostgreSQL.

Usage:
  DATABASE_URL=postgresql://user:pass@host:5432/db \\
  SQLITE_PATH=/data/users.db \\
  python scripts/migrate_sqlite_to_pg.py

Requires: schema already applied (sql/schema_pg.sql).
Does NOT drop existing PG data — skips rows that conflict on PK/UNIQUE.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

SQLITE_PATH = Path(os.environ.get("SQLITE_PATH") or "data/users.db")
DATABASE_URL = os.environ.get("DATABASE_URL") or ""

TABLES = [
    "users",
    "sessions",
    "used_codes",
    "email_codes",
    "gallery",
    "gallery_likes",
    "gallery_comments",
    "notifications",
]


def main() -> int:
    if not DATABASE_URL.startswith("postgres"):
        print("Set DATABASE_URL to postgresql://...", file=sys.stderr)
        return 1
    if not SQLITE_PATH.is_file():
        print(f"SQLite not found: {SQLITE_PATH}", file=sys.stderr)
        return 1

    import psycopg

    src = sqlite3.connect(str(SQLITE_PATH))
    src.row_factory = sqlite3.Row
    dst = psycopg.connect(DATABASE_URL)
    print(f"Source: {SQLITE_PATH}")
    print(f"Target: {DATABASE_URL.split('@')[-1]}")

    for table in TABLES:
        try:
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.Error as e:
            print(f"  skip {table}: {e}")
            continue
        if not rows:
            print(f"  {table}: 0 rows")
            continue
        cols = rows[0].keys()
        col_list = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        ok = 0
        with dst.cursor() as cur:
            for r in rows:
                try:
                    cur.execute(sql, [r[c] for c in cols])
                    ok += 1
                except Exception as e:
                    print(f"  {table} row error: {e}")
        dst.commit()
        print(f"  {table}: migrated ~{ok}/{len(rows)}")

    # Fix sequences for serial tables
    with dst.cursor() as cur:
        for table, col in (
            ("users", "id"),
            ("gallery", "id"),
            ("gallery_comments", "id"),
            ("notifications", "id"),
        ):
            try:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                    f"COALESCE((SELECT MAX({col}) FROM {table}), 1))"
                )
            except Exception as e:
                print(f"  sequence {table}: {e}")
        dst.commit()

    src.close()
    dst.close()
    print("Done. Verify row counts before switching app DATABASE_URL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
