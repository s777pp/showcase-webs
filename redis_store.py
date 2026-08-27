"""Redis helpers: jobs, quota, rate limit, access-code sessions.

Redis is OPTIONAL. When REDIS_URL is unset -- or the server is unreachable -- every
helper transparently degrades to in-process dicts, so the app keeps working.
Failures are recorded in last_error() instead of being swallowed, so /api/health
can report *why* Redis is down.
"""
from __future__ import annotations

import json
import os
import time
import threading
from typing import Optional

REDIS_URL = (os.environ.get("REDIS_URL") or "").strip()

_local_jobs: dict[str, dict] = {}
_local_usage: dict[str, dict] = {}
_local_sessions: dict[str, dict] = {}
_local_lock = threading.Lock()
_redis = None

# Probing a dead Redis costs socket_connect_timeout on EVERY call, and hot paths
# such as /api/process/start probe more than once. Cache the verdict briefly.
_OK_TTL = 5.0
_ok_cache = False
_ok_ts = 0.0
_last_error: Optional[str] = None

JOB_QUEUE = "sm:jobs:queue"
JOB_KEY = "sm:job:{}"
USER_JOBS_KEY = "sm:jobs:user:{}"
WORKER_BEAT_KEY = "sm:worker:beat"
JOB_TTL = 3600
TERMINAL = ("done", "error", "cancelled")


# ---------- connection ----------
def configured() -> bool:
    return bool(REDIS_URL)


def redis_host() -> str:
    """host:port from REDIS_URL, for diagnostics. Never exposes the password."""
    if not REDIS_URL:
        return ""
    try:
        from urllib.parse import urlparse
        u = urlparse(REDIS_URL)
        return "{}:{}".format(u.hostname or "?", u.port or 6379)
    except Exception:
        return "?"


def last_error() -> Optional[str]:
    return _last_error


def _note(e: Exception) -> None:
    """Record a failure and force reconnect + re-probe on the next call."""
    global _last_error, _ok_cache, _ok_ts, _redis
    _last_error = "{}: {}".format(type(e).__name__, e)
    _ok_cache = False
    _ok_ts = 0.0
    _redis = None


def get_redis():
    global _redis, _last_error
    if not REDIS_URL:
        return None
    if _redis is not None:
        return _redis
    try:
        import redis
    except Exception as e:
        _last_error = "redis package missing: {}: {}".format(type(e).__name__, e)
        return None
    try:
        _redis = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            # must stay above the longest blocking call (job_pop uses 3s)
            socket_timeout=10,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    except Exception as e:
        _last_error = "{}: {}".format(type(e).__name__, e)
        return None
    return _redis


def redis_ok() -> bool:
    """Cached PING. Reason for failure is available via last_error()."""
    global _ok_cache, _ok_ts, _last_error
    now = time.time()
    if now - _ok_ts < _OK_TTL:
        return _ok_cache
    _ok_ts = now
    if not REDIS_URL:
        _last_error = "REDIS_URL is not set"
        _ok_cache = False
        return False
    try:
        r = get_redis()
        if not r:
            _ok_cache = False
            return False
        r.ping()
        _last_error = None
        _ok_cache = True
    except Exception as e:
        _note(e)
        _ok_ts = now  # _note() reset it; keep the backoff window
    return _ok_cache


def _r():
    """Active client, or None when Redis is unavailable. Never raises."""
    return get_redis() if redis_ok() else None


# ---------- process jobs ----------
def job_create(jid: str, data: dict, enqueue: bool = True) -> None:
    """Store job metadata. enqueue=True also pushes onto the external-worker queue --
    pass False in embedded mode, otherwise entries pile up with nobody to pop them."""
    data = dict(data)
    data.setdefault("status", "queued")
    data.setdefault("pct", 0)
    data["updated"] = time.time()
    r = _r()
    if r:
        try:
            pipe = r.pipeline()
            pipe.set(JOB_KEY.format(jid), json.dumps(data), ex=JOB_TTL)
            uk = data.get("user_key")
            if uk:
                pipe.sadd(USER_JOBS_KEY.format(uk), jid)
                pipe.expire(USER_JOBS_KEY.format(uk), JOB_TTL)
            if enqueue:
                pipe.lpush(JOB_QUEUE, jid)
            pipe.execute()
            return
        except Exception as e:
            _note(e)
    with _local_lock:
        _local_jobs[jid] = data


def job_update(jid: str, **kw) -> None:
    """Upsert. The old version returned early when the key was missing, silently
    dropping progress written before job_create or after the TTL expired."""
    r = _r()
    if r:
        try:
            key = JOB_KEY.format(jid)
            raw = r.get(key)
            data = json.loads(raw) if raw else {}
            data.update(kw)
            data["updated"] = time.time()
            r.set(key, json.dumps(data), ex=JOB_TTL)
            uk = data.get("user_key")
            if uk and data.get("status") in TERMINAL:
                r.srem(USER_JOBS_KEY.format(uk), jid)
            return
        except Exception as e:
            _note(e)
    with _local_lock:
        j = _local_jobs.get(jid) or {}
        j.update(kw)
        j["updated"] = time.time()
        _local_jobs[jid] = j


def job_get(jid: str) -> Optional[dict]:
    r = _r()
    if r:
        try:
            raw = r.get(JOB_KEY.format(jid))
            if raw:
                return json.loads(raw)
        except Exception as e:
            _note(e)
    with _local_lock:
        j = _local_jobs.get(jid)
        return dict(j) if j else None


def job_pop(timeout: int = 3) -> Optional[str]:
    """Blocking pop for the external worker. Local mode: non-blocking scan."""
    r = _r()
    if r:
        try:
            item = r.brpop(JOB_QUEUE, timeout=timeout)
            return item[1] if item else None
        except Exception as e:
            _note(e)
            time.sleep(1)
            return None
    with _local_lock:
        for jid, j in list(_local_jobs.items()):
            if j.get("status") == "queued":
                j["status"] = "running"
                return jid
    time.sleep(min(timeout, 1))
    return None


def job_count_user(user_key: str, statuses: tuple[str, ...] = ("queued", "running")) -> int:
    """Active jobs for one user. Backed by a per-user set -- the old full
    scan_iter over sm:job:* plus a GET each was O(all jobs) per request."""
    if not user_key:
        return 0
    r = _r()
    n = 0
    if r:
        try:
            skey = USER_JOBS_KEY.format(user_key)
            stale = []
            for jid in r.smembers(skey):
                raw = r.get(JOB_KEY.format(jid))
                if not raw:
                    stale.append(jid)
                    continue
                st = (json.loads(raw) or {}).get("status")
                if st in statuses:
                    n += 1
                elif st in TERMINAL:
                    stale.append(jid)
            if stale:
                r.srem(skey, *stale)
            return n
        except Exception as e:
            _note(e)
            n = 0
    with _local_lock:
        for j in _local_jobs.values():
            if j.get("user_key") == user_key and j.get("status") in statuses:
                n += 1
    return n


def queue_depth() -> int:
    r = _r()
    if not r:
        return 0
    try:
        return int(r.llen(JOB_QUEUE))
    except Exception as e:
        _note(e)
        return 0


# ---------- external worker liveness ----------
def worker_beat(ttl: int = 30) -> None:
    """Called by worker.py each loop. Absence of the key means no worker is running,
    which lets the API fall back to embedded processing instead of queueing forever."""
    r = _r()
    if not r:
        return
    try:
        r.set(WORKER_BEAT_KEY, str(int(time.time())), ex=ttl)
    except Exception as e:
        _note(e)


def worker_alive() -> bool:
    r = _r()
    if not r:
        return False
    try:
        return bool(r.exists(WORKER_BEAT_KEY))
    except Exception as e:
        _note(e)
        return False


# ---------- quota (daily free tier) ----------
def quota_get(ip: str, day: str) -> int:
    r = _r()
    if r:
        try:
            return int(r.get("sm:quota:{}:{}".format(day, ip)) or 0)
        except Exception as e:
            _note(e)
    with _local_lock:
        u = _local_usage.get(ip) or {}
        if u.get("day") != day:
            return 0
        return int(u.get("count") or 0)


def quota_inc(ip: str, day: str, n: int = 1) -> int:
    r = _r()
    if r:
        try:
            key = "sm:quota:{}:{}".format(day, ip)
            val = r.incrby(key, n)
            r.expire(key, 86400 * 2)
            return int(val)
        except Exception as e:
            _note(e)
    with _local_lock:
        u = _local_usage.get(ip) or {"count": 0, "day": day}
        if u.get("day") != day:
            u = {"count": 0, "day": day}
        u["count"] = int(u.get("count") or 0) + n
        _local_usage[ip] = u
        return u["count"]


# ---------- access-code sessions (non-user) ----------
def access_session_set(token: str, payload: dict, ttl: int = 86400 * 7) -> None:
    r = _r()
    if r:
        try:
            r.set("sm:asess:{}".format(token), json.dumps(payload), ex=ttl)
            return
        except Exception as e:
            _note(e)
    with _local_lock:
        _local_sessions[token] = payload


def access_session_get(token: str) -> Optional[dict]:
    r = _r()
    if r:
        try:
            raw = r.get("sm:asess:{}".format(token))
            if raw:
                return json.loads(raw)
        except Exception as e:
            _note(e)
    with _local_lock:
        return _local_sessions.get(token)


def access_session_del(token: str) -> None:
    r = _r()
    if r:
        try:
            r.delete("sm:asess:{}".format(token))
            return
        except Exception as e:
            _note(e)
    with _local_lock:
        _local_sessions.pop(token, None)


# ---------- rate limit ----------
def rate_limit(key: str, limit: int, window_sec: int) -> tuple[bool, int]:
    """Return (allowed, remaining). Fails open when Redis is down."""
    now = int(time.time())
    r = _r()
    if r:
        try:
            k = "sm:rl:{}:{}".format(key, now // window_sec)
            count = r.incr(k)
            if count == 1:
                r.expire(k, window_sec + 1)
            return count <= limit, max(0, limit - count)
        except Exception as e:
            _note(e)
    with _local_lock:
        bucket = "rl:{}".format(key)
        data = _local_usage.setdefault(bucket, {"t": now, "n": 0})
        if now - int(data.get("t") or 0) >= window_sec:
            data = {"t": now, "n": 0}
        data["n"] = int(data.get("n") or 0) + 1
        _local_usage[bucket] = data
        return data["n"] <= limit, max(0, limit - data["n"])
