"""Deterministic scoring and Builder project generation for Steam DNA.

Network collection and optional AI interpretation live in separate modules;
this core accepts a bounded public-profile mapping and stays reproducible.
"""
from __future__ import annotations

import colorsys
import hashlib
import math
import time
from typing import Any
from urllib.parse import quote, urlparse


DNA_VERSION = 1
_MODES = {"workshop": 750, "featured": 630, "split": 606}
_SIGNAL_KEYS = ("focus", "variety", "mastery", "history", "activity", "collector")


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return default


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _log_score(value: float, target: float) -> float:
    return _clamp(math.log1p(max(0.0, value)) / math.log1p(target))


def _palette(seed: str, signals: dict[str, float]) -> list[str]:
    raw = int(seed[:8], 16)
    hue = (raw % 360) / 360.0
    offsets = (0.0, 0.08 + signals["variety"] * 0.16, 0.47 + signals["focus"] * 0.1)
    colors = []
    for index, offset in enumerate(offsets):
        rgb = colorsys.hsv_to_rgb((hue + offset) % 1.0, 0.72 - index * 0.08, 1.0)
        colors.append("#" + "".join(f"{round(channel * 255):02x}" for channel in rgb))
    return colors


def _safe_media_url(value: Any) -> str:
    url = str(value or "").strip()
    if url.startswith("/api/"):
        return url[:3000]
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        allowed = any(host.endswith(suffix) for suffix in (
            ".steamstatic.com", ".steampowered.com", ".steamusercontent.com", ".akamaihd.net"
        ))
        if parsed.scheme == "https" and allowed:
            return url[:3000]
    except Exception:
        pass
    return ""


def _proxy_url(value: Any) -> str:
    url = _safe_media_url(value)
    if url.startswith("https://"):
        return "/api/steam/proxy-image?url=" + quote(url, safe="")
    return url


def _showcase_art(snapshot: dict) -> str:
    """Prefer artwork the owner already chose for a public showcase."""
    showcases = snapshot.get("showcase_instances") or snapshot.get("showcases") or []
    ordered = sorted(
        (item for item in showcases[:20] if isinstance(item, dict)),
        key=lambda item: 0 if any(word in str(item.get("type") or "").lower() for word in ("artwork", "featured")) else 1,
    )
    for showcase in ordered:
        media = showcase.get("images") or showcase.get("media") or showcase.get("items") or []
        for item in media[:8] if isinstance(media, list) else []:
            value = item.get("image") or item.get("url") if isinstance(item, dict) else item
            proxied = _proxy_url(value)
            if proxied:
                return proxied
    return ""


def _archetype(signals: dict[str, float]) -> str:
    first, second = sorted(_SIGNAL_KEYS, key=signals.get, reverse=True)[:2]
    pair = {first, second}
    if pair == {"focus", "activity"}:
        return "pulse_runner"
    if "history" in pair and "collector" in pair:
        return "archive_keeper"
    if "variety" in pair:
        return "world_walker"
    if "mastery" in pair:
        return "apex_hunter"
    if "collector" in pair:
        return "library_core"
    return "signal_weaver"


def _facts(snapshot: dict, games: list[dict], recent: list[dict]) -> dict:
    played = [game for game in games if isinstance(game, dict)]
    total_minutes = sum(_number(game.get("playtime_forever")) for game in played)
    top = max(played, key=lambda game: _number(game.get("playtime_forever")), default={})
    created = int(_number(snapshot.get("timecreated")))
    years = 0.0
    if created:
        years = max(0.0, (time.time() - created) / 31_557_600)
    count = int(_number((snapshot.get("stats_map") or {}).get("games"), len(played)))
    count = max(count, len(played))
    return {
        "games": count,
        "hours": round(total_minutes / 60),
        "top_game": str(top.get("name") or "")[:100],
        "level": int(_number(snapshot.get("level"))),
        "account_years": round(years, 1),
        "recent_games": len(recent),
    }


def _signals(snapshot: dict, games: list[dict], recent: list[dict], facts: dict) -> dict[str, float]:
    minutes = [_number(game.get("playtime_forever")) for game in games if isinstance(game, dict)]
    positive = [value for value in minutes if value > 0]
    total = sum(positive)
    top_share = max(positive, default=0.0) / total if total else 0.0
    if len(positive) > 1 and total:
        entropy = -sum((value / total) * math.log(value / total) for value in positive)
        variety = entropy / math.log(len(positive))
    else:
        variety = _log_score(facts["games"], 250) * 0.65
    recent_minutes = sum(
        _number(game.get("playtime_2weeks")) for game in recent if isinstance(game, dict)
    )
    badges = len(snapshot.get("badges") or [])
    showcases = len(snapshot.get("showcase_instances") or [])
    content = sum(_number((snapshot.get("stats_map") or {}).get(key)) for key in (
        "screenshots", "videos", "workshop", "reviews", "guides", "artwork"
    ))
    history_source = facts["account_years"]
    history = _log_score(history_source, 16) if history_source else (
        _log_score(badges + showcases * 2, 120) * 0.72
    )
    mastery = _clamp(
        _log_score(max(positive, default=0.0) / 60, 2000) * 0.62
        + _log_score(facts["level"], 120) * 0.38
    )
    return {
        "focus": round(_clamp(top_share * 1.35 if total else 0.18), 4),
        "variety": round(_clamp(variety), 4),
        "mastery": round(mastery, 4),
        "history": round(_clamp(history), 4),
        "activity": round(_clamp(_log_score(recent_minutes / 60, 80) * 0.78 + _log_score(content, 2000) * 0.22), 4),
        "collector": round(_clamp(_log_score(facts["games"], 1000) * 0.78 + _log_score(badges, 250) * 0.22), 4),
    }


def _project(snapshot: dict, *, mode: str, seed: str, signals: dict[str, float], palette: list[str], archetype: str, variant: str = "cinematic") -> dict:
    width = _MODES[mode]
    avatar = _proxy_url(snapshot.get("avatar"))
    profile_background = _proxy_url(snapshot.get("background_movie") or snapshot.get("background"))
    showcase_background = _showcase_art(snapshot)
    background = showcase_background if variant == "cinematic" and showcase_background else profile_background or showcase_background
    is_video = bool(snapshot.get("background_movie") and background == profile_background)
    layout = {
        "cinematic": {"bg": .76, "effect": "streaks", "effect_opacity": .18, "dna_x": .24, "dna_y": .31, "dna_scale": .58, "dna_opacity": .72, "avatar": False, "name_x": .56, "name_y": .78, "name_size": 58, "signature_y": .85},
        "emblem": {"bg": .42, "effect": "stars", "effect_opacity": .30, "dna_x": .5, "dna_y": .43, "dna_scale": .88, "dna_opacity": 1, "avatar": True, "name_x": .5, "name_y": .79, "name_size": 48, "signature_y": .86},
        "pure": {"bg": .14, "effect": "matrix", "effect_opacity": .13, "dna_x": .5, "dna_y": .39, "dna_scale": 1.12, "dna_opacity": .94, "avatar": False, "name_x": .5, "name_y": .80, "name_size": 54, "signature_y": .87},
    }.get(variant) or {}
    layers: list[dict] = []
    if background:
        layers.append({
            "id": f"dna_background_{variant}", "type": "background", "name": "Profile artwork",
            "src": background, "mediaType": "video/webm" if is_video else "image/jpeg",
            "x": .5, "y": .5, "scale": 1, "rotation": 0, "opacity": layout["bg"],
            "visible": True, "animation": "none",
        })
    layers.extend([
        {
            "id": f"dna_atmosphere_{variant}", "type": "effect", "name": "DNA atmosphere",
            "effect": layout["effect"], "color": palette[1], "x": .5, "y": .5,
            "scale": 1.08, "rotation": -8 if variant == "cinematic" else 0,
            "opacity": layout["effect_opacity"], "visible": True, "animation": "none",
        },
        {
            "id": f"dna_core_{variant}", "type": "dna", "name": "Steam DNA Core",
            "seed": seed, "signals": signals, "palette": palette, "archetype": archetype,
            "x": layout["dna_x"], "y": layout["dna_y"], "scale": layout["dna_scale"],
            "rotation": 0, "opacity": layout["dna_opacity"],
            "visible": True, "animation": "none",
        },
    ])
    if avatar and layout["avatar"]:
        layers.append({
            "id": f"dna_avatar_{variant}", "type": "character", "name": "Steam avatar",
            "src": avatar, "mediaType": "image/jpeg", "x": layout["dna_x"], "y": layout["dna_y"],
            "scale": .23, "rotation": 0, "opacity": 1, "visible": True,
            "animation": "breathing", "chroma": False,
        })
    layers.extend([
        {
            "id": f"dna_name_{variant}", "type": "text", "name": "Profile name",
            "text": str(snapshot.get("name") or "STEAM DNA")[:80], "font": "Unbounded",
            "fontSize": layout["name_size"], "color": "#ffffff", "x": layout["name_x"], "y": layout["name_y"], "scale": 1,
            "rotation": 0, "opacity": 1, "visible": True, "animation": "none",
        },
        {
            "id": f"dna_signature_{variant}", "type": "text", "name": "DNA signature",
            "text": archetype.replace("_", " ").upper(), "font": "Consolas",
            "fontSize": 20, "color": palette[0], "x": layout["name_x"], "y": layout["signature_y"], "scale": 1,
            "rotation": 0, "opacity": .84, "visible": True, "animation": "none",
        },
        {
            "id": f"dna_frame_{variant}", "type": "frame", "name": "DNA frame",
            "color": palette[0], "frameWidth": 2 if variant == "pure" else 4, "x": .5, "y": .5,
            "scale": 1, "rotation": 0, "opacity": .64, "visible": True, "animation": "none",
        },
    ])
    return {
        "version": 1, "mode": mode, "width": width, "height": 1000,
        "background": "#050b12", "layers": layers,
    }


def build_profile_dna(snapshot: dict, *, user_id: int = 0, mode: str = "workshop") -> dict:
    """Build a bounded, reproducible DNA response and editable builder project."""
    if not isinstance(snapshot, dict) or not snapshot:
        raise ValueError("Steam profile snapshot is required")
    mode = mode if mode in _MODES else "workshop"
    games = [game for game in (snapshot.get("games") or [])[:500] if isinstance(game, dict)]
    recent = [game for game in (snapshot.get("recent_games") or [])[:20] if isinstance(game, dict)]
    identity = "|".join((
        str(snapshot.get("steamid") or user_id),
        str(snapshot.get("name") or ""),
        str(DNA_VERSION),
    ))
    seed = hashlib.sha256(identity.encode("utf-8", "replace")).hexdigest()[:16]
    facts = _facts(snapshot, games, recent)
    signals = _signals(snapshot, games, recent, facts)
    palette = _palette(seed, signals)
    archetype = _archetype(signals)
    variants = [
        {"id": variant, "project": _project(snapshot, mode=mode, seed=seed, signals=signals, palette=palette, archetype=archetype, variant=variant)}
        for variant in ("cinematic", "emblem", "pure")
    ]
    return {
        "version": DNA_VERSION,
        "seed": seed,
        "profile": {"name": str(snapshot.get("name") or "Steam profile")[:80], "avatar": _proxy_url(snapshot.get("avatar"))},
        "signals": signals,
        "facts": facts,
        "palette": palette,
        "archetype": archetype,
        "project": variants[0]["project"],
        "projects": variants,
    }
