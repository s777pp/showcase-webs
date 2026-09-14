"""Paid-animation admission and network-only external-worker coordination.

Redis reservations and submission fences fail closed. An ambiguous response
never causes a second submission; only a confirmed terminal task frees the slot.
"""
from __future__ import annotations
import os
import time
from datetime import datetime, timezone
import redis_store as rs
from smweb import object_store
from smweb.animation_experiment import keys, PROTOCOL_VERSION, MAX_OUTPUT_BYTES
from smweb.modal_animation_client import AnimationClient, AnimationServiceError

ACTIVE_KEY = "sm:animation:active"
TTL = 7500
ADMIT = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
if tonumber(redis.call('GET', KEYS[2]) or '0') >= tonumber(ARGV[2]) then return -1 end
if tonumber(redis.call('GET', KEYS[3]) or '0') >= tonumber(ARGV[3]) then return -1 end
redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[4])
redis.call('INCR', KEYS[2]); redis.call('EXPIRE', KEYS[2], ARGV[5])
redis.call('INCR', KEYS[3]); redis.call('EXPIRE', KEYS[3], ARGV[5])
return 1
"""
RELEASE = "if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0"

def limit(name):
    try:
        return max(1, min(5, int(os.environ.get(name, "3"))))
    except ValueError:
        return 3

def reserve(jid, owner):
    r = rs.get_redis()
    if not r or not rs.redis_ok():
        raise RuntimeError("Shared job queue unavailable")
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y%m%d")
    expiry = 86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 60
    return int(r.eval(ADMIT, 3, ACTIVE_KEY, f"sm:animation:day:{day}:{owner}",
                      f"sm:animation:day:{day}:global", jid,
                      limit("ANIMATION_DAILY_USER_LIMIT"), limit("ANIMATION_DAILY_GLOBAL_LIMIT"), TTL, expiry))

def release(jid):
    r = rs.get_redis()
    if r:
        r.eval(RELEASE, 1, ACTIVE_KEY, jid)

def cancelled(jid):
    r = rs.get_redis()
    if not r:
        raise RuntimeError("Shared job queue unavailable")
    return bool(r.get(f"sm:animation:cancel:{jid}"))

def run(jid: str, job: dict) -> None:
    terminal = False
    source = ""
    submitted = False
    try:
        source, output = keys(jid)
        if job.get("source_key") != source or job.get("result_key") != output:
            raise ValueError("Invalid animation objects")
        r = rs.get_redis()
        if not r or not rs.redis_ok():
            raise RuntimeError("Shared job queue unavailable")
        if cancelled(jid):
            terminal = True
            rs.job_update(jid, status="cancelled", stage="cancelled", pct=100)
            return
        client = AnimationClient()
        if client.health().get("protocol_version") != PROTOCOL_VERSION:
            terminal = True
            raise ValueError("Animation deployment must be updated")
        # Persist before crossing the paid API boundary. Crash/replay polls only.
        first = r.set(f"sm:animation:submitted:{jid}", "1", nx=True, ex=86400)
        submitted = True
        if first:
            payload = {"request_id": jid,
                       "source_url": object_store.presigned_get_url(source, expires=7200),
                       "result_url": object_store.presigned_put_url(output, expires=7200),
                       "selection": job["selection"], "quality": job["quality"],
                       "intensity": job["intensity"], "matte": job["matte"]}
            rs.job_update(jid, stage="submit", pct=8)
            try:
                client.submit(payload)
            except Exception:
                # The server may have accepted it. Query the same id, never retry.
                rs.job_update(jid, stage="checking", pct=8)
        deadline = time.monotonic() + 7200
        missing_since = None
        while time.monotonic() < deadline:
            if cancelled(jid):
                answer = client.cancel(jid)
                if answer.get("status") == "already_finished":
                    pass
                else:
                    terminal = True
                    rs.job_update(jid, status="cancelled", stage="cancelled", pct=100)
                    return
            try:
                done, result = client.result(jid)
                missing_since = None
            except AnimationServiceError as exc:
                # GET is safe to repeat; a lost response must not trigger POST.
                if exc.status_code in {401, 403, 410}:
                    raise
                if exc.status_code == 404:
                    if missing_since is None:
                        missing_since = time.monotonic()
                    if time.monotonic() - missing_since > 120:
                        raise
                rs.job_update(jid, stage="checking", pct=8)
                time.sleep(5)
                continue
            if done:
                terminal = True
                if result.get("status") != "done":
                    rs.job_update(jid, status="error", stage="error", pct=100, error="generation_failed")
                    return
                size = int(result.get("bytes", 0))
                head = object_store.client().head_object(Bucket=object_store.PRIVATE_BUCKET, Key=output)
                if not 0 < size <= MAX_OUTPUT_BYTES or int(head["ContentLength"]) != size:
                    raise ValueError("Invalid animation output")
                rs.job_update(jid, status="done", stage="done", pct=100, result_size=size,
                              motion_low=(result.get("motion") or {}).get("status") == "low_motion",
                              width=int(result.get("width", 0)), height=int(result.get("height", 0)))
                return
            stage = result.get("stage", "processing")
            if stage not in {"starting", "download", "load_model", "generate", "isolate", "check_motion", "encode", "upload"}:
                stage = "processing"
            step, total = int(result.get("step", 0)), int(result.get("total", 0))
            pct = min(80, 20 + int(60 * step / total)) if total > 0 else 15
            rs.job_update(jid, status="running", stage=stage, pct=pct)
            time.sleep(5)
        # A timeout is not evidence that the GPU stopped. Stop once explicitly.
        client.cancel(jid)
        terminal = True
        rs.job_update(jid, status="error", stage="error", pct=100, error="timeout")
    except Exception as exc:
        print(f"[animation] {jid} {type(exc).__name__}", flush=True)
        if not submitted:
            terminal = True
        try:
            rs.job_update(jid, status="error", stage="error", pct=100,
                          error="generation_failed" if terminal else "outcome_unknown")
        except Exception:
            pass
    finally:
        if terminal:
            try:
                if source:
                    object_store.delete(source, public=False)
            except Exception as exc:
                print(f"[animation cleanup] {jid} {type(exc).__name__}", flush=True)
            try:
                release(jid)
            except Exception as exc:
                print(f"[animation release] {jid} {type(exc).__name__}", flush=True)
