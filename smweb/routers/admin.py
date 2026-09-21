"""Authenticated control-center routes."""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

import auth_db
from smweb import admin_content, admin_control, maintenance, runtime_settings


router = APIRouter(prefix="/api/admin/control", tags=["admin-control"])


async def _json_object(request: Request) -> dict:
    try:
        value = await request.json()
    except Exception:
        value = {}
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    return value


def _require(request: Request, *, mutation: bool = False) -> None:
    if not admin_control.authorised(request, mutation=mutation):
        raise HTTPException(status_code=403, detail="Administrator session required")
    if mutation and not admin_control.origin_allowed(request):
        raise HTTPException(status_code=403, detail="Invalid request origin")


@router.post("/session")
async def login(request: Request):
    body = await _json_object(request)
    if not admin_control.secret_valid(str(body.get("secret") or "")):
        return JSONResponse({"ok": False, "msg": "Неверный ADMIN_SECRET"}, status_code=403)
    try:
        token, csrf, expires_at = admin_control.create_session()
    except RuntimeError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=503)
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    response = JSONResponse({"ok": True, "csrf": csrf, "expires_at": expires_at})
    response.set_cookie(
        admin_control.ADMIN_COOKIE, token, max_age=admin_control.SESSION_SECONDS,
        httponly=True, secure=proto == "https", samesite="strict", path="/api/admin",
    )
    admin_control.audit("session.login", "admin")
    return response


@router.delete("/session")
def logout(request: Request):
    _require(request, mutation=True)
    response = JSONResponse({"ok": True})
    response.delete_cookie(admin_control.ADMIN_COOKIE, path="/api/admin")
    return response


@router.get("/session")
def session(request: Request):
    data = admin_control.session_data(request.cookies.get(admin_control.ADMIN_COOKIE) or "")
    if not data:
        return JSONResponse({"ok": False}, status_code=401)
    return {"ok": True, "csrf": data["csrf"], "expires_at": data["exp"]}


@router.get("/overview")
def overview(request: Request, days: int = 30):
    _require(request)
    return admin_control.overview(days)


@router.get("/attention")
def attention(request: Request):
    _require(request)
    return {"ok": True, "items": admin_control.attention_items()}


@router.get("/system")
def system(request: Request):
    _require(request)
    return {"ok": True, "system": admin_control.system_snapshot()}


@router.get("/users")
def users(request: Request, q: str = "", page: int = 1, per_page: int = 30):
    _require(request)
    return admin_control.users(q, page, per_page)


@router.get("/users/{user_id}")
def user_detail(user_id: int, request: Request):
    _require(request)
    try:
        return admin_control.user_detail(user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/users/{user_id}/action")
async def user_action(user_id: int, request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    try:
        return admin_control.user_action(user_id, str(body.get("action") or ""), body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/codes")
def codes(request: Request):
    _require(request)
    return admin_control.codes()


@router.post("/codes")
async def generate_codes(request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    return admin_control.generate_codes(body.get("count", 1), body.get("duration_days", 7), body.get("label", "Pro"),
                                        body.get("campaign", ""), body.get("expires_days", 0))


@router.delete("/codes/{code}")
def revoke_code(code: str, request: Request):
    _require(request, mutation=True)
    try:
        return admin_control.revoke_code(code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs")
def jobs(request: Request, limit: int = 100):
    _require(request)
    return admin_control.jobs(limit)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, request: Request):
    _require(request, mutation=True)
    try:
        return admin_control.cancel_job(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str, request: Request):
    _require(request, mutation=True)
    try:
        return admin_control.retry_job(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/support")
def support_tickets(request: Request, status: str = "open"):
    _require(request)
    return {"ok": True, "items": admin_content.tickets(status)}


@router.post("/support/{ticket_id}")
async def update_support_ticket(ticket_id: str, request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    try:
        result = admin_content.update_ticket(ticket_id, str(body.get("status") or "working"), str(body.get("note") or ""))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    admin_control.audit("support.update", f"ticket:{ticket_id}", {"status": body.get("status")})
    return result


@router.get("/announcements")
def announcements(request: Request):
    _require(request)
    return {"ok": True, "items": admin_content.announcements()}


@router.post("/announcements")
async def save_announcement(request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    try:
        result = admin_content.save_announcement(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    admin_control.audit("announcement.save", f"announcement:{result['id']}", {"audience": body.get("audience"), "enabled": body.get("enabled") is not False})
    return result


@router.delete("/announcements/{announcement_id}")
def delete_announcement(announcement_id: str, request: Request):
    _require(request, mutation=True)
    try:
        result = admin_content.delete_announcement(announcement_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    admin_control.audit("announcement.delete", f"announcement:{announcement_id}")
    return result


@router.get("/catalog")
def catalog_rules(request: Request):
    _require(request)
    return {"ok": True, "items": admin_content.catalog_rules()}


@router.post("/catalog")
async def save_catalog_rule(request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    try:
        result = admin_content.save_catalog_rule(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    admin_control.audit("catalog.save", f"catalog:{result['key']}", {"hidden": bool(body.get("hidden")), "featured": bool(body.get("featured"))})
    return result


@router.delete("/catalog/{rule_key}")
def delete_catalog_rule(rule_key: str, request: Request):
    _require(request, mutation=True)
    try:
        result = admin_content.delete_catalog_rule(rule_key)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    admin_control.audit("catalog.delete", f"catalog:{rule_key}")
    return result


@router.get("/backups")
def backups(request: Request):
    _require(request)
    return {"ok": True, "backup": admin_content.backup_snapshot()}


@router.get("/gallery")
def gallery(request: Request, status: str = "pending"):
    _require(request)
    status = status if status in {"pending", "approved", "rejected"} else "pending"
    return {"ok": True, "items": auth_db.gallery_list(status=status, limit=100)}


@router.post("/gallery/{item_id}/moderate")
async def moderate_gallery(item_id: int, request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    status = str(body.get("status") or "")
    if status not in {"approved", "rejected", "pending"}:
        raise HTTPException(status_code=400, detail="Invalid gallery status")
    if not auth_db.gallery_set_status(item_id, status):
        raise HTTPException(status_code=404, detail="Gallery item not found")
    admin_control.audit("gallery.moderate", f"gallery:{item_id}", {"status": status})
    return {"ok": True}


@router.get("/maintenance")
def maintenance_state(request: Request):
    _require(request)
    return {"ok": True, "maintenance": maintenance.get_state()}


@router.post("/maintenance")
async def maintenance_update(request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    enabled = bool(body.get("enabled"))
    minutes = max(0, min(10080, int(body.get("minutes") or 0)))
    ends_at = time.time() + minutes * 60 if enabled and minutes else None
    state = maintenance.set_state(enabled, str(body.get("message") or ""), ends_at=ends_at)
    admin_control.audit("maintenance.update", "site", {"enabled": enabled, "minutes": minutes})
    return {"ok": True, "maintenance": state}


@router.get("/settings")
def settings(request: Request):
    _require(request)
    return {"ok": True, "settings": runtime_settings.snapshot()}


@router.post("/settings")
async def settings_update(request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    values = body.get("settings") if isinstance(body.get("settings"), dict) else body
    state = runtime_settings.update(values)
    admin_control.audit("settings.update", "runtime", {"changed": sorted(values.keys())})
    return {"ok": True, "settings": state}


@router.get("/audit")
def audit(request: Request, limit: int = 100):
    _require(request)
    return {"ok": True, "items": admin_control.audit_rows(limit)}
