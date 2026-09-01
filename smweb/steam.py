"""Steam OpenID realm, Web API fetch and profile merging.

Moved out of main.py unchanged; see docs/STRUCTURE.md.
"""


from __future__ import annotations

import hashlib
import hmac
import html
import io
import ipaddress
import json
import logging
import os
import re
import socket
import secrets
import tempfile
import shutil
import time
import uuid
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db


from smweb.core import HOST, LOGGER, PORT


# ====================== Steam OpenID login ======================
def _steam_realm() -> str:
    base = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    if not base:
        base = f"http://{HOST}:{PORT}"
    return base


def _steam_web_api_data(steam_id: str) -> dict:
    """Optional private-key enrichment; public HTML remains the showcase source."""
    key = (os.environ.get("STEAM_API_KEY") or "").strip()
    if not key or not str(steam_id).isdigit():
        return {}
    import requests as _req
    base = "https://api.steampowered.com"
    def get(path: str, **params):
        params.update({"key": key, "steamid": str(steam_id)})
        r = _req.get(base + path, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("response") or {}
    out: dict = {}
    try:
        players = get("/ISteamUser/GetPlayerSummaries/v2/", steamids=str(steam_id)).get("players") or []
        if players:
            out["player"] = players[0]
    except Exception:
        LOGGER.warning("Steam GetPlayerSummaries unavailable")
    try:
        owned = get("/IPlayerService/GetOwnedGames/v1/", include_appinfo=1, include_played_free_games=1)
        out["games"] = (owned.get("games") or [])[:500]
        out["game_count"] = int(owned.get("game_count") or len(out["games"]))
    except Exception:
        pass
    try:
        out["recent_games"] = (get("/IPlayerService/GetRecentlyPlayedGames/v1/").get("games") or [])[:20]
    except Exception:
        pass
    try:
        out["level"] = int(get("/IPlayerService/GetSteamLevel/v1/").get("player_level") or 0)
    except Exception:
        pass
    return out


def _merge_steam_api(profile: dict) -> dict:
    sid = str(profile.get("steamid") or "")
    api = _steam_web_api_data(sid)
    if not api:
        return profile
    player = api.get("player") or {}
    profile["name"] = player.get("personaname") or profile.get("name")
    profile["avatar"] = player.get("avatarfull") or profile.get("avatar")
    profile["status"] = "online" if int(player.get("personastate") or 0) else profile.get("status")
    if api.get("level"):
        profile["level"] = api["level"]
    profile["games"] = api.get("games") or []
    profile["recent_games"] = api.get("recent_games") or []
    profile.setdefault("stats_map", {})["games"] = api.get("game_count") or profile.get("stats_map", {}).get("games", 0)
    return profile


def _clean_extension_profile(raw: dict, steam_id: str) -> dict:
    """Normalize and bound untrusted DOM data sent by the extension."""
    def txt(value, limit=500):
        return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]
    def url(value):
        value = txt(value, 2048)
        try:
            parsed = urlparse(value)
            host = (parsed.hostname or "").lower()
            allowed = host == "steamcommunity.com" or any(host.endswith(suffix) for suffix in (
                ".steamstatic.com", ".akamaihd.net", ".steamusercontent.com"
            ))
            return value if parsed.scheme == "https" and allowed else ""
        except Exception:
            return ""
    def media_list(items, limit=40):
        out = []
        for item in (items if isinstance(items, list) else [])[:limit]:
            if isinstance(item, str):
                u = url(item)
                if u: out.append(u)
            elif isinstance(item, dict):
                u = url(item.get("url") or item.get("image"))
                if u: out.append(u)
        return list(dict.fromkeys(out))
    p = raw if isinstance(raw, dict) else {}
    bg = p.get("background_item") if isinstance(p.get("background_item"), dict) else {}
    frame = p.get("avatar_frame") if isinstance(p.get("avatar_frame"), dict) else {}
    showcases = []
    for sc in (p.get("showcase_instances") if isinstance(p.get("showcase_instances"), list) else [])[:20]:
        if not isinstance(sc, dict):
            continue
        images = media_list(sc.get("images"), 40)
        if not images and isinstance(sc.get("media"), list):
            images = media_list(sc.get("media"), 40)
        showcases.append({
            "type": txt(sc.get("type"), 40).lower() or "other",
            "title": txt(sc.get("title"), 120),
            "images": images,
            "text": txt(sc.get("text"), 1200),
            "links": [
                {"title": txt(link.get("title"), 160), "url": url(link.get("url"))}
                for link in (sc.get("links") if isinstance(sc.get("links"), list) else [])[:30]
                if isinstance(link, dict) and url(link.get("url"))
            ],
            "width": max(0, min(int(sc.get("width") or 0), 3000)),
            "height": max(0, min(int(sc.get("height") or 0), 10000)),
        })
    def cards(name, limit=100):
        out = []
        for item in (p.get(name) if isinstance(p.get(name), list) else [])[:limit]:
            if not isinstance(item, dict): continue
            image = url(item.get("image"))
            if image: out.append({"image": image, "title": txt(item.get("title") or item.get("name"), 120), "url": url(item.get("url"))})
        return out
    stats = {}
    if isinstance(p.get("stats_map"), dict):
        for key in ("games", "inventory", "screenshots", "videos", "workshop", "reviews", "guides", "artwork"):
            try: stats[key] = max(0, min(int(p["stats_map"].get(key) or 0), 100000000))
            except Exception: pass
    fav = p.get("favorite_badge") if isinstance(p.get("favorite_badge"), dict) else {}
    return {
        "steamid": steam_id,
        "url": url(p.get("url")) or f"https://steamcommunity.com/profiles/{steam_id}",
        "name": txt(p.get("name"), 80), "realname": txt(p.get("realname"), 120),
        "summary": txt(p.get("summary"), 2000), "status": txt(p.get("status"), 80),
        "level": max(0, min(int(p.get("level") or 0), 9999)), "avatar": url(p.get("avatar")),
        "background": url(bg.get("poster")), "background_movie": url(bg.get("webm") or bg.get("mp4")),
        "background_item": {"poster": url(bg.get("poster")), "webm": url(bg.get("webm")), "mp4": url(bg.get("mp4"))},
        "frame": url(frame.get("animated") or frame.get("static")),
        "avatar_frame": {"animated": url(frame.get("animated")), "static": url(frame.get("static"))},
        "favorite_badge": {"image": url(fav.get("image")), "title": txt(fav.get("title"), 120), "xp": txt(fav.get("xp"), 40)},
        "badges": cards("badges"), "awards": cards("awards"), "groups": cards("groups", 30),
        "stats_map": stats, "showcase_instances": showcases,
        "sync_mode": "steam_api_plus_extension", "captured_at": txt(p.get("captured_at"), 80),
    }


def _merge_nonempty_profile(old: dict | None, new: dict) -> dict:
    """A partial Steam page must not erase a previous successful capture."""
    def meaningful(value):
        if isinstance(value, dict): return any(meaningful(v) for v in value.values())
        if isinstance(value, list): return bool(value)
        return value not in (None, "")
    out = dict(old or {})
    for key, value in new.items():
        if meaningful(value):
            if key == "stats_map" and isinstance(value, dict):
                merged = dict(out.get(key) or {}); merged.update(value); out[key] = merged
            else:
                out[key] = value
    return out
