"""Network worker for Profile Doctor and Smart Design."""
from __future__ import annotations

import time

import redis_store as rs
import steam_catalog
from smweb.profile_insights import fallback_doctor, generate
from smweb.steam import _merge_steam_api


def run(job_id: str, job: dict) -> None:
    kind = str(job.get("insight_kind") or "doctor")

    def progress(stage: str, pct: int) -> None:
        rs.job_update(job_id, status="running", stage=stage, pct=pct)

    progress("profile", 8)
    imported = steam_catalog.profile(str(job.get("url") or ""), progress=progress)
    if not imported.get("ok"):
        rs.job_update(job_id, status="error", pct=100, stage="error",
                      error=imported.get("msg") or "Steam profile unavailable",
                      error_code=imported.get("code") or "steam_profile_unavailable")
        return
    profile = _merge_steam_api(imported["profile"])
    progress("analysis", 88)
    try:
        result = generate(kind, profile, str(job.get("language") or "en"), str(job.get("style") or "auto"))
    except Exception:
        if kind != "doctor":
            raise
        result = fallback_doctor(profile, str(job.get("language") or "en"))
        result["warning"] = "ai_unavailable"
    # A degraded baseline is useful, but must not consume a Free user's weekly
    # successful AI analysis. Pro history may retain it for diagnostics.
    if job.get("is_pro") or not result.get("warning"):
        rs.profile_insight_history_add(int(job.get("user_id") or 0), {
            "kind": kind, "created": time.time(), "expires_at": time.time() + 7 * 86400,
            "result": result,
        })
    rs.job_update(job_id, status="done", pct=100, stage="done", result=result)
