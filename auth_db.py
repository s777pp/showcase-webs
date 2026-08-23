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
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS email_codes (
            email TEXT PRIMARY KEY,
            code_hash TEXT NOT NULL,
            expires_at REAL NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_sent REAL DEFAULT 0
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
        ("email_verified", "INTEGER DEFAULT 0"),
        ("discord_id", "TEXT"),
        ("discord_username", "TEXT"),
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
            "INSERT INTO users(email, password_hash, is_pro, email_verified, created_at) VALUES (?,?,0,1,?)",
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
               u.da_access_token, u.da_refresh_token, u.da_client_id, u.da_client_secret, u.display_name, u.avatar_path,
               COALESCE(u.email_verified, 0) AS email_verified
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
        "email_verified": bool(row["email_verified"]) if "email_verified" in row.keys() else True,
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


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def create_email_code(email: str, ttl_sec: int = 900) -> tuple[bool, str, str]:
    """Create 6-digit code. Returns (ok, msg, plain_code). plain_code only if ok."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Invalid email", ""
    c = _conn()
    row = c.execute("SELECT last_sent FROM email_codes WHERE email=?", (email,)).fetchone()
    now = time.time()
    if row and row["last_sent"] and now - float(row["last_sent"]) < 60:
        c.close()
        return False, "Wait 60 seconds before resending", ""
    code = f"{secrets.randbelow(1_000_000):06d}"
    c.execute(
        """
        INSERT INTO email_codes(email, code_hash, expires_at, attempts, last_sent)
        VALUES (?,?,?,?,?)
        ON CONFLICT(email) DO UPDATE SET
          code_hash=excluded.code_hash,
          expires_at=excluded.expires_at,
          attempts=0,
          last_sent=excluded.last_sent
        """,
        (email, _hash_code(code), now + ttl_sec, 0, now),
    )
    c.commit()
    c.close()
    return True, "OK", code


def verify_email_code(email: str, code: str) -> tuple[bool, str]:
    email = email.strip().lower()
    code = (code or "").strip()
    if not email or not code:
        return False, "Enter email and code"
    c = _conn()
    row = c.execute(
        "SELECT code_hash, expires_at, attempts FROM email_codes WHERE email=?",
        (email,),
    ).fetchone()
    if not row:
        c.close()
        return False, "No code requested — register or resend"
    if float(row["expires_at"]) < time.time():
        c.close()
        return False, "Code expired — request a new one"
    attempts = int(row["attempts"] or 0)
    if attempts >= 8:
        c.close()
        return False, "Too many attempts — request a new code"
    c.execute("UPDATE email_codes SET attempts=? WHERE email=?", (attempts + 1, email))
    c.commit()
    if not secrets.compare_digest(row["code_hash"], _hash_code(code)):
        c.close()
        return False, "Wrong code"
    c.execute("UPDATE users SET email_verified=1 WHERE email=?", (email,))
    c.execute("DELETE FROM email_codes WHERE email=?", (email,))
    c.commit()
    c.close()
    return True, "Email verified"


def is_verified(email: str) -> bool:
    email = email.strip().lower()
    c = _conn()
    row = c.execute(
        "SELECT COALESCE(email_verified, 0) AS v FROM users WHERE email=?",
        (email,),
    ).fetchone()
    c.close()
    return bool(row and int(row["v"]))


def user_exists(email: str) -> bool:
    email = email.strip().lower()
    c = _conn()
    row = c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone()
    c.close()
    return bool(row)


def wipe_all_users() -> int:
    """Delete all users, sessions, email codes. Returns deleted user count."""
    c = _conn()
    n = c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    c.execute("DELETE FROM sessions")
    c.execute("DELETE FROM email_codes")
    c.execute("DELETE FROM used_codes")
    c.execute("DELETE FROM users")
    c.commit()
    c.close()
    return int(n or 0)


# ─── Gallery ────────────────────────────────────────────────────────────────

def _ensure_gallery(c: sqlite3.Connection) -> None:
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            mode TEXT,
            image_path TEXT NOT NULL,
            thumb_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    c.commit()


def gallery_add(user_id: int | None, title: str, mode: str, image_path: str, thumb_path: str | None = None) -> int:
    c = _conn()
    _ensure_gallery(c)
    cur = c.execute(
        "INSERT INTO gallery(user_id, title, mode, image_path, thumb_path, status, created_at) VALUES (?,?,?,?,?,'pending',?)",
        (user_id, (title or "")[:80], mode, image_path, thumb_path, time.time()),
    )
    c.commit()
    gid = cur.lastrowid
    c.close()
    return int(gid or 0)


def gallery_list(status: str = "approved", limit: int = 40, offset: int = 0) -> list[dict]:
    c = _conn()
    _ensure_gallery(c)
    rows = c.execute(
        """
        SELECT g.id, g.title, g.mode, g.image_path, g.thumb_path, g.status, g.created_at,
               u.display_name, u.email, u.discord_username
        FROM gallery g LEFT JOIN users u ON u.id = g.user_id
        WHERE g.status=?
        ORDER BY g.created_at DESC
        LIMIT ? OFFSET ?
        """,
        (status, limit, offset),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def gallery_set_status(item_id: int, status: str) -> bool:
    if status not in ("pending", "approved", "rejected"):
        return False
    c = _conn()
    _ensure_gallery(c)
    c.execute("UPDATE gallery SET status=? WHERE id=?", (status, item_id))
    c.commit()
    n = c.total_changes
    c.close()
    return n > 0


def gallery_get(item_id: int) -> dict | None:
    c = _conn()
    _ensure_gallery(c)
    row = c.execute("SELECT * FROM gallery WHERE id=?", (item_id,)).fetchone()
    c.close()
    return dict(row) if row else None


# ─── Discord ────────────────────────────────────────────────────────────────

def user_by_discord(discord_id: str) -> dict | None:
    if not discord_id:
        return None
    c = _conn()
    row = c.execute(
        "SELECT id, email, is_pro, pro_code, pro_until, discord_id, discord_username, display_name, avatar_path FROM users WHERE discord_id=?",
        (str(discord_id),),
    ).fetchone()
    c.close()
    if not row:
        return None
    return dict(row)


def register_or_login_discord(discord_id: str, username: str, email: str | None = None) -> tuple[bool, str, str | None]:
    """Return (ok, msg, session_token). Creates account if needed."""
    discord_id = str(discord_id)
    username = (username or "discord")[:40]
    existing = user_by_discord(discord_id)
    c = _conn()
    if existing:
        uid = int(existing["id"])
        c.execute("UPDATE users SET discord_username=? WHERE id=?", (username, uid))
        c.commit()
    else:
        # synthetic email if none
        em = (email or f"discord_{discord_id}@users.local").strip().lower()
        # unique email
        try:
            c.execute(
                "INSERT INTO users(email, password_hash, is_pro, email_verified, discord_id, discord_username, display_name, created_at) VALUES (?,?,0,1,?,?,?,?)",
                (em, _hash_pw(secrets.token_hex(16)), discord_id, username, username, time.time()),
            )
            c.commit()
            uid = c.execute("SELECT id FROM users WHERE discord_id=?", (discord_id,)).fetchone()["id"]
        except sqlite3.IntegrityError:
            # email taken — just link if possible
            row = c.execute("SELECT id FROM users WHERE email=?", (em,)).fetchone()
            if not row:
                c.close()
                return False, "Could not create Discord account", None
            uid = int(row["id"])
            c.execute("UPDATE users SET discord_id=?, discord_username=? WHERE id=?", (discord_id, username, uid))
            c.commit()
    token = secrets.token_hex(24)
    c.execute("INSERT INTO sessions(token, user_id, created_at) VALUES (?,?,?)", (token, uid, time.time()))
    c.commit()
    c.close()
    return True, "OK", token
