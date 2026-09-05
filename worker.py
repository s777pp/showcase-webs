#!/usr/bin/env python3
"""Heavy job worker: FFmpeg / gifski / Pillow process jobs from the Redis queue.

  REDIS_URL=redis://redis:6379/0 WORKER_MODE=external python worker.py

Only needed when the API runs with WORKER_MODE=external (see docker-compose.yml).
In the default embedded mode the API processes jobs in its own thread pool and
this file is not used at all.

Concurrency: MAX_JOB_WORKERS (default 2).

IMPORTANT: this process must share the /data volume with the API, otherwise the
API cannot serve the resulting ZIP. On Railway a volume cannot be mounted into
two services -- use embedded mode there.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ensure app root on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

MAX_WORKERS = int(os.environ.get("MAX_JOB_WORKERS", "2"))
BEAT_TTL = 30
BEAT_EVERY = 10.0


def _process_one(jid: str) -> None:
    import redis_store as rs

    job = rs.job_get(jid)
    if not job:
        print(f"[worker] {jid} vanished before pickup", flush=True)
        return
    if job.get("status") not in ("queued", "running"):
        return
    rs.job_update(jid, status="running", pct=5, stage="prepare")
    try:
        if job.get("kind") == "steam_profile_import":
            from smweb.profile_import_jobs import run
            run(jid, job)
            return
        if job.get("kind") == "compose":
            from smweb.compose_jobs import run
            run(jid, job)
            return
        from main import _run_process_job_from_payload

        _run_process_job_from_payload(jid, job)
    except Exception as e:
        traceback.print_exc()
        rs.job_update(jid, status="error", pct=100, stage="error", error=f"{type(e).__name__}: {e}")


def main() -> None:
    import redis_store as rs

    if not rs.configured():
        print("[worker] REDIS_URL is not set — nothing to consume. Exiting.", flush=True)
        return
    if not rs.redis_ok():
        print(f"[worker] Redis unreachable at {rs.redis_host()}: {rs.last_error()}", flush=True)
        print("[worker] retrying...", flush=True)

    print(f"[worker] starting MAX_JOB_WORKERS={MAX_WORKERS} redis={rs.redis_host()}", flush=True)
    last_beat = 0.0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        inflight = set()
        while True:
            now = time.time()
            # Publish liveness so the API knows an external worker exists; without
            # this it falls back to embedded processing rather than queueing forever.
            if now - last_beat >= BEAT_EVERY:
                rs.worker_beat(ttl=BEAT_TTL)
                last_beat = now

            done = {f for f in inflight if f.done()}
            for f in done:
                try:
                    f.result()
                except Exception:
                    traceback.print_exc()
            inflight -= done

            if len(inflight) >= MAX_WORKERS:
                time.sleep(0.3)
                continue
            jid = rs.job_pop(timeout=3)
            if not jid:
                continue
            print(f"[worker] pick {jid}", flush=True)
            inflight.add(pool.submit(_process_one, jid))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[worker] stopped", flush=True)
