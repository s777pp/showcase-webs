"""Pro bought in the owner's Telegram bot (2026-10-06).

The bot takes the money (Telegram Stars, CryptoBot, or a transfer the owner confirms by hand) and then reports
the payment through ``/api/bot-admin/pro/*`` (``X-Bot-Admin-Secret``, see routers/bot_admin.py). The bot is the
only caller and it is trusted to have checked the payment; this module only decides WHICH account gets the Pro:

* The purchase started on the site: a signed-in user chose "Telegram bot" in the purchase dialog,
  ``create_order`` stored a random token and the browser opened ``t.me/<bot>?start=buy_<token>``. The bot sends
  the token back with the payment, and the token names the account.
* The Telegram user is already known: an earlier purchase of theirs landed on an account (``telegram_links``),
  or an account signs in through Telegram (``users.telegram_id``).
* Nobody is known: the sale waits as ``pending`` with a claim token. The bot gives the buyer
  ``/billing/telegram/claim?tg=<token>``; whoever opens it signed in receives the Pro, once.

``telegram_links`` only routes later purchases. It is deliberately NOT ``users.telegram_id``: that column lets a
Telegram account sign in, and paying for somebody's order must never hand out a login.

Every bot payment grants once: ``payment_id`` is the bot's random order id and the grant is an atomic
``pending -> granted`` transition, so retries from the bot are safe. Days are added on top of what is left,
exactly like Gumroad purchases (smweb/gumroad_billing.py).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
import sqlite3
import time

import auth_db
from smweb import gumroad_billing

LOG = logging.getLogger("sm.telegram_billing")

# plan id -> days (None = forever). Same ids and lengths as the Gumroad plans.
PLANS: dict[str, int | None] = {plan: days for plan, (_permalink, days) in gumroad_billing.PLANS.items()}
ORDER_TTL = 30 * 86400
START_PREFIX = "buy_"          # t.me/<bot>?start=buy_<token>
METHODS = ("stars", "crypto", "paypal", "card_uah", "manual")

_TOKEN = re.compile(r"^[A-Za-z0-9_\-]{16,64}$")
_PAYMENT_ID = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")
_TG_ID = re.compile(r"^[0-9]{3,20}$")


def configured() -> bool:
    """The bot can report purchases only when both sides share BOT_ADMIN_SECRET."""
    return bool((os.environ.get("BOT_ADMIN_SECRET") or "").strip())


def bot_username() -> str:
    for name in ("TELEGRAM_SHOP_BOT_USERNAME", "TELEGRAM_BOT_USERNAME"):
        value = (os.environ.get(name) or "").strip().lstrip("@")
        if re.fullmatch(r"[A-Za-z0-9_]{5,32}", value):
            return value
    return "SteamMakerBot"


def marker(payment_id: str) -> str:
    """pro_code of an account whose current Pro came from a bot payment."""
    return "TGS-" + hashlib.sha256(payment_id.encode("utf-8")).hexdigest()[:40].upper()


def _site_origin() -> str:
    return (os.environ.get("APP_URL") or "https://showcasemaker.com").strip().rstrip("/")


def claim_url(token: str) -> str:
    return f"{_site_origin()}/billing/telegram/claim?tg={token}"


def valid_token(value: str) -> bool:
    return bool(_TOKEN.match(value or ""))


# ---------------------------------------------------------------- orders started on the site
def create_order(user_id: int, plan: str) -> dict:
    if plan not in PLANS:
        raise ValueError("plan")
    token = secrets.token_urlsafe(18)
    now = time.time()
    c = auth_db._conn()
    try:
        c.execute("DELETE FROM telegram_orders WHERE created_at<? AND payment_id IS NULL", (now - ORDER_TTL,))
        c.execute("INSERT INTO telegram_orders (token, user_id, plan, created_at) VALUES (?,?,?,?)",
                  (token, int(user_id), plan, now))
        c.commit()
    finally:
        c.close()
    return {"token": token, "url": f"https://t.me/{bot_username()}?start={START_PREFIX}{token}"}


def _order(token: str) -> dict | None:
    if not valid_token(token):
        return None
    c = auth_db._conn()
    try:
        row = c.execute("SELECT token, user_id, plan, created_at, payment_id FROM telegram_orders WHERE token=?",
                        (token,)).fetchone()
        return dict(row) if row else None
    finally:
        c.close()


def _order_usable(order: dict | None, payment_id: str = "") -> bool:
    return bool(order) and order["payment_id"] in (None, "", payment_id) and time.time() - order["created_at"] < ORDER_TTL


def order_info(token: str) -> dict | None:
    """What the bot shows after ``/start buy_<token>``: the plan chosen on the site and whose account it is."""
    order = _order(token)
    if not _order_usable(order):
        return None
    state = gumroad_billing.pro_state(int(order["user_id"]))
    return {"plan": order["plan"], "account": account_label(int(order["user_id"])), "pro": state}


# ---------------------------------------------------------------- accounts
def account_label(user_id: int) -> str:
    """A name the buyer recognises without exposing a full e-mail address."""
    c = auth_db._conn()
    try:
        row = c.execute("SELECT email, display_name, profile_username FROM users WHERE id=?", (int(user_id),)).fetchone()
    finally:
        c.close()
    if not row:
        return ""
    name = str(row["display_name"] or row["profile_username"] or "").strip()
    if name:
        return name[:40]
    email = str(row["email"] or "")
    local, _, domain = email.partition("@")
    if not domain or domain == "users.local":
        return f"#{int(user_id)}"
    return f"{local[:2]}***@{domain}"


def account_for(tg_id: str) -> int | None:
    """The site account that gets purchases of this Telegram user, if one is known."""
    tg_id = str(tg_id or "")
    if not _TG_ID.match(tg_id):
        return None
    c = auth_db._conn()
    try:
        row = c.execute(
            "SELECT l.user_id FROM telegram_links l JOIN users u ON u.id=l.user_id WHERE l.tg_id=?", (tg_id,)).fetchone()
        if row:
            return int(row["user_id"])
        row = c.execute("SELECT id FROM users WHERE telegram_id=? ORDER BY id LIMIT 1", (tg_id,)).fetchone()
        return int(row["id"]) if row else None
    finally:
        c.close()


def account_info(tg_id: str) -> dict:
    user_id = account_for(tg_id)
    if user_id is None:
        return {"linked": False, "account": "", "pro": {"pro": False, "until": None, "lifetime": False}}
    return {"linked": True, "account": account_label(user_id), "pro": gumroad_billing.pro_state(user_id)}


def _link(tg_id: str, user_id: int) -> None:
    c = auth_db._conn()
    try:
        c.execute(
            "INSERT INTO telegram_links (tg_id, user_id, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(tg_id) DO UPDATE SET user_id=excluded.user_id, updated_at=excluded.updated_at",
            (str(tg_id), int(user_id), time.time()))
        c.commit()
    finally:
        c.close()


# ---------------------------------------------------------------- Pro time (same arithmetic as Gumroad)
def _grant(user_id: int, payment_id: str, days: int | None) -> None:
    now = time.time()
    c = auth_db._conn()
    try:
        if days is None:
            c.execute("UPDATE users SET is_pro=1, pro_until=NULL, pro_code=? WHERE id=?", (marker(payment_id), int(user_id)))
        else:
            # Extend what is left (or start now); permanent Pro is left alone.
            c.execute(
                "UPDATE users SET is_pro=1, pro_code=?, pro_until=(CASE WHEN is_pro=1 AND pro_until IS NOT NULL "
                "AND pro_until>? THEN pro_until ELSE ? END)+? WHERE id=? AND NOT (is_pro=1 AND pro_until IS NULL)",
                (marker(payment_id), now, now, float(days) * 86400, int(user_id)),
            )
        c.commit()
    finally:
        c.close()


def _revoke(user_id: int, payment_id: str, days: int | None) -> None:
    now = time.time()
    c = auth_db._conn()
    try:
        if days is None:
            c.execute("UPDATE users SET is_pro=0, pro_until=NULL WHERE id=? AND pro_until IS NULL AND pro_code=?",
                      (int(user_id), marker(payment_id)))
        else:
            c.execute("UPDATE users SET pro_until=pro_until-? WHERE id=? AND is_pro=1 AND pro_until IS NOT NULL",
                      (float(days) * 86400, int(user_id)))
            c.execute("UPDATE users SET is_pro=0, pro_until=NULL WHERE id=? AND pro_until IS NOT NULL AND pro_until<=?",
                      (int(user_id), now))
        c.commit()
    finally:
        c.close()


# ---------------------------------------------------------------- sales
def _row(payment_id: str = "", claim_token: str = "") -> dict | None:
    c = auth_db._conn()
    try:
        if payment_id:
            row = c.execute("SELECT * FROM telegram_sales WHERE payment_id=?", (payment_id,)).fetchone()
        else:
            row = c.execute("SELECT * FROM telegram_sales WHERE claim_token=?", (claim_token,)).fetchone()
        return dict(row) if row else None
    finally:
        c.close()


def _store(payment_id: str, tg_id: str, tg_username: str, plan: str, method: str, amount: str, currency: str) -> dict:
    now = time.time()
    c = auth_db._conn()
    try:
        try:
            c.execute(
                "INSERT INTO telegram_sales (payment_id, tg_id, tg_username, plan, days, status, method, amount, "
                "currency, claim_token, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (payment_id, tg_id, tg_username[:64] or None, plan, PLANS[plan], "pending", method, amount[:24],
                 currency[:8], secrets.token_urlsafe(18), now, now),
            )
            c.commit()
        except sqlite3.IntegrityError:
            c.rollback()
    finally:
        c.close()
    return _row(payment_id) or {}


def _transition(payment_id: str, old: str, new: str, **fields) -> bool:
    """Atomic state change; True only for the one caller that made it."""
    sets = ", ".join(["status=?", "updated_at=?"] + [f"{key}=?" for key in fields])
    c = auth_db._conn()
    try:
        cursor = c.execute(f"UPDATE telegram_sales SET {sets} WHERE payment_id=? AND status=?",
                           (new, time.time(), *fields.values(), payment_id, old))
        c.commit()
        return cursor.rowcount == 1
    finally:
        c.close()


def _bind(payment_id: str, user_id: int, order_token: str = "") -> bool:
    """Attach a sale to an account once. True when it belongs to user_id afterwards."""
    c = auth_db._conn()
    try:
        c.execute("UPDATE telegram_sales SET user_id=?, order_token=?, updated_at=? WHERE payment_id=? AND user_id IS NULL",
                  (int(user_id), order_token or None, time.time(), payment_id))
        if order_token:
            c.execute("UPDATE telegram_orders SET payment_id=? WHERE token=? AND payment_id IS NULL", (payment_id, order_token))
        c.commit()
        row = c.execute("SELECT user_id FROM telegram_sales WHERE payment_id=?", (payment_id,)).fetchone()
        return bool(row) and row["user_id"] is not None and int(row["user_id"]) == int(user_id)
    finally:
        c.close()


def _finish(row: dict, owner: int) -> dict:
    """Grant a bound sale (once) and describe the result for the bot / the claim page."""
    payment_id = str(row["payment_id"])
    granted = _transition(payment_id, "pending", "granted", granted_at=time.time())
    if granted:
        _grant(owner, payment_id, row["days"])
        _link(str(row["tg_id"]), owner)
        _bell(owner, str(row["plan"]))
        try:
            from smweb import analytics
            analytics.record("pro_activated", user_id=owner, properties={"method": "telegram"},
                             event_key=f"pro:telegram:{marker(payment_id)}")
        except Exception:
            LOG.debug("analytics failed", exc_info=True)
    else:
        status = (_row(payment_id) or {}).get("status")
        if status != "granted":
            return {"status": "revoked", "plan": row["plan"]}
    return {"status": "granted" if granted else "already", "plan": row["plan"], "user_id": owner,
            "account": account_label(owner), "pro": gumroad_billing.pro_state(owner)}


def record_payment(payment_id: str, tg_id: str, plan: str, *, tg_username: str = "", method: str = "manual",
                   amount: str = "", currency: str = "", order_token: str = "", claim_only: bool = False) -> dict:
    """A payment the bot has verified. Returns {"status": granted | already | claim | revoked, ...}.

    ``claim`` means no account is known yet: the answer carries ``claim_url`` for the buyer.
    ``claim_only`` skips the known-account lookup (the buyer said the Pro is for another account).
    """
    payment_id, tg_id = str(payment_id or ""), str(tg_id or "")
    if not _PAYMENT_ID.match(payment_id) or not _TG_ID.match(tg_id):
        raise ValueError("payment")
    if plan not in PLANS:
        raise ValueError("plan")
    method = method if method in METHODS else "manual"
    row = _store(payment_id, tg_id, str(tg_username or "").lstrip("@"), plan, method, str(amount or ""), str(currency or ""))
    if not row:
        raise RuntimeError("sale was not stored")
    if row["status"] in ("revoked", "refunded"):
        return {"status": "revoked", "plan": row["plan"]}

    owner = row.get("user_id")
    if owner is None:
        order = _order(order_token) if order_token else None
        if _order_usable(order, payment_id):
            _bind(payment_id, int(order["user_id"]), order["token"])
        elif not claim_only:
            known = account_for(tg_id)
            if known is not None:
                _bind(payment_id, known)
        row = _row(payment_id) or row
        owner = row.get("user_id")
    if owner is None:
        if row["status"] == "granted":
            # Delivered earlier to an account that has been deleted since: nothing left to hand out.
            return {"status": "already", "plan": row["plan"], "account": "", "pro": None}
        return {"status": "claim", "plan": row["plan"], "claim_url": claim_url(str(row["claim_token"]))}
    return _finish(row, int(owner))


def claim(token: str, user_id: int) -> dict:
    """The claim page: bind a waiting sale to the signed-in account. Status: granted, already, taken, refunded, unknown."""
    if not valid_token(token):
        return {"status": "unknown"}
    row = _row(claim_token=token)
    if not row:
        return {"status": "unknown"}
    if row["status"] in ("revoked", "refunded"):
        return {"status": "refunded", "plan": row["plan"]}
    payment_id = str(row["payment_id"])
    if not _bind(payment_id, int(user_id)):
        return {"status": "taken", "plan": row["plan"]}
    result = _finish(_row(payment_id) or row, int(user_id))
    if result["status"] == "granted":
        _tell_owner(f"🔗 Покупка Pro из Telegram привязана: {row['plan']} → аккаунт #{int(user_id)}")
    return result if result["status"] != "revoked" else {"status": "refunded", "plan": row["plan"]}


def revoke(payment_id: str) -> dict:
    """A refund made in the bot: take the days back. Status: revoked, refunded (never granted), already, unknown."""
    payment_id = str(payment_id or "")
    row = _row(payment_id) if _PAYMENT_ID.match(payment_id) else None
    if not row:
        return {"status": "unknown"}
    if row["status"] == "granted" and _transition(payment_id, "granted", "revoked", revoked_at=time.time()):
        if row.get("user_id") is not None:
            _revoke(int(row["user_id"]), payment_id, row["days"])
        return {"status": "revoked", "plan": row["plan"]}
    if row["status"] == "pending" and _transition(payment_id, "pending", "refunded", revoked_at=time.time()):
        return {"status": "refunded", "plan": row["plan"]}
    return {"status": "already", "plan": row["plan"]}


def purchases_for(user_id: int, limit: int = 30) -> list[dict]:
    c = auth_db._conn()
    try:
        rows = c.execute(
            "SELECT plan, days, status, method, amount, currency, created_at, granted_at, revoked_at FROM telegram_sales "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (int(user_id), int(limit))).fetchall()
        return [dict(row) for row in rows]
    finally:
        c.close()


def price_label(amount, currency) -> str:
    """'300 ⭐', '3.99 USDT', '$3.99' for the account page."""
    amount, currency = str(amount or "").strip(), str(currency or "").strip().upper()
    if not amount:
        return ""
    if currency == "XTR":
        return f"{amount} ⭐"
    if currency == "USD":
        return f"${amount}"
    return f"{amount} {currency}".strip()


# ---------------------------------------------------------------- side effects
def _tell_owner(text: str) -> None:
    try:
        from smweb import admin_notify
        admin_notify.send(text)
    except Exception:
        LOG.debug("owner notification failed", exc_info=True)


def _bell(user_id: int, plan: str) -> None:
    try:
        from smweb import notify
        state = gumroad_billing.pro_state(user_id)
        notify.add(user_id, "pro_purchased", title="Pro", link="/?activate=1",
                   meta={"plan": plan, "until": state.get("until"), "lifetime": state.get("lifetime")})
    except Exception:
        LOG.debug("bell notification failed", exc_info=True)
