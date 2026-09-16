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
_local_insight_history: dict[int, list[dict]] = {}
_local_dna_cache: dict[str, tuple[float, dict]] = {}
_local_job_cache: dict[str, tuple[float, str]] = {}
_local_lock = threading.Lock()
_redis = None

# Probing a dead Redis costs socket_connect_timeout on EVERY call, and hot paths
# such as /api/process/start probe more than once. Cache the verdict briefly.
_OK_TTL = 5.0
_ok_cache = False
_ok_ts = 0.0
_last_error: Optional[str] = None

JOB_QUEUE = "sm:jobs:queue"
PROFILE_JOB_QUEUE = "sm:jobs:profile-queue"
UPSCALE_JOB_QUEUE = "sm:jobs:upscale-queue"
JOB_KEY = "sm:job:{}"
USER_JOBS_KEY = "sm:jobs:user:{}"
WORKER_BEAT_KEY = "sm:worker:beat"
JOB_TTL = max(3600, int(os.environ.get("JOB_HISTORY_TTL_SECONDS") or 86400))
TERMINAL = ("done", "error", "cancelled")
INSIGHT_HISTORY_KEY = "sm:profile-insights:{}"
DNA_CACHE_KEY = "sm:steam-dna-cache:{}"


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
    kind = str(data.get("kind") or "process")
    data.setdefault("kind", kind)
    data.setdefault("queue", queue_for_kind(kind))
    data.setdefault("created", time.time())
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
                if data.get("queue") == "profile":
                    queue = PROFILE_JOB_QUEUE
                elif data.get("queue") == "gpu":
                    queue = UPSCALE_JOB_QUEUE
                else:
                    queue = JOB_QUEUE
                pipe.lpush(queue, jid)
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
            # Keep terminal jobs in the per-user set for the unified job center.
            # The set and job keys expire together, so history remains bounded.
            if uk:
                r.sadd(USER_JOBS_KEY.format(uk), jid)
                r.expire(USER_JOBS_KEY.format(uk), JOB_TTL)
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


def profile_job_pop(timeout: int = 1) -> Optional[str]:
    """Pop a network-heavy Steam import independently of media encoding."""
    r = _r()
    if r:
        try:
            item = r.brpop(PROFILE_JOB_QUEUE, timeout=timeout)
            return item[1] if item else None
        except Exception as e:
            _note(e)
            time.sleep(1)
    return None


def upscale_job_pop(timeout: int = 1) -> Optional[str]:
    """Pop lightweight Modal coordination jobs without blocking CPU encoders."""
    r = _r()
    if r:
        try:
            item = r.brpop(UPSCALE_JOB_QUEUE, timeout=timeout)
            return item[1] if item else None
        except Exception as e:
            _note(e)
            time.sleep(1)
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


def job_find_active(user_key: str, kind: str, source_key: str = "") -> Optional[tuple[str, dict]]:
    """Find an equivalent active job without exposing another user's result."""
    if not user_key:
        return None
    r = _r()
    if r:
        try:
            for jid in r.smembers(USER_JOBS_KEY.format(user_key)):
                raw = r.get(JOB_KEY.format(jid))
                if not raw:
                    continue
                job = json.loads(raw) or {}
                if (job.get("status") in ("queued", "running") and
                        job.get("kind") == kind and
                        (not source_key or job.get("source_key") == source_key)):
                    return jid, job
            return None
        except Exception as e:
            _note(e)
    with _local_lock:
        for jid, job in _local_jobs.items():
            if (job.get("user_key") == user_key and job.get("status") in ("queued", "running") and
                    job.get("kind") == kind and
                    (not source_key or job.get("source_key") == source_key)):
                return jid, dict(job)
    return None


def queue_depth() -> int:
    r = _r()
    if not r:
        return 0
    try:
        return int(r.llen(JOB_QUEUE)) + int(r.llen(PROFILE_JOB_QUEUE)) + int(r.llen(UPSCALE_JOB_QUEUE))
    except Exception as e:
        _note(e)
        return 0


def queue_depths() -> dict[str, int]:
    r = _r()
    if not r:
        with _local_lock:
            values = {"media": 0, "profile": 0, "gpu": 0}
            for job in _local_jobs.values():
                if job.get("status") == "queued":
                    queue = str(job.get("queue") or queue_for_kind(str(job.get("kind") or "process")))
                    values[queue] = values.get(queue, 0) + 1
            return values
    try:
        return {
            "media": int(r.llen(JOB_QUEUE)),
            "profile": int(r.llen(PROFILE_JOB_QUEUE)),
            "gpu": int(r.llen(UPSCALE_JOB_QUEUE)),
        }
    except Exception as e:
        _note(e)
        return {"media": 0, "profile": 0, "gpu": 0}


def queue_for_kind(kind: str) -> str:
    kind = str(kind or "process")
    if kind in {"steam_profile_import", "profile_insight", "steam_dna"}:
        return "profile"
    if kind == "upscale":
        return "gpu"
    return "media"


def job_list_user(user_key: str, limit: int = 50) -> list[tuple[str, dict]]:
    """Recent jobs for one owner, including terminal results."""
    if not user_key:
        return []
    found: list[tuple[str, dict]] = []
    r = _r()
    if r:
        try:
            skey = USER_JOBS_KEY.format(user_key)
            stale = []
            for jid in r.smembers(skey):
                raw = r.get(JOB_KEY.format(jid))
                if not raw:
                    stale.append(jid)
                    continue
                found.append((jid, json.loads(raw) or {}))
            if stale:
                r.srem(skey, *stale)
        except Exception as e:
            _note(e)
            found = []
    if not r:
        with _local_lock:
            found = [(jid, dict(job)) for jid, job in _local_jobs.items() if job.get("user_key") == user_key]
    found.sort(key=lambda item: float(item[1].get("updated") or item[1].get("created") or 0), reverse=True)
    return found[:max(1, min(100, int(limit)))]


def job_cancel(jid: str) -> Optional[dict]:
    """Request cancellation and remove queued work before a worker can claim it."""
    job = job_get(jid)
    if not job:
        return None
    if job.get("status") in TERMINAL:
        return job
    status = "cancelled" if job.get("status") == "queued" else "running"
    job_update(jid, cancel_requested=True, status=status,
               stage="cancelled" if status == "cancelled" else "cancelling")
    r = _r()
    if r:
        try:
            pipe = r.pipeline()
            pipe.lrem(JOB_QUEUE, 0, jid)
            pipe.lrem(PROFILE_JOB_QUEUE, 0, jid)
            pipe.lrem(UPSCALE_JOB_QUEUE, 0, jid)
            pipe.execute()
        except Exception as e:
            _note(e)
    return job_get(jid)


def job_cache_get(cache_key: str) -> Optional[str]:
    if not cache_key:
        return None
    key = "sm:job-cache:{}".format(cache_key)
    r = _r()
    if r:
        try:
            return r.get(key) or None
        except Exception as e:
            _note(e)
    with _local_lock:
        item = _local_job_cache.get(cache_key)
        if not item or item[0] <= time.time():
            _local_job_cache.pop(cache_key, None)
            return None
        return item[1]


def job_cache_put(cache_key: str, jid: str, ttl: int | None = None) -> None:
    if not cache_key or not jid:
        return
    ttl = max(300, min(int(ttl or JOB_TTL), JOB_TTL))
    r = _r()
    if r:
        try:
            r.set("sm:job-cache:{}".format(cache_key), jid, ex=ttl)
            return
        except Exception as e:
            _note(e)
    with _local_lock:
        _local_job_cache[cache_key] = (time.time() + ttl, jid)


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
def rate_limit(key: str, limit: int, window_sec: int, *, fail_closed: bool = False) -> tuple[bool, int]:
    """Return (allowed, remaining). Paid callers may require a shared fail-closed cap."""
    now = int(time.time())
    r = _r()
    if fail_closed and configured() and not r:
        return False, 0
    if r:
        try:
            k = "sm:rl:{}:{}".format(key, now // window_sec)
            count = r.incr(k)
            if count == 1:
                r.expire(k, window_sec + 1)
            return count <= limit, max(0, limit - count)
        except Exception as e:
            _note(e)
            if fail_closed:
                return False, 0
    with _local_lock:
        bucket = "rl:{}".format(key)
        data = _local_usage.setdefault(bucket, {"t": now, "n": 0})
        if now - int(data.get("t") or 0) >= window_sec:
            data = {"t": now, "n": 0}
        data["n"] = int(data.get("n") or 0) + 1
        _local_usage[bucket] = data
        return data["n"] <= limit, max(0, limit - data["n"])


def profile_insight_history_add(user_id: int, item: dict, ttl: int = 7 * 86400) -> None:
    safe = json.dumps(item, ensure_ascii=False)
    r = _r()
    if r:
        try:
            key = INSIGHT_HISTORY_KEY.format(int(user_id))
            pipe = r.pipeline()
            pipe.lpush(key, safe)
            pipe.ltrim(key, 0, 9)
            pipe.expire(key, ttl)
            pipe.execute()
            return
        except Exception as e:
            _note(e)
    with _local_lock:
        rows = _local_insight_history.setdefault(int(user_id), [])
        rows.insert(0, dict(item))
        del rows[10:]


def profile_insight_history(user_id: int) -> list[dict]:
    r = _r()
    if r:
        try:
            return [json.loads(row) for row in r.lrange(INSIGHT_HISTORY_KEY.format(int(user_id)), 0, 9)]
        except Exception as e:
            _note(e)
    with _local_lock:
        return [dict(row) for row in _local_insight_history.get(int(user_id), [])]


def steam_dna_cache_get(key: str) -> Optional[dict]:
    """Return a detached cached DNA result, or None after its TTL expires."""
    safe_key = str(key)[:80]
    r = _r()
    if r:
        try:
            raw = r.get(DNA_CACHE_KEY.format(safe_key))
            return json.loads(raw) if raw else None
        except Exception as e:
            _note(e)
    now = time.time()
    with _local_lock:
        cached = _local_dna_cache.get(safe_key)
        if not cached:
            return None
        expires_at, value = cached
        if expires_at <= now:
            _local_dna_cache.pop(safe_key, None)
            return None
        return json.loads(json.dumps(value))


def steam_dna_cache_set(key: str, value: dict, ttl: int = 3600) -> None:
    safe_key = str(key)[:80]
    ttl = max(1, int(ttl))
    safe = json.dumps(value, ensure_ascii=False)
    r = _r()
    if r:
        try:
            r.set(DNA_CACHE_KEY.format(safe_key), safe, ex=ttl)
            return
        except Exception as e:
            _note(e)
    with _local_lock:
        _local_dna_cache[safe_key] = (time.time() + ttl, json.loads(safe))
