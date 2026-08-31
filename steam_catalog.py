#!/usr/bin/env python3
"""Steam catalog helpers: profile backgrounds, achievements and app search.

Everything here talks to public Steam endpoints — no Web API key required —
and caches aggressively, because the Community market rate-limits hard and a
catalog page must not turn into 24 upstream requests per keystroke.

Cached rows live in DATA/steam_cache.json so a restart keeps the catalog warm.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from html import unescape
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import requests
import xml.etree.ElementTree as ET

LOGGER = logging.getLogger("sm.steam")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)
TIMEOUT = 12

# Market search is the only public listing of profile backgrounds.
MARKET_SEARCH = "https://steamcommunity.com/market/search/render/"
ACH_PAGE = "https://steamcommunity.com/stats/{appid}/achievements/"
# GetAppList needs a Web API key (404 without one); the community search
# endpoint is public, already ranked, and returns icons.
APP_SEARCH = "https://steamcommunity.com/actions/SearchApps/{q}"

# Per-entry TTLs. Backgrounds change rarely; achievements essentially never.
TTL_BG = 6 * 3600
TTL_ACH = 24 * 3600
TTL_APPS = 24 * 3600
TTL_PROFILE = 15 * 60

_LOCK = threading.Lock()
_MEM: dict[str, tuple[float, Any]] = {}
_CACHE_PATH: Optional[Path] = None


def configure(data_dir: Path) -> None:
    """Point the on-disk cache at DATA_DIR and load whatever is already there."""
    global _CACHE_PATH
    _CACHE_PATH = Path(data_dir) / "steam_cache.json"
    try:
        if _CACHE_PATH.is_file():
            raw = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            now = time.time()
            with _LOCK:
                for k, v in raw.items():
                    # Stored as [expires_at, payload]; drop anything already stale.
                    if isinstance(v, list) and len(v) == 2 and float(v[0]) > now:
                        _MEM[k] = (float(v[0]), v[1])
            LOGGER.info("steam cache loaded: %d entries", len(_MEM))
    except Exception as e:
        LOGGER.warning("steam cache load failed: %s", e)


def _flush() -> None:
    if not _CACHE_PATH:
        return
    try:
        with _LOCK:
            snapshot = {k: [exp, val] for k, (exp, val) in _MEM.items()}
        tmp = _CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot), encoding="utf-8")
        tmp.replace(_CACHE_PATH)
    except Exception as e:
        LOGGER.warning("steam cache flush failed: %s", e)


def _get(key: str):
    with _LOCK:
        hit = _MEM.get(key)
    if not hit:
        return None
    exp, val = hit
    if exp < time.time():
        with _LOCK:
            _MEM.pop(key, None)
        return None
    return val


def _put(key: str, val, ttl: int) -> None:
    with _LOCK:
        _MEM[key] = (time.time() + ttl, val)
        # Keep the file bounded — drop the oldest entries past a sane ceiling.
        if len(_MEM) > 4000:
            for k, _ in sorted(_MEM.items(), key=lambda kv: kv[1][0])[:800]:
                _MEM.pop(k, None)
    _flush()


def _fetch(url: str, params: dict | None = None) -> Optional[requests.Response]:
    try:
        r = requests.get(
            url,
            params=params,
            timeout=TIMEOUT,
            headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
        )
        if r.status_code == 429:
            LOGGER.warning("steam rate limited: %s", url)
            return None
        if r.status_code != 200:
            LOGGER.warning("steam %s → HTTP %s", url, r.status_code)
            return None
        return r
    except Exception as e:
        LOGGER.warning("steam fetch failed %s: %s", url, e)
        return None


# --------------------------------------------------------------------------
# Profile backgrounds
# --------------------------------------------------------------------------
def _icon_url(icon: str, size: str = "360fx360f") -> str:
    if not icon:
        return ""
    return f"https://community.cloudflare.steamstatic.com/economy/image/{icon}/{size}"


def backgrounds(q: str = "", page: int = 0, kind: str = "all", count: int = 24, asset: str = "background") -> dict:
    """Search Steam Market for profile backgrounds.

    `kind` filters static vs animated. Animated backgrounds are a distinct
    market item type, so the query differs rather than post-filtering a page
    that may contain none of them.
    """
    page = max(0, int(page))
    count = max(1, min(50, int(count)))
    kind = (kind or "all").lower()
    asset = (asset or "background").lower()
    if asset not in ("background", "avatar", "frame"):
        asset = "background"
    q = (q or "").strip()

    key = f"asset2:{asset}:{kind}:{q.lower()}:{page}:{count}"
    cached = _get(key)
    if cached is not None:
        return cached

    if asset == "avatar":
        item_class = "tag_item_class_11"
    elif asset == "frame":
        item_class = "tag_item_class_14"
    else:
        item_class = "tag_item_class_3"

    if kind == "animated" and asset == "background":
        tag = "Animated Profile Background"
    elif kind == "static":
        tag = "Profile Background"
    else:
        tag = ""

    params = {
        "query": q,
        "start": page * count,
        "count": count,
        "search_descriptions": 0,
        "sort_column": "popular",
        "sort_dir": "desc",
        "appid": 753,
        "norender": 1,
        "category_753_item_class[]": item_class,
    }
    if tag:
        params["category_753_Type[]"] = f"tag_{tag.replace(' ', '_')}"

    r = _fetch(MARKET_SEARCH, params)
    if r is None:
        return {"ok": False, "items": [], "total": 0, "msg": "Steam is unavailable, try again shortly"}

    try:
        data = r.json()
    except Exception:
        return {"ok": False, "items": [], "total": 0, "msg": "Unexpected response from Steam"}

    items = []
    for row in data.get("results") or []:
        asset = ((row.get("asset_description") or {}) if isinstance(row, dict) else {})
        name = unescape(str(row.get("name") or ""))
        icon = str(asset.get("icon_url_large") or asset.get("icon_url") or "")
        item_type = str(asset.get("type") or "")
        hash_name = str(row.get("hash_name") or row.get("name") or "")
        animated = "animated" in item_type.lower() or "animated" in name.lower()
        if kind == "animated" and not animated:
            continue
        if kind == "static" and animated:
            continue
        price = row.get("sell_price_text") or row.get("sale_price_text") or ""
        items.append(
            {
                "name": name,
                "game": unescape(
                    re.sub(r"\s*(Animated\s+)?Profile Background$", "", item_type).strip()
                ),
                "image": _icon_url(icon),
                "animated": animated,
                "price": str(price),
                "market_url": (
                    f"https://steamcommunity.com/market/listings/753/{quote(hash_name)}"
                    if hash_name
                    else ""
                ),
                "asset": asset,
            }
        )

    out = {
        "ok": True,
        "items": items,
        "total": int(data.get("total_count") or 0),
        "page": page,
    }
    _put(key, out, TTL_BG)
    return out


def profile(url: str) -> dict:
    """Load the public part of a Steam profile without a Web API key."""
    raw = (url or "").strip().rstrip("/")
    m = re.match(r"^https?://steamcommunity\.com/(id|profiles)/([^/?#]+)$", raw, re.I)
    if not m:
        return {"ok": False, "msg": "Enter a public steamcommunity.com profile URL"}
    canonical = f"https://steamcommunity.com/{m.group(1).lower()}/{quote(m.group(2))}"
    key = f"profile2:{canonical.lower()}"
    cached = _get(key)
    if cached is not None:
        return cached
    r = _fetch(canonical + "/?xml=1")
    if r is None:
        return {"ok": False, "msg": "Steam profile is unavailable or private"}
    try:
        root = ET.fromstring(r.content)
        def txt(name: str) -> str:
            node = root.find(name)
            return (node.text or "").strip() if node is not None else ""
        if root.tag == "response" or txt("error"):
            return {"ok": False, "msg": txt("error") or "Steam profile is private"}
        groups = []
        for group in root.findall("./groups/group")[:6]:
            groups.append({
                "name": (group.findtext("groupName") or "").strip(),
                "avatar": (group.findtext("avatarMedium") or "").strip(),
            })
        page = _fetch(canonical)
        page_html = page.text if page is not None else ""
        level_match = re.search(r'friendPlayerLevelNum[^>]*>\s*(\d+)', page_html, re.I)
        bg_match = re.search(r'profile_page[^>]+style="[^"]*background-image:\s*url\([\'\"]?([^\)\'\"]+)', page_html, re.I)
        counts = [int(x.replace(',', '')) for x in re.findall(r'profile_count_link_total[^>]*>\s*([\d,]+)', page_html, re.I)]
        summary = unescape(txt("summary"))
        summary = re.sub(r"<br\s*/?>", "\n", summary, flags=re.I)
        summary = _clean(summary)
        out = {
            "ok": True,
            "profile": {
                "url": canonical,
                "steamid": txt("steamID64"),
                "name": txt("steamID"),
                "avatar": txt("avatarFull") or txt("avatarMedium"),
                "headline": txt("headline"),
                "summary": summary,
                "location": txt("location"),
                "realname": txt("realname"),
                "status": txt("onlineState"),
                "member_since": txt("memberSince"),
                "groups": groups,
                "level": int(level_match.group(1)) if level_match else None,
                "background": unescape(bg_match.group(1)) if bg_match else "",
                "stats": counts[:6],
            },
        }
        _put(key, out, TTL_PROFILE)
        return out
    except Exception as e:
        LOGGER.warning("steam profile parse failed: %s", e)
        return {"ok": False, "msg": "Steam returned an unexpected profile page"}


# --------------------------------------------------------------------------
# Achievements
# --------------------------------------------------------------------------
# The public achievements page renders each row inside .achieveRow. Parsing it
# with regex is fragile by nature, so every field is optional and a structural
# change degrades to an empty list rather than an exception.
_ROW_RE = re.compile(
    r'<div class="achieveRow.*?<img[^>]+src="([^"]+)".*?'
    r'<h3[^>]*>(.*?)</h3>\s*<h5[^>]*>(.*?)</h5>',
    re.S,
)
_PCT_RE = re.compile(r'<div class="achievePercent">\s*([\d.,]+%)\s*</div>')
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return unescape(_TAG_RE.sub("", s or "")).strip()


def achievements(appid: str) -> dict:
    appid = re.sub(r"\D", "", str(appid or ""))[:12]
    if not appid:
        return {"ok": False, "items": [], "msg": "AppID must be a number"}

    key = f"ach:{appid}"
    cached = _get(key)
    if cached is not None:
        return cached

    r = _fetch(ACH_PAGE.format(appid=appid))
    if r is None:
        return {"ok": False, "items": [], "msg": "Steam is unavailable, try again shortly"}

    html_text = r.text
    if "achieveRow" not in html_text:
        # Either the game has no achievements or Steam served an age gate.
        msg = "This game has no public achievements"
        if "agecheck" in html_text or "login" in r.url:
            msg = "Steam did not return the achievement page for this game"
        out = {"ok": False, "items": [], "msg": msg}
        _put(key, out, 600)
        return out

    percents = _PCT_RE.findall(html_text)
    items = []
    for i, (img, title, desc) in enumerate(_ROW_RE.findall(html_text)):
        name = _clean(title)
        if not name:
            continue
        items.append(
            {
                "name": name,
                "description": _clean(desc),
                "image": img.strip(),
                "percent": percents[i] if i < len(percents) else "",
            }
        )

    out = {"ok": True, "items": items, "appid": appid, "count": len(items)}
    _put(key, out, TTL_ACH if items else 900)
    return out


# --------------------------------------------------------------------------
# App search — used to look up an AppID by game name
# --------------------------------------------------------------------------
def apps(q: str, limit: int = 24) -> dict:
    """Search Steam apps by name via the public community search endpoint."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"ok": False, "items": [], "msg": "Enter at least 2 characters"}

    key = f"apps:{q.lower()}:{limit}"
    cached = _get(key)
    if cached is not None:
        return cached

    r = _fetch(APP_SEARCH.format(q=quote(q)))
    if r is None:
        return {"ok": False, "items": [], "msg": "Steam is unavailable, try again shortly"}
    try:
        rows = r.json()
    except Exception:
        return {"ok": False, "items": [], "msg": "Unexpected response from Steam"}
    if not isinstance(rows, list):
        rows = []

    items = []
    for row in rows[:limit]:
        appid = str(row.get("appid") or "").strip()
        if not appid.isdigit():
            continue
        items.append(
            {
                "appid": int(appid),
                "name": unescape(str(row.get("name") or "")),
                "image": str(row.get("icon") or "")
                or f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
            }
        )

    out = {"ok": True, "items": items}
    _put(key, out, TTL_APPS)
    return out
