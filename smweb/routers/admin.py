"""Authenticated control-center routes."""
from __future__ import annotations

import re
import time
import zipfile

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

import auth_db
from smweb import admin_content, admin_control, admin_jobs, maintenance, runtime_settings


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
                                        body.get("campaign", ""), body.get("expires_days", 0),
                                        body.get("duration_hours", 0))


@router.delete("/codes/{code}")
def revoke_code(code: str, request: Request):
    _require(request, mutation=True)
    try:
        return admin_control.revoke_code(code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs")
def jobs(request: Request, limit: int = 150, status: str = "all", kind: str = "", q: str = "", source: str = ""):
    _require(request)
    return admin_control.jobs(limit, status, kind, q, source)


# Literal job sub-routes live under /jobs/{id}/... ; the files are served inline
# only for sniffed image/video types, otherwise as attachments, and never cached.
_FILE_HEADERS = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                 "Content-Security-Policy": "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; sandbox"}


def _disposition(name: str, inline: bool) -> str:
    safe = re.sub(r'[^A-Za-z0-9._ -]', "_", name)[:120] or "file"
    return f'{"inline" if inline else "attachment"}; filename="{safe}"'


@router.get("/jobs/{job_id}")
def job_detail(job_id: str, request: Request):
    _require(request)
    try:
        return admin_jobs.job_detail(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/output/{index}")
def job_output(job_id: str, index: int, request: Request, download: int = 0):
    _require(request)
    try:
        data, media_type, name = admin_jobs.output_entry(job_id, index)
    except (LookupError, ValueError, OSError, zipfile.BadZipFile) as exc:
        raise HTTPException(status_code=404, detail=str(exc) or "Result unavailable") from exc
    inline = not download and media_type != "application/octet-stream"
    return Response(data, media_type=media_type,
                    headers={**_FILE_HEADERS, "Content-Disposition": _disposition(name, inline)})


@router.get("/jobs/{job_id}/source/{index}")
def job_source(job_id: str, index: int, request: Request, download: int = 0):
    _require(request)
    try:
        path, media_type, name = admin_jobs.source_file(job_id, index)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if download:
        admin_control.audit("job.source_download", f"job:{job_id}", {"index": index})
    inline = not download and media_type != "application/octet-stream"
    return FileResponse(path, media_type=media_type,
                        headers={**_FILE_HEADERS, "Content-Disposition": _disposition(name, inline)})


@router.get("/jobs/{job_id}/result")
def job_result(job_id: str, request: Request, inline: int = 0):
    _require(request)
    try:
        path, media_type, name, remote_key = admin_jobs.result_file(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if path is None:
        # Private R2 object: short redirect, the URL itself is never put in JSON.
        from smweb import object_store
        try:
            url = object_store.presigned_get_url(remote_key, expires=300, download_name=name, media_type=media_type)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Result is not available") from exc
        return RedirectResponse(url, status_code=302, headers={"Cache-Control": "private, no-store"})
    show_inline = bool(inline) and media_type.startswith(("image/", "video/"))
    return FileResponse(path, media_type=media_type,
                        headers={**_FILE_HEADERS, "Content-Disposition": _disposition(name, show_inline)})


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
    from smweb import support_threads
    items = admin_content.tickets(status)
    threads = support_threads.admin_threads([t["id"] for t in items])
    for item in items:
        item["thread"] = threads.get(item["id"], [])
    return {"ok": True, "items": items}


@router.post("/support/{ticket_id}/reply")
async def reply_support_ticket(ticket_id: str, request: Request):
    """Answer a ticket: stored in the thread, shown in the user's bell, e-mailed when possible."""
    _require(request, mutation=True)
    body = await _json_object(request)
    from smweb import support_threads
    try:
        result = support_threads.reply_from_support(ticket_id, str(body.get("text") or ""), str(body.get("status") or "resolved"))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    admin_control.audit("support.reply", f"ticket:{ticket_id}", {"emailed": result.get("emailed")})
    return result


# ---------------------------------------------------------------- purchases (2026-10-09)
@router.get("/purchases")
def purchases_list(request: Request, days: int = 30, source: str = "", status: str = "", q: str = ""):
    _require(request)
    from smweb import admin_billing
    return admin_billing.purchases(days, source if source in ("gumroad", "telegram") else "", status, q)


@router.post("/purchases/gumroad/{sale_id}/recheck")
def purchases_recheck(sale_id: str, request: Request):
    _require(request, mutation=True)
    from smweb import admin_billing
    try:
        result = admin_billing.recheck(sale_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    admin_control.audit("purchases.recheck", "gumroad_sale", {"status": result.get("status")})
    return {"ok": True, **result}


@router.post("/purchases/telegram/{payment_id}/refund")
def purchases_refund(payment_id: str, request: Request):
    _require(request, mutation=True)
    from smweb import admin_billing
    try:
        result = admin_billing.refund_telegram(payment_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    admin_control.audit("purchases.refund", "telegram_sale", {"status": result.get("status"), "plan": result.get("plan")})
    return {"ok": True, **result}


@router.post("/purchases/{source}/{sale_id}/attach")
async def purchases_attach(source: str, sale_id: str, request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    from smweb import admin_billing
    try:
        # sync_sale may call Gumroad over the network: keep it off the event loop.
        result = await run_in_threadpool(admin_billing.attach, source, sale_id, body.get("user"))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    admin_control.audit("purchases.attach", f"user:{result['user_id']}",
                        {"source": source, "status": result.get("status"), "plan": result.get("plan")})
    return {"ok": True, **result}


# ---------------------------------------------------------------- Info box community templates (2026-10-09)
# Hiding is DELETE /api/admin/control/infobox/{id} in routers/infobox.py (included before this router).
@router.get("/infobox")
def infobox_list(request: Request, status: str = "published", q: str = "", offset: int = 0):
    _require(request)
    from smweb import infobox
    return {"ok": True, **infobox.admin_listing(status, q, 60, offset)}


@router.post("/infobox/{template_id}/restore")
def infobox_restore(template_id: str, request: Request):
    _require(request, mutation=True)
    from smweb import infobox
    if not infobox.restore(template_id):
        raise HTTPException(status_code=404, detail="Шаблон не найден или уже опубликован")
    admin_control.audit("infobox.restore", f"infobox:{template_id}")
    return {"ok": True}


# ---------------------------------------------------------------- server errors (2026-10-01)
@router.get("/errors")
def errors_list(request: Request, status: str = "open"):
    _require(request)
    from smweb import error_log
    return {"ok": True, **error_log.listing(status if status in ("open", "resolved", "all") else "open")}


@router.post("/errors/resolve-all")
def errors_resolve_all(request: Request):
    _require(request, mutation=True)
    from smweb import error_log
    count = error_log.resolve(None)
    admin_control.audit("errors.resolve_all", "server_errors", {"count": count})
    return {"ok": True, "count": count}


@router.post("/errors/{error_id}/resolve")
def errors_resolve(error_id: str, request: Request):
    _require(request, mutation=True)
    from smweb import error_log
    if not error_log.resolve(error_id):
        raise HTTPException(status_code=404, detail="Ошибка не найдена или уже решена")
    admin_control.audit("errors.resolve", f"error:{error_id}")
    return {"ok": True}


@router.delete("/errors/resolved")
def errors_delete_resolved(request: Request):
    _require(request, mutation=True)
    from smweb import error_log
    count = error_log.delete_resolved()
    admin_control.audit("errors.delete_resolved", "server_errors", {"count": count})
    return {"ok": True, "count": count}


# ---------------------------------------------------------------- messages to users (2026-10-07)
@router.get("/messages")
def messages_list(request: Request):
    _require(request)
    from smweb import admin_messages
    return {"ok": True, "items": admin_messages.history()}


@router.post("/messages/count")
async def messages_count(request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    from smweb import admin_messages
    return admin_messages.count(str(body.get("audience") or "users"), body.get("targets"))


@router.post("/messages")
async def messages_send(request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    from smweb import admin_messages
    try:
        result = admin_messages.send(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    admin_control.audit("messages.send", f"message:{result['id']}",
                        {"audience": body.get("audience"), "recipients": result["recipients"]})
    return result


@router.delete("/messages/{message_id}")
def messages_recall(message_id: str, request: Request):
    _require(request, mutation=True)
    from smweb import admin_messages
    try:
        removed = admin_messages.recall(message_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    admin_control.audit("messages.recall", f"message:{message_id}", {"removed": removed})
    return {"ok": True, "removed": removed}


# ---------------------------------------------------------------- news (2026-10-01)
@router.get("/news")
def news_list(request: Request):
    _require(request)
    from smweb import news
    return {"ok": True, "items": news.admin_list(), "categories": list(news.CATEGORIES)}


@router.post("/news")
async def news_save(request: Request):
    _require(request, mutation=True)
    body = await _json_object(request)
    from smweb import news
    try:
        result = news.save(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    admin_control.audit("news.save", f"news:{result['id']}", {"status": body.get("status")})
    _announce_news(result.get("slug"))
    return result


def _announce_news(slug) -> None:
    """IndexNow (smweb/indexnow.py): a post that is live now goes to Yandex/Bing at once; scheduled ones are
    picked up by the hourly sitemap check when their time comes."""
    try:
        from smweb import indexnow, news
        from smweb.locales import localized_path
        post = next((p for p in news.published(limit=60) if p.get("slug") == slug), None)
        if post:
            indexnow.announce([indexnow.SITE + localized_path(language, path) for language in ("en", "ru")
                               for path in ("/news/" + post["slug"], "/news")])
    except Exception:
        pass


@router.delete("/news/{post_id}")
def news_delete(post_id: str, request: Request):
    _require(request, mutation=True)
    from smweb import news
    if not news.delete(post_id):
        raise HTTPException(status_code=404, detail="Новость не найдена")
    admin_control.audit("news.delete", f"news:{post_id}")
    return {"ok": True}


@router.post("/news/image")
async def news_image(request: Request):
    """One picture for a post (cover or inline); returns its public URL."""
    _require(request, mutation=True)
    form = await request.form(max_files=1, max_fields=4, max_part_size=15 * 1024 * 1024)
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        raise HTTPException(status_code=400, detail="Нет файла")
    data = await upload.read()
    if not data or len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Картинка до 15 МБ")
    from smweb import news
    try:
        url = news.store_image(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Это не картинка (PNG, JPG, WebP или GIF)") from exc
    return {"ok": True, "url": url}


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
