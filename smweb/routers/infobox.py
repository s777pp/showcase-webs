"""Info box templates published by visitors (smweb/infobox.py; UI: static/js/infobox.js)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

import redis_store as rs
from smweb import admin_control, emoticon_colors, infobox
from smweb.core import _auth_user

router = APIRouter()


@router.get("/api/infobox/templates")
def templates(category: str = "", sort: str = "new", limit: int = 24, offset: int = 0, request: Request = None):
    items, total = infobox.listing(category, sort, limit, offset)
    viewer = _auth_user(request) if request else None
    uid = int(viewer["id"]) if viewer else 0
    for item in items:
        item["owner"] = bool(uid) and item.pop("user_id") == uid
        item.pop("user_id", None)
    return {"ok": True, "items": items, "total": total, "logged_in": bool(viewer)}


@router.post("/api/infobox/templates")
async def publish(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "code": "login", "msg": "Sign in to publish"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict) or not body.get("rights"):
        return JSONResponse({"ok": False, "code": "rights", "msg": "Confirm that you have the rights"}, status_code=400)
    allowed, _ = rs.rate_limit(f"infobox:publish:{int(user['id'])}", 10, 3600)
    if not allowed:
        return JSONResponse({"ok": False, "code": "rate", "msg": "Too many templates. Try again later"}, status_code=429)
    try:
        row = infobox.create(int(user["id"]), body.get("title", ""), body.get("body", ""), str(body.get("category") or ""))
    except ValueError as exc:
        return JSONResponse({"ok": False, "code": str(exc), "msg": "Check the title and the text"}, status_code=400)
    return {"ok": True, "id": row["id"]}


@router.post("/api/infobox/emoticons")
async def emoticons(request: Request):
    """Colours of the visitor's own Steam emoticons for "Picture from emoticons" (smweb/emoticon_colors.py).

    The browser sends the names in batches of up to emoticon_colors.MAX_NAMES; unknown ones are fetched from Steam's
    CDN once and cached for good. No account needed: the names come from the visitor's own Steam page.
    """
    try:
        body = await request.json()
    except Exception:
        body = None
    names = emoticon_colors.clean_names(body.get("names") if isinstance(body, dict) else None)
    if not names:
        return JSONResponse({"ok": False, "code": "empty"}, status_code=400)
    if len(names) > emoticon_colors.MAX_NAMES:
        return JSONResponse({"ok": False, "code": "too_many", "max": emoticon_colors.MAX_NAMES}, status_code=400)
    result = await run_in_threadpool(emoticon_colors.colors, names)
    return {"ok": True, **result}


@router.post("/api/infobox/templates/{template_id}/use")
def use(template_id: str, request: Request):
    # A copy or an insert of a community template; once per address and template a day.
    from smweb.core import _ip
    allowed, _ = rs.rate_limit(f"infobox:use:{template_id}:{_ip(request)}", 1, 86400)
    if allowed:
        infobox.used(template_id)
    return {"ok": True}


@router.delete("/api/infobox/templates/{template_id}")
def delete(template_id: str, request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "code": "login"}, status_code=401)
    if not infobox.remove(template_id, int(user["id"])):
        return JSONResponse({"ok": False, "code": "not_found"}, status_code=404)
    return {"ok": True}


@router.delete("/api/admin/control/infobox/{template_id}")
def hide(template_id: str, request: Request):
    """The owner hides any community template (admin session + CSRF header, like the rest of the control centre)."""
    if not admin_control.authorised(request, mutation=True) or not admin_control.origin_allowed(request):
        return JSONResponse({"ok": False, "msg": "Administrator session required"}, status_code=403)
    if not infobox.remove(template_id):
        return JSONResponse({"ok": False, "msg": "Шаблон не найден"}, status_code=404)
    admin_control.audit("infobox.hide", f"infobox:{template_id}")
    return {"ok": True}
