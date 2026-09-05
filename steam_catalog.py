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
import os
import re
from html.parser import HTMLParser
import threading
import time
import unicodedata
from html import unescape
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, urlsplit

import requests
import steam_profile_guard
import steam_browser_import
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

# Label on a Steam profile count link -> the key the mockup builder uses.
_STAT_KEYS = {
    "games": "games",
    "inventory": "inv",
    "screenshots": "screens",
    "videos": "videos",
    "workshop items": "workshop",
    "reviews": "reviews",
    "guides": "guides",
    "artwork": "art",
    "groups": "groups",
    "friends": "friends",
    "profile awards": "awards",
    "badges": "badges",
}

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


def _fetch(url: str, params: dict | None = None, retries: int = 3) -> Optional[requests.Response]:
    """GET Steam with retries. 429/5xx → backoff (Steam often throttles datacenter IPs)."""
    headers = {
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    }
    last_err = None
    for attempt in range(max(1, retries)):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT, headers=headers)
            if r.status_code == 429 or r.status_code >= 500:
                LOGGER.warning("steam %s → HTTP %s (try %s)", url, r.status_code, attempt + 1)
                time.sleep(1.2 * (attempt + 1))
                last_err = r.status_code
                continue
            if r.status_code != 200:
                LOGGER.warning("steam %s → HTTP %s", url, r.status_code)
                return None
            return r
        except Exception as e:
            last_err = e
            LOGGER.warning("steam fetch failed %s: %s", url, e)
            time.sleep(0.8 * (attempt + 1))
    LOGGER.warning("steam give up %s last=%s", url, last_err)
    return None


# --------------------------------------------------------------------------
# Profile backgrounds
# --------------------------------------------------------------------------
def _icon_url(icon: str, size: str = "360fx360f") -> str:
    if not icon:
        return ""
    return f"https://community.cloudflare.steamstatic.com/economy/image/{icon}/{size}"


# Steam community-item classes on appid 753. The market only understands these
# numeric tags, so keeping them in one table beats sprinkling magic strings.
ITEM_CLASS = {
    "card": "tag_item_class_2",
    "background": "tag_item_class_3",
    "emoticon": "tag_item_class_4",
    "booster": "tag_item_class_5",
}
# Avatars (13), frames (14) and animated backgrounds (15) are deliberately absent:
# those classes exist in Steam taxonomy but carry zero market listings because
# they are points-shop rewards. See POINTS_CLASS below.
# "badge" is not a market item at all - badges are crafted from cards. We build
# it by grouping the card listings of a game, so it reuses the card class.
# The points-shop kinds are appended in the Points Shop section below.
MARKET_ASSETS = tuple(ITEM_CLASS) + ("badge",)

# Trailing item-kind noise in asset_description.type ("Portal 2 Trading Card"),
# stripped so the UI can show the game on its own line.
_TYPE_SUFFIX = re.compile(
    r"\s*(Animated\s+)?(Profile Background|Trading Card|Foil Trading Card|"
    r"Booster Pack|Avatar Frame|Animated Avatar|Avatar|Emoticon)$",
    re.I,
)


MARKET_PAGE = 10  # Steam caps market/search/render at 10 rows, whatever count says


def _extra_key(extra: dict | None) -> str:
    if not extra:
        return ""
    return "|".join("%s=%s" % (k, extra[k]) for k in sorted(extra))


def _market_slab(item_class: str, q: str, start: int, extra: dict | None = None):
    """One 10-row slab of market/search/render. Returns (rows, total) or None.

    The endpoint silently clamps `count` to 10 -- it answers pagesize 10 even for
    count=100 -- so a slab is the real unit of paging and the unit we cache.
    """
    start = max(0, int(start))
    key = "slab:%s:%s:%d:%s" % (item_class, q.lower(), start, _extra_key(extra))
    cached = _get(key)
    if cached is not None:
        return cached["rows"], cached["total"]

    params = {
        "query": q,
        "start": start,
        "count": MARKET_PAGE,
        "search_descriptions": 0,
        "sort_column": "popular",
        "sort_dir": "desc",
        "appid": 753,
        "norender": 1,
        "category_753_item_class[]": item_class,
    }
    if extra:
        params.update(extra)
    r = _fetch(MARKET_SEARCH, params)
    if r is None:
        return None
    try:
        data = r.json()
    except Exception:
        return None
    if not isinstance(data, dict) or not data.get("success"):
        return None
    out = {"rows": data.get("results") or [], "total": int(data.get("total_count") or 0)}
    _put(key, out, TTL_BG)
    return out["rows"], out["total"]


def _market_rows(item_class: str, q: str, start: int, count: int, extra: dict | None = None):
    """Assemble `count` rows from consecutive slabs. Returns (rows, total) or None."""
    start = max(0, int(start))
    count = max(1, int(count))
    rows: list = []
    total = 0
    pos = start
    while len(rows) < count:
        base = pos - (pos % MARKET_PAGE)
        got = _market_slab(item_class, q, base, extra)
        if got is None:
            return (rows[:count], total) if rows else None
        slab, total = got
        if not slab:
            break
        rows.extend(slab[pos - base:])
        if len(slab) < MARKET_PAGE:
            break
        pos = base + MARKET_PAGE
        if pos >= total:
            break
    return rows[:count], total


def _game_facet(appid: int) -> dict:
    """Narrow a 753 search to one game. The facet value needs the tag_ prefix."""
    return {"category_753_Game[]": "tag_app_%d" % int(appid)}


def card_set(appid: int, foil: bool = False) -> dict:
    """Every trading card of one game, with the price of the full set.

    This is the exact answer for a badge: a badge is crafted from one full set,
    so summing the cheapest listing of each card is what it costs to make.
    """
    try:
        appid = int(appid)
    except (TypeError, ValueError):
        return {"ok": False, "items": [], "msg": "Bad appid"}
    if appid <= 0:
        return {"ok": False, "items": [], "msg": "Bad appid"}

    key = "cardset:%d:%d" % (appid, int(bool(foil)))
    cached = _get(key)
    if cached is not None:
        return cached

    extra = _game_facet(appid)
    extra["category_753_cardborder[]"] = "tag_cardborder_1" if foil else "tag_cardborder_0"
    got = _market_rows(ITEM_CLASS["card"], "", 0, 60, extra)
    if got is None:
        return {"ok": False, "items": [], "msg": "Steam is unavailable, try again shortly"}
    rows, total = got

    items = []
    cents = 0
    for row in rows:
        it = _row_to_item(row, "card")
        if it is None:
            continue
        items.append(it)
        cents += _price_cents(it["price"])
    sample = next((i["price"] for i in items if i["price"]), "")
    out = {
        "ok": True,
        "appid": appid,
        "foil": bool(foil),
        "game": next((i["game"] for i in items if i["game"]), ""),
        "items": items,
        "count": len(items),
        "total": total,
        "set_price_cents": cents,
        "set_price": _price_like(sample, cents),
        "capsule": APP_CAPSULE.format(appid),
        "badge_url": "https://steamcommunity.com/my/gamecards/%d" % appid,
        "partial": len(items) < total,
    }
    _put(key, out, TTL_BG)
    return out


def _badge_row(appid: int, name: str, game: str, image: str, market_url: str = "") -> dict:
    """One badge candidate. Price stays empty until card_set(appid) is asked for."""
    capsule = APP_CAPSULE.format(appid) if appid else ""
    return {
        "name": name,
        "game": game,
        "appid": appid,
        "defid": None,
        "asset": "badge",
        "image": image or capsule,
        "capsule": capsule,
        "movie": "",
        "movie_mp4": "",
        "animated": False,
        "tiled": False,
        "foil": False,
        "source": "market",
        "price": "",
        "points": 0,
        "card_count": 0,
        "cards": [],
        "buy_url": ("https://steamcommunity.com/my/gamecards/%d" % appid) if appid else "",
        "market_url": market_url,
        "partial": True,
    }


def _badges(q: str, page: int, count: int) -> dict:
    """Badge candidates: one row per game.

    A badge has no market listing of its own -- it is crafted from a full card
    set -- so this lists games and leaves the exact set and its price to
    card_set(appid), which the UI calls once a game is picked. With a search term
    we resolve games by name; without one we read the games off the popular card
    listings.
    """
    page = max(0, int(page))
    count = max(1, min(50, int(count)))

    if len(q) >= 2:
        found = apps(q, limit=count)
        if not found.get("ok"):
            return {"ok": False, "items": [], "total": 0, "msg": found.get("msg") or "No games found"}
        items = [
            _badge_row(a["appid"], a["name"], a["name"], APP_CAPSULE.format(a["appid"]))
            for a in found.get("items") or []
        ]
        return {"ok": True, "items": items, "total": len(items), "page": page, "source": "market"}

    got = _market_rows(ITEM_CLASS["card"], "", page * count * 3, count * 3)
    if got is None:
        return {"ok": False, "items": [], "total": 0, "msg": "Steam is unavailable, try again shortly"}
    rows, total = got
    seen: dict[int, dict] = {}
    for row in rows:
        it = _row_to_item(row, "card")
        if it is None or not it["appid"] or it["appid"] in seen:
            continue
        seen[it["appid"]] = _badge_row(
            it["appid"], it["game"] or it["name"], it["game"], it["capsule"], it["market_url"]
        )
    return {"ok": True, "items": list(seen.values())[:count], "total": total, "page": page, "source": "market"}


def _row_to_item(row: dict, asset: str) -> dict | None:
    """Flatten one market row into the shape the builder UI consumes."""
    if not isinstance(row, dict):
        return None
    ad = row.get("asset_description") or {}
    if not isinstance(ad, dict):
        ad = {}
    name = unescape(str(row.get("name") or ""))
    icon = str(ad.get("icon_url_large") or ad.get("icon_url") or "")
    if not name or not icon:
        return None
    item_type = unescape(str(ad.get("type") or ""))
    hash_name = str(row.get("hash_name") or row.get("name") or "")
    animated = "animated" in item_type.lower() or "animated" in name.lower()
    try:
        appid = int(ad.get("market_fee_app") or 0)
    except (TypeError, ValueError):
        appid = 0
    market_url = ""
    if hash_name:
        market_url = "https://steamcommunity.com/market/listings/753/" + quote(hash_name)
    if not appid:
        # market_fee_app is often absent, but every community hash name is
        # "{appid}-{item}", which is the only place the game id survives.
        m = re.match(r"^(\d+)-", str(ad.get("market_hash_name") or hash_name))
        if m:
            appid = int(m.group(1))
    game = _TYPE_SUFFIX.sub("", item_type).strip()
    if not game:
        # Booster packs carry a bare "Booster Pack" type; the game is in the name.
        game = _TYPE_SUFFIX.sub("", name).strip()
    return {
        "name": name,
        "game": game,
        "appid": appid,
        "defid": None,
        "image": _icon_url(icon),
        "movie": "",
        "movie_mp4": "",
        "animated": animated,
        "tiled": False,
        "foil": "foil" in item_type.lower() or "(foil)" in name.lower(),
        "source": "market",
        "price": str(row.get("sell_price_text") or row.get("sale_price_text") or ""),
        "points": 0,
        "buy_url": market_url,
        "market_url": market_url,
        "capsule": APP_CAPSULE.format(appid) if appid else "",
        "asset": asset,
    }


def _price_cents(text: str) -> int:
    """Market prices arrive pre-formatted per locale. Digits are enough to sum."""
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else 0


def _price_like(sample: str, cents: int) -> str:
    """Render `cents` in the same layout Steam used for `sample`.

    Currency position and decimal separator differ per account region ($0.30 vs
    0,30 EUR), and we never learn the region -- so a sample price from the same
    response is the only trustworthy template.
    """
    m = re.search(r"\d+(?:[.,]\d{2})?", sample or "")
    if not m:
        return ""
    token = m.group(0)
    sep = "," if ("," in token and "." not in token) else "."
    whole, frac = divmod(max(0, cents), 100)
    return sample[: m.start()] + "%d%s%02d" % (whole, sep, frac) + sample[m.end():]


def backgrounds(q: str = "", page: int = 0, kind: str = "all", count: int = 24, asset: str = "background") -> dict:
    """Search the Steam Market for profile-decoration items.

    `asset` picks the catalog: background, avatar, frame, card, booster,
    emoticon or badge. `kind` narrows it - static/animated for backgrounds and
    avatars, normal/foil for cards - and is applied in the query rather than by
    post-filtering a page that may contain none of the wanted type.
    """
    page = max(0, int(page))
    count = max(1, min(50, int(count)))
    kind = (kind or "all").lower()
    asset = (asset or "background").lower()
    if asset not in ASSETS:
        asset = "background"
    q = (q or "").strip()

    # Points-shop kinds never reach the market at all.
    if asset in POINTS_CLASS:
        return points_items(asset, q=q, page=page, count=count)
    if asset == "background" and kind == "animated":
        return points_items("animated_background", q=q, page=page, count=count)
    if asset == "background" and kind == "points":
        return points_items("points_background", q=q, page=page, count=count)

    key = "asset3:%s:%s:%s:%d:%d" % (asset, kind, q.lower(), page, count)
    cached = _get(key)
    if cached is not None:
        return cached

    if asset == "badge":
        out = _badges(q, page, count)
        if out.get("ok"):
            _put(key, out, TTL_BG)
        return out

    extra: dict = {}
    if asset == "background":
        if kind == "static":
            extra["category_753_Type[]"] = "tag_Profile_Background"
    elif asset == "card":
        if kind == "foil":
            extra["category_753_cardborder[]"] = "tag_cardborder_1"
        elif kind in ("normal", "static"):
            extra["category_753_cardborder[]"] = "tag_cardborder_0"

    got = _market_rows(ITEM_CLASS[asset], q, page * count, count, extra)
    if got is None:
        # Market search is aggressively rate-limited on hosting providers.
        # The Points Shop exposes an official, keyless background catalog and
        # is a better fallback than leaving the designer empty.
        if asset == "background":
            fallback = points_items("points_background", q, page, count)
            if fallback.get("ok"):
                fallback["fallback"] = "points_shop"
                return fallback
        return {"ok": False, "items": [], "total": 0, "msg": "Steam is unavailable, try again shortly"}
    results, total = got

    items = []
    for row in results:
        it = _row_to_item(row, asset)
        if it is None:
            continue
        # Animated avatars share the avatar class, so they are filtered here.
        if kind == "animated" and not it["animated"]:
            continue
        if kind == "static" and it["animated"] and asset != "card":
            continue
        items.append(it)

    out = {"ok": True, "items": items, "total": total, "page": page}
    _put(key, out, TTL_BG)
    return out


class _ProfilePageParser(HTMLParser):
    """Extract server-rendered showcase media without depending on Steam's CSS layout."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.current = None
        self.showcases = []
        self._title_depth = None
        self._title_parts = []
        self.badges = []
        self.awards = []
        self.background = {"poster": "", "webm": "", "mp4": ""}
        self.avatar_frame = {"animated": "", "static": ""}
        self._background_depth = None
        self._frame_depth = None

    @staticmethod
    def _attrs(attrs):
        return {str(k).lower(): (v or "") for k, v in attrs}

    @staticmethod
    def _media(a):
        for key in ("data-src", "data-image", "data-background-image", "src"):
            val = (a.get(key) or "").strip()
            if val and not val.startswith("data:"):
                return unescape(val)
        style = a.get("style") or ""
        m = re.search(r"url\([\"']?([^\)\"']+)", style, re.I)
        return unescape(m.group(1)) if m else ""

    def handle_starttag(self, tag, attrs):
        a = self._attrs(attrs)
        classes = set((a.get("class") or "").split())
        if tag == "div":
            self.depth += 1
        if tag == "div" and "profile_animated_background" in classes:
            self._background_depth = self.depth
        if tag == "div" and "profile_avatar_frame" in classes:
            self._frame_depth = self.depth
        if self._background_depth is not None:
            media = self._media(a)
            if tag == "video" and media:
                self.background["poster"] = media
            if tag == "source":
                src = (a.get("src") or a.get("srcset") or "").strip()
                if src:
                    kind = "mp4" if "mp4" in (a.get("type") or "").lower() or ".mp4" in src.lower() else "webm"
                    self.background[kind] = unescape(src)
        if self._frame_depth is not None and tag in ("img", "source"):
            src = (a.get("srcset") or a.get("src") or "").strip()
            if src:
                key = "static" if "reduced-motion" in (a.get("media") or "").lower() else "animated"
                self.avatar_frame[key] = unescape(src.split()[0])
        if tag == "div" and self.current is None and "profile_customization" in classes:
            self.current = {"depth": self.depth, "title": "", "images": [], "links": [], "text": []}
        if self.current is not None:
            if any("profile_customization_header" in c for c in classes):
                self._title_depth = self.depth
                self._title_parts = []
            href = (a.get("href") or "").strip()
            if href and ("sharedfiles" in href or "filedetails" in href):
                self.current["links"].append(unescape(href))
            media = self._media(a)
            if media and tag in ("img", "source", "video"):
                low = media.lower()
                if not any(x in low for x in ("blank.gif", "pixel.gif", "trans.gif")):
                    self.current["images"].append(media)
        media = self._media(a)
        if media and tag == "img":
            joined = " ".join(classes).lower()
            if "badge" in joined and media not in self.badges:
                self.badges.append(media)
            if ("award" in joined or "profile_award" in joined) and media not in self.awards:
                self.awards.append(media)

    def handle_data(self, data):
        txt = re.sub(r"\s+", " ", data or "").strip()
        if not txt or self.current is None:
            return
        self.current["text"].append(txt)
        if self._title_depth is not None:
            self._title_parts.append(txt)

    def handle_endtag(self, tag):
        if tag != "div":
            return
        if self.current is not None and self._title_depth == self.depth:
            self.current["title"] = " ".join(self._title_parts).strip()
            self._title_depth = None
            self._title_parts = []
        if self.current is not None and self.current["depth"] == self.depth:
            item = self.current
            item["images"] = list(dict.fromkeys(item["images"]))
            item["links"] = list(dict.fromkeys(item["links"]))
            item["text"] = " ".join(item["text"])
            title = item["title"].lower().strip()
            plain_title = unicodedata.normalize("NFKD", item["title"]).lower().strip()
            # Classify by the customization header, never by all body text.
            # A Recent Activity block can contain the words "Workshop Submission"
            # and used to be imported as a fake 15-image Workshop showcase.
            if "workshop" in title or "мастерск" in title:
                item["type"] = "workshop"
            elif "guide" in title or "руковод" in title:
                item["type"] = "guide"
            elif "featured artwork" in title or "избранная иллюстрац" in title:
                item["type"] = "featured"
            elif title == "artwork showcase" or title == "витрина иллюстраций":
                item["type"] = "artwork"
            elif "artwork" in title or "illustration" in title or "иллюстра" in title or "screenshot" in title:
                item["type"] = "artwork"
            elif ("information" in plain_title or "custom info" in plain_title or "информац" in plain_title or
                  "about me" in plain_title or "обо мне" in plain_title):
                item["type"] = "info"
            elif "recent activity" in title or "недавняя активность" in title:
                item["type"] = "activity"
            else:
                # Keep unsupported Steam blocks in their real order.  The
                # renderer can show a compact placeholder and future versions
                # can add a specialised editor without requiring a re-import.
                item["type"] = "unknown"
            if item["type"] != "activity":
                self.showcases.append(item)
            self.current = None
        if self._background_depth == self.depth:
            self._background_depth = None
        if self._frame_depth == self.depth:
            self._frame_depth = None
        self.depth = max(0, self.depth - 1)


def _profile_customizations(page_html: str) -> dict:
    parser = _ProfilePageParser()
    try:
        parser.feed(page_html or "")
    except Exception as exc:
        LOGGER.debug("profile showcase parse degraded: %s", exc)
    return {
        "showcases": parser.showcases[:20],
        "badges": parser.badges[:16],
        "awards": parser.awards[:12],
        "background_item": parser.background,
        "avatar_frame": parser.avatar_frame,
    }


def _normalise_showcase(item: dict) -> dict:
    """Reduce Steam's noisy block media to the slots visible in the showcase."""
    result = dict(item)
    images = []
    for raw in item.get("images") or []:
        url = unescape(str(raw or "")).strip()
        # Steam serves author avatars from several CDN hosts, not only Akamai.
        # These appear inside Workshop headers but are not showcase tiles.
        avatar_host = (urlsplit(url).hostname or "").lower().startswith("avatars.")
        if not url or avatar_host or any(noise in url.lower() for noise in (
            "avatars.akamai", "/avatars/", "steamcommunity/public/images/skin",
            "blank.gif", "pixel.gif", "trans.gif",
        )):
            continue
        if url not in images:
            images.append(url)
    typ = result.get("type") or "unknown"
    if typ == "workshop":
        result["images"] = images[:15]
    elif typ in ("guide", "featured"):
        result["images"] = images[:1]
    elif typ == "artwork":
        # Artwork Showcase is 506px + 100px. Steam may render thumbnail
        # duplicates before the two full-height assets, so prefer the largest
        # community-file URLs while preserving DOM order.
        full = [u for u in images if "steamuserimages" in u.lower() or "usercontent" in u.lower()]
        result["images"] = (full or images)[:2]
    else:
        result["images"] = images[:8]
    return result


def profile(url: str, progress=None) -> dict:
    """Load the public part of a Steam profile without a Web API key.

    Accepts full URL, /id/vanity, /profiles/steamid64, bare vanity or SteamID64.
    """
    raw = (url or "").strip()
    if not raw:
        return {"ok": False, "msg": "Enter a public steamcommunity.com profile URL"}
    if re.fullmatch(r"\d{17}", raw):
        canonical = f"https://steamcommunity.com/profiles/{raw}"
    elif re.fullmatch(r"[A-Za-z0-9_-]{2,64}", raw):
        canonical = f"https://steamcommunity.com/id/{raw}"
    else:
        raw = raw.rstrip("/")
        m = re.search(r"steamcommunity\.com/(id|profiles)/([^/?#]+)", raw, re.I)
        if not m:
            return {"ok": False, "msg": "Enter a public steamcommunity.com profile URL"}
        canonical = f"https://steamcommunity.com/{m.group(1).lower()}/{quote(m.group(2))}"

    cache_dir = _CACHE_PATH.parent if _CACHE_PATH else Path(os.environ.get('DATA_DIR', 'data'))
    browser_configured = steam_browser_import.configured()
    return steam_profile_guard.run(
        cache_dir / 'steam_profiles.sqlite3', canonical.lower(),
        lambda: _load_profile(canonical, progress=progress),
        use_global_gate=not browser_configured,
    )


def _profile_fetch(url):
    response = requests.get(url, timeout=TIMEOUT,
                            headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
    if response.status_code == 429:
        raise steam_profile_guard.RateLimited(response.headers.get('Retry-After'))
    return response if response.status_code == 200 else None


def _html_text(page_html: str, class_name: str) -> str:
    match = re.search(
        r'<[^>]+class=["\'][^"\']*\b' + re.escape(class_name) + r'\b[^"\']*["\'][^>]*>(.*?)</[^>]+>',
        page_html or "", re.S | re.I,
    )
    if not match:
        return ""
    value = re.sub(r"<br\s*/?>", "\n", match.group(1), flags=re.I)
    return _clean(unescape(re.sub(r"<[^>]+>", " ", value)))


def _html_profile_fields(page_html: str) -> dict:
    """Identity fields used when Browser API replaces Steam's XML endpoint."""
    data = {}
    match = re.search(r"g_rgProfileData\s*=\s*(\{.*?\})\s*;", page_html or "", re.S)
    if match:
        try:
            data = json.loads(match.group(1))
        except (TypeError, ValueError):
            data = {}
    steam_id = str(data.get("steamid") or "")
    if not steam_id:
        found = re.search(r'\b(?:steamid|steamID64)["\']?\s*[:=]\s*["\'](\d{17})', page_html or "", re.I)
        steam_id = found.group(1) if found else ""
    avatar = ""
    found = re.search(r'class=["\'][^"\']*playerAvatarAutoSizeInner[^"\']*["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)', page_html or "", re.S | re.I)
    if found:
        avatar = unescape(found.group(1))
    return {
        "steamID64": steam_id,
        "steamID": str(data.get("personaname") or _html_text(page_html, "actual_persona_name")),
        "avatarFull": avatar,
        "avatarMedium": avatar,
        "summary": _html_text(page_html, "profile_summary"),
        "headline": "",
        "location": _html_text(page_html, "header_real_name"),
        "realname": "",
        "onlineState": "online" if "profile_in_game" in (page_html or "") else "offline",
        "memberSince": "",
    }


def _load_profile(canonical, progress=None):
    page_html = ""
    root = None
    r = None
    browser_error = None
    if steam_browser_import.configured():
        try:
            page_html = steam_browser_import.fetch_html(canonical, progress=progress)
        except steam_browser_import.BrowserImportError as exc:
            browser_error = exc

    if not page_html:
        r = _profile_fetch(canonical + "/?xml=1")
        if r is None:
            if browser_error:
                return {"ok": False, "code": browser_error.code, "msg": str(browser_error)}
            return {"ok": False, "msg": "Steam profile is unavailable or private"}
    try:
        if r is not None and not page_html:
            root = ET.fromstring(r.content)
        html_fields = _html_profile_fields(page_html) if page_html else {}
        def txt(name: str) -> str:
            if root is None:
                return str(html_fields.get(name) or "").strip()
            node = root.find(name)
            return (node.text or "").strip() if node is not None else ""
        if root is not None and (root.tag == "response" or txt("error")):
            return {"ok": False, "msg": txt("error") or "Steam profile is private"}
        groups = []
        if root is not None:
            for group in root.findall("./groups/group")[:6]:
                groups.append({
                    "name": (group.findtext("groupName") or "").strip(),
                    "avatar": (group.findtext("avatarMedium") or "").strip(),
                })
        if not page_html:
            page = _profile_fetch(canonical + '/?l=english')
            page_html = page.text if page is not None else ""
        if not page_html or not re.search(r'class=[\"\'][^\"\']*\bprofile_page\b', page_html, re.I):
            return {'ok': False, 'code': 'steam_profile_incomplete',
                    'msg': 'Steam did not return the full public profile. Try later or use the extension.'}
        level_match = re.search(r'friendPlayerLevelNum[^>]*>\s*(\d+)', page_html, re.I)
        bg_match = re.search(r'profile_page[^>]+style="[^"]*background-image:\s*url\([\'\"]?([^\)\'\"]+)', page_html, re.I)
        counts = [int(x.replace(',', '')) for x in re.findall(r'profile_count_link_total[^>]*>\s*([\d,]+)', page_html, re.I)]
        # The count links a profile shows depend on what that profile actually has,
        # so their order is not fixed — read the label next to each number instead
        # of trusting a position.
        stat_map: dict = {}
        for label_html, num in re.findall(
            r'profile_count_link[^>]*>(.{0,400}?)profile_count_link_total[^>]*>\s*([\d,]+)',
            page_html, re.S | re.I,
        ):
            # The window can end inside an unfinished tag; drop that tail first,
            # otherwise its attribute text sticks to the label.
            frag = re.sub(r'<[^>]*$', '', label_html)
            label = unescape(re.sub(r'<[^>]+>', ' ', frag))
            label = re.sub(r'\s+', ' ', label).strip().lower()
            key = _STAT_KEYS.get(label)
            if not key:
                for phrase, k in _STAT_KEYS.items():
                    if label.endswith(phrase):
                        key = k
                        break
            if key and key not in stat_map:
                stat_map[key] = int(num.replace(',', ''))
        summary = unescape(txt("summary"))
        summary = re.sub(r"<br\s*/?>", "\n", summary, flags=re.I)
        summary = _clean(summary)
        custom = _profile_customizations(page_html)
        showcase_instances = [_normalise_showcase(s) for s in custom["showcases"]]
        background_item = custom.get("background_item") or {}
        avatar_frame = custom.get("avatar_frame") or {}
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
                "background": (background_item.get("poster") or
                               (unescape(bg_match.group(1)) if bg_match else "")),
                "background_movie": (background_item.get("webm") or background_item.get("mp4") or ""),
                "background_item": background_item,
                "frame": avatar_frame.get("animated") or avatar_frame.get("static") or "",
                "avatar_frame": avatar_frame,
                "stats": counts[:6],
                "stats_map": stat_map,
                "showcases": showcase_instances,
                "showcase_instances": showcase_instances,
                "showcase_order": [s.get("type") or "unknown" for s in showcase_instances],
                "badges": [
                    (b if isinstance(b, str) else (b.get("image") or b.get("url") or ""))
                    for b in (custom.get("badges") or [])
                    if (b if isinstance(b, str) else (b.get("image") or b.get("url")))
                ],
                "badge_items": custom.get("badges") or [],
                "awards": custom["awards"],
                "sync_mode": "browser_plus_api" if root is None else "api_plus_html",
                "steam_api_available": False,
            },
        }
        # Community HTML supplies showcases, while Valve's Web API supplies
        # stable account fields when Steam rate-limits datacenter HTML.
        api_key = (os.environ.get("STEAM_API_KEY") or "").strip()
        steam_id = out["profile"].get("steamid") or ""
        if api_key and steam_id.isdigit():
            out["profile"]["steam_api_available"] = True
            def api(path: str, **params) -> dict:
                params.update({"key": api_key, "steamid": steam_id})
                response = requests.get("https://api.steampowered.com" + path, params=params,
                                        timeout=TIMEOUT, headers={"User-Agent": UA})
                response.raise_for_status()
                return response.json().get("response") or {}
            # These endpoints are independent. Fetching them serially added up
            # to three network round trips after the browser had already
            # rendered the page.
            with ThreadPoolExecutor(max_workers=3, thread_name_prefix="steam-api") as pool:
                summaries_f = pool.submit(api, "/ISteamUser/GetPlayerSummaries/v2/", steamids=steam_id)
                level_f = pool.submit(api, "/IPlayerService/GetSteamLevel/v1/")
                owned_f = pool.submit(
                    api, "/IPlayerService/GetOwnedGames/v1/",
                    include_appinfo=1, include_played_free_games=1,
                )
            try:
                players = summaries_f.result().get("players") or []
                if players:
                    player = players[0]
                    out["profile"]["name"] = player.get("personaname") or out["profile"]["name"]
                    out["profile"]["avatar"] = player.get("avatarfull") or out["profile"]["avatar"]
                    out["profile"]["realname"] = player.get("realname") or out["profile"]["realname"]
                    if player.get("personastate") is not None:
                        out["profile"]["status"] = "online" if int(player.get("personastate") or 0) else "offline"
            except Exception as exc:
                LOGGER.info("Steam GetPlayerSummaries unavailable: %s", exc)
            try:
                level = level_f.result().get("player_level")
                if level is not None:
                    out["profile"]["level"] = int(level)
            except Exception as exc:
                LOGGER.info("Steam GetSteamLevel unavailable: %s", exc)
            try:
                owned = owned_f.result()
                games = owned.get("games") or []
                out["profile"]["games"] = games[:500]
                out["profile"]["stats_map"]["games"] = int(owned.get("game_count") or len(games))
            except Exception as exc:
                LOGGER.info("Steam GetOwnedGames unavailable/private: %s", exc)
        return out
    except steam_profile_guard.RateLimited:
        raise
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


# ==========================================================================
# Steam Points Shop
#
# Avatar frames, animated avatars, animated backgrounds and profile themes are
# NOT community-market items -- they are bought with Steam Points, so the market
# search returns nothing for them (item classes 13/14/15 exist in the taxonomy
# but have zero listings). The points shop has its own public read endpoint,
# which is what this section talks to.
# ==========================================================================

POINTS_QUERY = "https://api.steampowered.com/ILoyaltyRewardsService/QueryRewardItems/v1/"
# Every points-shop asset is addressed as {appid}/{40-hex}.{ext} under this base.
POINTS_CDN = "https://shared.cloudflare.steamstatic.com/community_assets/images/items"
POINTS_SHOP_APP = "https://store.steampowered.com/points/shop/app/"
APP_CAPSULE = "https://cdn.cloudflare.steamstatic.com/steam/apps/{}/capsule_231x87.jpg"

# ECommunityItemClass values the points shop actually serves.
POINTS_CLASS = {
    "avatar": 13,
    "frame": 14,
    "animated_background": 15,
    "points_background": 3,
    "theme": 8,
    "points_emoticon": 4,
}
TTL_POINTS = 6 * 3600
_POINTS_BLOCK = 1000  # server maximum per request


def _points_asset(appid: int, filename: str) -> str:
    if not appid or not filename:
        return ""
    return "%s/%d/%s" % (POINTS_CDN, appid, filename)


def _points_item(defn: dict, asset: str) -> dict | None:
    """Flatten one reward definition into the shared catalog item shape."""
    if not isinstance(defn, dict):
        return None
    cid = defn.get("community_item_data") or {}
    if not isinstance(cid, dict):
        cid = {}
    try:
        appid = int(defn.get("appid") or 0)
    except (TypeError, ValueError):
        appid = 0
    image = _points_asset(appid, str(cid.get("item_image_large") or cid.get("item_image_small") or ""))
    if not image:
        return None
    try:
        points = int(defn.get("point_cost") or 0)
    except (TypeError, ValueError):
        points = 0
    name = str(cid.get("item_title") or cid.get("item_name") or "").strip()
    return {
        "name": name,
        "game": "",
        "appid": appid,
        "defid": defn.get("defid"),
        "image": image,
        # Animated items ship a looping video; the still is only a poster frame.
        "movie": _points_asset(appid, str(cid.get("item_movie_webm") or "")),
        "movie_mp4": _points_asset(appid, str(cid.get("item_movie_mp4") or "")),
        "animated": bool(cid.get("animated")),
        "tiled": bool(cid.get("tiled")),
        "foil": False,
        "source": "points",
        "price": "",
        "points": points,
        "buy_url": (POINTS_SHOP_APP + str(appid)) if appid else "",
        "market_url": "",
        "capsule": APP_CAPSULE.format(appid) if appid else "",
        "asset": asset,
    }


def _points_block(cls: int, term: str, block: int) -> tuple[list, int, str] | None:
    """One 1000-item block. Returns (definitions, total, next_cursor).

    The endpoint pages by opaque cursor, not offset, so reaching block N means
    walking blocks 0..N. Each block is cached, which makes the walk free after
    the first visit and keeps ordinary first-page browsing at one request.
    """
    cursor = ""
    for i in range(block + 1):
        key = "points:%d:%s:%d" % (cls, term.lower(), i)
        cached = _get(key)
        if cached is None:
            payload = {
                "language": "english",
                "count": _POINTS_BLOCK,
                "community_item_classes": [cls],
            }
            if term:
                payload["search_term"] = term
            if cursor:
                payload["cursor"] = cursor
            r = _fetch(POINTS_QUERY, {"input_json": json.dumps(payload)})
            if r is None:
                return None
            try:
                resp = (r.json() or {}).get("response") or {}
            except Exception:
                return None
            cached = {
                "defs": resp.get("definitions") or [],
                "total": int(resp.get("total_count") or 0),
                "next": str(resp.get("next_cursor") or ""),
            }
            _put(key, cached, TTL_POINTS)
        if i == block:
            return cached["defs"], cached["total"], cached["next"]
        cursor = cached["next"]
        if not cursor:
            # Ran out of data before the requested block.
            return [], cached["total"], ""
    return None


def points_items(asset: str, q: str = "", page: int = 0, count: int = 24) -> dict:
    """Catalog page for a points-shop asset kind."""
    cls = POINTS_CLASS.get(asset)
    if cls is None:
        return {"ok": False, "items": [], "total": 0, "msg": "Unknown points-shop asset"}
    page = max(0, int(page))
    count = max(1, min(100, int(count)))
    q = (q or "").strip()

    start = page * count
    block = start // _POINTS_BLOCK
    got = _points_block(cls, q, block)
    if got is None:
        return {"ok": False, "items": [], "total": 0, "msg": "Steam is unavailable, try again shortly"}
    defs, total, _next = got
    offset = start - block * _POINTS_BLOCK
    window = defs[offset:offset + count]
    # A page may straddle two blocks.
    if len(window) < count and len(defs) >= _POINTS_BLOCK:
        more = _points_block(cls, q, block + 1)
        if more is not None:
            window += more[0][: count - len(window)]

    items = []
    for d in window:
        it = _points_item(d, asset)
        if it is not None:
            items.append(it)
    return {"ok": True, "items": items, "total": total, "page": page, "source": "points"}


# Every catalog kind the builder may ask for, market and points shop together.
ASSETS = MARKET_ASSETS + tuple(POINTS_CLASS)
