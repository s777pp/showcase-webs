"""Redis helpers: jobs, quota, rate limit, access-code sessions.
Falls back to in-process dicts when REDIS_URL is unset (local/dev).
"""
from __future__ import annotations

import json
import os
import time
import threading
from typing import Any, Optional

REDIS_URL = (os.environ.get("REDIS_URL") or "").strip()

_local_jobs: dict[str, dict] = {}
_local_usage: dict[str, dict] = {}
_local_sessions: dict[str, dict] = {}
_local_lock = threading.Lock()
_redis = None


def get_redis():
    global _redis
    if not REDIS_URL:
        return None
    if _redis is not None:
        return _redis
    import redis
    _redis = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
    return _redis


def redis_ok() -> bool:
    try:
        r = get_redis()
        if not r:
            return False
        r.ping()
        return True
    except Exception:
        return False


# ---------- process jobs ----------
JOB_QUEUE = "sm:jobs:queue"
JOB_KEY = "sm:job:{}"


def job_create(jid: str, data: dict) -> None:
    data = dict(data)
    data.setdefault("status", "queued")
    data.setdefault("pct", 0)
    data.setdefault("updated", time.time())
    r = get_redis()
    if r:
        r.set(JOB_KEY.format(jid), json.dumps(data), ex=3600)
        r.lpush(JOB_QUEUE, jid)
        return
    with _local_lock:
        _local_jobs[jid] = data


def job_update(jid: str, **kw) -> None:
    r = get_redis()
    if r:
        raw = r.get(JOB_KEY.format(jid))
        if not raw:
            return
        data = json.loads(raw)
        data.update(kw)
        data["updated"] = time.time()
        r.set(JOB_KEY.format(jid), json.dumps(data), ex=3600)
        return
    with _local_lock:
        if jid in _local_jobs:
            _local_jobs[jid].update(kw)
            _local_jobs[jid]["updated"] = time.time()


def job_get(jid: str) -> Optional[dict]:
    r = get_redis()
    if r:
        raw = r.get(JOB_KEY.format(jid))
        return json.loads(raw) if raw else None
    with _local_lock:
        j = _local_jobs.get(jid)
        return dict(j) if j else None


def job_pop(timeout: int = 5) -> Optional[str]:
    """Blocking pop for worker. Local mode: non-blocking scan."""
    r = get_redis()
    if r:
        item = r.brpop(JOB_QUEUE, timeout=timeout)
        if not item:
            return None
        return item[1]
    # local: find first queued
    with _local_lock:
        for jid, j in list(_local_jobs.items()):
            if j.get("status") == "queued":
                j["status"] = "running"
                return jid
    time.sleep(min(timeout, 1))
    return None


def job_count_user(user_key: str, statuses: tuple[str, ...] = ("queued", "running")) -> int:
    """Best-effort count; Redis scans keys (ok at small scale)."""
    r = get_redis()
    n = 0
    if r:
        for key in r.scan_iter("sm:job:*", count=100):
            raw = r.get(key)
            if not raw:
                continue
            j = json.loads(raw)
            if j.get("user_key") == user_key and j.get("status") in statuses:
                n += 1
        return n
    with _local_lock:
        for j in _local_jobs.values():
            if j.get("user_key") == user_key and j.get("status") in statuses:
                n += 1
    return n


# ---------- quota (daily free tier) ----------
def quota_get(ip: str, day: str) -> int:
    r = get_redis()
    if r:
        v = r.get(f"sm:quota:{day}:{ip}")
        return int(v or 0)
    with _local_lock:
        u = _local_usage.get(ip) or {}
        if u.get("day") != day:
            return 0
        return int(u.get("count") or 0)


def quota_inc(ip: str, day: str, n: int = 1) -> int:
    r = get_redis()
    if r:
        key = f"sm:quota:{day}:{ip}"
        val = r.incrby(key, n)
        r.expire(key, 86400 * 2)
        return int(val)
    with _local_lock:
        u = _local_usage.get(ip) or {"count": 0, "day": day}
        if u.get("day") != day:
            u = {"count": 0, "day": day}
        u["count"] = int(u.get("count") or 0) + n
        _local_usage[ip] = u
        return u["count"]


# ---------- access-code sessions (non-user) ----------
def access_session_set(token: str, payload: dict, ttl: int = 86400 * 7) -> None:
    r = get_redis()
    if r:
        r.set(f"sm:asess:{token}", json.dumps(payload), ex=ttl)
        return
    with _local_lock:
        _local_sessions[token] = payload


def access_session_get(token: str) -> Optional[dict]:
    r = get_redis()
    if r:
        raw = r.get(f"sm:asess:{token}")
        return json.loads(raw) if raw else None
    with _local_lock:
        return _local_sessions.get(token)


def access_session_del(token: str) -> None:
    r = get_redis()
    if r:
        r.delete(f"sm:asess:{token}")
        return
    with _local_lock:
        _local_sessions.pop(token, None)


# ---------- rate limit ----------
def rate_limit(key: str, limit: int, window_sec: int) -> tuple[bool, int]:
    """Return (allowed, remaining)."""
    r = get_redis()
    now = int(time.time())
    if r:
        k = f"sm:rl:{key}:{now // window_sec}"
        count = r.incr(k)
        if count == 1:
            r.expire(k, window_sec + 1)
        return count <= limit, max(0, limit - count)
    # local sliding bucket (approximate)
    with _local_lock:
        bucket = f"rl:{key}"
        data = _local_usage.setdefault(bucket, {"t": now, "n": 0})
        if now - int(data.get("t") or 0) >= window_sec:
            data = {"t": now, "n": 0}
        data["n"] = int(data.get("n") or 0) + 1
        _local_usage[bucket] = data
        return data["n"] <= limit, max(0, limit - data["n"])
