"""Steam-ready sets from community gallery works (owner, 2026-10-08: "upload a showcase from the Gallery to Steam
automatically through the extension").

A gallery release is a ZIP with up to 120 PNG / JPG / GIF files in any layout: our own Process ZIPs (part_1..5,
featured_630, center_506 + side_100, full_* previews), Workshop Studio rows (row_N/part_1..5) or the author's own
names. ``find_sets`` picks the files that make one Steam upload for the work's showcase type, per folder;
``steam_readiness.apply_safe_fixes`` then gives them Steam's order, our names and HEX 21 (no pixel changes).

The parts are cut out of the ZIP once and kept under DATA/cache/gallery-steam/<id>-<hash>/ (7 days), so a 200 MB
archive in R2 is read once, not per file. The site hands the parts to SteamShowcase Helper (START_AUTO_UPLOAD,
static/js/gallery-steam.js), which uploads them on the user's own Steam session.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import time
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image

from smweb import core, object_store
from smweb.core import _safe_data_path
from smweb.steam_readiness import STEAM_FILE_LIMIT, Candidate, _AUXILIARY, apply_safe_fixes

KEEP_SECONDS = 7 * 24 * 3600
MAX_SETS = 12
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif"}
COUNTS = {"workshop": 5, "featured": 1, "split": 2}
_PART = re.compile(r"(?:^|[^a-z])part[_ -]?([1-5])(?:[^0-9]|$)", re.I)
_CENTER = re.compile(r"center|centre|506|left|main|big", re.I)
_SIDE = re.compile(r"side|100|right|small", re.I)


class NoSteamSet(ValueError):
    """The ZIP has no complete set for the work's showcase type. ``code``: no_set | too_large."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _natural(text: str) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def _width(data: bytes) -> int:
    try:
        with Image.open(io.BytesIO(data[:-1] + b";" if data[:6] in (b"GIF87a", b"GIF89a") and data.endswith(b"!") else data)) as image:
            return int(image.width)
    except Exception:
        return 0


def _sets_in_folder(files: list[tuple[str, bytes]], mode: str) -> list[list[tuple[str, bytes]]]:
    """Every complete set for ``mode`` among the files of one folder (already filtered to Steam-sized images)."""
    name = lambda item: PurePosixPath(item[0]).name
    if mode == "workshop":
        if len(files) == 5:
            return [files]
        numbered: dict[int, tuple[str, bytes]] = {}
        for item in files:
            match = _PART.search(name(item))
            if match and int(match.group(1)) not in numbered:
                numbered[int(match.group(1))] = item
        return [[numbered[n] for n in range(1, 6)]] if len(numbered) == 5 else []
    if mode == "featured":
        named = [item for item in files if "featured" in name(item).lower()]
        if named:
            return [[item] for item in named]
        if len(files) == 1:
            return [files]
        return [[item] for item in files if _width(item[1]) == 630]
    # split: one wide (506) and one narrow (100) part
    if len(files) == 2:
        return [files]
    centers = [item for item in files if _CENTER.search(name(item)) and not _SIDE.search(name(item))]
    sides = [item for item in files if _SIDE.search(name(item)) and not _CENTER.search(name(item))]
    if len(centers) == 1 and len(sides) == 1:
        return [[centers[0], sides[0]]]
    wide = [item for item in files if _width(item[1]) == 506]
    narrow = [item for item in files if _width(item[1]) == 100]
    return [[wide[0], narrow[0]]] if len(wide) == 1 and len(narrow) == 1 else []


def find_sets(entries: list[tuple[str, bytes]], mode: str, oversized: bool = False) -> list[dict]:
    """[{label, files: [Candidate, ...]}] in Steam order with Steam names and HEX 21; raises NoSteamSet.

    ``oversized`` says the archive also had images over Steam's 5 MB (they never reach ``entries``)."""
    if mode not in COUNTS:
        raise NoSteamSet("no_set")
    folders: dict[str, list[tuple[str, bytes]]] = {}
    for raw_name, data in entries:
        member = raw_name.replace("\\", "/")
        path = PurePosixPath(member)
        if path.suffix.lower() not in IMAGE_SUFFIXES or _AUXILIARY.search(member):
            continue
        if len(data) > STEAM_FILE_LIMIT:
            oversized = True
            continue
        folders.setdefault(str(path.parent) if str(path.parent) != "." else "", []).append((member, data))
    sets = []
    for folder in sorted(folders, key=_natural):
        files = sorted(folders[folder], key=lambda item: _natural(item[0]))
        for group in _sets_in_folder(files, mode):
            try:
                fixed_mode, fixed = apply_safe_fixes([Candidate(n, d) for n, d in group], mode)
            except ValueError:
                continue
            if fixed_mode == mode and len(fixed) == COUNTS[mode]:
                label = folder or ""
                if mode == "featured" and len(folders[folder]) > 1:
                    label = (folder + "/" if folder else "") + PurePosixPath(group[0][0]).name
                sets.append({"label": label, "files": fixed})
            if len(sets) >= MAX_SETS:
                return sets
    if not sets:
        raise NoSteamSet("too_large" if oversized else "no_set")
    return sets


def _archive_entries(row: dict) -> tuple[list[tuple[str, bytes]], bool]:
    """Images of the ZIP that fit Steam's limit, and whether any image was over it."""
    stored = str(row.get("archive_path") or "")
    path = _safe_data_path(stored)
    if path and path.is_file():
        source: object = str(path)
    elif stored and object_store.configured():
        source = io.BytesIO(object_store.get_bytes(object_store.key_from_stored(stored), public=False))
    else:
        raise FileNotFoundError("archive")
    out, oversized = [], False
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or PurePosixPath(entry.filename.replace("\\", "/")).suffix.lower() not in IMAGE_SUFFIXES:
                continue
            if entry.file_size > STEAM_FILE_LIMIT:
                oversized = True
                continue
            with archive.open(entry) as member:
                out.append((entry.filename, member.read(STEAM_FILE_LIMIT + 1)))
    return out, oversized


def _cache() -> Path:
    return Path(core.DATA) / "cache" / "gallery-steam"


def _folder(item_id: int, row: dict) -> Path:
    digest = hashlib.sha1(str(row.get("archive_path") or "").encode()).hexdigest()[:12]
    return _cache() / f"{int(item_id)}-{digest}"


def _prune() -> None:
    cache = _cache()
    if not cache.is_dir():
        return
    cutoff = time.time() - KEEP_SECONDS
    for child in cache.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            pass


def manifest(item_id: int, row: dict) -> dict:
    """{"mode", "sets": [{"label", "files": [{"name", "size", "width", "height", "animated"}]}]} (cached)."""
    folder = _folder(item_id, row)
    cached = folder / "manifest.json"
    if cached.is_file():
        try:
            return json.loads(cached.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    _prune()
    mode = str(row.get("mode") or "workshop")
    entries, oversized = _archive_entries(row)
    sets = find_sets(entries, mode, oversized)
    from smweb.steam_readiness import inspect_file
    work = folder.with_name(folder.name + f".tmp{time.time_ns()}")
    work.mkdir(parents=True, exist_ok=True)
    out = {"mode": mode, "sets": []}
    for s_index, item in enumerate(sets):
        files = []
        for f_index, candidate in enumerate(item["files"]):
            (work / f"{s_index}-{f_index}").write_bytes(candidate.data)
            info = inspect_file(candidate)
            files.append({"name": candidate.name, "size": len(candidate.data), "width": info["width"],
                          "height": info["height"], "animated": info["animated"]})
        out["sets"].append({"label": item["label"], "files": files})
    (work / "manifest.json").write_text(json.dumps(out), encoding="utf-8")
    try:
        work.rename(folder)
    except OSError:                       # a parallel request finished first: keep its copy
        shutil.rmtree(work, ignore_errors=True)
    return out


def part_path(item_id: int, row: dict, set_index: int, file_index: int) -> Path | None:
    path = _folder(item_id, row) / f"{int(set_index)}-{int(file_index)}"
    return path if path.is_file() else None
