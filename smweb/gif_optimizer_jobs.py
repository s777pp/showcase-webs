"""Background job of the GIF Optimizer tab (runs in the worker, or the embedded pool without one)."""
from __future__ import annotations

import shutil
import time
import traceback
from pathlib import Path

import redis_store as rs
from smweb import gif_optimizer, job_diagnostics, object_store, process_control


def run(jid: str, job: dict) -> None:
    root = Path(str(job["job_dir"]))
    source = Path(str(job["source_path"]))
    try:
        rs.job_update(jid, status="running", pct=10, stage="prepare")
        before = source.stat().st_size
        stem = str(job.get("stem") or "optimized")
        result = root / f"{stem}_optimized.gif"
        rs.job_update(jid, pct=25, stage="encode")
        if job.get("mode") == "auto":
            details = gif_optimizer.auto(source, result, job_id=jid)
        else:
            engine = gif_optimizer.manual(source, result, colors=int(job.get("colors") or 256),
                                          lossy=int(job.get("lossy") or 0), job_id=jid)
            details = {"engine": engine}
            # A preset can make an already well-packed GIF heavier: never hand back a bigger file.
            if result.stat().st_size >= before:
                shutil.copyfile(source, result)
                details["kept_original"] = True
        process_control.checkpoint(jid)
        after_info = gif_optimizer.info(result)
        result_key = ""
        if object_store.configured():
            rs.job_update(jid, pct=90, stage="upload")
            result_key = object_store.upload_file(result, f"jobs/{jid}/{result.name}", public=False)
        rs.job_update(jid, status="done", pct=100, stage="done", finished=time.time(),
                      result_path=str(result), result_key=result_key, filename=result.name,
                      media_type="image/gif", size_before=before, size_after=after_info["size"],
                      out_width=after_info["width"], out_height=after_info["height"],
                      out_frames=after_info["frames"], engine=details.get("engine", ""),
                      already_fits=bool(details.get("already_fits")),
                      kept_original=bool(details.get("kept_original")))
        cache_key = str(job.get("cache_key") or "")
        if cache_key:
            rs.job_cache_put(cache_key, jid)
        # The source stays for the before/after comparison until the regular job cleanup.
    except process_control.JobCancelled:
        process_control.mark_cancelled(jid)
        shutil.rmtree(root, ignore_errors=True)
    except Exception as exc:
        traceback.print_exc()
        user_error = str(exc) if isinstance(exc, ValueError) else "GIF optimization failed"
        rs.job_update(jid, status="error", pct=100, stage="error", error=user_error, finished=time.time(),
                      error_detail=job_diagnostics.scrub(f"{type(exc).__name__}: {exc}", root)[:500],
                      error_traces=[job_diagnostics.trace_text(exc, root)])
