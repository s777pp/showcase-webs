"""Background orchestration for live public-profile Steam DNA analysis."""
from __future__ import annotations

import os

import redis_store as rs
import steam_catalog
from smweb import steam_dna_ai
from smweb.steam import _merge_steam_api
from smweb.steam_dna import build_profile_dna


def _cache_ttl() -> int:
    try:
        return max(300, min(86400, int(os.environ.get("STEAM_DNA_CACHE_SEC", "3600"))))
    except ValueError:
        return 3600


def run(job_id: str, job: dict) -> None:
    """Fetch a current profile without saving it to the user's imported snapshot."""
    def progress(stage: str, pct: int) -> None:
        rs.job_update(job_id, status="running", pct=max(5, min(98, int(pct))), stage=stage)

    progress("profile_open", 7)
    try:
        imported = steam_catalog.profile(str(job.get("url") or ""), progress=progress)
    except Exception:
        rs.job_update(
            job_id, status="error", pct=100, stage="error",
            error="Steam profile provider unavailable", code="profile_unavailable", retry=True,
        )
        return
    if not imported.get("ok") or not isinstance(imported.get("profile"), dict):
        rs.job_update(
            job_id, status="error", pct=100, stage="error",
            error=str(imported.get("error") or imported.get("msg") or "profile_unavailable")[:120],
            code=str(imported.get("code") or "profile_unavailable")[:60],
            retry=bool(imported.get("retry")),
        )
        return

    progress("profile_enrich", 89)
    profile = _merge_steam_api(imported["profile"])
    result = build_profile_dna(profile, user_id=0, mode=str(job.get("mode") or "workshop"))
    result["live_profile"] = {
        "showcases": len(profile.get("showcase_instances") or []),
        "sync_mode": str(imported.get("sync_mode") or "live"),
        "cached": bool(imported.get("cached")),
        "stale": bool(imported.get("stale")),
    }

    ai_meta = {"used": False, "available": steam_dna_ai.configured()}
    if ai_meta["available"]:
        progress("ai_interpretation", 93)
        try:
            result["interpretation"] = steam_dna_ai.enrich_profile_dna(
                result, profile, str(job.get("language") or "en")
            )
            ai_meta["used"] = True
        except steam_dna_ai.SteamDnaAiUnavailable:
            ai_meta["reason"] = "unavailable"
    result["ai"] = ai_meta

    cache_key = str(job.get("cache_key") or "")
    if cache_key:
        rs.steam_dna_cache_set(cache_key, result, ttl=_cache_ttl())
    rs.job_update(job_id, status="done", pct=100, stage="done", result=result)
