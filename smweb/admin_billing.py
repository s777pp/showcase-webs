"""Purchases for the control centre (2026-10-09): Gumroad and Telegram-bot sales in one list.

Until now every sale and refund reached the owner only as a bot message. This module reads the two sales tables
(``gumroad_sales``, ``telegram_sales``) and offers the three things the owner actually needs to do by hand:

* attach a sale nobody received yet (``pending``: bought without an order and never claimed) to an account,
  through the same code paths as the buyer's own claim (``telegram_billing.claim`` / ``gumroad_billing.sync_sale``),
  so Pro time, bell, analytics and the owner bot behave exactly as for a normal purchase;
* re-read a Gumroad sale from Gumroad (refund check) - nothing is ever trusted from our own table alone;
* take back a Telegram sale refunded outside the site (``telegram_billing.revoke``, same as the bot's /refund).

Claim links of pending Telegram sales are shown to the owner only (they hand out Pro once; the buyer needs one).
"""
from __future__ import annotations

import time

import auth_db
from smweb import gumroad_billing, telegram_billing

STATUSES = ("pending", "granted", "revoked", "refunded")
PLAN_LABELS = {"1d": "Pro 1 день", "7d": "Pro 7 дней", "30d": "Pro 30 дней", "90d": "Pro 90 дней", "unlimited": "Pro навсегда"}
METHOD_LABELS = {"stars": "Telegram Stars", "crypto": "CryptoBot", "paypal": "PayPal", "card_uah": "Карта (UAH)",
                 "manual": "Вручную"}


def _users(ids: set[int]) -> dict[int, dict]:
    if not ids:
        return {}
    c = auth_db._conn()
    try:
        marks = ",".join("?" * len(ids))
        rows = c.execute(f"SELECT id, email, display_name, profile_username FROM users WHERE id IN ({marks})",
                         list(ids)).fetchall()
    finally:
        c.close()
    return {int(row["id"]): dict(row) for row in rows}


def _who(user_id, users: dict[int, dict]) -> dict | None:
    if user_id is None:
        return None
    row = users.get(int(user_id)) or {}
    name = row.get("display_name") or row.get("profile_username") or row.get("email") or f"ID {int(user_id)}"
    return {"id": int(user_id), "name": name, "email": row.get("email") or "", "deleted": not row}


def _gumroad_rows(since: float) -> list[dict]:
    c = auth_db._conn()
    try:
        rows = c.execute(
            "SELECT sale_id, user_id, plan, days, status, price_cents, currency, source, is_test, sale_created, "
            "granted_at, revoked_at, updated_at FROM gumroad_sales WHERE COALESCE(sale_created, updated_at)>=? "
            "ORDER BY COALESCE(sale_created, updated_at) DESC LIMIT 500", (since,)).fetchall()
    finally:
        c.close()
    items = []
    for row in rows:
        row = dict(row)
        items.append({
            "source": "gumroad", "id": row["sale_id"], "plan": row["plan"], "plan_label": PLAN_LABELS.get(row["plan"], row["plan"]),
            "status": row["status"], "user_id": row["user_id"],
            "price": gumroad_billing.price_label(row["price_cents"], row["currency"]),
            "amount": (int(row["price_cents"]) / 100) if row["price_cents"] is not None else None,
            "currency": str(row["currency"] or "usd").upper(),
            "method": "Gumroad" + (" · тест" if row["is_test"] else ""), "test": bool(row["is_test"]),
            "created_at": row["sale_created"] or row["updated_at"], "granted_at": row["granted_at"],
            "revoked_at": row["revoked_at"], "buyer": "", "claim_url": "",
        })
    return items


def _telegram_rows(since: float) -> list[dict]:
    c = auth_db._conn()
    try:
        rows = c.execute(
            "SELECT payment_id, tg_id, tg_username, user_id, plan, days, status, method, amount, currency, claim_token, "
            "created_at, granted_at, revoked_at FROM telegram_sales WHERE created_at>=? ORDER BY created_at DESC LIMIT 500",
            (since,)).fetchall()
    finally:
        c.close()
    items = []
    for row in rows:
        row = dict(row)
        try:
            amount = float(str(row["amount"] or "").replace(",", "."))
        except ValueError:
            amount = None
        buyer = f"@{row['tg_username']}" if row["tg_username"] else f"Telegram {row['tg_id']}"
        items.append({
            "source": "telegram", "id": row["payment_id"], "plan": row["plan"], "plan_label": PLAN_LABELS.get(row["plan"], row["plan"]),
            "status": row["status"], "user_id": row["user_id"],
            "price": telegram_billing.price_label(row["amount"], row["currency"]), "amount": amount,
            "currency": "⭐" if str(row["currency"] or "").upper() == "XTR" else str(row["currency"] or "").upper(),
            "method": METHOD_LABELS.get(row["method"], row["method"] or "—"), "test": False,
            "created_at": row["created_at"], "granted_at": row["granted_at"], "revoked_at": row["revoked_at"],
            "buyer": buyer, "tg_id": row["tg_id"],
            "claim_url": telegram_billing.claim_url(row["claim_token"]) if row["status"] == "pending" and row["claim_token"] else "",
        })
    return items


def purchases(days: int = 30, source: str = "", status: str = "", query: str = "") -> dict:
    """Sales of the period, newest first, plus money received per currency and what waits for the owner."""
    days = max(1, min(3650, int(days or 30)))
    since = time.time() - days * 86400
    items = []
    if source in ("", "gumroad"):
        items += _gumroad_rows(since)
    if source in ("", "telegram"):
        items += _telegram_rows(since)
    users = _users({int(item["user_id"]) for item in items if item["user_id"] is not None})
    for item in items:
        item["user"] = _who(item["user_id"], users)
    items.sort(key=lambda item: float(item["created_at"] or 0), reverse=True)

    # Money received = paid and not taken back; test purchases never count.
    revenue: dict[str, float] = {}
    counts = {key: 0 for key in STATUSES}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
        if item["status"] in ("granted", "pending") and not item["test"] and item["amount"] is not None:
            revenue[item["currency"]] = round(revenue.get(item["currency"], 0) + item["amount"], 2)
    by_plan: dict[str, int] = {}
    for item in items:
        if item["status"] == "granted" and not item["test"]:
            by_plan[item["plan_label"]] = by_plan.get(item["plan_label"], 0) + 1

    if status in STATUSES:
        items = [item for item in items if item["status"] == status]
    query = str(query or "").strip().lower()
    if query:
        items = [item for item in items if query in item["id"].lower() or query in item["buyer"].lower()
                 or query in str(item.get("tg_id") or "") or (item["user"] and (query in item["user"]["name"].lower()
                 or query in item["user"]["email"].lower() or query == str(item["user"]["id"])))]
    return {"ok": True, "days": days, "items": items[:300], "counts": counts, "revenue": revenue, "by_plan": by_plan,
            "pending_total": pending_count(), "gumroad": gumroad_billing.configured(),
            "telegram": telegram_billing.configured()}


def pending_count() -> int:
    """Paid sales that still wait for an account (all time)."""
    c = auth_db._conn()
    try:
        g = dict(c.execute("SELECT COUNT(*) AS n FROM gumroad_sales WHERE status='pending' AND is_test=0").fetchone())["n"]
        t = dict(c.execute("SELECT COUNT(*) AS n FROM telegram_sales WHERE status='pending'").fetchone())["n"]
    finally:
        c.close()
    return int(g or 0) + int(t or 0)


def summary(days: int = 30) -> dict:
    """Small block for the overview: sales, money and pending sales of the period."""
    data = purchases(days)
    return {"sales": data["counts"].get("granted", 0) + data["counts"].get("pending", 0),
            "revenue": data["revenue"], "pending": data["pending_total"], "refunds": data["counts"].get("revoked", 0)}


def _resolve_user(value) -> int:
    from smweb import admin_messages
    found, _missing = admin_messages.resolve_targets([str(value or "").strip()])
    if not found:
        raise LookupError("Аккаунт не найден: впиши ID, e-mail или ник")
    return found[0]


def attach(source: str, sale_id: str, user_ref) -> dict:
    """Give a waiting sale to an account. Returns the billing module's own result."""
    user_id = _resolve_user(user_ref)
    if source == "telegram":
        c = auth_db._conn()
        try:
            row = c.execute("SELECT claim_token, status FROM telegram_sales WHERE payment_id=?", (str(sale_id),)).fetchone()
        finally:
            c.close()
        if not row:
            raise LookupError("Покупка не найдена")
        if row["status"] != "pending":
            raise ValueError("Эта покупка уже привязана или возвращена")
        result = telegram_billing.claim(str(row["claim_token"]), user_id)
    elif source == "gumroad":
        if not gumroad_billing.valid_sale_id(str(sale_id)):
            raise LookupError("Покупка не найдена")
        try:
            result = gumroad_billing.sync_sale(str(sale_id), claim_user=user_id, source="admin")
        except gumroad_billing.Unavailable as exc:
            raise ValueError("Gumroad сейчас не отвечает, попробуй позже") from exc
    else:
        raise ValueError("source")
    result = {key: value for key, value in result.items() if key in ("status", "plan", "user_id", "account")}
    result["user_id"] = user_id
    return result


def recheck(sale_id: str) -> dict:
    if not gumroad_billing.valid_sale_id(str(sale_id)):
        raise LookupError("Покупка не найдена")
    try:
        result = gumroad_billing.sync_sale(str(sale_id), source="admin")
    except gumroad_billing.Unavailable as exc:
        raise ValueError("Gumroad сейчас не отвечает, попробуй позже") from exc
    return {"status": result.get("status"), "plan": result.get("plan")}


def refund_telegram(payment_id: str) -> dict:
    result = telegram_billing.revoke(str(payment_id))
    if result.get("status") == "unknown":
        raise LookupError("Покупка не найдена")
    return result


def for_user(user_id: int) -> dict:
    """User card: purchases of both kinds and the Telegram accounts that pay into this account."""
    uid = int(user_id)
    c = auth_db._conn()
    try:
        gumroad = [dict(row) for row in c.execute(
            "SELECT sale_id, plan, status, price_cents, currency, is_test, sale_created, updated_at FROM gumroad_sales "
            "WHERE user_id=? ORDER BY COALESCE(sale_created, updated_at) DESC LIMIT 30", (uid,)).fetchall()]
        telegram = [dict(row) for row in c.execute(
            "SELECT payment_id, plan, status, method, amount, currency, created_at FROM telegram_sales "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (uid,)).fetchall()]
        links = [dict(row) for row in c.execute(
            "SELECT tg_id, updated_at FROM telegram_links WHERE user_id=? ORDER BY updated_at DESC", (uid,)).fetchall()]
        login = c.execute("SELECT telegram_id, pro_code FROM users WHERE id=?", (uid,)).fetchone()
    finally:
        c.close()
    items = [{"source": "gumroad", "id": row["sale_id"], "plan_label": PLAN_LABELS.get(row["plan"], row["plan"]),
              "status": row["status"], "price": gumroad_billing.price_label(row["price_cents"], row["currency"]),
              "method": "Gumroad" + (" · тест" if row["is_test"] else ""),
              "created_at": row["sale_created"] or row["updated_at"]} for row in gumroad]
    items += [{"source": "telegram", "id": row["payment_id"], "plan_label": PLAN_LABELS.get(row["plan"], row["plan"]),
               "status": row["status"], "price": telegram_billing.price_label(row["amount"], row["currency"]),
               "method": METHOD_LABELS.get(row["method"], row["method"] or "—"), "created_at": row["created_at"]}
              for row in telegram]
    items.sort(key=lambda item: float(item["created_at"] or 0), reverse=True)
    pro_code = str((login["pro_code"] if login else "") or "")
    origin = ("Покупка Gumroad" if pro_code.startswith("GRS-") else "Покупка в Telegram-боте" if pro_code.startswith("TGS-")
              else "Выдано вручную" if pro_code == "ADMIN-GRANT" else "Пробный ключ" if pro_code.startswith("SM-TRIAL")
              else "Ключ активации" if pro_code else "")
    return {"items": items, "telegram_links": links,
            "telegram_login": bool(login and login["telegram_id"]), "pro_origin": origin}
