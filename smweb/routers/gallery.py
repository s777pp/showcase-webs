"""Public gallery, moderation, likes, comments, notifications.

Moved out of main.py unchanged; see docs/STRUCTURE.md.
"""


from __future__ import annotations

import hashlib
import hmac
import html
import io
import ipaddress
import json
import logging
import os
import re
import socket
import secrets
import tempfile
import shutil
import time
import uuid
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db
from smweb import object_store


from fastapi import APIRouter


from smweb.core import DATA, LOGGER, MAX_UPLOAD_MB, _admin_ok, _auth_user, _is_gallery_admin



router = APIRouter()


@router.get("/api/gallery/list")
def gallery_list(request: Request, status: str = "approved", limit: int = 40, offset: int = 0):
    viewer = _auth_user(request)
    viewer_id = int(viewer["id"]) if viewer else None
    # `status` arrives from the query string. Letting anyone pass
    # status=pending published the un-moderated queue to the whole internet and
    # made the admin-only /api/gallery/pending pointless. Only a moderator may
    # ask for anything other than the approved feed.
    if status != "approved" and not (_admin_ok(request) or _is_gallery_admin(viewer)):
        status = "approved"
    items = auth_db.gallery_list(status=status, limit=min(int(limit), 100), offset=max(0, int(offset)))
    # filter + collect ids
    filtered = []
    for it in items:
        st = str(it.get("status") or "").lower()
        if st in ("deleted", "rejected", "removed"):
            continue
        img_path = it.get("image_path") or ""
        if img_path and not object_store.configured() and not Path(img_path).is_file():
            # also try relative to DATA
            if not (Path(DATA) / img_path).is_file():
                continue
        filtered.append(it)
    ids = [int(it["id"]) for it in filtered]
    likes_map = auth_db.gallery_like_counts(ids)
    comments_map = auth_db.gallery_comment_counts(ids)
    liked_set = auth_db.gallery_user_liked(viewer_id, ids) if viewer_id else set()
    out = []
    for it in filtered:
        author = it.get("display_name") or it.get("discord_username") or (it.get("email") or "anon")
        if isinstance(author, str) and "@" in author:
            author = author.split("@")[0]
        uid = it.get("user_id") or it.get("uid") or it.get("author_id")
        try:
            uid = int(uid) if uid is not None else None
        except Exception:
            uid = None
        iid = int(it["id"])
        # Always ensure public profile username for registered authors
        # so gallery → /profile/{username} works even if they never opened profile
        un = (it.get("profile_username") or "").strip()
        if uid:
            try:
                un = auth_db.ensure_profile_username(int(uid), author) or un
            except Exception:
                if not un:
                    un = f"user{uid}"
        out.append({
            "id": iid,
            "title": it.get("title") or "",
            "mode": it.get("mode") or "",
            "author": str(author)[:40],
            "user_id": uid,
            "username": un,
            "profile_url": f"/profile/{un}" if un else "",
            "avatar_url": f"/api/auth/avatar/{uid}" if uid else "",
            "url": f"/api/gallery/image/{iid}",
            "created_at": it.get("created_at"),
            "likes": likes_map.get(iid, 0),
            "comments": comments_map.get(iid, 0),
            "liked": iid in liked_set,
        })
    return {"ok": True, "items": out, "logged_in": bool(viewer)}


def _publish_to_r2(key: str, data: bytes, local: Path, thumb_key: str | None) -> None:
    """Mirror a freshly published gallery image into R2.

    Gallery keys carry a random suffix and are never overwritten, so they are
    safe to cache forever.  The local copy under /data is kept unless R2 can
    actually serve the object publicly -- otherwise the redirect fallback in
    gallery_image() would have nothing left to read.
    """
    if not object_store.configured():
        return
    try:
        object_store.put_bytes(
            key, data, media_type=object_store.content_type(key), immutable=True
        )
        if thumb_key:
            tp = local.with_name(Path(thumb_key).name)
            if tp.is_file():
                object_store.upload_file(tp, thumb_key, public=True, immutable=True)
    except Exception:
        # The local file is already written, so serving still works.
        LOGGER.exception("gallery R2 upload failed for %s", key)
        return
    if not object_store.public_url(key):
        # R2_PUBLIC_BASE_URL is unset: /api/gallery/image falls back to disk.
        return
    for victim in (local, local.with_name(Path(thumb_key).name) if thumb_key else None):
        if victim is not None:
            try:
                victim.unlink()
            except Exception:
                pass


@router.get("/api/gallery/image/{item_id}")
def gallery_image(item_id: int):
    item = auth_db.gallery_get(item_id)
    if not item or item.get("status") != "approved":
        return JSONResponse({"ok": False}, status_code=404)
    stored = str(item["image_path"])
    if object_store.configured():
        try:
            url = object_store.public_url(object_store.key_from_stored(stored))
            if url:
                return RedirectResponse(url, status_code=307, headers={"Cache-Control": "public, max-age=31536000, immutable"})
        except Exception:
            return JSONResponse({"ok": False}, status_code=404)
    path = Path(stored)
    if not path.is_file():
        path = Path(DATA) / stored
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path)


@router.post("/api/gallery/submit")
async def gallery_submit(
    request: Request,
    title: str = Form(""),
    mode: str = Form("workshop"),
    file: UploadFile = File(...),
):
    # Was anonymous (uid 0), so anyone could fill the disk and the public feed
    # without an account. /api/gallery/publish — the endpoint the UI actually
    # uses — has always required login; this one was the way around it.
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to publish"}, status_code=401)
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "Too large"}, status_code=400)
    ext = Path(file.filename or "x.png").suffix.lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return JSONResponse({"ok": False, "msg": "Images only"}, status_code=400)
    # Trust the bytes, not the filename: verify() parses the header, so a
    # renamed archive or script no longer lands in the gallery directory.
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception:
        return JSONResponse({"ok": False, "msg": "Not a valid image"}, status_code=400)
    uid = int(user["id"])
    name = f"{int(time.time())}_{secrets.token_hex(4)}{ext}"
    key = f"gallery/u{uid}/{name}"
    path = Path(DATA) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    thumb = None
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        im.thumbnail((400, 400))
        tp = path.with_suffix(".thumb.png")
        im.save(tp, "PNG")
        thumb = f"gallery/u{uid}/{tp.name}"
    except Exception:
        pass
    _publish_to_r2(key, raw, path, thumb)
    gid = auth_db.gallery_add(uid, title, mode, key, thumb, status="approved")
    return {"ok": True, "id": gid, "msg": "Published"}


@router.post("/api/gallery/publish")
async def gallery_publish(
    request: Request,
    mode: str = Form("workshop"),
    size: int = Form(750),
    wm_text: str = Form("n1t1337"),
    wm_font: str = Form("lap"),
    wm_opacity: int = Form(22),
    wm_enable: str = Form("1"),
    wm_corner: str = Form("bl"),
    wm_scale: float = Form(1.0),
    wm_color: str = Form("#ffffff"),
    wm_x: str = Form(""),
    wm_y: str = Form(""),
    auto_contrast: str = Form("0"),
    title: str = Form(""),
    file: UploadFile = File(...),
):
    """Build showcase preview (with/without WM) and submit to gallery as pending."""
    from PIL import ImageOps
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to publish"}, status_code=401)
    mode = (mode or "workshop").lower().strip()
    if mode not in ("workshop", "featured", "split"):
        return JSONResponse({"ok": False, "msg": "Unknown mode"}, status_code=400)
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "Too large"}, status_code=400)
    fname = (file.filename or "x.png").lower()
    ext = Path(fname).suffix.lower()
    # Sniff real format by magic bytes (fixes missing/wrong extension)
    head = raw[:16] if raw else b""
    is_gif = ext == ".gif" or head[:6] in (b"GIF87a", b"GIF89a")
    is_png = ext == ".png" or head[:8] == b"\x89PNG\r\n\x1a\n"
    is_jpg = ext in (".jpg", ".jpeg") or head[:3] == b"\xff\xd8\xff"
    is_webp = ext == ".webp" or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    is_bmp = ext == ".bmp" or head[:2] == b"BM"
    is_video = ext in (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v") or head[4:8] == b"ftyp"
    is_image = is_gif or is_png or is_jpg or is_webp or is_bmp
    if not is_image and not is_video:
        return JSONResponse(
            {"ok": False, "msg": "Images and GIF only (PNG/JPG/WEBP/GIF)"},
            status_code=400,
        )
    # normalize extension from sniffed type when missing/wrong
    if not ext or ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".mp4", ".webm", ".mov", ".avi", ".mkv"):
        if is_gif:
            ext = ".gif"
        elif is_png:
            ext = ".png"
        elif is_jpg:
            ext = ".jpg"
        elif is_webp:
            ext = ".webp"
        elif is_bmp:
            ext = ".bmp"
        elif is_video:
            ext = ".mp4"

    wm_on = wm_enable not in ("0", "false", "False", "")
    opacity = (wm_opacity / 100.0) if wm_on else 0.0
    text = wm_text if wm_on else ""
    color = (wm_color or "#ffffff").strip() or "#ffffff"
    corner = (wm_corner or "bl").strip().lower()
    if corner not in ("tl", "tr", "bl", "br"):
        corner = "bl"
    try:
        scale = max(0.4, min(2.5, float(wm_scale)))
    except Exception:
        scale = 1.0
    if scale > 2.5:
        scale = max(0.4, min(2.5, scale / 100.0))
    wm_x_f = wm_y_f = None
    try:
        if str(wm_x).strip() != "" and str(wm_y).strip() != "":
            wm_x_f = max(0.0, min(1.0, float(wm_x)))
            wm_y_f = max(0.0, min(1.0, float(wm_y)))
    except Exception:
        pass
    try:
        size_i = int(size)
    except Exception:
        size_i = 750
    if size_i not in (630, 640, 750, 800):
        size_i = 750

    import tempfile
    work = Path(tempfile.mkdtemp(prefix="sm_gal_"))
    try:
        data = None
        out_ext = ".png"

        if is_gif or is_video:
            # Animated / video: process full pipeline, keep animation in gallery
            src_ext = ext if ext else (".gif" if is_gif else ".mp4")
            if is_gif and raw[:6] in (b"GIF87a", b"GIF89a"):
                src_ext = ".gif"
            src = work / f"source{src_ext}"
            src.write_bytes(raw)
            use_video = is_video or src_ext in (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v")
            if use_video:
                if mode == "workshop":
                    paths = proc.process_video_workshop(
                        src, work, fps=12, width=size_i,
                        wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                        duration=8.0, wm_corner=corner, wm_scale=scale,
                        wm_x=wm_x_f, wm_y=wm_y_f, encoder="gifski",
                    )
                    pick = paths.get("full_with_bars.gif") or paths.get("full_original.gif")
                elif mode == "featured":
                    paths = proc.process_video_featured(
                        src, work, fps=12, duration=8.0, encoder="gifski",
                        wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                        wm_corner=corner, wm_scale=scale, wm_x=wm_x_f, wm_y=wm_y_f,
                    )
                    pick = (
                        paths.get("full_with_watermark.gif")
                        or paths.get("full_with_bars.gif")
                        or paths.get("featured_630.gif")
                        or paths.get("full_original.gif")
                    )
                else:
                    paths = proc.process_video_split(
                        src, work, fps=12,
                        wm_text=text, wm_font=wm_font, wm_opacity=opacity, wm_color=color,
                        duration=8.0, wm_corner=corner, wm_scale=scale,
                        wm_x=wm_x_f, wm_y=wm_y_f, encoder="gifski",
                    )
                    pick = paths.get("full_with_bars.gif") or paths.get("full_original.gif") or paths.get("center_506.gif")
            elif mode == "workshop":
                paths = proc.process_gif_workshop(
                    src, work,
                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                    wm_color=color, wm_corner=corner, wm_scale=scale,
                    wm_x=wm_x_f, wm_y=wm_y_f, encoder="gifski", fps=12,
                )
                pick = paths.get("full_with_bars.gif") or paths.get("full_original.gif")
            elif mode == "featured":
                paths = proc.process_gif_featured(
                    src, work, fps=12, encoder="gifski",
                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                    wm_color=color, wm_corner=corner, wm_scale=scale,
                    wm_x=wm_x_f, wm_y=wm_y_f,
                )
                pick = (
                    paths.get("full_with_watermark.gif")
                    or paths.get("full_with_bars.gif")
                    or paths.get("featured_630.gif")
                    or paths.get("full_original.gif")
                )
            else:
                paths = proc.process_gif_split(
                    src, work, fps=12,
                    wm_text=text, wm_font=wm_font, wm_opacity=opacity,
                    wm_color=color, wm_corner=corner, wm_scale=scale,
                    wm_x=wm_x_f, wm_y=wm_y_f, encoder="gifski",
                )
                pick = paths.get("full_with_bars.gif") or paths.get("full_original.gif") or paths.get("center_506.gif")
            if pick and Path(pick).is_file():
                data = Path(pick).read_bytes()
                out_ext = ".gif"
            else:
                # fallback: first frame as static
                im = Image.open(io.BytesIO(raw))
                im.seek(0)
                img = im.convert("RGBA")
                is_gif = False  # fall through to static path below using img
                # handled in static block
                buf = io.BytesIO()
                if mode == "workshop":
                    if img.size[0] != size_i:
                        nh = max(1, int(img.size[1] * (size_i / max(1, img.size[0]))))
                        img = img.resize((size_i, nh), Image.Resampling.LANCZOS)
                    parts = proc.process_image_workshop(
                        img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                    )
                    data = parts.get("full_with_bars.png") or parts.get("full_original.png")
                elif mode == "featured":
                    parts = proc.process_image_featured(
                        img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                    )
                    data = (
                        parts.get("full_with_watermark.png")
                        or parts.get("full_with_bars.png")
                        or parts.get("featured_630.png")
                        or parts.get("full_original.png")
                    )
                else:
                    parts = proc.process_image_split(
                        img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                    )
                    data = parts.get("full_with_bars.png") or parts.get("full_original.png")
                out_ext = ".png"
        else:
            img = Image.open(io.BytesIO(raw))
            img.load()
            if max(img.size) > 4096:
                img.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
            if str(auto_contrast).lower() in ("1", "true", "yes", "on"):
                img = ImageOps.autocontrast(img.convert("RGB"), cutoff=1)
            img = img.convert("RGBA")
            if mode == "workshop" and img.size[0] != size_i:
                nh = max(1, int(img.size[1] * (size_i / max(1, img.size[0]))))
                img = img.resize((size_i, nh), Image.Resampling.LANCZOS)
            if mode == "workshop":
                parts = proc.process_image_workshop(
                    img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                )
                data = parts.get("full_with_bars.png") or parts.get("full_original.png")
            elif mode == "featured":
                parts = proc.process_image_featured(
                    img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                )
                data = (
                    parts.get("full_with_watermark.png")
                    or parts.get("full_with_bars.png")
                    or parts.get("featured_630.png")
                    or parts.get("full_original.png")
                )
            else:
                parts = proc.process_image_split(
                    img, text, wm_font, opacity, color, corner, scale, wm_x_f, wm_y_f
                )
                data = parts.get("full_with_bars.png") or parts.get("full_original.png")
            out_ext = ".png"

        if not data:
            return JSONResponse({"ok": False, "msg": "Nothing to publish"}, status_code=400)

        uid = int(user["id"])
        name = f"{int(time.time())}_{secrets.token_hex(4)}_{mode}{out_ext}"
        key = f"gallery/u{uid}/{name}"
        path = Path(DATA) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        thumb = None
        try:
            im = Image.open(io.BytesIO(data))
            im.seek(0)
            im = im.convert("RGBA")
            im.thumbnail((400, 400))
            tp = path.with_name(path.stem + ".thumb.png")
            im.save(tp, "PNG")
            thumb = f"gallery/u{uid}/{tp.name}"
        except Exception:
            pass
        ttl = (title or "").strip() or f"{mode} showcase"
        _publish_to_r2(key, data, path, thumb)
        gid = auth_db.gallery_add(uid, ttl, mode, key, thumb, status="approved")
        return {"ok": True, "id": gid, "msg": "Published"}
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"{type(e).__name__}: {e}"}, status_code=500)
    finally:
        shutil.rmtree(work, ignore_errors=True)


@router.get("/api/gallery/pending")
async def gallery_pending(request: Request):
    user = _auth_user(request)
    if not (_admin_ok(request) or _is_gallery_admin(user)):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    return {"ok": True, "items": auth_db.gallery_list(status="pending", limit=100)}


@router.get("/api/gallery/am_admin")
def gallery_am_admin(request: Request):
    user = _auth_user(request)
    return {"ok": True, "admin": _is_gallery_admin(user), "email": (user or {}).get("email")}


@router.get("/api/notifications")
def api_notifications(request: Request, limit: int = 40):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in"}, status_code=401)
    rows = auth_db.notifications_list(int(user["id"]), limit=min(int(limit), 80))
    unread = auth_db.notifications_unread_count(int(user["id"]))
    out = []
    for r in rows:
        actor = r.get("display_name") or r.get("discord_username") or (r.get("email") or "")
        if isinstance(actor, str) and "@" in actor:
            actor = actor.split("@")[0]
        aid = r.get("actor_id")
        out.append({
            "id": r["id"],
            "kind": r.get("kind"),
            "body": r.get("body") or "",
            "item_id": r.get("item_id"),
            "comment_id": r.get("comment_id"),
            "is_read": bool(r.get("is_read")),
            "created_at": r.get("created_at"),
            "actor": str(actor)[:40],
            "actor_avatar": f"/api/auth/avatar/{aid}" if aid else "",
        })
    return {"ok": True, "items": out, "unread": unread}


@router.post("/api/notifications/read")
async def api_notifications_read(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    ids = body.get("ids")
    if ids is not None and not isinstance(ids, list):
        ids = None
    n = auth_db.notifications_mark_read(int(user["id"]), [int(x) for x in ids] if ids else None)
    return {"ok": True, "marked": n, "unread": auth_db.notifications_unread_count(int(user["id"]))}


@router.get("/api/notifications/unread")
def api_notifications_unread(request: Request):
    user = _auth_user(request)
    if not user:
        return {"ok": True, "unread": 0, "logged_in": False}
    return {"ok": True, "unread": auth_db.notifications_unread_count(int(user["id"])), "logged_in": True}


@router.post("/api/gallery/mod/{item_id}")
async def gallery_mod(item_id: int, request: Request):
    user = _auth_user(request)
    if not (_admin_ok(request) or _is_gallery_admin(user)):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)
    body = await request.json()
    status = str(body.get("status") or "")
    if not auth_db.gallery_set_status(item_id, status):
        return JSONResponse({"ok": False, "msg": "Bad status"}, status_code=400)
    return {"ok": True, "id": item_id, "status": status}


@router.delete("/api/gallery/{item_id}")
@router.post("/api/gallery/delete/{item_id}")
async def gallery_delete(item_id: int, request: Request):
    """Admin (or post owner) can remove a gallery item."""
    user = _auth_user(request)
    is_admin = _admin_ok(request) or _is_gallery_admin(user)
    item = auth_db.gallery_get(item_id)
    if not item:
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    owner_id = item.get("user_id") or item.get("uid") or item.get("author_id")
    is_owner = False
    if user and owner_id is not None:
        try:
            is_owner = int(user.get("id")) == int(owner_id)
        except Exception:
            is_owner = False
    if not (is_admin or is_owner):
        return JSONResponse({"ok": False, "msg": "Forbidden"}, status_code=403)

    # Remove files first so list won't show a broken card even if DB update is partial
    try:
        p = Path(item.get("image_path") or "")
        if p.is_file():
            p.unlink(missing_ok=True)
        thumb = item.get("thumb_path") or ""
        if thumb:
            Path(thumb).unlink(missing_ok=True)
        elif p:
            tp = p.with_name(p.stem + ".thumb.png")
            if tp.is_file():
                tp.unlink(missing_ok=True)
    except Exception:
        pass

    # Mark as not public — try several status values (auth_db may whitelist)
    marked = False
    for st in ("deleted", "rejected", "removed"):
        try:
            if auth_db.gallery_set_status(item_id, st):
                marked = True
                break
        except Exception:
            continue

    # Hard delete if the status update failed. This used to probe auth_db.connect()
    # and auth_db.get_conn() -- neither exists -- and then opened a *new* SQLite
    # file next to the real one, so on PostgreSQL it silently deleted nothing.
    if not marked:
        conn = None
        try:
            conn = auth_db._conn()
            conn.execute("DELETE FROM gallery WHERE id=?", (int(item_id),))
            conn.commit()
            marked = True
        except Exception:
            LOGGER.exception("gallery hard delete failed for %s", item_id)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    return {"ok": True, "id": item_id, "status": "deleted", "db": marked}


# ====================== Gallery social API ======================

@router.post("/api/gallery/{item_id}/like")
async def gallery_like(item_id: int, request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to like"}, status_code=401)
    liked, total = auth_db.gallery_like_toggle(int(user["id"]), int(item_id))
    return {"ok": True, "liked": liked, "likes": total}


@router.get("/api/gallery/{item_id}/comments")
def gallery_comments(item_id: int, request: Request):
    rows = auth_db.gallery_list_comments(int(item_id))
    viewer = _auth_user(request)
    stats = auth_db.gallery_item_stats(int(item_id), int(viewer["id"]) if viewer else None)
    out = []
    for r in rows:
        author = r.get("display_name") or r.get("discord_username") or (r.get("email") or "anon")
        if isinstance(author, str) and "@" in author:
            author = author.split("@")[0]
        uid = r.get("user_id")
        out.append({
            "id": r["id"],
            "parent_id": r.get("parent_id"),
            "body": r.get("body") or "",
            "user_id": uid,
            "author": str(author)[:40],
            "avatar_url": f"/api/auth/avatar/{uid}" if uid else "",
            "created_at": r.get("created_at"),
        })
    # IMPORTANT: do not **stats after "comments" — stats also has key "comments" (int count)
    return {
        "ok": True,
        "comments": out,
        "likes": stats.get("likes", 0),
        "liked": stats.get("liked", False),
        "comment_count": stats.get("comments", len(out)),
    }


@router.post("/api/gallery/{item_id}/comments")
async def gallery_post_comment(item_id: int, request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Log in to comment"}, status_code=401)
    try:
        body_json = await request.json()
    except Exception:
        body_json = {}
    body = str(body_json.get("body") or "").strip()
    parent_id = body_json.get("parent_id")
    try:
        parent_id = int(parent_id) if parent_id not in (None, "", 0, "0") else None
    except Exception:
        parent_id = None
    if not body:
        return JSONResponse({"ok": False, "msg": "Empty comment"}, status_code=400)
    row = auth_db.gallery_add_comment(int(user["id"]), int(item_id), body, parent_id)
    if not row:
        return JSONResponse({"ok": False, "msg": "Failed"}, status_code=400)
    author = row.get("display_name") or row.get("discord_username") or (row.get("email") or user.get("email") or "you")
    if isinstance(author, str) and "@" in author:
        author = author.split("@")[0]
    uid = row.get("user_id") or user["id"]
    return {
        "ok": True,
        "comment": {
            "id": row.get("id"),
            "parent_id": row.get("parent_id"),
            "body": row.get("body") or body,
            "user_id": uid,
            "author": str(author)[:40],
            "avatar_url": f"/api/auth/avatar/{uid}",
            "created_at": row.get("created_at"),
        },
    }
