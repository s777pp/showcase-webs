"""Telegram mini app (owner, 2026-10-09): the site's everyday tools inside the shop bot, at /tg.

Who is calling: every /api/tg-app/* request carries Telegram's ``initData`` in the X-Tg-Init-Data header. It is
signed by Telegram with the bot token (HMAC-SHA256, key = HMAC("WebAppData", token)); ``verify`` checks the
signature and its age, so the Telegram user id can be trusted without cookies (web.telegram.org shows the app in a
third-party iframe where the site cookie is not sent). The token is TG_APP_BOT_TOKEN, else ADMIN_BOT_TOKEN: it must
be the bot whose menu button opens the app.

Limits are the bot's cutting limits (smweb/telegram_cut.py): Pro through a known account (telegram_billing.account_for),
else TELEGRAM_CUT_DAILY files a day per Telegram id, shared by cutting, link downloads and conversions. Upscale needs
a Pro account (the site's own rules, routers/media.upscale_refusal).

Results: every tool ends with a file the server holds (a cut ZIP, a file in JOBS/<id>/ marked with .tg_owner, or an
upscale result in private R2). The app shows it through a short signed link (``sign``) and the bot can send it into
the user's chat (``send_document``), because file downloads inside Telegram's web views are unreliable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl

import redis_store as rs
from smweb import telegram_cut
from smweb.core import JOBS, _day

LOGGER = logging.getLogger(__name__)
INIT_MAX_AGE = 24 * 3600
LINK_TTL = 15 * 60
SEND_MAX_BYTES = 49 * 1024 * 1024          # Bot API sendDocument limit is 50 MB
OWNER_FILE = ".tg_owner"
_FILE_ID = re.compile(r"^[0-9a-f]{32}$")


def bot_token() -> str:
    return (os.environ.get("TG_APP_BOT_TOKEN") or os.environ.get("ADMIN_BOT_TOKEN") or "").strip()


def configured() -> bool:
    return bool(bot_token())


# ---------------------------------------------------------------- who is calling
def verify(init_data: str, token: str | None = None, now: float | None = None) -> dict | None:
    """The Telegram user of a valid, fresh initData string, else None."""
    token = token if token is not None else bot_token()
    if not token or not init_data or len(init_data) > 8192:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    received = pairs.pop("hash", "")
    # Every other field, Bot API 8's "signature" included, is part of the checked string.
    check = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode("utf-8"), hashlib.sha256).hexdigest()
    if not received or not hmac.compare_digest(expected, received):
        return None
    try:
        auth_date = int(pairs.get("auth_date") or 0)
        user = json.loads(pairs.get("user") or "{}")
    except (ValueError, TypeError):
        return None
    if not auth_date or (now or time.time()) - auth_date > INIT_MAX_AGE:
        return None
    if not isinstance(user, dict) or not telegram_cut.valid_tg(str(user.get("id") or "")):
        return None
    return {"id": str(user["id"]), "first_name": str(user.get("first_name") or "")[:64],
            "username": str(user.get("username") or "")[:64], "language": str(user.get("language_code") or "")[:8]}


def user_from(request) -> dict | None:
    return verify(request.headers.get("x-tg-init-data") or "")


# ---------------------------------------------------------------- account, Pro and the daily limit
def account(tg_id: str) -> dict | None:
    """The site account that holds this Telegram user's Pro (Telegram sign-in or an earlier bot purchase)."""
    from smweb import telegram_billing
    user_id = telegram_billing.account_for(tg_id)
    if not user_id:
        return None
    import auth_db
    c = auth_db._conn()
    try:
        row = c.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
        return dict(row) if row else None
    finally:
        c.close()


def can_use(tg_id: str) -> tuple[bool, dict]:
    q = telegram_cut.quota(tg_id)
    return (q["pro"] or q["left"] > 0), q


def charge(tg_id: str, quota: dict) -> None:
    if not quota.get("pro"):
        rs.quota_inc(telegram_cut.owner(tg_id), _day(), 1)


# ---------------------------------------------------------------- files the app made (downloads, conversions)
def mark(directory: Path, tg_id: str, name: str, media_type: str) -> None:
    (directory / OWNER_FILE).write_text(json.dumps({"tg": tg_id, "name": name, "type": media_type}), encoding="utf-8")


def owned_file(tg_id: str, file_id: str) -> dict | None:
    if not _FILE_ID.match(str(file_id or "")):
        return None
    directory = JOBS / file_id
    try:
        meta = json.loads((directory / OWNER_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if str(meta.get("tg")) != str(tg_id):
        return None
    path = directory / Path(str(meta.get("name") or "")).name
    if not path.is_file():
        return None
    return {"path": path, "name": path.name, "type": str(meta.get("type") or "application/octet-stream")}


def resolve(tg_id: str, kind: str, ref: str) -> dict | None:
    """{"name", "type", and "path" (local) or "key" (private R2)} of a finished result owned by this user."""
    if kind == "cut":
        job = telegram_cut.job_for(tg_id, ref)
        if not job or job.get("status") != "done":
            return None
        path = Path(str(job.get("zip_path") or ""))
        if path.is_file():
            return {"path": path, "name": "showcase.zip", "type": "application/zip"}
        if job.get("result_key"):
            return {"key": str(job["result_key"]), "name": "showcase.zip", "type": "application/zip"}
        return None
    if kind == "file":
        return owned_file(tg_id, ref)
    if kind == "upscale":
        user = account(tg_id)
        job = rs.job_get(ref) if re.fullmatch(r"[a-f0-9]{32}", str(ref or "")) else None
        if not user or not job or job.get("kind") != "upscale" or job.get("user_key") != str(int(user["id"])):
            return None
        if job.get("status") != "done" or not job.get("result_key"):
            return None
        return {"key": str(job["result_key"]), "name": str(job.get("download_name") or "upscaled.png"),
                "type": str(job.get("content_type") or "application/octet-stream")}
    return None


def read_bytes(item: dict) -> bytes:
    if item.get("path"):
        return Path(item["path"]).read_bytes()
    from smweb import object_store
    return object_store.get_bytes(item["key"], public=False)


def size_of(item: dict) -> int | None:
    if item.get("path"):
        try:
            return Path(item["path"]).stat().st_size
        except OSError:
            return None
    return None


# ---------------------------------------------------------------- short signed links (preview, WebApp.downloadFile)
def _secret() -> bytes:
    return ("tg-app:" + (os.environ.get("SECRET_KEY") or "showcasemaker")).encode("utf-8")


def sign(tg_id: str, kind: str, ref: str, inline: bool = False, ttl: int = LINK_TTL) -> str:
    body = json.dumps({"t": tg_id, "k": kind, "r": ref, "i": 1 if inline else 0, "e": int(time.time()) + ttl},
                      separators=(",", ":")).encode("utf-8")
    data = base64.urlsafe_b64encode(body).decode("ascii").rstrip("=")
    mac = hmac.new(_secret(), data.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    return f"{data}.{mac}"


def unsign(token: str) -> dict | None:
    try:
        data, mac = str(token or "").split(".", 1)
        expected = hmac.new(_secret(), data.encode("ascii"), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(expected, mac):
            return None
        body = json.loads(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
    except (ValueError, TypeError, UnicodeError):
        return None
    if int(body.get("e") or 0) < time.time():
        return None
    return body


# ---------------------------------------------------------------- the bot writes into the user's chat
def _api(method: str, **kwargs):
    import requests
    return requests.post(f"https://api.telegram.org/bot{bot_token()}/{method}", timeout=60, **kwargs)


def send_document(chat_id: str, name: str, data: bytes, caption: str = "") -> tuple[bool, str]:
    if not configured():
        return False, "not_configured"
    if len(data) > SEND_MAX_BYTES:
        return False, "too_big"
    try:
        response = _api("sendDocument", data={"chat_id": chat_id, "caption": caption[:1000]},
                        files={"document": (name, data)})
        payload = response.json()
    except Exception:
        LOGGER.warning("tg app: sendDocument failed", exc_info=True)
        return False, "telegram"
    if not payload.get("ok"):
        # 403 = the user blocked the bot or never pressed Start.
        LOGGER.info("tg app: sendDocument refused (%s)", payload.get("error_code"))
        return False, "blocked" if payload.get("error_code") == 403 else "telegram"
    return True, ""


def send_text(chat_id: str, text: str) -> tuple[bool, str]:
    """Plain text (no parse mode, so BBCode brackets stay as they are); longer than one message -> a .txt file."""
    if not configured():
        return False, "not_configured"
    if len(text) > 4000:
        return send_document(chat_id, "infobox.txt", text.encode("utf-8"))
    try:
        payload = _api("sendMessage", data={"chat_id": chat_id, "text": text}).json()
    except Exception:
        LOGGER.warning("tg app: sendMessage failed", exc_info=True)
        return False, "telegram"
    if not payload.get("ok"):
        return False, "blocked" if payload.get("error_code") == 403 else "telegram"
    return True, ""
