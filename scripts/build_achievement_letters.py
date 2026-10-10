"""Build our own catalogue of Steam games whose achievements are letters (the "Achievement letters" tab,
static/js/achievement-letters.js). Run it on a computer, not on the VPS (Steam rate-limits the server):

    py -3.14 scripts/build_achievement_letters.py            # STEAM_API_KEY from the environment or .env

Discovery: Steam store search for letter-ish words, then every game of the developers/publishers of the sets found
(letter games come in series). A game is a set when at least MIN_LETTERS different Latin letters are achievement names
("A", "a", "Letter A", "A!", "[A]" ...). Achievement icons and global percentages come from the official Steam Web API
(GetSchemaForGame, GetGlobalAchievementPercentagesForApp). Output: static/assets/achievements/letters.json, compact:
{"generated", "cdn", "colors", "sets": [{"appid", "name", "total", "letters": {"A": [[icon, percent, title, color], ...]},
"digits": {...}}]}. ``color`` is the icon's main colour (red / orange / yellow / green / blue / purple / pink / white /
black), measured on the icon itself, for the colour filter of the tab.
Icons are Steam's own CDN files (cdn + appid + "/" + icon + ".jpg"); nothing is copied from other sites.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

import colorsys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "assets" / "achievements" / "letters.json"
CDN = "https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/"
MIN_LETTERS = 20
MAX_VARIANTS = 12
WORKERS = 8
TERMS = [
    "alphabet", "letters", "letter", "abc", "a-z", "achievement", "achievements", "achievement hunter",
    "achievement collector", "achievement clicker", "100% achievements", "achievements spam", "typing", "font",
    "words", "word puzzle", "zup", "neon letters", "pixel letters", "alphabet puzzle", "alphabet shooter",
    "keyboard", "type", "letters puzzle", "puzzle achievements", "1000 achievements", "easy achievements",
    "relaxing achievements", "minimal puzzle", "the letters", "spelling",
]
PATTERNS = [
    re.compile(r"^\s*([A-Za-z])\s*[!?.:]*\s*$"),
    re.compile(r"^\s*(?:letter|буква)\s+([A-Za-z])\s*[!?.]*\s*$", re.I),
    re.compile(r"^\s*[\[\(\"'«]\s*([A-Za-z])\s*[\]\)\"'»]\s*$"),
]
DIGIT = re.compile(r"^\s*(?:number\s+)?([0-9])\s*[!?.]*\s*$", re.I)


def steam_key() -> str:
    key = os.environ.get("STEAM_API_KEY", "").strip()
    env = ROOT / ".env"
    if not key and env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("STEAM_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("STEAM_API_KEY is not set")
    return key


def fetch(url: str, tries: int = 4):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ShowcaseMaker catalogue"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as exc:                      # 429 / timeouts: back off and retry
            wait = 5 * (attempt + 1) * (6 if "429" in str(exc) else 1)
            print(f"  retry in {wait}s ({type(exc).__name__}: {str(exc)[:60]})", flush=True)
            time.sleep(wait)
    return None


def search(term: str = "", developer: str = "", publisher: str = "") -> set[int]:
    found: set[int] = set()
    for start in range(0, 300, 100):
        params = {"query": "", "start": start, "count": 100, "infinite": 1, "category1": 998}
        if term:
            params["term"] = term
        if developer:
            params["developer"] = developer
        if publisher:
            params["publisher"] = publisher
        raw = fetch("https://store.steampowered.com/search/results/?" + urllib.parse.urlencode(params))
        time.sleep(1.2)
        if not raw:
            break
        try:
            data = json.loads(raw)
        except ValueError:
            break
        ids = {int(x) for x in re.findall(r'data-ds-appid="(\d+)"', data.get("results_html", ""))}
        found |= ids
        if len(ids) < 100 or start + 100 >= int(data.get("total_count") or 0):
            break
    return found


COLORS = ("red", "orange", "yellow", "green", "blue", "purple", "pink", "white", "black")


def icon_color(appid: int, icon: str) -> str:
    """Main colour of an achievement icon: hue of the saturated pixels, else white / black by brightness."""
    from PIL import Image
    data = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(f"{CDN}{appid}/{icon}.jpg", headers={"User-Agent": "Mozilla/5.0 ShowcaseMaker catalogue"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            break
        except Exception:
            time.sleep(2 * (attempt + 1))
    if not data:
        return ""
    try:
        image = Image.open(BytesIO(data)).convert("RGB").resize((24, 24))
    except Exception:
        return ""
    coloured, bright, x, y, weight = 0, 0, 0.0, 0.0, 0.0
    import math
    raw = image.tobytes()
    pixels = [tuple(raw[i:i + 3]) for i in range(0, len(raw), 3)]
    for r, g, b in pixels:
        h, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if val > 0.82 and sat < 0.25:
            bright += 1
        if sat > 0.35 and val > 0.25:
            coloured += 1
            w = sat * val
            x += math.cos(h * 2 * math.pi) * w
            y += math.sin(h * 2 * math.pi) * w
            weight += w
    if coloured < len(pixels) * 0.12:
        return "white" if bright >= len(pixels) * 0.08 else "black"
    hue = (math.degrees(math.atan2(y, x)) + 360) % 360
    for limit, name in ((15, "red"), (40, "orange"), (70, "yellow"), (170, "green"), (250, "blue"), (290, "purple"),
                        (340, "pink"), (361, "red")):
        if hue < limit:
            return name
    return "red"


def letter_of(name: str) -> tuple[str, str] | None:
    for pattern in PATTERNS:
        m = pattern.match(name or "")
        if m:
            return "letter", m.group(1).upper()
    m = DIGIT.match(name or "")
    return ("digit", m.group(1)) if m else None


def check(appid: int, key: str) -> dict | None:
    raw = fetch(f"https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key={key}&appid={appid}&l=english")
    time.sleep(0.35)
    if not raw:
        return None
    try:
        game = json.loads(raw).get("game") or {}
    except ValueError:
        return None
    achievements = (game.get("availableGameStats") or {}).get("achievements") or []
    if len(achievements) < MIN_LETTERS:
        return None
    letters: dict[str, list] = {}
    digits: dict[str, list] = {}
    rows = []
    for a in achievements:
        hit = letter_of(a.get("displayName") or "")
        icon = re.search(r"/apps/\d+/([0-9a-f]{40})\.jpg", a.get("icon") or "")
        if hit and icon:
            rows.append((hit, icon.group(1), a.get("name"), (a.get("displayName") or "").strip()[:24]))
    if len({h[1] for h, *_ in rows if h[0] == "letter"}) < MIN_LETTERS:
        return None
    percents = {}
    raw = fetch(f"https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/?gameid={appid}")
    time.sleep(0.35)
    try:
        for item in json.loads(raw or "{}").get("achievementpercentages", {}).get("achievements", []):
            percents[item["name"]] = round(float(item["percent"]), 1)
    except (ValueError, TypeError, KeyError):
        pass
    for (kind, char), icon, api_name, title in rows:
        target = letters if kind == "letter" else digits
        variants = target.setdefault(char, [])
        if len(variants) < MAX_VARIANTS and all(v[0] != icon for v in variants):
            variants.append([icon, percents.get(api_name), title])
    return {"appid": appid, "name": html.unescape(game.get("gameName") or str(appid))[:80], "total": len(achievements),
            "letters": dict(sorted(letters.items())), "digits": dict(sorted(digits.items()))}


def details(appid: int) -> tuple[str, list[str], list[str]]:
    raw = fetch(f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english&filters=basic,developers,publishers")
    time.sleep(1.5)
    try:
        data = json.loads(raw or "{}").get(str(appid), {}).get("data") or {}
    except ValueError:
        data = {}
    return data.get("name") or "", data.get("developers") or [], data.get("publishers") or []


def main() -> None:
    key = steam_key()
    candidates: set[int] = set()
    for term in TERMS:
        ids = search(term=term)
        print(f"search {term!r}: {len(ids)}", flush=True)
        candidates |= ids
    checked: dict[int, dict | None] = {}
    people_done: set[str] = set()
    queue = sorted(candidates)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(WORKERS) as pool:
        while queue:
            batch = [a for a in dict.fromkeys(queue) if a not in checked]
            queue = []
            for index, (appid, found) in enumerate(zip(batch, pool.map(lambda a: check(a, key), batch)), 1):
                checked[appid] = found
                if index % 250 == 0:
                    print(f"  checked {index}/{len(batch)}", flush=True)
                if not found:
                    continue
                print(f"  set {appid} {found['name']!r}: {len(found['letters'])} letters", flush=True)
                name, developers, publishers = details(appid)
                if name:
                    found["name"] = name[:80]
                for who, kind in [(d, "developer") for d in developers] + [(p, "publisher") for p in publishers]:
                    if who in people_done:
                        continue
                    people_done.add(who)
                    more = search(**{kind: who})
                    print(f"    {kind} {who!r}: {len(more)} games", flush=True)
                    queue.extend(sorted(more - set(checked)))
    sets = sorted((s for s in checked.values() if s), key=lambda s: (-len(s["letters"]), s["name"].lower()))
    variants = [(s["appid"], v) for s in sets for group in ("letters", "digits") for vs in s[group].values() for v in vs]
    print(f"colours for {len(variants)} icons", flush=True)
    with ThreadPoolExecutor(WORKERS * 2) as pool:
        for index, ((appid, variant), color) in enumerate(zip(variants, pool.map(lambda av: icon_color(*av[0:1], av[1][0]),
                                                                                   variants)), 1):
            variant.append(color)
            if index % 1000 == 0:
                print(f"  colours {index}/{len(variants)}", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated": time.strftime("%Y-%m-%d"), "cdn": CDN, "colors": list(COLORS), "sets": sets},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    items = sum(len(v) for s in sets for v in list(s["letters"].values()) + list(s["digits"].values()))
    print(f"{len(sets)} sets, {items} icons, {len(checked)} games checked -> {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
