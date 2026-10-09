"""Live "now on the site" counter for the landing monitor (2026-10-07, owner request).

Every shell page (ss-shell.js) posts ``/api/presence`` once a minute while the tab is visible.
A visitor is the account id, the browser cookie or the IP (``core.owner_key``), stored only as a
short hash with the time of the last ping: a Redis sorted set ``sm:presence`` (shared by every
Uvicorn process), or a dict in this process without Redis. Anyone silent for ``WINDOW`` seconds
drops out; nothing is kept longer than that.
"""
from __future__ import annotations

import hashlib
import threading
import time

import redis_store as rs

KEY = "sm:presence"
WINDOW = 150  # a ping a minute, with room for one missed ping
_local: dict[str, float] = {}
_lock = threading.Lock()


def visitor_hash(owner_key: str) -> str:
    return hashlib.sha256(("presence:" + str(owner_key)).encode("utf-8")).hexdigest()[:20]


def ping(owner_key: str, now: float | None = None) -> int:
    """Record one visitor and return how many were seen within the window."""
    now = time.time() if now is None else now
    member = visitor_hash(owner_key)
    r = rs._r()
    if r:
        try:
            pipe = r.pipeline()
            pipe.zadd(KEY, {member: now})
            pipe.zremrangebyscore(KEY, "-inf", now - WINDOW)
            pipe.zcard(KEY)
            pipe.expire(KEY, WINDOW * 2)
            return int(pipe.execute()[2] or 0)
        except Exception as exc:
            rs._note(exc)
    with _lock:
        _local[member] = now
        for key in [k for k, seen in _local.items() if seen < now - WINDOW]:
            _local.pop(key, None)
        return len(_local)


def count(now: float | None = None) -> int:
    """Visitors seen within the window, without adding one (admin overview)."""
    now = time.time() if now is None else now
    r = rs._r()
    if r:
        try:
            return int(r.zcount(KEY, now - WINDOW, "+inf") or 0)
        except Exception as exc:
            rs._note(exc)
    with _lock:
        return sum(1 for seen in _local.values() if seen >= now - WINDOW)
