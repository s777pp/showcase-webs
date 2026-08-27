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
        ("profile_username", "TEXT"),
        ("profile_summary", "TEXT"),
        ("profile_background", "TEXT"),
        ("profile_bg_x", "REAL"),
        ("profile_bg_y", "REAL"),
        ("profile_bg_scale", "REAL"),
        ("profile_bg_overlay", "REAL"),
        ("profile_level", "INTEGER"),
        ("profile_xp", "INTEGER"),
        ("profile_location", "TEXT"),
        ("profile_status", "TEXT"),
        ("profile_visibility", "TEXT"),
        ("google_id", "TEXT"),
        ("telegram_id", "TEXT"),
        ("telegram_username", "TEXT"),
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
    # ensure profile columns exist
    try:
        for col, typ in (
            ("profile_username", "TEXT"), ("profile_summary", "TEXT"), ("profile_background", "TEXT"),
            ("profile_bg_x", "REAL"), ("profile_bg_y", "REAL"), ("profile_bg_scale", "REAL"),
            ("profile_bg_overlay", "REAL"), ("profile_level", "INTEGER"), ("profile_xp", "INTEGER"),
            ("profile_location", "TEXT"), ("profile_status", "TEXT"), ("profile_visibility", "TEXT"),
        ):
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
                c.commit()
            except Exception:
                pass
    except Exception:
        pass
    try:
        row = c.execute(
            """
            SELECT u.id, u.email, u.is_pro, u.pro_code, u.pro_until, u.stripe_customer_id,
                   u.da_access_token, u.da_refresh_token, u.da_client_id, u.da_client_secret, u.display_name, u.avatar_path,
                   COALESCE(u.email_verified, 0) AS email_verified,
                   u.profile_username, u.profile_summary, u.profile_background,
                   u.profile_bg_x, u.profile_bg_y, u.profile_bg_scale, u.profile_bg_overlay,
                   u.profile_level, u.profile_xp, u.profile_location, u.profile_status, u.profile_visibility
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token=?
            """,
            (token,),
        ).fetchone()
    except Exception:
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
    def _g(k, default=None):
        try:
            return row[k] if k in row.keys() else default
        except Exception:
            return default
    return {
        "id": row["id"],
        "email": row["email"],
        "is_pro": bool(row["is_pro"]),
        "pro_code": row["pro_code"],
        "pro_until": row["pro_until"],
        "stripe_customer_id": _g("stripe_customer_id"),
        "da_access_token": _g("da_access_token"),
        "da_refresh_token": _g("da_refresh_token"),
        "da_client_id": _g("da_client_id"),
        "da_client_secret": _g("da_client_secret"),
        "display_name": _g("display_name"),
        "avatar_path": _g("avatar_path"),
        "email_verified": bool(_g("email_verified", 0)),
        "profile_username": _g("profile_username"),
        "profile_summary": _g("profile_summary"),
        "profile_background": _g("profile_background"),
        "profile_bg_x": _g("profile_bg_x", 50),
        "profile_bg_y": _g("profile_bg_y", 30),
        "profile_bg_scale": _g("profile_bg_scale", 1),
        "profile_bg_overlay": _g("profile_bg_overlay", 0.45),
        "profile_level": _g("profile_level", 1) or 1,
        "profile_xp": _g("profile_xp", 0) or 0,
        "profile_location": _g("profile_location"),
        "profile_status": _g("profile_status") or "online",
        "profile_visibility": _g("profile_visibility") or "public",
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
        SELECT g.id, g.user_id, g.title, g.mode, g.image_path, g.thumb_path, g.status, g.created_at,
               u.display_name, u.email, u.discord_username, u.avatar_path, u.profile_username
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



def user_by_google(google_id: str) -> dict | None:
    if not google_id:
        return None
    c = _conn()
    row = c.execute(
        "SELECT id, email, is_pro, pro_code, pro_until, google_id, display_name, avatar_path FROM users WHERE google_id=?",
        (str(google_id),),
    ).fetchone()
    c.close()
    if not row:
        return None
    return dict(row)


def register_or_login_google(google_id: str, email: str | None, name: str | None = None) -> tuple[bool, str, str | None]:
    """Return (ok, msg, session_token). Creates account if needed."""
    google_id = str(google_id)
    name = (name or "google")[:40]
    existing = user_by_google(google_id)
    c = _conn()
    if existing:
        uid = int(existing["id"])
        if name:
            c.execute(
                "UPDATE users SET display_name=COALESCE(display_name, ?) WHERE id=?",
                (name, uid),
            )
            c.commit()
    else:
        em = (email or f"google_{google_id}@users.local").strip().lower()
        try:
            c.execute(
                "INSERT INTO users(email, password_hash, is_pro, email_verified, google_id, display_name, created_at) VALUES (?,?,0,1,?,?,?)",
                (em, _hash_pw(secrets.token_hex(16)), google_id, name, time.time()),
            )
            c.commit()
            uid = c.execute("SELECT id FROM users WHERE google_id=?", (google_id,)).fetchone()["id"]
        except sqlite3.IntegrityError:
            row = c.execute("SELECT id FROM users WHERE email=?", (em,)).fetchone()
            if not row:
                c.close()
                return False, "Could not create Google account", None
            uid = int(row["id"])
            c.execute("UPDATE users SET google_id=? WHERE id=?", (google_id, uid))
            if name:
                c.execute(
                    "UPDATE users SET display_name=COALESCE(display_name, ?) WHERE id=?",
                    (name, uid),
                )
            c.commit()
    token = secrets.token_hex(24)
    c.execute("INSERT INTO sessions(token, user_id, created_at) VALUES (?,?,?)", (token, uid, time.time()))
    c.commit()
    c.close()
    return True, "OK", token


# ====================== Gallery social: likes / comments / notifications ======================

# ─── Telegram ───────────────────────────────────────────────────────────────

def user_by_telegram(telegram_id: str) -> dict | None:
    if not telegram_id:
        return None
    c = _conn()
    row = c.execute(
        "SELECT id, email, is_pro, pro_code, pro_until, telegram_id, telegram_username, display_name, avatar_path FROM users WHERE telegram_id=?",
        (str(telegram_id),),
    ).fetchone()
    c.close()
    return dict(row) if row else None


def register_or_login_telegram(
    telegram_id: str,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    photo_url: str | None = None,
) -> tuple[bool, str, str | None]:
    """Return (ok, msg, session_token). Creates account if needed."""
    telegram_id = str(telegram_id)
    uname = (username or first_name or "telegram")[:40]
    display = " ".join(x for x in [(first_name or "").strip(), (last_name or "").strip()] if x)[:40] or uname
    existing = user_by_telegram(telegram_id)
    c = _conn()
    if existing:
        uid = int(existing["id"])
        c.execute(
            "UPDATE users SET telegram_username=?, display_name=COALESCE(display_name, ?) WHERE id=?",
            (uname, display, uid),
        )
        c.commit()
    else:
        em = f"tg_{telegram_id}@users.local"
        try:
            c.execute(
                """INSERT INTO users(
                    email, password_hash, is_pro, email_verified,
                    telegram_id, telegram_username, display_name, created_at
                ) VALUES (?,?,0,1,?,?,?,?)""",
                (em, _hash_pw(secrets.token_hex(16)), telegram_id, uname, display, time.time()),
            )
            c.commit()
            uid = c.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()["id"]
        except sqlite3.IntegrityError:
            row = c.execute("SELECT id FROM users WHERE email=?", (em,)).fetchone()
            if not row:
                c.close()
                return False, "Could not create Telegram account", None
            uid = int(row["id"])
            c.execute(
                "UPDATE users SET telegram_id=?, telegram_username=?, display_name=COALESCE(display_name, ?) WHERE id=?",
                (telegram_id, uname, display, uid),
            )
            c.commit()
    token = secrets.token_hex(24)
    c.execute(
        "INSERT INTO sessions(token, user_id, created_at) VALUES (?,?,?)",
        (token, uid, time.time()),
    )
    c.commit()
    c.close()
    return True, "OK", token



def _ensure_social(c) -> None:
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS gallery_likes (
            item_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at REAL,
            PRIMARY KEY (item_id, user_id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS gallery_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            parent_id INTEGER,
            body TEXT NOT NULL,
            created_at REAL,
            deleted INTEGER DEFAULT 0
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            actor_id INTEGER,
            item_id INTEGER,
            comment_id INTEGER,
            body TEXT,
            is_read INTEGER DEFAULT 0,
            created_at REAL
        )
        """
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_likes_item ON gallery_likes(item_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_comments_item ON gallery_comments(item_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read)")
    c.commit()


def gallery_like_counts(item_ids: list[int]) -> dict[int, int]:
    if not item_ids:
        return {}
    c = _conn()
    _ensure_social(c)
    q = ",".join("?" * len(item_ids))
    rows = c.execute(
        f"SELECT item_id, COUNT(*) AS n FROM gallery_likes WHERE item_id IN ({q}) GROUP BY item_id",
        item_ids,
    ).fetchall()
    c.close()
    return {int(r["item_id"]): int(r["n"]) for r in rows}


def gallery_user_liked(user_id: int, item_ids: list[int]) -> set[int]:
    if not user_id or not item_ids:
        return set()
    c = _conn()
    _ensure_social(c)
    q = ",".join("?" * len(item_ids))
    rows = c.execute(
        f"SELECT item_id FROM gallery_likes WHERE user_id=? AND item_id IN ({q})",
        [user_id, *item_ids],
    ).fetchall()
    c.close()
    return {int(r["item_id"]) for r in rows}


def gallery_comment_counts(item_ids: list[int]) -> dict[int, int]:
    if not item_ids:
        return {}
    c = _conn()
    _ensure_social(c)
    q = ",".join("?" * len(item_ids))
    rows = c.execute(
        f"SELECT item_id, COUNT(*) AS n FROM gallery_comments WHERE deleted=0 AND item_id IN ({q}) GROUP BY item_id",
        item_ids,
    ).fetchall()
    c.close()
    return {int(r["item_id"]): int(r["n"]) for r in rows}


def gallery_like_toggle(user_id: int, item_id: int) -> tuple[bool, int]:
    """Toggle like. Returns (liked_now, total_count)."""
    c = _conn()
    _ensure_social(c)
    _ensure_gallery(c)
    item = c.execute("SELECT id, user_id, title FROM gallery WHERE id=?", (item_id,)).fetchone()
    if not item:
        c.close()
        return False, 0
    existing = c.execute(
        "SELECT 1 FROM gallery_likes WHERE item_id=? AND user_id=?",
        (item_id, user_id),
    ).fetchone()
    liked = False
    if existing:
        c.execute("DELETE FROM gallery_likes WHERE item_id=? AND user_id=?", (item_id, user_id))
        liked = False
    else:
        c.execute(
            "INSERT INTO gallery_likes(item_id, user_id, created_at) VALUES (?,?,?)",
            (item_id, user_id, time.time()),
        )
        liked = True
        owner = item["user_id"]
        if owner and int(owner) != int(user_id):
            actor = c.execute(
                "SELECT display_name, email, discord_username FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
            name = (actor["display_name"] if actor else None) or (
                actor["discord_username"] if actor else None
            ) or ((actor["email"] or "someone").split("@")[0] if actor else "someone")
            title = (item["title"] or "работу")[:40]
            c.execute(
                """INSERT INTO notifications(user_id, kind, actor_id, item_id, body, is_read, created_at)
                   VALUES (?,?,?,?,?,0,?)""",
                (int(owner), "like", user_id, item_id, f"{name} лайкнул(а) «{title}»", time.time()),
            )
    c.commit()
    n = c.execute("SELECT COUNT(*) AS n FROM gallery_likes WHERE item_id=?", (item_id,)).fetchone()["n"]
    c.close()
    return liked, int(n)


def gallery_add_comment(user_id: int, item_id: int, body: str, parent_id: int | None = None) -> dict | None:
    body = (body or "").strip()[:1000]
    if not body:
        return None
    c = _conn()
    _ensure_social(c)
    _ensure_gallery(c)
    item = c.execute("SELECT id, user_id, title FROM gallery WHERE id=?", (item_id,)).fetchone()
    if not item:
        c.close()
        return None
    if parent_id:
        parent = c.execute(
            "SELECT id, user_id, item_id FROM gallery_comments WHERE id=? AND deleted=0",
            (parent_id,),
        ).fetchone()
        if not parent or int(parent["item_id"]) != int(item_id):
            c.close()
            return None
    cur = c.execute(
        """INSERT INTO gallery_comments(item_id, user_id, parent_id, body, created_at, deleted)
           VALUES (?,?,?,?,?,0)""",
        (item_id, user_id, parent_id, body, time.time()),
    )
    cid = int(cur.lastrowid or 0)
    actor = c.execute(
        "SELECT display_name, email, discord_username FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    name = (actor["display_name"] if actor else None) or (
        actor["discord_username"] if actor else None
    ) or ((actor["email"] or "someone").split("@")[0] if actor else "someone")
    title = (item["title"] or "работу")[:40]
    # notify owner
    owner = item["user_id"]
    if owner and int(owner) != int(user_id):
        kind = "reply" if parent_id else "comment"
        msg = f"{name} ответил(а) под «{title}»" if parent_id else f"{name} прокомментировал(а) «{title}»"
        c.execute(
            """INSERT INTO notifications(user_id, kind, actor_id, item_id, comment_id, body, is_read, created_at)
               VALUES (?,?,?,?,?,?,0,?)""",
            (int(owner), kind, user_id, item_id, cid, msg, time.time()),
        )
    # notify parent comment author on reply
    if parent_id:
        parent = c.execute("SELECT user_id FROM gallery_comments WHERE id=?", (parent_id,)).fetchone()
        if parent and int(parent["user_id"]) != int(user_id) and (
            not owner or int(parent["user_id"]) != int(owner)
        ):
            c.execute(
                """INSERT INTO notifications(user_id, kind, actor_id, item_id, comment_id, body, is_read, created_at)
                   VALUES (?,?,?,?,?,?,0,?)""",
                (
                    int(parent["user_id"]),
                    "reply",
                    user_id,
                    item_id,
                    cid,
                    f"{name} ответил(а) на ваш комментарий",
                    time.time(),
                ),
            )
    c.commit()
    row = c.execute(
        """SELECT c.id, c.item_id, c.user_id, c.parent_id, c.body, c.created_at,
                  u.display_name, u.email, u.discord_username
           FROM gallery_comments c LEFT JOIN users u ON u.id = c.user_id
           WHERE c.id=?""",
        (cid,),
    ).fetchone()
    c.close()
    return dict(row) if row else {"id": cid, "body": body, "user_id": user_id, "parent_id": parent_id}


def gallery_list_comments(item_id: int, limit: int = 100) -> list[dict]:
    c = _conn()
    _ensure_social(c)
    rows = c.execute(
        """
        SELECT c.id, c.item_id, c.user_id, c.parent_id, c.body, c.created_at,
               u.display_name, u.email, u.discord_username
        FROM gallery_comments c
        LEFT JOIN users u ON u.id = c.user_id
        WHERE c.item_id=? AND c.deleted=0
        ORDER BY c.created_at ASC
        LIMIT ?
        """,
        (item_id, limit),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def gallery_item_stats(item_id: int, viewer_id: int | None = None) -> dict:
    c = _conn()
    _ensure_social(c)
    likes = c.execute("SELECT COUNT(*) AS n FROM gallery_likes WHERE item_id=?", (item_id,)).fetchone()["n"]
    comments = c.execute(
        "SELECT COUNT(*) AS n FROM gallery_comments WHERE item_id=? AND deleted=0", (item_id,)
    ).fetchone()["n"]
    liked = False
    if viewer_id:
        liked = bool(
            c.execute(
                "SELECT 1 FROM gallery_likes WHERE item_id=? AND user_id=?",
                (item_id, viewer_id),
            ).fetchone()
        )
    c.close()
    return {"likes": int(likes), "comments": int(comments), "liked": liked}


def notifications_list(user_id: int, limit: int = 40) -> list[dict]:
    c = _conn()
    _ensure_social(c)
    rows = c.execute(
        """
        SELECT n.id, n.kind, n.actor_id, n.item_id, n.comment_id, n.body, n.is_read, n.created_at,
               u.display_name, u.email, u.discord_username
        FROM notifications n
        LEFT JOIN users u ON u.id = n.actor_id
        WHERE n.user_id=?
        ORDER BY n.created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def notifications_unread_count(user_id: int) -> int:
    c = _conn()
    _ensure_social(c)
    n = c.execute(
        "SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=0",
        (user_id,),
    ).fetchone()["n"]
    c.close()
    return int(n)


def notifications_mark_read(user_id: int, ids: list[int] | None = None) -> int:
    c = _conn()
    _ensure_social(c)
    if ids:
        q = ",".join("?" * len(ids))
        c.execute(
            f"UPDATE notifications SET is_read=1 WHERE user_id=? AND id IN ({q})",
            [user_id, *ids],
        )
    else:
        c.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
    c.commit()
    n = c.total_changes
    c.close()
    return n



# ====================== Steam-style public profile ======================

_RESERVED_USERNAMES = {
    "admin", "api", "app", "static", "profile", "edit", "login", "register",
    "gallery", "support", "help", "null", "undefined", "me", "settings",
}


def _slug_username(raw: str) -> str:
    s = (raw or "").strip().lower()
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("_", "-"):
            out.append(ch)
    return "".join(out)[:24]


def ensure_profile_username(user_id: int, preferred: str | None = None) -> str:
    """Ensure user has a unique profile_username; return it."""
    c = _conn()
    row = c.execute("SELECT profile_username, display_name, email, id FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        c.close()
        return ""
    existing = (row["profile_username"] or "").strip()
    if existing:
        c.close()
        return existing
    base = _slug_username(preferred or row["display_name"] or (row["email"] or "").split("@")[0] or f"user{user_id}")
    if not base or base in _RESERVED_USERNAMES:
        base = f"user{user_id}"
    candidate = base
    n = 0
    while True:
        taken = c.execute(
            "SELECT id FROM users WHERE lower(profile_username)=? AND id!=?",
            (candidate.lower(), user_id),
        ).fetchone()
        if not taken:
            break
        n += 1
        candidate = f"{base}{n}"
        if n > 999:
            candidate = f"user{user_id}"
            break
    c.execute("UPDATE users SET profile_username=? WHERE id=?", (candidate, user_id))
    c.commit()
    c.close()
    return candidate


def get_public_profile(username: str) -> dict | None:
    un = _slug_username(username)
    if not un:
        return None
    c = _conn()
    row = c.execute(
        """
        SELECT id, email, display_name, avatar_path, is_pro,
               profile_username, profile_summary, profile_background,
               profile_bg_x, profile_bg_y, profile_bg_scale, profile_bg_overlay,
               profile_level, profile_xp, profile_location, profile_status, profile_visibility,
               created_at
        FROM users WHERE lower(profile_username)=?
        """,
        (un.lower(),),
    ).fetchone()
    c.close()
    if not row:
        return None
    vis = (row["profile_visibility"] or "public").lower()
    return {
        "id": int(row["id"]),
        "email": row["email"],
        "display_name": row["display_name"] or row["profile_username"] or "User",
        "avatar_path": row["avatar_path"],
        "is_pro": bool(row["is_pro"]),
        "profile_username": row["profile_username"],
        "profile_summary": row["profile_summary"] or "",
        "profile_background": row["profile_background"],
        "profile_bg_x": float(row["profile_bg_x"] if row["profile_bg_x"] is not None else 50),
        "profile_bg_y": float(row["profile_bg_y"] if row["profile_bg_y"] is not None else 30),
        "profile_bg_scale": float(row["profile_bg_scale"] if row["profile_bg_scale"] is not None else 1),
        "profile_bg_overlay": float(row["profile_bg_overlay"] if row["profile_bg_overlay"] is not None else 0.5),
        "profile_level": int(row["profile_level"] or 1),
        "profile_xp": int(row["profile_xp"] or 0),
        "profile_location": row["profile_location"] or "",
        "profile_status": (row["profile_status"] or "online").lower(),
        "profile_visibility": vis,
        "created_at": row["created_at"],
    }


def update_steam_profile(user_id: int, **fields) -> tuple[bool, str]:
    """Update profile fields. Returns (ok, msg)."""
    allowed = {
        "display_name", "profile_summary", "profile_location", "profile_status",
        "profile_visibility", "profile_level", "profile_xp",
        "profile_bg_x", "profile_bg_y", "profile_bg_scale", "profile_bg_overlay",
        "profile_background", "avatar_path", "profile_username",
    }
    c = _conn()
    sets = []
    vals = []
    if "profile_username" in fields and fields["profile_username"] is not None:
        un = _slug_username(str(fields["profile_username"]))
        if len(un) < 3:
            c.close()
            return False, "Username min 3 chars"
        if un in _RESERVED_USERNAMES:
            c.close()
            return False, "Username reserved"
        taken = c.execute(
            "SELECT id FROM users WHERE lower(profile_username)=? AND id!=?",
            (un.lower(), user_id),
        ).fetchone()
        if taken:
            c.close()
            return False, "Username taken"
        sets.append("profile_username=?")
        vals.append(un)
    for k, v in fields.items():
        if k not in allowed or k == "profile_username":
            continue
        if k == "display_name":
            v = (str(v or "").strip()[:40] or None)
        elif k == "profile_summary":
            v = (str(v or "").strip()[:2000])
        elif k == "profile_location":
            v = (str(v or "").strip()[:80])
        elif k == "profile_status":
            v = (str(v or "online").strip().lower()[:20])
        elif k == "profile_visibility":
            v = (str(v or "public").strip().lower())
            if v not in ("public", "private", "friends"):
                v = "public"
        elif k in ("profile_level", "profile_xp"):
            try:
                v = max(0, int(v))
            except Exception:
                continue
        elif k in ("profile_bg_x", "profile_bg_y", "profile_bg_scale", "profile_bg_overlay"):
            try:
                v = float(v)
            except Exception:
                continue
        sets.append(f"{k}=?")
        vals.append(v)
    if not sets:
        c.close()
        return False, "Nothing to update"
    vals.append(user_id)
    c.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", vals)
    c.commit()
    c.close()
    return True, "OK"



def _ensure_profile_showcases(c):
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS profile_showcases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sc_type TEXT NOT NULL,
            title TEXT,
            sort_order INTEGER DEFAULT 0,
            data_json TEXT,
            created_at REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    c.commit()


def profile_showcase_list(user_id: int) -> list[dict]:
    c = _conn()
    _ensure_profile_showcases(c)
    rows = c.execute(
        "SELECT id, user_id, sc_type, title, sort_order, data_json, created_at FROM profile_showcases WHERE user_id=? ORDER BY sort_order ASC, id ASC",
        (user_id,),
    ).fetchall()
    c.close()
    out = []
    for r in rows:
        import json
        data = {}
        try:
            data = json.loads(r["data_json"] or "{}")
        except Exception:
            data = {}
        out.append({
            "id": int(r["id"]),
            "user_id": int(r["user_id"]),
            "type": r["sc_type"],
            "title": r["title"] or "",
            "sort_order": int(r["sort_order"] or 0),
            "data": data,
            "created_at": r["created_at"],
        })
    return out


def profile_showcase_add(user_id: int, sc_type: str, title: str, data: dict, sort_order: int | None = None) -> int:
    import json
    c = _conn()
    _ensure_profile_showcases(c)
    if sort_order is None:
        row = c.execute("SELECT COALESCE(MAX(sort_order),0)+1 AS n FROM profile_showcases WHERE user_id=?", (user_id,)).fetchone()
        sort_order = int(row["n"])
    cur = c.execute(
        "INSERT INTO profile_showcases(user_id, sc_type, title, sort_order, data_json, created_at) VALUES (?,?,?,?,?,?)",
        (user_id, sc_type, (title or "")[:80], sort_order, json.dumps(data or {}), time.time()),
    )
    c.commit()
    sid = int(cur.lastrowid or 0)
    c.close()
    return sid


def profile_showcase_delete(user_id: int, showcase_id: int) -> bool:
    c = _conn()
    _ensure_profile_showcases(c)
    cur = c.execute("DELETE FROM profile_showcases WHERE id=? AND user_id=?", (showcase_id, user_id))
    c.commit()
    n = cur.rowcount
    c.close()
    return n > 0


def profile_showcase_reorder(user_id: int, ordered_ids: list[int]) -> None:
    c = _conn()
    _ensure_profile_showcases(c)
    for i, sid in enumerate(ordered_ids):
        c.execute("UPDATE profile_showcases SET sort_order=? WHERE id=? AND user_id=?", (i, sid, user_id))
    c.commit()
    c.close()


def gallery_list_for_user(user_id: int, limit: int = 50) -> list[dict]:
    c = _conn()
    _ensure_gallery(c)
    rows = c.execute(
        """
        SELECT id, user_id, title, mode, image_path, thumb_path, status, created_at
        FROM gallery WHERE user_id=? ORDER BY created_at DESC LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]
