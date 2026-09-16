"""Reusable, resumable source media stored on the shared data volume.

The module deliberately exposes a small interface: create an upload, append a
chunk, complete it, then resolve/list assets for one browser owner.  Routers and
tools do not need to know where partial files or metadata live.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import mimetypes
import os
import re
import secrets
import threading
import time
from pathlib import Path

from fastapi import Request

from smweb.core import DATA, MAX_UPLOAD_MB, _auth_user, _ip


ROOT = Path(DATA) / "media-assets"
CHUNK_SIZE = max(256 * 1024, int(os.environ.get("ASSET_CHUNK_SIZE", str(2 * 1024 * 1024))))
ASSET_TTL = max(3600, int(os.environ.get("ASSET_TTL_SECONDS", str(7 * 86400))))
PENDING_TTL = max(900, int(os.environ.get("ASSET_PENDING_TTL_SECONDS", str(86400))))
_LOCK = threading.RLock()
_UPLOAD_LOCKS: dict[str, asyncio.Lock] = {}
_CLEANUP_TS = 0.0
_ID = re.compile(r"^[a-f0-9]{32}$")


def owner_key(request: Request) -> str:
    """Stable owner shared by assets and jobs without exposing session tokens."""
    try:
        user = _auth_user(request)
    except Exception:
        user = None
    return f"user:{int(user['id'])}" if user and user.get("id") else f"ip:{_ip(request)}"


def _owner_hash(owner: str) -> str:
    return hashlib.sha256(owner.encode("utf-8")).hexdigest()


def _safe_name(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(str(name or "media")).name).strip(" .")
    return clean[:120] or "media"


def _dir(identifier: str) -> Path:
    if not _ID.fullmatch(str(identifier or "")):
        raise ValueError("Invalid asset identifier")
    return ROOT / identifier


def _read(identifier: str) -> dict | None:
    try:
        value = json.loads((_dir(identifier) / "meta.json").read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _write(identifier: str, value: dict) -> None:
    root = _dir(identifier)
    root.mkdir(parents=True, exist_ok=True)
    temp = root / "meta.tmp"
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temp.replace(root / "meta.json")


def create_upload(owner: str, *, name: str, size: int, media_type: str = "") -> dict:
    maybe_cleanup()
    size = int(size or 0)
    maximum = MAX_UPLOAD_MB * 1024 * 1024
    if size <= 0 or size > maximum:
        raise ValueError(f"File size must be between 1 byte and {MAX_UPLOAD_MB} MB")
    ROOT.mkdir(parents=True, exist_ok=True)
    identifier = secrets.token_hex(16)
    now = time.time()
    meta = {
        "id": identifier,
        "name": _safe_name(name),
        "size": size,
        "media_type": str(media_type or mimetypes.guess_type(name)[0] or "application/octet-stream")[:120],
        "owner": _owner_hash(owner),
        "offset": 0,
        "status": "uploading",
        "created": now,
        "updated": now,
        "expires": now + PENDING_TTL,
    }
    with _LOCK:
        _write(identifier, meta)
        (_dir(identifier) / "upload.part").touch()
    return public(meta)


def upload_status(identifier: str, owner: str) -> dict | None:
    meta = _read(identifier)
    if not meta or meta.get("owner") != _owner_hash(owner):
        return None
    return public(meta)


def _upload_lock(identifier: str) -> asyncio.Lock:
    with _LOCK:
        return _UPLOAD_LOCKS.setdefault(identifier, asyncio.Lock())


async def append_async(identifier: str, owner: str, expected_offset: int, chunks) -> dict:
    # Serialise PATCH requests per upload so two browser retries cannot both
    # append from the same offset and silently corrupt the source.
    async with _upload_lock(identifier):
        return await _append_locked(identifier, owner, expected_offset, chunks)


async def _append_locked(identifier: str, owner: str, expected_offset: int, chunks) -> dict:
    maximum = MAX_UPLOAD_MB * 1024 * 1024
    with _LOCK:
        meta = _read(identifier)
        if not meta or meta.get("owner") != _owner_hash(owner):
            raise FileNotFoundError("Upload not found")
        if meta.get("status") != "uploading":
            raise ValueError("Upload is already complete")
        offset = int(meta.get("offset") or 0)
        if int(expected_offset) != offset:
            raise OffsetError(offset)
        path = _dir(identifier) / "upload.part"
    written = 0
    # Resume from the committed metadata offset. If a previous connection died
    # after writing bytes but before committing metadata, discard that tail.
    with path.open("r+b") as destination:
        destination.seek(offset)
        destination.truncate()
        async for chunk in chunks:
            if not chunk:
                continue
            written += len(chunk)
            if offset + written > min(maximum, int(meta["size"])):
                raise ValueError("Chunk exceeds declared file size")
            destination.write(chunk)
    with _LOCK:
        current = _read(identifier)
        if not current or current.get("owner") != _owner_hash(owner):
            raise FileNotFoundError("Upload not found")
        current["offset"] = offset + written
        current["updated"] = time.time()
        _write(identifier, current)
    return public(current)


def complete(identifier: str, owner: str, expected_sha256: str = "") -> dict:
    with _LOCK:
        meta = _read(identifier)
        if not meta or meta.get("owner") != _owner_hash(owner):
            raise FileNotFoundError("Upload not found")
        if meta.get("status") == "ready":
            return public(meta)
        if int(meta.get("offset") or 0) != int(meta.get("size") or 0):
            raise ValueError("Upload is incomplete")
        root = _dir(identifier)
        partial = root / "upload.part"
        digest = hashlib.sha256()
        with partial.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        expected = str(expected_sha256 or "").strip().lower()
        if expected and not secrets.compare_digest(expected, actual):
            raise ValueError("File checksum does not match")
        source_path = root / ("source" + (Path(meta["name"]).suffix.lower() or ".bin"))
        partial.replace(source_path)
        now = time.time()
        meta.update({"status": "ready", "sha256": actual, "path": str(source_path), "updated": now,
                     "expires": now + ASSET_TTL})
        _write(identifier, meta)
        return public(meta)


def resolve(identifier: str, owner: str) -> tuple[dict, Path] | None:
    meta = _read(identifier)
    if not meta or meta.get("owner") != _owner_hash(owner) or meta.get("status") != "ready":
        return None
    path = Path(str(meta.get("path") or ""))
    try:
        path.resolve().relative_to(_dir(identifier).resolve())
    except (OSError, ValueError):
        return None
    return (public(meta), path) if path.is_file() else None


def list_assets(owner: str, limit: int = 40) -> list[dict]:
    maybe_cleanup()
    if not ROOT.is_dir():
        return []
    wanted = _owner_hash(owner)
    found = []
    for entry in ROOT.iterdir():
        meta = _read(entry.name) if entry.is_dir() else None
        if meta and meta.get("owner") == wanted and meta.get("status") == "ready":
            found.append(public(meta))
    return sorted(found, key=lambda item: float(item.get("updated") or 0), reverse=True)[:max(1, min(100, int(limit)))]


def delete_asset(identifier: str, owner: str) -> bool:
    import shutil
    meta = _read(identifier)
    if not meta or meta.get("owner") != _owner_hash(owner):
        return False
    shutil.rmtree(_dir(identifier), ignore_errors=True)
    return True


def cleanup(now: float | None = None) -> int:
    import shutil
    now = float(now or time.time())
    removed = 0
    if not ROOT.is_dir():
        return 0
    for entry in ROOT.iterdir():
        meta = _read(entry.name) if entry.is_dir() else None
        if not meta or float(meta.get("expires") or 0) <= now:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
    return removed


def maybe_cleanup(interval: int = 3600) -> None:
    """Bound disk growth without putting a directory scan on every request."""
    global _CLEANUP_TS
    now = time.time()
    with _LOCK:
        if now - _CLEANUP_TS < max(60, int(interval)):
            return
        _CLEANUP_TS = now
    cleanup(now)


def public(meta: dict) -> dict:
    return {key: meta.get(key) for key in (
        "id", "name", "size", "media_type", "offset", "status", "sha256", "created", "updated", "expires"
    )}


class OffsetError(ValueError):
    def __init__(self, offset: int):
        super().__init__("Upload offset does not match")
        self.offset = int(offset)
