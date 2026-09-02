#!/usr/bin/env python3
"""Merge the legacy SQLite database into PostgreSQL while preserving IDs."""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

import psycopg
from psycopg import sql


TABLES = [
    "users", "sessions", "used_codes", "email_codes", "profile_import_tickets",
    "gallery", "gallery_likes", "gallery_comments", "notifications", "profile_showcases",
]


def normalize(table: str, column: str, value):
    if value is None:
        return None
    if (table, column) in {
        ("users", "avatar_path"), ("users", "profile_background"),
        ("gallery", "image_path"), ("gallery", "thumb_path"),
    }:
        text = str(value).replace("\\", "/")
        if "/data/" in text:
            text = text.split("/data/", 1)[1]
        return text.lstrip("/")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sqlite", type=Path)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument("--apply", action="store_true", help="commit changes; default is a dry run")
    args = parser.parse_args()
    if not args.sqlite.is_file():
        raise SystemExit(f"SQLite backup not found: {args.sqlite}")
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required")

    src = sqlite3.connect(str(args.sqlite))
    src.row_factory = sqlite3.Row
    counts: dict[str, int] = {}
    with psycopg.connect(args.database_url) as dst:
        for table in TABLES:
            exists = src.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            if not exists:
                continue
            source_cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})")]
            with dst.cursor() as cur:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (table,))
                dest_cols = {r[0] for r in cur.fetchall()}
            cols = [c for c in source_cols if c in dest_cols]
            rows = src.execute(f"SELECT {','.join(cols)} FROM {table}").fetchall()
            if rows:
                statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
                    sql.Identifier(table),
                    sql.SQL(",").join(map(sql.Identifier, cols)),
                    sql.SQL(",").join(sql.Placeholder() for _ in cols),
                )
                with dst.cursor() as cur:
                    cur.executemany(statement, [tuple(normalize(table, c, row[c]) for c in cols) for row in rows])
            counts[table] = len(rows)

        for table in ("users", "gallery", "gallery_comments", "notifications", "profile_showcases"):
            with dst.cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT setval(pg_get_serial_sequence(%s,'id'), COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM {}").format(sql.Identifier(table)),
                    (table,),
                )
        if not args.apply:
            dst.rollback()
        else:
            dst.commit()
    src.close()
    mode = "IMPORTED" if args.apply else "DRY RUN"
    print(mode + ": " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
