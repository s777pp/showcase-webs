"""Create (or reset) a local test account with Pro for the development server.

Local runs have no e-mail delivery, so the sign-up code cannot arrive. This
writes the account straight into the local SQLite database instead.

    python scripts/dev_account.py you@example.com "a-password-10+" [days]

Refuses to run against PostgreSQL (DATABASE_URL), so it cannot touch production.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if (os.environ.get("DATABASE_URL") or "").strip():
    sys.exit("DATABASE_URL is set: this script only works on the local SQLite database.")

import auth_db  # noqa: E402

if len(sys.argv) < 3:
    sys.exit(__doc__)
email, password = auth_db.normalize_email(sys.argv[1]), sys.argv[2]
days = float(sys.argv[3]) if len(sys.argv) > 3 else 365
if not email or len(password) < 10:
    sys.exit("Need a valid e-mail and a password of at least 10 characters.")

if not auth_db.user_exists(email):
    ok, msg = auth_db.register(email, password)
    if not ok:
        sys.exit(msg)
else:
    c = auth_db._conn()
    try:
        c.execute("UPDATE users SET password_hash=?, email_verified=1 WHERE email=?",
                  (auth_db._hash_pw(password), email))
        c.commit()
    finally:
        c.close()

c = auth_db._conn()
try:
    user_id = int(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"])
finally:
    c.close()
auth_db.set_pro(user_id, True, until=time.time() + days * 86400)
print(f"Local account ready: {email} (Pro for {days:g} days). Database: {auth_db.DB}")
