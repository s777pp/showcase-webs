"""Colours of Steam emoticons for the "Picture from emoticons" tool (static/js/infobox-emoji.js).

The browser cannot read the pixels of Steam's emoticon images (no CORS), so the server does it once per emoticon:
the 18x18 picture Steam shows in profile texts is split into a 3x3 grid and every cell keeps its alpha-weighted
mean colour plus its coverage ([r, g, b, a], 0-255). The browser composites that on the Info box background and
matches picture cells against it. Emoticon pictures never change under the same name, so results are cached on disk
for good (one small JSON file per name, written atomically, safe for several app workers). A name Steam does not
know (404) is remembered for a day, then asked again.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image

from smweb.core import DATA

_LOG = logging.getLogger("sm.emoticons")

CDN = "https://community.fastly.steamstatic.com/economy/emoticon/"
NAME = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
GRID = 3
SIZE = 18
MAX_NAMES = 400           # per request; the browser sends the list in batches
MAX_BYTES = 512 * 1024
MISSING_TTL = 86400
WORKERS = 12
_CACHE = Path(DATA) / "cache" / "emoticons"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def clean_names(raw) -> list[str]:
    """Unique valid names in their first-seen order (colons and Steam's U+02D0 delimiters stripped)."""
    out, seen = [], set()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, str):
            continue
        name = item.strip().strip(":ː")
        if NAME.match(name) and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def grid_colors(data: bytes) -> list[list[int]]:
    """3x3 cells of [r, g, b, a]: alpha-weighted mean colour and mean coverage of the picture Steam shows."""
    with Image.open(io.BytesIO(data)) as image:
        image.seek(0)
        picture = image.convert("RGBA")
    if picture.size != (SIZE, SIZE):
        picture = picture.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    pixels = picture.load()
    step = SIZE // GRID
    cells = []
    for gy in range(GRID):
        for gx in range(GRID):
            r = g = b = weight = 0.0
            for y in range(gy * step, (gy + 1) * step):
                for x in range(gx * step, (gx + 1) * step):
                    pr, pg, pb, pa = pixels[x, y]
                    a = pa / 255.0
                    r += pr * a
                    g += pg * a
                    b += pb * a
                    weight += a
            count = step * step
            if weight > 0:
                cells.append([round(r / weight), round(g / weight), round(b / weight), round(255 * weight / count)])
            else:
                cells.append([0, 0, 0, 0])
    return cells


def _path(name: str) -> Path:
    return _CACHE / f"{name}.json"


def _cached(name: str):
    """(hit, value): value is the cell list, or None for a name Steam does not have."""
    try:
        record = json.loads(_path(name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, None
    if record.get("missing"):
        if time.time() - float(record.get("t") or 0) < MISSING_TTL:
            return True, None
        return False, None
    cells = record.get("c")
    if isinstance(cells, list) and len(cells) == GRID * GRID:
        return True, cells
    return False, None


def _store(name: str, record: dict) -> None:
    try:
        _CACHE.mkdir(parents=True, exist_ok=True)
        target = _path(name)
        tmp = target.with_name(f"{target.name}.{uuid.uuid4().hex[:8]}.tmp")
        tmp.write_text(json.dumps(record, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        _LOG.debug("emoticon cache write failed", exc_info=True)


def _download(name: str):
    """('ok', cells) | ('missing', None) | ('error', None). Errors are not cached: the next request tries again."""
    try:
        response = requests.get(CDN + name, timeout=8, headers={"User-Agent": _UA}, stream=True)
        if response.status_code == 404:
            return "missing", None
        if response.status_code != 200 or not str(response.headers.get("Content-Type", "")).startswith("image/"):
            return "error", None
        data = response.raw.read(MAX_BYTES + 1, decode_content=True)
        if len(data) > MAX_BYTES:
            return "error", None
        return "ok", grid_colors(data)
    except Exception:
        _LOG.debug("emoticon download failed: %s", name, exc_info=True)
        return "error", None


def colors(names: list[str]) -> dict:
    """{"items": {name: cells}, "missing": [names Steam does not have], "failed": [names to retry later]}."""
    items, missing, todo = {}, [], []
    for name in names[:MAX_NAMES]:
        hit, value = _cached(name)
        if not hit:
            todo.append(name)
        elif value is None:
            missing.append(name)
        else:
            items[name] = value
    failed = []
    if todo:
        with ThreadPoolExecutor(max_workers=min(WORKERS, len(todo))) as pool:
            for name, (status, value) in zip(todo, pool.map(_download, todo)):
                if status == "ok":
                    items[name] = value
                    _store(name, {"c": value})
                elif status == "missing":
                    missing.append(name)
                    _store(name, {"missing": True, "t": time.time()})
                else:
                    failed.append(name)
    return {"items": items, "missing": missing, "failed": failed}
