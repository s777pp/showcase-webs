"""Pro purchases through Gumroad (2026-10-06).

Five Gumroad products (custom permalinks ``sm-pro-1d``, ``-7d``, ``-30d``, ``-90d``, ``-unlimited``) sell Pro.
How a purchase reaches an account:

* A signed-in user presses a plan on the site: ``create_order`` stores a random order token and the browser
  opens the product with ``?sm_order=<token>``.  Gumroad copies URL parameters into the Ping
  (``url_params``), so the Ping names the order, and the order names the account.
* Anyone else (bought straight on Gumroad, lost Ping) opens the button in the purchase content:
  ``/billing/gumroad/claim?sale_id=...`` binds the sale to the signed-in account once.

The Ping is unsigned and delivered at least once, so it is only a trigger: every sale is read back through
the Gumroad API (``GUMROAD_ACCESS_TOKEN``) before Pro is granted or taken back.  Each sale grants once
(an atomic ``pending -> granted`` transition); a refund, chargeback or lost dispute takes the days back.
Pro time is added in one SQL statement on top of what is left, so two purchases never overwrite each other.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import auth_db

LOG = logging.getLogger("sm.gumroad")

API = "https://api.gumroad.com/v2"
# plan id -> (custom permalink, days; None = lifetime)
PLANS: dict[str, tuple[str, int | None]] = {
    "1d": ("sm-pro-1d", 1),
    "7d": ("sm-pro-7d", 7),
    "30d": ("sm-pro-30d", 30),
    "90d": ("sm-pro-90d", 90),
    "unlimited": ("sm-pro-unlimited", None),
}
# Shown until the Gumroad product list can be read (then Gumroad's own prices win).
DEFAULT_PRICES = {"1d": "$0.99", "7d": "$1.99", "30d": "$3.99", "90d": "$4.99", "unlimited": "$5.99"}
ORDER_PARAM = "sm_order"
ORDER_TTL = 30 * 86400
RECHECK_DAYS = 60          # granted sales are re-read for refunds this long
RECHECK_EVERY = 6 * 3600   # ... at most this often per sale
PRODUCTS_TTL = 600

_SALE_ID = re.compile(r"^[A-Za-z0-9_=\-]{6,80}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_\-]{16,64}$")

_products_lock = threading.Lock()
_products_cache: dict = {"at": 0.0, "data": None}
_last_reconcile = 0.0
_reconcile_lock = threading.Lock()


class Unavailable(Exception):
    """Gumroad API not configured or not reachable: try again later."""


def access_token() -> str:
    return (os.environ.get("GUMROAD_ACCESS_TOKEN") or "").strip()


def configured() -> bool:
    return bool(access_token())


def store_url() -> str:
    return (os.environ.get("GUMROAD_STORE_URL") or "https://serhiiperepelytsia.gumroad.com").strip().rstrip("/")


def marker(sale_id: str) -> str:
    """pro_code for a lifetime purchase: a hash, never the Gumroad id itself."""
    return "GRS-" + hashlib.sha256(sale_id.encode("utf-8")).hexdigest()[:40].upper()


def valid_sale_id(value: str) -> bool:
    return bool(_SALE_ID.match(value or ""))


# ---------------------------------------------------------------- Gumroad API
def _api_get(path: str, timeout: float = 8) -> dict:
    token = access_token()
    if not token:
        raise Unavailable("not configured")
    request = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "ShowcaseMaker/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"success": False, "not_found": True}
        LOG.warning("gumroad api %s: HTTP %s", path.split("?")[0].rsplit("/", 1)[0], exc.code)
        raise Unavailable(f"http {exc.code}") from None
    except Exception as exc:
        LOG.warning("gumroad api unreachable: %s", type(exc).__name__)
        raise Unavailable(type(exc).__name__) from None
    try:
        return json.loads(raw)
    except ValueError:
        raise Unavailable("bad json") from None


def fetch_sale(sale_id: str) -> dict | None:
    """The sale as Gumroad reports it, or None when it is not one of ours."""
    data = _api_get("/sales/" + urllib.parse.quote(sale_id, safe=""))
    if not data.get("success"):
        return None
    sale = data.get("sale")
    return sale if isinstance(sale, dict) else None


def products(force: bool = False) -> dict:
    """{plan: {product_id, permalinks, price, published, url}} from the seller's product list (cached)."""
    with _products_lock:
        cached = _products_cache["data"]
        if cached is not None and not force and time.time() - _products_cache["at"] < PRODUCTS_TTL:
            return cached
    data = _api_get("/products")
    by_permalink = {permalink: plan for plan, (permalink, _days) in PLANS.items()}
    result: dict = {}
    for item in data.get("products") or []:
        if not isinstance(item, dict) or item.get("deleted"):
            continue
        short = str(item.get("short_url") or "")
        names = {str(item.get("custom_permalink") or ""), short.rstrip("/").rsplit("/", 1)[-1]}
        plan = next((by_permalink[name] for name in names if name in by_permalink), None)
        if not plan:
            continue
        result[plan] = {
            "product_id": str(item.get("id") or ""),
            "permalinks": sorted(name for name in names if name),
            "price": price_label(item.get("price"), item.get("currency"), item.get("formatted_price")),
            "price_cents": item.get("price"),
            "currency": str(item.get("currency") or ""),
            "published": bool(item.get("published")),
            "url": short if short.startswith("https://") else f"{store_url()}/l/{PLANS[plan][0]}",
        }
    with _products_lock:
        _products_cache.update(at=time.time(), data=result)
    return result


_SYMBOLS = {"usd": "$", "eur": "€", "gbp": "£"}


def price_label(cents, currency, formatted="") -> str:
    """'$0.99' from cents; Gumroad's own formatted_price says '99¢', which reads oddly next to '$5.99'."""
    symbol = _SYMBOLS.get(str(currency or "usd").lower())
    try:
        value = int(cents)
    except (TypeError, ValueError):
        value = None
    if symbol and value is not None and value >= 0:
        return f"{symbol}{value / 100:.2f}"
    return str(formatted or "")


def plan_for_sale(sale: dict) -> str | None:
    product_id = str(sale.get("product_id") or "")
    permalink = str(sale.get("product_permalink") or "")
    by_permalink = {permalink_: plan for plan, (permalink_, _days) in PLANS.items()}
    if permalink in by_permalink:
        return by_permalink[permalink]
    try:
        known = products()
    except Unavailable:
        known = {}
    for plan, info in known.items():
        if product_id and info.get("product_id") == product_id:
            return plan
        if permalink and permalink in info.get("permalinks", []):
            return plan
    return None


def _flag(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def sale_revoked(sale: dict) -> bool:
    if _flag(sale.get("refunded")) or _flag(sale.get("chargedback")) or _flag(sale.get("access_revoked")):
        return True
    return _flag(sale.get("disputed")) and not _flag(sale.get("dispute_won"))


def _timestamp(value) -> float | None:
    if not value:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# ---------------------------------------------------------------- orders
def create_order(user_id: int, plan: str) -> dict:
    if plan not in PLANS:
        raise ValueError("plan")
    token = secrets.token_urlsafe(18)
    c = auth_db._conn()
    try:
        c.execute("INSERT INTO gumroad_orders (token, user_id, plan, created_at) VALUES (?,?,?,?)",
                  (token, int(user_id), plan, time.time()))
        c.commit()
    finally:
        c.close()
    try:
        url = products().get(plan, {}).get("url") or ""
    except Unavailable:
        url = ""
    url = url or f"{store_url()}/l/{PLANS[plan][0]}"
    return {"token": token, "url": f"{url}?wanted=true&{ORDER_PARAM}={token}"}


def _order(token: str) -> dict | None:
    if not _TOKEN.match(token or ""):
        return None
    c = auth_db._conn()
    try:
        row = c.execute("SELECT token, user_id, plan, created_at, sale_id FROM gumroad_orders WHERE token=?",
                        (token,)).fetchone()
        return dict(row) if row else None
    finally:
        c.close()


def order_from_ping(form: dict) -> str:
    """The order token from a Ping, whatever way Gumroad encoded the url_params dictionary."""
    for key in (f"url_params[{ORDER_PARAM}]", ORDER_PARAM):
        value = str(form.get(key) or "").strip()
        if value:
            return value
    raw = form.get("url_params")
    if isinstance(raw, dict):
        return str(raw.get(ORDER_PARAM) or "").strip()
    if isinstance(raw, str) and ORDER_PARAM in raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return str(parsed.get(ORDER_PARAM) or "").strip()
        except ValueError:
            pass
        found = re.search(re.escape(ORDER_PARAM) + r"""['"]?\s*(?:=>|[:=])\s*['"]?([A-Za-z0-9_\-]{16,64})""", raw)
        if found:
            return found.group(1)
    return ""


# ---------------------------------------------------------------- Pro time
def _grant(user_id: int, sale_id: str, days: int | None) -> None:
    now = time.time()
    c = auth_db._conn()
    try:
        if days is None:
            c.execute("UPDATE users SET is_pro=1, pro_until=NULL, pro_code=? WHERE id=?", (marker(sale_id), int(user_id)))
        else:
            # Extend what is left (or start now); permanent Pro is left alone.
            # pro_code marks the purchase, so the site no longer calls this Pro a "trial".
            c.execute(
                "UPDATE users SET is_pro=1, pro_code=?, pro_until=(CASE WHEN is_pro=1 AND pro_until IS NOT NULL "
                "AND pro_until>? THEN pro_until ELSE ? END)+? WHERE id=? AND NOT (is_pro=1 AND pro_until IS NULL)",
                (marker(sale_id), now, now, float(days) * 86400, int(user_id)),
            )
        c.commit()
    finally:
        c.close()


def _revoke(user_id: int, sale_id: str, days: int | None) -> None:
    now = time.time()
    c = auth_db._conn()
    try:
        if days is None:
            c.execute("UPDATE users SET is_pro=0, pro_until=NULL WHERE id=? AND pro_until IS NULL AND pro_code=?",
                      (int(user_id), marker(sale_id)))
        else:
            c.execute("UPDATE users SET pro_until=pro_until-? WHERE id=? AND is_pro=1 AND pro_until IS NOT NULL",
                      (float(days) * 86400, int(user_id)))
            c.execute("UPDATE users SET is_pro=0, pro_until=NULL WHERE id=? AND pro_until IS NOT NULL AND pro_until<=?",
                      (int(user_id), now))
        c.commit()
    finally:
        c.close()


def pro_state(user_id: int) -> dict:
    c = auth_db._conn()
    try:
        row = c.execute("SELECT is_pro, pro_until FROM users WHERE id=?", (int(user_id),)).fetchone()
    finally:
        c.close()
    if not row or not row["is_pro"]:
        return {"pro": False, "until": None, "lifetime": False}
    until = row["pro_until"]
    if until is not None and float(until) <= time.time():
        return {"pro": False, "until": None, "lifetime": False}
    return {"pro": True, "until": float(until) if until is not None else None, "lifetime": until is None}


# ---------------------------------------------------------------- sales
def _row(c, sale_id: str) -> dict | None:
    row = c.execute("SELECT * FROM gumroad_sales WHERE sale_id=?", (sale_id,)).fetchone()
    return dict(row) if row else None


def _transition(sale_id: str, old: str, new: str, **fields) -> bool:
    """Atomic state change; True only for the one caller that made it."""
    sets = ", ".join(["status=?", "updated_at=?"] + [f"{key}=?" for key in fields])
    c = auth_db._conn()
    try:
        cursor = c.execute(f"UPDATE gumroad_sales SET {sets} WHERE sale_id=? AND status=?",
                           (new, time.time(), *fields.values(), sale_id, old))
        c.commit()
        return cursor.rowcount == 1
    finally:
        c.close()


def _store(sale_id: str, sale: dict, plan: str, source: str, is_test: bool) -> dict:
    now = time.time()
    c = auth_db._conn()
    try:
        try:
            c.execute(
                "INSERT INTO gumroad_sales (sale_id, plan, days, status, price_cents, currency, source, is_test, "
                "sale_created, checked_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (sale_id, plan, PLANS[plan][1], "pending", _cents(sale), str(sale.get("currency") or "")[:8],
                 source, 1 if is_test else 0, _timestamp(sale.get("created_at")), now, now),
            )
            c.commit()
        except sqlite3.IntegrityError:
            c.rollback()
            c.execute("UPDATE gumroad_sales SET checked_at=? WHERE sale_id=?", (now, sale_id))
            c.commit()
        return _row(c, sale_id) or {}
    finally:
        c.close()


def _cents(sale: dict) -> int | None:
    for key in ("price_cents", "price"):
        try:
            return int(sale.get(key))
        except (TypeError, ValueError):
            continue
    return None


def _bind(sale_id: str, user_id: int, order_token: str = "") -> bool:
    """Attach a sale to an account once. True when it belongs to user_id afterwards."""
    c = auth_db._conn()
    try:
        c.execute("UPDATE gumroad_sales SET user_id=?, order_token=?, updated_at=? WHERE sale_id=? AND user_id IS NULL",
                  (int(user_id), order_token or None, time.time(), sale_id))
        if order_token:
            c.execute("UPDATE gumroad_orders SET sale_id=? WHERE token=? AND sale_id IS NULL", (sale_id, order_token))
        c.commit()
        row = c.execute("SELECT user_id FROM gumroad_sales WHERE sale_id=?", (sale_id,)).fetchone()
        return bool(row) and row["user_id"] is not None and int(row["user_id"]) == int(user_id)
    finally:
        c.close()


def sync_sale(sale_id: str, *, order_token: str = "", claim_user: int | None = None,
              source: str = "ping", is_test: bool = False) -> dict:
    """Read one sale back from Gumroad and bring our records and the account's Pro in line with it.

    Returns {"status": ...}: granted, already, pending (nobody to give it to yet), revoked, refunded,
    taken (another account owns it), unknown (not a sale of ours) or other_product.
    """
    if not valid_sale_id(sale_id):
        return {"status": "unknown"}
    sale = fetch_sale(sale_id)
    if not sale:
        return {"status": "unknown"}
    plan = plan_for_sale(sale)
    if not plan:
        return {"status": "other_product"}
    row = _store(sale_id, sale, plan, source, is_test)
    days = PLANS[plan][1]

    if sale_revoked(sale):
        if row.get("status") == "granted" and _transition(sale_id, "granted", "revoked", revoked_at=time.time()):
            if row.get("user_id") is not None:
                _revoke(int(row["user_id"]), sale_id, days)
            _tell_owner("refund", sale_id, plan, row.get("user_id"), sale)
            return {"status": "revoked", "plan": plan}
        if row.get("status") == "pending":
            _transition(sale_id, "pending", "refunded", revoked_at=time.time())
        return {"status": "refunded", "plan": plan}

    owner = row.get("user_id")
    if owner is None:
        order = _order(order_token) if order_token else None
        sale_at = _timestamp(sale.get("created_at")) or time.time()
        if order and order["plan"] == plan and order["sale_id"] in (None, sale_id) \
                and order["created_at"] <= sale_at + 300 and time.time() - order["created_at"] < ORDER_TTL:
            owner = int(order["user_id"]) if _bind(sale_id, int(order["user_id"]), order["token"]) else None
        elif claim_user is not None:
            owner = int(claim_user) if _bind(sale_id, int(claim_user)) else None
        if owner is None:
            fresh = auth_db._conn()
            try:
                owner = (_row(fresh, sale_id) or {}).get("user_id")
            finally:
                fresh.close()
    if owner is None:
        return {"status": "pending", "plan": plan}
    if claim_user is not None and int(owner) != int(claim_user):
        return {"status": "taken", "plan": plan}
    if _transition(sale_id, "pending", "granted", granted_at=time.time()):
        _grant(int(owner), sale_id, days)
        _tell_owner("sale", sale_id, plan, owner, sale)
        _bell(int(owner), plan)
        try:
            from smweb import analytics
            analytics.record("pro_activated", user_id=int(owner), properties={"method": "gumroad"},
                             event_key=f"pro:gumroad-sale:{marker(sale_id)}")
        except Exception:
            LOG.debug("analytics failed", exc_info=True)
        return {"status": "granted", "plan": plan, "user_id": int(owner)}
    current = auth_db._conn()
    try:
        status = (_row(current, sale_id) or {}).get("status")
    finally:
        current.close()
    return {"status": "already" if status == "granted" else str(status or "pending"), "plan": plan}


# ---------------------------------------------------------------- side effects
def _tell_owner(kind: str, sale_id: str, plan: str, user_id, sale: dict) -> None:
    try:
        from smweb import admin_notify
        import html
        price = str(sale.get("formatted_total_price") or sale.get("formatted_display_price") or "")
        title = "💳 Покупка Pro" if kind == "sale" else "↩️ Возврат Pro"
        who = f"аккаунт #{int(user_id)}" if user_id is not None else "ещё не привязана к аккаунту"
        admin_notify.send(f"<b>{title}</b>: {html.escape(plan)} {html.escape(price)}\n{who}")
    except Exception:
        LOG.debug("owner notification failed", exc_info=True)


def _bell(user_id: int, plan: str) -> None:
    try:
        from smweb import notify
        state = pro_state(user_id)
        notify.add(user_id, "pro_purchased", title="Pro", link="/?activate=1",
                   meta={"plan": plan, "until": state.get("until"), "lifetime": state.get("lifetime")})
    except Exception:
        LOG.debug("bell notification failed", exc_info=True)


# ---------------------------------------------------------------- periodic check
def reconcile(limit: int = 40) -> int:
    """Re-read recent granted sales so refunds and chargebacks are caught even if their Ping was lost."""
    if not configured():
        return 0
    now = time.time()
    c = auth_db._conn()
    try:
        rows = c.execute(
            "SELECT sale_id FROM gumroad_sales WHERE status='granted' AND (sale_created IS NULL OR sale_created>?) "
            "AND (checked_at IS NULL OR checked_at<?) ORDER BY checked_at LIMIT ?",
            (now - RECHECK_DAYS * 86400, now - RECHECK_EVERY, int(limit)),
        ).fetchall()
        c.execute("DELETE FROM gumroad_orders WHERE created_at<? AND sale_id IS NULL", (now - ORDER_TTL,))
        c.commit()
    finally:
        c.close()
    checked = 0
    for row in rows:
        try:
            sync_sale(str(row["sale_id"]), source="recheck")
            checked += 1
        except Unavailable:
            break
        except Exception:
            LOG.warning("gumroad recheck failed", exc_info=True)
    return checked


def maybe_reconcile(interval: float = 3600) -> None:
    global _last_reconcile
    now = time.time()
    if now - _last_reconcile < interval or not _reconcile_lock.acquire(blocking=False):
        return
    try:
        _last_reconcile = now
        reconcile()
    finally:
        _reconcile_lock.release()


def recent_sales(limit: int = 100) -> list[dict]:
    c = auth_db._conn()
    try:
        rows = c.execute(
            "SELECT sale_id, user_id, plan, days, status, price_cents, currency, source, is_test, sale_created, "
            "granted_at, revoked_at FROM gumroad_sales ORDER BY updated_at DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(row) for row in rows]
    finally:
        c.close()
