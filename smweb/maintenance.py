"""Shared, file-backed maintenance notice controlled from the VPS.

The notice intentionally lives under DATA_DIR: all Uvicorn workers see the
same state, it survives container recreation, and no database migration or
application restart is needed. The public interface is deliberately small.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from smweb.core import DATA


STATE_FILE = Path(DATA) / "maintenance.json"


def get_state() -> dict:
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        raw = {}
    return {
        "enabled": bool(raw.get("enabled")),
        "message": str(raw.get("message") or "")[:240],
        "updated_at": float(raw.get("updated_at") or 0),
    }


def set_state(enabled: bool, message: str = "") -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "enabled": bool(enabled),
        "message": str(message or "").strip()[:240] if enabled else "",
        "updated_at": time.time(),
    }
    descriptor, temporary = tempfile.mkstemp(
        prefix="maintenance-", suffix=".json", dir=str(STATE_FILE.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        # `docker compose exec` runs operational commands as root, while the
        # web process deliberately runs as appuser. mkstemp defaults to 0600,
        # which made the freshly written state invisible to the application.
        # The notice contains no secrets, so make it readable across users.
        os.chmod(temporary, 0o644)
        os.replace(temporary, STATE_FILE)
    finally:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError:
            pass
    return state
