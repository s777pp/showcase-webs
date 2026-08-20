"""Пользователи + сессии (SQLite)."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "users.db"
DB.parent.mkdir(parents=True, exist_ok=True)


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB))
    c.row_factory = sqlite3.Row
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_pro INTEGER DEFAULT 0,
            stripe_customer_id TEXT,
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
        return False, "Некорректный email"
    if len(password) < 6:
        return False, "Пароль минимум 6 символов"
    c = _conn()
    try:
        c.execute(
            "INSERT INTO users(email, password_hash, is_pro, created_at) VALUES (?,?,0,?)",
            (email, _hash_pw(password), time.time()),
        )
        c.commit()
        return True, "Аккаунт создан"
    except sqlite3.IntegrityError:
        return False, "Email уже зарегистрирован"
    finally:
        c.close()


def login(email: str, password: str) -> tuple[bool, str, Optional[str]]:
    """→ ok, msg, session_token"""
    email = email.strip().lower()
    c = _conn()
    row = c.execute("SELECT id, password_hash FROM users WHERE email=?", (email,)).fetchone()
    if not row or not _check_pw(password, row["password_hash"]):
        c.close()
        return False, "Неверный email или пароль", None
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
        SELECT u.id, u.email, u.is_pro, u.stripe_customer_id
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
        "stripe_customer_id": row["stripe_customer_id"],
    }


def set_pro(user_id: int, pro: bool = True) -> None:
    c = _conn()
    c.execute("UPDATE users SET is_pro=? WHERE id=?", (1 if pro else 0, user_id))
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
