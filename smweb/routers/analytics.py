"""Allowlisted product events and an aggregate-only admin report."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from smweb import analytics
from smweb.core import _admin_ok


router = APIRouter()
PUBLIC_TOOLS = frozenset({
    "about", "builder", "check", "compose", "convert", "da", "design-ai",
    "doctor", "download", "hex", "loop", "preview", "process", "projects",
    "steam", "upscale",
})


def _public_properties(event_name: str, value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    result = {}
    if event_name == "tool_open" and source.get("tool") in PUBLIC_TOOLS:
        result["tool"] = source["tool"]
    if event_name == "file_added":
        if source.get("file_type") in {"image", "video", "other"}:
            result["file_type"] = source["file_type"]
        if source.get("size_bucket") in {"under_1mb", "1_5mb", "5_20mb", "over_20mb"}:
            result["size_bucket"] = source["size_bucket"]
        try:
            result["value"] = max(1, min(10, int(source.get("value") or 1)))
        except (TypeError, ValueError):
            result["value"] = 1
    if event_name in {"process_failed", "extension_launch_clicked", "extension_launch_confirmed"}:
        if source.get("mode") in {"workshop", "featured", "split", "all"}:
            result["mode"] = source["mode"]
    if event_name == "process_failed" and source.get("reason") in {"client", "network", "start_rejected", "timeout"}:
        result["reason"] = source["reason"]
    return result


@router.post("/api/analytics/event", status_code=202)
async def public_event(request: Request):
    try:
        if int(request.headers.get("content-length") or 0) > 4096:
            return JSONResponse({"ok": False, "msg": "Payload too large"}, status_code=413)
    except ValueError:
        return JSONResponse({"ok": False, "msg": "Invalid payload"}, status_code=400)
    try:
        body = await request.json()
    except Exception:
        body = {}
    event_name = str(body.get("event") or "")
    if body.get("consent") is not True or event_name not in analytics.PUBLIC_EVENTS:
        return JSONResponse({"ok": False, "msg": "Event not accepted"}, status_code=400)
    accepted = analytics.record(
        event_name,
        session_id=str(body.get("session_id") or ""),
        language=str(body.get("language") or ""),
        path=str(body.get("path") or ""),
        properties=_public_properties(event_name, body.get("properties")),
        event_key=str(body.get("event_key") or ""),
    )
    if not accepted:
        return JSONResponse({"ok": False, "msg": "Analytics unavailable"}, status_code=503)
    return {"ok": True}


@router.get("/api/admin/analytics")
def admin_report(request: Request, days: int = 30):
    if not _admin_ok(request):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    try:
        return analytics.report(days)
    except Exception:
        return JSONResponse({"ok": False, "msg": "Analytics unavailable"}, status_code=503)
