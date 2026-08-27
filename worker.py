#!/usr/bin/env python3
"""Heavy job worker: FFmpeg / gifski / Pillow process jobs from Redis (or local queue).

  REDIS_URL=redis://redis:6379/0 python worker.py

Concurrency: MAX_JOB_WORKERS (default 2).
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


def _process_one(jid: str) -> None:
    import redis_store as rs
    import json

    job = rs.job_get(jid)
    if not job:
        return
    if job.get("status") not in ("queued", "running"):
        return
    rs.job_update(jid, status="running", pct=5, stage="prepare")
    try:
        # payload stored when enqueued from main
        from main import _run_process_job_from_payload

        _run_process_job_from_payload(jid, job)
    except Exception as e:
        traceback.print_exc()
        rs.job_update(jid, status="error", pct=100, stage="error", error=f"{type(e).__name__}: {e}")


def main() -> None:
    import redis_store as rs

    print(f"[worker] starting MAX_JOB_WORKERS={MAX_WORKERS} redis={rs.redis_ok()}", flush=True)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        inflight = set()
        while True:
            # reap done futures
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
            fut = pool.submit(_process_one, jid)
            inflight.add(fut)


if __name__ == "__main__":
    main()
