"""Public gallery + moderation (test feature)."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Request, File, Form, UploadFile
from fastapi.responses import JSONResponse, FileResponse

import auth_db
from config import DATA, ADMIN_SECRET, MAX_UPLOAD_MB
from logging_config import log
from utils import auth_user, validate_upload

router = APIRouter(prefix="/api/gallery", tags=["gallery"])

GALLERY_DIR = DATA / "gallery"
GALLERY_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/list")
def gallery_list(status: str = "approved", limit: int = 40, offset: int = 0):
    items = auth_db.gallery_list(status=status, limit=min(limit, 100), offset=max(0, offset))
    # expose only public fields + url
    out = []
    for it in items:
        out.append({
            "id": it["id"],
            "title": it.get("title") or "",
            "mode": it.get("mode") or "",
            "author": it.get("display_name") or (it.get("email") or "anon")[:20],
            "url": f"/api/gallery/image/{it['id']}",
            "thumb": f"/api/gallery/image/{it['id']}?thumb=1" if it.get("thumb_path") else None,
            "created_at": it.get("created_at"),
        })
    return {"ok": True, "items": out, "count": len(out)}


@router.get("/image/{item_id}")
def gallery_image(item_id: int, thumb: int = 0):
    item = auth_db.gallery_get(item_id)
    if not item or item.get("status") != "approved":
        # allow pending only for admin later; for now public only approved
        if not item:
            return JSONResponse({"ok": False}, status_code=404)
        if item.get("status") != "approved":
            return JSONResponse({"ok": False, "msg": "Not public"}, status_code=403)
    path = Path(item["thumb_path"] if thumb and item.get("thumb_path") else item["image_path"])
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path)


@router.post("/submit")
async def gallery_submit(
    request: Request,
    title: str = Form(""),
    mode: str = Form("workshop"),
    file: UploadFile = File(...),
):
    """User submits a showcase image for the public gallery (pending moderation)."""
    user = auth_user(request)
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "File too large"}, status_code=400)
    ok, err = validate_upload(raw, file.filename or "img.png")
    if not ok:
        return JSONResponse({"ok": False, "msg": err}, status_code=400)
    # only images for gallery
    ext = Path(file.filename or "x.png").suffix.lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return JSONResponse({"ok": False, "msg": "Only images for gallery"}, status_code=400)

    uid = int(user["id"]) if user else None
    sub = GALLERY_DIR / f"u{uid or 0}"
    sub.mkdir(parents=True, exist_ok=True)
    import time
    name = f"{int(time.time())}_{secrets_token()}{ext}"
    path = sub / name
    path.write_bytes(raw)

    # simple thumb with Pillow
    thumb_path = None
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        im.thumbnail((400, 400))
        tp = path.with_suffix(".thumb.png")
        im.save(tp, "PNG")
        thumb_path = str(tp)
    except Exception:
        pass

    gid = auth_db.gallery_add(uid, title, mode, str(path), thumb_path)
    log.info("gallery submit id=%s user=%s", gid, uid)
    return {"ok": True, "id": gid, "msg": "Submitted for moderation"}


def secrets_token(n: int = 6) -> str:
    import secrets
    return secrets.token_hex(n)


@router.post("/mod/{item_id}")
async def gallery_mod(item_id: int, request: Request):
    """Admin: set status approved/rejected. Header X-Admin-Secret."""
    secret = ADMIN_SECRET
    got = (request.headers.get("x-admin-secret") or "").strip()
    if not secret or got != secret:
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    body = await request.json()
    status = str(body.get("status") or "").strip()
    if not auth_db.gallery_set_status(item_id, status):
        return JSONResponse({"ok": False, "msg": "Invalid status or id"}, status_code=400)
    return {"ok": True, "id": item_id, "status": status}


@router.get("/pending")
async def gallery_pending(request: Request):
    secret = ADMIN_SECRET
    got = (request.headers.get("x-admin-secret") or "").strip()
    if not secret or got != secret:
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    items = auth_db.gallery_list(status="pending", limit=100)
    return {"ok": True, "items": items}
