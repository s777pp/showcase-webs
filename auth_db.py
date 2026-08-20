"""Users + sessions (SQLite). Supports Railway volume via DATA_DIR."""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DATA_DIR") or (ROOT / "data"))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / "users.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB), timeout=30)
    c.row_factory = sqlite3.Row
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_pro INTEGER DEFAULT 0,
            pro_code TEXT,
            pro_until REAL,
            stripe_customer_id TEXT,
            da_access_token TEXT,
            da_refresh_token TEXT,
            da_client_id TEXT,
            da_client_secret TEXT,
            display_name TEXT,
            avatar_path TEXT,
            created_at REAL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS used_codes (
            code TEXT PRIMARY KEY,
            user_id INTEGER,
            used_at REAL
        )
        """
    )
    # migrations for older DBs
    cols = {r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()}
    for col, typ in (
        ("pro_code", "TEXT"),
        ("pro_until", "REAL"),
        ("da_access_token", "TEXT"),
        ("da_refresh_token", "TEXT"),
        ("da_client_id", "TEXT"),
        ("da_client_secret", "TEXT"),
        ("display_name", "TEXT"),
        ("avatar_path", "TEXT"),
    ):
        if col not in cols:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
            except Exception:
                pass
    c.commit()
    return c


def _hash_pw(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${h.hex()}"


def _check_pw(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
        return secrets.compare_digest(_hash_pw(password, salt), stored)
    except Exception:
        return False


def register(email: str, password: str) -> tuple[bool, str]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Invalid email"
    if len(password) < 6:
        return False, "Password min 6 characters"
    c = _conn()
    try:
        c.execute(
            "INSERT INTO users(email, password_hash, is_pro, created_at) VALUES (?,?,0,?)",
            (email, _hash_pw(password), time.time()),
        )
        c.commit()
        return True, "Account created"
    except sqlite3.IntegrityError:
        return False, "Email already registered"
    finally:
        c.close()


def login(email: str, password: str) -> tuple[bool, str, Optional[str]]:
    email = email.strip().lower()
    c = _conn()
    row = c.execute("SELECT id, password_hash FROM users WHERE email=?", (email,)).fetchone()
    if not row or not _check_pw(password, row["password_hash"]):
        c.close()
        return False, "Wrong email or password", None
    token = secrets.token_hex(24)
    c.execute(
        "INSERT INTO sessions(token, user_id, created_at) VALUES (?,?,?)",
        (token, row["id"], time.time()),
    )
    c.commit()
    c.close()
    return True, "OK", token


def user_by_token(token: str) -> Optional[dict]:
    if not token:
        return None
    c = _conn()
    row = c.execute(
        """
        SELECT u.id, u.email, u.is_pro, u.pro_code, u.pro_until, u.stripe_customer_id,
               u.da_access_token, u.da_refresh_token, u.da_client_id, u.da_client_secret, u.display_name, u.avatar_path
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token=?
        """,
        (token,),
    ).fetchone()
    c.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "is_pro": bool(row["is_pro"]),
        "pro_code": row["pro_code"],
        "pro_until": row["pro_until"],
        "stripe_customer_id": row["stripe_customer_id"],
        "da_access_token": row["da_access_token"],
        "da_refresh_token": row["da_refresh_token"],
        "da_client_id": row["da_client_id"],
        "da_client_secret": row["da_client_secret"],
        "display_name": row["display_name"],
        "avatar_path": row["avatar_path"],
    }


def set_pro(user_id: int, pro: bool = True, code: str | None = None, until: float | None = None) -> None:
    """until=None means permanent Pro; until=timestamp means trial until that time."""
    c = _conn()
    if code is not None:
        c.execute(
            "UPDATE users SET is_pro=?, pro_code=?, pro_until=? WHERE id=?",
            (1 if pro else 0, code, until, user_id),
        )
    else:
        c.execute(
            "UPDATE users SET is_pro=?, pro_until=? WHERE id=?",
            (1 if pro else 0, until if pro else None, user_id),
        )
    c.commit()
    c.close()


def effective_pro(user: dict | None) -> bool:
    """True if permanent Pro or trial not expired."""
    if not user:
        return False
    if not user.get("is_pro"):
        return False
    until = user.get("pro_until")
    if until is None:
        return True
    try:
        until_f = float(until)
    except (TypeError, ValueError):
        return True
    if time.time() > until_f:
        # expire
        try:
            set_pro(int(user["id"]), False, code=user.get("pro_code"), until=None)
        except Exception:
            pass
        return False
    return True


def code_used(code: str) -> Optional[int]:
    """Return user_id if code already used, else None."""
    c = _conn()
    row = c.execute("SELECT user_id FROM used_codes WHERE code=?", (code,)).fetchone()
    c.close()
    return int(row["user_id"]) if row and row["user_id"] is not None else (0 if row else None)


def mark_code_used(code: str, user_id: int) -> None:
    c = _conn()
    c.execute(
        "INSERT OR REPLACE INTO used_codes(code, user_id, used_at) VALUES (?,?,?)",
        (code, user_id, time.time()),
    )
    c.commit()
    c.close()


def set_da_tokens(user_id: int, access: str | None, refresh: str | None = None) -> None:
    c = _conn()
    c.execute(
        "UPDATE users SET da_access_token=?, da_refresh_token=? WHERE id=?",
        (access, refresh, user_id),
    )
    c.commit()
    c.close()


def set_stripe_customer(user_id: int, customer_id: str) -> None:
    c = _conn()
    c.execute(
        "UPDATE users SET stripe_customer_id=? WHERE id=?",
        (customer_id, user_id),
    )
    c.commit()
    c.close()


def logout(token: str) -> None:
    c = _conn()
    c.execute("DELETE FROM sessions WHERE token=?", (token,))
    c.commit()
    c.close()


def set_da_keys(user_id: int, client_id: str | None, client_secret: str | None) -> None:
    c = _conn()
    c.execute(
        "UPDATE users SET da_client_id=?, da_client_secret=? WHERE id=?",
        ((client_id or "").strip() or None, (client_secret or "").strip() or None, user_id),
    )
    c.commit()
    c.close()


def update_profile(user_id: int, display_name: str | None = None, avatar_path: str | None = None) -> None:
    c = _conn()
    if display_name is not None:
        name = (display_name or "").strip()[:40] or None
        c.execute("UPDATE users SET display_name=? WHERE id=?", (name, user_id))
    if avatar_path is not None:
        c.execute("UPDATE users SET avatar_path=? WHERE id=?", (avatar_path, user_id))
    c.commit()
    c.close()
