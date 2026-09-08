"""Short-lived browser ownership for files stored under ``DATA/jobs``.

Preview and source-download jobs expose several related files.  A random URL is
not authorization by itself, so every such directory carries a one-way marker
bound to the browser session (or to the client IP for anonymous visitors).
"""
from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

from fastapi import Request

from smweb.core import _ip


_MARKER = ".owner"


def _browser_fingerprint(request: Request) -> str:
    token = (
        request.headers.get("x-session-token")
        or request.cookies.get("sm_session")
        or ""
    ).strip()
    material = f"session:{token}" if token else f"ip:{_ip(request)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def bind_job(directory: Path, request: Request) -> None:
    """Bind an existing job directory to the current browser."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / _MARKER).write_text(_browser_fingerprint(request), encoding="ascii")


def browser_owns_job(directory: Path, request: Request) -> bool:
    """Return ``True`` only for a directory explicitly bound to this browser."""
    try:
        stored = (directory / _MARKER).read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return False
    return bool(stored) and secrets.compare_digest(stored, _browser_fingerprint(request))
