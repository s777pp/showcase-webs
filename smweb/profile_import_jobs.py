"""Background job implementation for importing a public Steam profile."""
from __future__ import annotations

import auth_db
import redis_store as rs
import steam_catalog
from smweb.steam import _merge_steam_api


def run(job_id: str, job: dict) -> None:
    user_id = int(job.get("user_id") or 0)
    url = str(job.get("url") or "").strip()

    def progress(stage: str, pct: int) -> None:
        rs.job_update(job_id, status="running", stage=stage, pct=pct)

    progress("browser_connect", 8)
    result = steam_catalog.profile(url, progress=progress)
    if not result.get("ok"):
        rs.job_update(
            job_id, status="error", pct=100, stage="error",
            error=result.get("msg") or "Steam profile unavailable",
            error_code=result.get("code") or "steam_profile_unavailable",
            retry_after=result.get("retry_after"),
        )
        return

    progress("steam_enrich", 86)
    profile = _merge_steam_api(result["profile"])
    auth_db.save_steam_profile_snapshot(user_id, profile)
    payload = {
        "ok": True,
        "profile": profile,
        **{key: result[key] for key in ("cached", "stale", "warning_code", "retry_after") if key in result},
    }
    rs.job_update(job_id, status="done", pct=100, stage="done", result=payload)

