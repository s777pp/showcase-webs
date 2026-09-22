"""Queued remove.bg processing for still Builder source layers."""
from __future__ import annotations

from pathlib import Path

import redis_store as rs
from smweb import object_store
from smweb.core import DATA, _safe_data_path
from smweb import process_control
from smweb.remove_bg_client import RemoveBgError, remove_background


def _local_output_path(key: str) -> Path:
    base = Path(DATA).resolve()
    path = (base / key).resolve()
    if base not in path.parents:
        raise ValueError("Invalid Builder result path")
    return path


def _source_bytes(key: str) -> bytes:
    if object_store.configured():
        return object_store.get_bytes(key, public=False)
    path = _safe_data_path(key)
    if not path or not path.is_file():
        raise FileNotFoundError("Builder source not found")
    return path.read_bytes()


def _save(key: str, data: bytes, media_type: str) -> None:
    if object_store.configured():
        object_store.put_bytes(key, data, public=False, media_type=media_type)
        return
    path = _local_output_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def run(jid: str, job: dict) -> None:
    """Worker entry point. All paths come from the authenticated Builder API."""
    try:
        with process_control.job_context(jid):
            process_control.checkpoint(jid)
            rs.job_update(jid, status="running", pct=3, stage="load")
            source_key = str(job["source_key"])
            data = _source_bytes(source_key)
            process_control.checkpoint(jid)
            rs.job_update(jid, pct=25, stage="provider")
            result = remove_background(data, Path(source_key).name)
            out_suffix, media_type = ".png", "image/png"
            process_control.checkpoint(jid)
            rs.job_update(jid, pct=85, stage="store")
            output_name = str(job["output_stem"]) + out_suffix
            output_key = f"builder/{int(job['user_id'])}/{output_name}"
            _save(output_key, result, media_type)
            rs.job_update(jid, status="done", pct=100, stage="done", result={
                "url": f"/api/builder/assets/{output_name}", "media_type": media_type,
            })
    except process_control.JobCancelled:
        process_control.mark_cancelled(jid)
    except RemoveBgError as exc:
        rs.job_update(jid, status="error", pct=100, stage="error", error=str(exc), error_code=exc.code)
    except Exception:
        rs.job_update(jid, status="error", pct=100, stage="error",
                      error="AI background removal is temporarily unavailable",
                      error_code="provider_unavailable")
