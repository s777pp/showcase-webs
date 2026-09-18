"""Small durable interface for settings that may change without a deploy.

The JSON file lives on DATA_DIR so every web worker and the worker container
see the same values. Reads are cached by file mtime; writes use atomic replace.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

import auth_db


STATE_FILE = Path(auth_db.DATA) / "runtime_settings.json"
DEFAULTS = {
    "registration_enabled": True,
    "process_enabled": True,
    "upscale_enabled": True,
    "builder_enabled": True,
    "gallery_submissions_enabled": True,
    "experimental_enabled": True,
    "free_daily_limit": max(1, int(os.environ.get("FREE_LIMIT") or 5)),
}
_BOOL_KEYS = {key for key, value in DEFAULTS.items() if isinstance(value, bool)}
_INT_RANGES = {"free_daily_limit": (1, 100)}
_lock = threading.RLock()
_cache: dict | None = None
_cache_mtime = -1.0


def _normalise(values: dict | None) -> dict:
    clean = dict(DEFAULTS)
    values = values if isinstance(values, dict) else {}
    for key in _BOOL_KEYS:
        if key in values:
            clean[key] = bool(values[key])
    for key, (low, high) in _INT_RANGES.items():
        if key in values:
            try:
                clean[key] = max(low, min(high, int(values[key])))
            except (TypeError, ValueError):
                pass
    return clean


def snapshot() -> dict:
    global _cache, _cache_mtime
    try:
        mtime = STATE_FILE.stat().st_mtime
    except OSError:
        mtime = -1.0
    with _lock:
        if _cache is not None and mtime == _cache_mtime:
            return dict(_cache)
        try:
            payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            payload = {}
        _cache = _normalise(payload)
        _cache_mtime = mtime
        return dict(_cache)


def update(values: dict) -> dict:
    global _cache, _cache_mtime
    with _lock:
        merged = snapshot()
        merged.update(values if isinstance(values, dict) else {})
        clean = _normalise(merged)
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix="settings-", suffix=".json", dir=str(STATE_FILE.parent))
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(clean, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o640)
            os.replace(temporary, STATE_FILE)
        finally:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass
        _cache = clean
        _cache_mtime = STATE_FILE.stat().st_mtime
        return dict(clean)


def flag(name: str) -> bool:
    return bool(snapshot().get(name, DEFAULTS.get(name, False)))


def integer(name: str, fallback: int) -> int:
    try:
        return int(snapshot().get(name, fallback))
    except (TypeError, ValueError):
        return int(fallback)
