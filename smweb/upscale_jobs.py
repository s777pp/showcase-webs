"""External-worker runner for Modal GPU upscale jobs."""
from __future__ import annotations

import os
import time

import redis_store as rs
from smweb import object_store
from smweb import modal_upscale_client as modal_client


POLL_SECONDS = max(1.0, float(os.environ.get("MODAL_UPSCALE_POLL_SECONDS", "3")))
TIMEOUT_SECONDS = max(60, int(os.environ.get("MODAL_UPSCALE_TIMEOUT_SECONDS", "3600")))


def run(jid: str, job: dict) -> None:
    source_key = str(job.get("source_key") or "")
    result_key = str(job.get("result_key") or "")
    if not source_key or not result_key:
        raise ValueError("Upscale object keys are missing")
    if not modal_client.configured():
        raise RuntimeError("Modal upscale service is not configured")

    try:
        # URLs expire independently and authorize exactly one object each.
        source_url = object_store.presigned_get_url(source_key, expires=TIMEOUT_SECONDS + 900)
        result_url = object_store.presigned_put_url(result_key, expires=TIMEOUT_SECONDS + 900)
        payload = {
            "request_id": jid,
            "source_url": source_url,
            "result_url": result_url,
            "filename": str(job.get("filename") or "upload.bin")[:160],
            "media_kind": str(job.get("media_kind") or ""),
            "preset": str(job.get("preset") or "general"),
            "scale": int(job.get("scale") or 2),
        }
        rs.job_update(jid, status="running", pct=8, stage="gpu-submit")
        started = time.monotonic()
        call_id = modal_client.submit(payload)
        rs.job_update(jid, call_id=call_id, pct=12, stage="gpu-queued")
        while True:
            elapsed = time.monotonic() - started
            if elapsed > TIMEOUT_SECONDS:
                raise TimeoutError("GPU upscale timed out")
            done, result = modal_client.result(call_id)
            if done:
                if not result.get("ok"):
                    raise RuntimeError(str(result.get("error") or "GPU upscale failed")[:500])
                rs.job_update(
                    jid,
                    status="done",
                    pct=100,
                    stage="done",
                    content_type=str(result.get("content_type") or job.get("content_type") or "application/octet-stream"),
                    result_size=int(result.get("size") or 0),
                    frames=int(result.get("frames") or 0),
                    gpu_elapsed=float(result.get("elapsed") or 0),
                )
                return
            # Modal does not expose frame-level progress here. Move slowly so
            # users can still tell the queued job is alive without promising ETA.
            pct = min(92, 15 + int(elapsed / 8))
            rs.job_update(jid, pct=pct, stage="gpu-processing")
            time.sleep(POLL_SECONDS)
    except TimeoutError:
        rs.job_update(jid, status="error", pct=100, stage="error", error="GPU upscale timed out")
        return
    except Exception as exc:
        # HTTP client exceptions may embed a presigned R2 URL. Never copy the
        # raw exception into Redis where it would later be returned to a user.
        rs.job_update(
            jid, status="error", pct=100, stage="error",
            error=f"Upscale service failed ({type(exc).__name__})",
        )
        return
    finally:
        # The original is temporary; the output remains private until the
        # authenticated download route creates its own short-lived URL.
        object_store.delete(source_key, public=False)
