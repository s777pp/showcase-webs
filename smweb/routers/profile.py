"""Public profiles, profile assets and showcases.

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


from smweb.core import DATA, LOGGER, PROFILE_EDITABLE_FIELDS, _auth_user, _safe_data_path
from smweb.steam import _clean_extension_profile, _merge_nonempty_profile, _merge_steam_api



router = APIRouter()
_profile_import_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="steam-profile")


@router.get("/api/profile/me")
def api_profile_me(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    un = auth_db.ensure_profile_username(int(user["id"]), user.get("display_name"))
    prof = auth_db.get_public_profile(un)
    if not prof:
        return JSONResponse({"ok": False, "msg": "Profile not found"}, status_code=404)
    av = prof.get("avatar_path") or ""
    av_url = f"/api/auth/avatar/{prof['id']}" if av else ""
    bg = prof.get("profile_background") or ""
    bg_url = f"/api/profile/bg/{prof['id']}" if bg else ""
    return {
        "ok": True,
        "is_owner": True,
        "profile": {
            **{k: v for k, v in prof.items() if k != "email"},
            "avatar_url": av_url,
            "background_url": bg_url,
            "username": un,
            "snapshot": auth_db.get_profile_builder_snapshot(int(user["id"])),
            "steam": auth_db.get_steam_profile_snapshot(int(user["id"])),
        },
    }


@router.get("/api/profile/account-overview")
def api_profile_account_overview(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    stats = auth_db.account_activity_stats(int(user["id"]))
    return {
        "ok": True,
        "display_name": user.get("display_name") or "",
        "email": user.get("email") or "",
        "avatar_url": f"/api/auth/avatar/{int(user['id'])}" if user.get("avatar_path") else "",
        "is_pro": bool(auth_db.effective_pro(user)),
        "gallery_uploads": stats["gallery_uploads"],
        "showcase_count": stats["showcase_count"],
    }


@router.get("/api/profile/my-library")
def api_profile_library(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    items = auth_db.gallery_list_for_user(int(user["id"]), 80)
    out = []
    for g in items:
        out.append({
            "id": g["id"],
            "title": g.get("title") or "",
            "mode": g.get("mode") or "",
            "status": g.get("status") or "",
            "url": f"/api/gallery/image/{g['id']}" if g.get("image_path") else "",
        })
    return {"ok": True, "items": out}


@router.get("/api/profile/steam-snapshot")
def api_profile_steam_snapshot(request: Request):
    """Return saved Steam profile JSON for the logged-in user (or ?user_id= for public)."""
    uid = None
    q_uid = (request.query_params.get("user_id") or "").strip()
    if q_uid.isdigit():
        uid = int(q_uid)
    else:
        user = _auth_user(request)
        if not user:
            return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
        uid = int(user["id"])
    snap = auth_db.get_steam_profile_snapshot(uid)
    if not snap:
        return JSONResponse({"ok": False, "msg": "No Steam profile linked"}, status_code=404)
    return {"ok": True, "profile": snap}


@router.post("/api/profile/update")
async def api_profile_update(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    auth_db.ensure_profile_username(int(user["id"]), user.get("display_name"))
    ct = (request.headers.get("content-type") or "").lower()
    fields: dict = {}
    try:
        if "multipart/form-data" in ct:
            form = await request.form()
            for key in PROFILE_EDITABLE_FIELDS:
                if key in form and form.get(key) is not None:
                    fields[key] = form.get(key)
            bgf = form.get("background")
            if bgf is not None and hasattr(bgf, "read"):
                raw = await bgf.read()
                if raw and len(raw) < 12_000_000:
                    name = getattr(bgf, "filename", "") or "bg.png"
                    ext = Path(str(name)).suffix.lower()
                    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                        ext = ".png"
                    key = f"profile_bg/{user['id']}{ext}"
                    if object_store.configured():
                        object_store.put_bytes(key, raw, media_type=object_store.content_type(key))
                    else:
                        dest = Path(DATA) / key
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(raw)
                    fields["profile_background"] = key
        else:
            body = await request.json()
            if isinstance(body, dict):
                # Same whitelist as the multipart branch. This used to be
                # `fields = body`, which handed the caller every column
                # update_steam_profile accepts — including avatar_path and
                # profile_background, i.e. arbitrary file read via the image
                # endpoints that serve them.
                fields = {k: body[k] for k in PROFILE_EDITABLE_FIELDS if k in body}
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=400)
    ok, msg = auth_db.update_steam_profile(int(user["id"]), **fields)
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    un = auth_db.ensure_profile_username(int(user["id"]))
    return {"ok": True, "msg": msg, "username": un}


@router.post("/api/profile/snapshot")
async def api_profile_snapshot_save(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    try:
        body = await request.json()
        snapshot = body.get("snapshot") if isinstance(body, dict) else None
        if not isinstance(snapshot, dict):
            return JSONResponse({"ok": False, "msg": "Invalid snapshot"}, status_code=400)
        auth_db.save_profile_builder_snapshot(int(user["id"]), snapshot)
        auth_db.ensure_profile_username(int(user["id"]), snapshot.get("name") or user.get("display_name"))
        auth_db.update_steam_profile(
            int(user["id"]),
            display_name=str(snapshot.get("name") or "")[:40],
            profile_summary=str(snapshot.get("summary") or "")[:2000],
            profile_level=int(snapshot.get("level") or 1),
        )
        # The avatar selected in the profile editor is also the account avatar
        # shown in every shared header. Only accept our own immutable asset URL.
        avatar = str(snapshot.get("avatar") or "")
        marker = f"/api/profile/asset/{int(user['id'])}/"
        if avatar.startswith(marker):
            name = Path(avatar.split(marker, 1)[1].split("?", 1)[0]).name
            if name:
                auth_db.update_profile(int(user["id"]), avatar_path=f"profile_assets/{int(user['id'])}/{name}")
        un = auth_db.ensure_profile_username(int(user["id"]))
        return {"ok": True, "username": un, "url": f"/profile/{un}"}
    except ValueError as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=413)
    except Exception:
        LOGGER.exception("save profile snapshot")
        return JSONResponse({"ok": False, "msg": "Could not save profile"}, status_code=500)


@router.post("/api/profile/asset")
async def api_profile_asset(request: Request, file: UploadFile = File(...)):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    raw = await file.read()
    if not raw or len(raw) > 24 * 1024 * 1024:
        return JSONResponse({"ok": False, "msg": "File must be under 24 MB"}, status_code=400)
    ext = Path(file.filename or "asset.bin").suffix.lower()
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".webm", ".mp4"}
    if ext not in allowed:
        return JSONResponse({"ok": False, "msg": "PNG, JPG, WEBP, GIF, WEBM or MP4 only"}, status_code=400)
    uid = int(user["id"])
    name = secrets.token_hex(12) + ext
    key = f"profile_assets/{uid}/{name}"
    if object_store.configured():
        object_store.put_bytes(key, raw, media_type=object_store.content_type(name))
    else:
        out = Path(DATA) / key
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
    return {"ok": True, "url": f"/api/profile/asset/{uid}/{name}"}


@router.get("/api/profile/asset/{user_id}/{name}")
def api_profile_asset_get(user_id: int, name: str):
    if Path(name).name != name:
        return JSONResponse({"ok": False}, status_code=404)
    key = f"profile_assets/{user_id}/{name}"
    if object_store.configured():
        url = object_store.public_url(key)
        if url:
            return RedirectResponse(
                url, status_code=307, headers={"Cache-Control": object_store.MUTABLE_CACHE}
            )
    path = Path(DATA) / key
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    return FileResponse(path, headers={"Cache-Control": object_store.MUTABLE_CACHE})


@router.get("/api/profile/bg/{user_id}")
def api_profile_bg(user_id: int):
    c = auth_db._conn()
    row = c.execute("SELECT profile_background FROM users WHERE id=?", (user_id,)).fetchone()
    c.close()
    if not row or not row["profile_background"]:
        return JSONResponse({"ok": False}, status_code=404)
    stored = str(row["profile_background"])
    if object_store.configured():
        try:
            url = object_store.public_url(object_store.key_from_stored(stored))
            if url:
                return RedirectResponse(
                    url, status_code=307, headers={"Cache-Control": object_store.MUTABLE_CACHE}
                )
        except Exception:
            LOGGER.exception("R2 background lookup failed")
    # Containment check: "../../etc/passwd" stored here used to escape DATA.
    path = _safe_data_path(stored)
    if path is None:
        path = _safe_data_path(Path(stored).name, subdir="profile_bg")
    if path is None:
        return JSONResponse({"ok": False}, status_code=404)
    media = "image/png"
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"): media = "image/jpeg"
    elif s == ".webp": media = "image/webp"
    elif s == ".gif": media = "image/gif"
    elif s == ".mp4": media = "video/mp4"
    elif s == ".webm": media = "video/webm"
    elif s == ".mov": media = "video/quicktime"
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type=media)


@router.post("/api/profile/showcase/add")
async def api_profile_showcase_add(request: Request):
    """Add showcase: type=featured|artwork|workshop|split, optional file upload or gallery_id.
    Workshop/Split: one image is auto-sliced via processor.
    """
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    uid = int(user["id"])
    auth_db.ensure_profile_username(uid, user.get("display_name"))
    form = await request.form()
    sc_type = str(form.get("type") or "featured").strip().lower()
    if sc_type not in ("featured", "artwork", "workshop", "split"):
        return JSONResponse({"ok": False, "msg": "Invalid type"}, status_code=400)
    if sc_type == "workshop":
        existing = [s for s in auth_db.profile_showcase_list(uid) if s.get("type") == "workshop"]
        # one Workshop block on profile; it holds up to 3 rows (3 source images)
        if len(existing) >= 1:
            return JSONResponse({"ok": False, "msg": "Workshop showcase already exists — remove it to upload a new set (up to 3 images)"}, status_code=400)
    title = str(form.get("title") or sc_type)[:80]
    out_dir = Path(DATA) / "profile_sc" / str(uid)
    out_dir.mkdir(parents=True, exist_ok=True)
    import tempfile
    import shutil
    import processor as proc

    files_saved: list[str] = []
    # collect uploaded files
    uploads = []
    for k, v in form.multi_items():
        if str(k) in ("file", "files") or str(k).startswith("file"):
            if v is not None and hasattr(v, "read"):
                uploads.append(v)

    gallery_id = form.get("gallery_id")
    if gallery_id and not uploads:
        try:
            gid = int(gallery_id)
            g = auth_db.gallery_get(gid)
            if g and int(g.get("user_id") or 0) == uid and g.get("image_path"):
                stored = str(g["image_path"])
                src = Path(DATA) / stored
                blob = None
                if object_store.configured():
                    try: blob = object_store.get_bytes(object_store.key_from_stored(stored), public=True)
                    except Exception: blob = None
                elif src.is_file():
                    blob = src.read_bytes()
                if blob:
                    class _F:
                        filename = Path(stored).name
                        async def read(self, _blob=blob):
                            return _blob
                    uploads.append(_F())
        except Exception as e:
            print("gallery pull", e)

    if not uploads:
        return JSONResponse({"ok": False, "msg": "Upload a file or pick from library"}, status_code=400)

    try:
        raw0 = await uploads[0].read()
        name0 = getattr(uploads[0], "filename", None) or "img.png"
        tmp = Path(tempfile.mkdtemp(prefix="psc_"))
        src_path = tmp / Path(str(name0)).name
        src_path.write_bytes(raw0)
        ts = str(int(time.time()))
        work = tmp / "out"
        work.mkdir()

        from PIL import Image as PILImage

        def _save_dict(out_map: dict):
            for fname, blob in out_map.items():
                if not isinstance(blob, (bytes, bytearray)):
                    continue
                if not str(fname).lower().endswith((".png", ".gif", ".jpg", ".jpeg", ".webp")):
                    continue
                dest = out_dir / f"{ts}_{Path(str(fname)).name}"
                dest.write_bytes(bytes(blob))
                files_saved.append(dest.name)

        VID_EXT = {".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"}
        GIF_EXT = {".gif"}
        IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

        def _ext_of(nm: str) -> str:
            return Path(str(nm)).suffix.lower() or ".png"

        def _copy_named(src: Path, row_i: int, part_name: str) -> str:
            """Copy processor output into profile_sc with stable name …_rN_pM.ext"""
            # part_1.gif → p1
            m = None
            import re as _re
            m = _re.match(r"part_(\d+)\.", part_name, _re.I)
            if m:
                fname = f"{ts}_r{row_i}_p{m.group(1)}{src.suffix.lower()}"
            elif "center" in part_name.lower():
                fname = f"{ts}_r{row_i}_center{src.suffix.lower()}"
            elif "side" in part_name.lower():
                fname = f"{ts}_r{row_i}_side{src.suffix.lower()}"
            elif "featured" in part_name.lower():
                fname = f"{ts}_r{row_i}_featured{src.suffix.lower()}"
            else:
                fname = f"{ts}_r{row_i}_{src.name}"
            dest = out_dir / fname
            dest.write_bytes(src.read_bytes())
            return fname

        if sc_type == "workshop":
            # Up to 3 sources → each becomes a row of 5 parts (PNG or GIF)
            try:
                sources = [(name0, raw0)]
                for extra in uploads[1:3]:
                    try:
                        raw = await extra.read()
                        nm = getattr(extra, "filename", None) or "img.png"
                        if raw:
                            sources.append((nm, raw))
                    except Exception:
                        pass
                row_i = 0
                for nm, raw in sources[:3]:
                    row_i += 1
                    ext = _ext_of(nm)
                    sp = tmp / f"src_{row_i}{ext}"
                    sp.write_bytes(raw)
                    work = tmp / f"work_{row_i}"
                    work.mkdir(exist_ok=True)

                    if ext in VID_EXT:
                        if not proc.find_ffmpeg():
                            raise RuntimeError("FFmpeg required for video")
                        paths = proc.process_video_workshop(
                            sp, work, fps=12, width=750, wm_text="", wm_opacity=0.0, duration=12,
                        )
                        for pname, ppath in paths.items():
                            if not str(pname).startswith("part_"):
                                continue
                            if Path(ppath).is_file():
                                files_saved.append(_copy_named(Path(ppath), row_i, pname))
                    elif ext in GIF_EXT:
                        if proc.find_ffmpeg():
                            paths = proc.process_gif_workshop(
                                sp, work, wm_text="", wm_opacity=0.0,
                            )
                            for pname, ppath in paths.items():
                                if not str(pname).startswith("part_"):
                                    continue
                                if Path(ppath).is_file():
                                    files_saved.append(_copy_named(Path(ppath), row_i, pname))
                        else:
                            # fallback: first frame PNG crop
                            from PIL import Image as _PIL
                            import io as _io
                            im = _PIL.open(_io.BytesIO(raw))
                            im.seek(0)
                            frame = im.convert("RGBA")
                            w, h = frame.size
                            pw = max(1, w // 5)
                            for pi in range(5):
                                left = pi * pw
                                right = (pi + 1) * pw if pi < 4 else w
                                part = frame.crop((left, 0, right, h))
                                buf = _io.BytesIO()
                                part.save(buf, format="PNG")
                                fname = f"{ts}_r{row_i}_p{pi+1}.png"
                                (out_dir / fname).write_bytes(buf.getvalue())
                                files_saved.append(fname)
                    else:
                        # static image — pure PIL 5-crop PNG
                        from PIL import Image as _PIL
                        import io as _io
                        im = _PIL.open(_io.BytesIO(raw)).convert("RGBA")
                        w, h = im.size
                        if w < 5:
                            continue
                        pw = w // 5
                        for pi in range(5):
                            left = pi * pw
                            right = (pi + 1) * pw if pi < 4 else w
                            part = im.crop((left, 0, right, h))
                            buf = _io.BytesIO()
                            part.save(buf, format="PNG", optimize=True)
                            fname = f"{ts}_r{row_i}_p{pi+1}.png"
                            (out_dir / fname).write_bytes(buf.getvalue())
                            files_saved.append(fname)
                if not files_saved:
                    shutil.rmtree(tmp, ignore_errors=True)
                    return JSONResponse({"ok": False, "msg": "Workshop produced no files"}, status_code=500)
            except Exception as e:
                shutil.rmtree(tmp, ignore_errors=True)
                return JSONResponse({"ok": False, "msg": f"Workshop process failed: {e}"}, status_code=500)

        elif sc_type == "split":
            try:
                ext = _ext_of(name0)
                work = tmp / "work_split"
                work.mkdir(exist_ok=True)
                if ext in VID_EXT:
                    if not proc.find_ffmpeg():
                        raise RuntimeError("FFmpeg required for video")
                    paths = proc.process_video_split(src_path, work, fps=12, wm_text="", wm_opacity=0.0)
                    for pname, ppath in paths.items():
                        if Path(ppath).is_file() and ("center" in pname or "side" in pname or pname.startswith("part")):
                            files_saved.append(_copy_named(Path(ppath), 1, pname))
                elif ext in GIF_EXT and proc.find_ffmpeg():
                    paths = proc.process_gif_split(src_path, work, fps=12, wm_text="", wm_opacity=0.0)
                    for pname, ppath in paths.items():
                        if Path(ppath).is_file() and ("center" in pname or "side" in pname):
                            files_saved.append(_copy_named(Path(ppath), 1, pname))
                else:
                    im = PILImage.open(src_path).convert("RGBA")
                    _save_dict(proc.process_image_split(im, wm_text="", wm_opacity=0))
                    # rename saved to center/side labels if needed
                    # _save_dict already used ts_ prefix
            except Exception as e:
                shutil.rmtree(tmp, ignore_errors=True)
                return JSONResponse({"ok": False, "msg": f"Split process failed: {e}"}, status_code=500)

        elif sc_type == "featured":
            try:
                ext = _ext_of(name0)
                work = tmp / "work_feat"
                work.mkdir(exist_ok=True)
                if ext in VID_EXT:
                    if not proc.find_ffmpeg():
                        raise RuntimeError("FFmpeg required for video")
                    paths = proc.process_video_featured(src_path, work, fps=12, wm_text="", wm_opacity=0.0)
                    for pname, ppath in paths.items():
                        if Path(ppath).is_file() and ("featured" in pname or "full_original" in pname):
                            files_saved.append(_copy_named(Path(ppath), 1, pname))
                elif ext in GIF_EXT and proc.find_ffmpeg():
                    paths = proc.process_gif_featured(src_path, work, fps=12, wm_text="", wm_opacity=0.0)
                    for pname, ppath in paths.items():
                        if Path(ppath).is_file() and ("featured" in pname or "full_original" in pname):
                            files_saved.append(_copy_named(Path(ppath), 1, pname))
                else:
                    im = PILImage.open(src_path).convert("RGBA")
                    _save_dict(proc.process_image_featured(im, wm_text="", wm_opacity=0))
            except Exception as e:
                print("featured process", e)
                dest = out_dir / f"{ts}_featured{src_path.suffix or '.png'}"
                dest.write_bytes(raw0)
                files_saved.append(dest.name)

        else:  # artwork — store as-is (image/gif/video file)
            dest = out_dir / f"{ts}_art{Path(str(name0)).suffix or '.png'}"
            dest.write_bytes(raw0)
            files_saved.append(dest.name)
            for extra in uploads[1:]:
                try:
                    raw = await extra.read()
                    nm = getattr(extra, "filename", None) or "extra.png"
                    d2 = out_dir / f"{ts}_{Path(str(nm)).name}"
                    d2.write_bytes(raw)
                    files_saved.append(d2.name)
                except Exception:
                    pass

        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        rid = getattr(request.state, "request_id", "-")
        LOGGER.exception("showcase upload failed rid=%s", rid)
        return JSONResponse({"ok": False, "msg": "Showcase upload failed", "request_id": rid}, status_code=500)

    if not files_saved:
        return JSONResponse({"ok": False, "msg": "No output files"}, status_code=500)

    if object_store.configured():
        for saved_name in files_saved:
            local_file = out_dir / saved_name
            object_store.upload_file(local_file, f"profile_sc/{uid}/{saved_name}", public=True)

    sid = auth_db.profile_showcase_add(uid, sc_type, title, {"files": files_saved})
    return {"ok": True, "id": sid, "files": files_saved, "type": sc_type}


@router.post("/api/profile/showcase/delete")
async def api_profile_showcase_delete(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    body = await request.json()
    sid = int(body.get("id") or 0)
    files = []
    for showcase in auth_db.profile_showcase_list(int(user["id"])):
        if int(showcase.get("id") or 0) == sid:
            files = list((showcase.get("data") or {}).get("files") or [])
            break
    ok = auth_db.profile_showcase_delete(int(user["id"]), sid)
    if ok:
        for filename in files:
            safe_name = Path(str(filename)).name
            if object_store.configured():
                try: object_store.delete(f"profile_sc/{int(user['id'])}/{safe_name}")
                except Exception: pass
            try: (Path(DATA) / "profile_sc" / str(int(user["id"])) / safe_name).unlink(missing_ok=True)
            except Exception: pass
    return {"ok": ok}


@router.get("/api/profile/file/{user_id}/{name}")
def api_profile_file(user_id: int, name: str):
    name = Path(name).name
    if object_store.configured():
        url = object_store.public_url(f"profile_sc/{user_id}/{name}")
        if url:
            return RedirectResponse(
                url, status_code=307, headers={"Cache-Control": object_store.MUTABLE_CACHE}
            )
    path = Path(DATA) / "profile_sc" / str(user_id) / name
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    media = "image/png"
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"): media = "image/jpeg"
    elif s == ".webp": media = "image/webp"
    elif s == ".gif": media = "image/gif"
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type=media)


@router.post("/api/profile/import-ticket")
def api_profile_import_ticket(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login through Steam first"}, status_code=401)
    link = auth_db.steam_link_for_user(int(user["id"]))
    if not link:
        return JSONResponse({"ok": False, "msg": "Steam account is not linked"}, status_code=409)
    try:
        ticket, expires = auth_db.create_profile_import_ticket(int(user["id"]), link["steam_id"])
    except ValueError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=429)
    return {"ok": True, "ticket": ticket, "expires_at": expires, "steamid": link["steam_id"], "profile_url": f"https://steamcommunity.com/profiles/{link['steam_id']}"}


@router.post("/api/profile/extension-import")
async def api_profile_extension_import(request: Request):
    length = int(request.headers.get("content-length") or 0)
    if length > 1_500_000:
        return JSONResponse({"ok": False, "msg": "Profile snapshot is too large"}, status_code=413)
    auth = (request.headers.get("authorization") or "").strip()
    ticket = auth[13:].strip() if auth.lower().startswith("importticket ") else ""
    try:
        raw = await request.body()
        if len(raw) > 1_500_000: raise ValueError("Profile snapshot is too large")
        body = json.loads(raw or b"{}")
    except Exception as exc:
        return JSONResponse({"ok": False, "msg": str(exc) or "Invalid JSON"}, status_code=400)
    if not ticket: ticket = str(body.get("ticket") or "")
    steam_id = str(body.get("steamid") or "")
    if not re.fullmatch(r"\d{17}", steam_id):
        return JSONResponse({"ok": False, "msg": "Invalid SteamID"}, status_code=400)
    grant = auth_db.consume_profile_import_ticket(ticket, steam_id)
    if not grant:
        return JSONResponse({"ok": False, "msg": "Import ticket expired, invalid or already used"}, status_code=401)
    try:
        profile = _clean_extension_profile(body.get("profile") or {}, steam_id)
        if not profile.get("name") and not profile.get("avatar"):
            return JSONResponse({"ok": False, "msg": "Steam page did not expose public profile data"}, status_code=422)
        profile = _merge_steam_api(profile)
        profile = _merge_nonempty_profile(auth_db.get_steam_profile_snapshot(grant["user_id"]), profile)
        auth_db.save_steam_profile_snapshot(grant["user_id"], profile)
        avatar_url = str(profile.get("avatar") or "").strip()
        if avatar_url:
            try:
                import requests as _rq
                avatar_response = _rq.get(avatar_url, timeout=12, headers={"User-Agent": "Mozilla/5.0 ShowcaseMaker"})
                if avatar_response.ok and avatar_response.content and len(avatar_response.content) <= 8_000_000:
                    content_type = (avatar_response.headers.get("content-type") or "").lower()
                    ext = ".png" if "png" in content_type else (".webp" if "webp" in content_type else ".jpg")
                    # Versioned like /api/auth/profile: a stable key would keep
                    # the old picture in caches after a re-import.
                    rel = f"avatars/{grant['user_id']}-{secrets.token_hex(4)}{ext}"
                    if object_store.configured():
                        object_store.put_bytes(
                            rel, avatar_response.content,
                            media_type=content_type.split(";", 1)[0] or object_store.content_type(rel),
                            immutable=True,
                        )
                    else:
                        (DATA / rel).parent.mkdir(parents=True, exist_ok=True)
                        (DATA / rel).write_bytes(avatar_response.content)
                    old_avatar = ""
                    try:
                        _c = auth_db._conn()
                        try:
                            _row = _c.execute(
                                "SELECT avatar_path FROM users WHERE id=?", (grant["user_id"],)
                            ).fetchone()
                            old_avatar = str((_row["avatar_path"] if _row else "") or "").strip()
                        finally:
                            _c.close()
                    except Exception:
                        old_avatar = ""
                    auth_db.update_profile(grant["user_id"], display_name=profile.get("name") or None, avatar_path=rel)
                    # Unique keys mean the previous object is now an orphan.
                    if old_avatar and old_avatar != rel:
                        if object_store.configured():
                            try: object_store.delete(object_store.key_from_stored(old_avatar))
                            except Exception: pass
                        else:
                            _old = _safe_data_path(old_avatar)
                            if _old is not None:
                                try: _old.unlink()
                                except Exception: pass
            except Exception:
                LOGGER.warning("Could not cache imported Steam avatar", exc_info=True)
        return {"ok": True, "profile": profile, "showcases": len(profile.get("showcase_instances") or [])}
    except Exception:
        LOGGER.exception("extension Steam profile import failed")
        return JSONResponse({"ok": False, "msg": "Steam profile import failed"}, status_code=500)


@router.post("/api/profile/steam-import")
async def api_profile_steam_import(request: Request):
    """Re-fetch Steam profile for logged-in user (by steam_id or body.url) and save snapshot."""
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    url = (body.get("url") or "").strip()
    if not url:
        # try linked steam id
        c_user = auth_db.user_by_token(request.cookies.get("sm_session") or "")
        # fallthrough: use steam from snapshot
        snap = auth_db.get_steam_profile_snapshot(int(user["id"]))
        if snap and snap.get("steamid"):
            url = f"https://steamcommunity.com/profiles/{snap['steamid']}"
        elif snap and snap.get("url"):
            url = snap["url"]
    if not url:
        return JSONResponse({"ok": False, "msg": "No Steam URL"}, status_code=400)
    try:
        import steam_catalog
        import steam_browser_import

        # Browser imports can take up to a minute.  When Browser API is active,
        # return immediately and let the shared worker queue do the expensive
        # rendered-page collection.  The extension route above is untouched.
        if steam_browser_import.configured():
            uid = int(user["id"])
            user_key = f"steam:{uid}"
            source_key = hashlib.sha256(url.lower().encode("utf-8")).hexdigest()[:24]
            existing = rs.job_find_active(user_key, "steam_profile_import", source_key)
            if existing:
                return {"ok": True, "queued": True, "job_id": existing[0]}
            jid = secrets.token_hex(12)
            external = ((os.environ.get("WORKER_MODE") or "embedded").strip().lower() == "external" and
                        rs.redis_ok() and rs.worker_alive())
            payload = {
                "kind": "steam_profile_import", "status": "queued", "pct": 1,
                "stage": "queued", "user_key": user_key, "user_id": uid,
                "source_key": source_key, "url": url, "created": time.time(),
            }
            rs.job_create(jid, payload, enqueue=external)
            if not external:
                from smweb.profile_import_jobs import run as run_profile_import
                _profile_import_pool.submit(run_profile_import, jid, payload)
            return {"ok": True, "queued": True, "job_id": jid}

        pr = steam_catalog.profile(url)
        if not pr.get("ok"):
            return JSONResponse(pr, status_code=400)
        profile = _merge_steam_api(pr["profile"])
        auth_db.save_steam_profile_snapshot(int(user["id"]), profile)
        return {"ok": True, "profile": profile,
                **{k: pr[k] for k in ('cached', 'stale', 'warning_code', 'retry_after') if k in pr}}
    except Exception:
        LOGGER.exception("Steam profile import start failed")
        return JSONResponse({"ok": False, "msg": "Steam profile import failed"}, status_code=500)


@router.get("/api/profile/steam-import/status/{job_id}")
def api_profile_steam_import_status(job_id: str, request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    job = rs.job_get(job_id)
    if not job or job.get("kind") != "steam_profile_import":
        return JSONResponse({"ok": False, "msg": "Import job not found"}, status_code=404)
    if int(job.get("user_id") or 0) != int(user["id"]):
        return JSONResponse({"ok": False, "msg": "Import job not found"}, status_code=404)
    response = {
        "ok": True, "status": job.get("status") or "queued",
        "pct": int(job.get("pct") or 0), "stage": job.get("stage") or "queued",
    }
    if job.get("status") == "done":
        response["result"] = job.get("result") or {}
    elif job.get("status") == "error":
        response.update({"error": job.get("error"), "code": job.get("error_code"),
                         "retry_after": job.get("retry_after")})
    return response


@router.get("/api/profile/{username}")
def api_profile_get(username: str, request: Request):
    prof = auth_db.get_public_profile(username)
    if not prof:
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    viewer = _auth_user(request)
    is_owner = bool(viewer and int(viewer["id"]) == int(prof["id"]))
    vis = (prof.get("profile_visibility") or "public").lower()
    if vis == "private" and not is_owner:
        return JSONResponse({"ok": False, "msg": "Private profile"}, status_code=403)
    av = prof.get("avatar_path") or ""
    av_url = f"/api/auth/avatar/{prof['id']}" if av else ""
    bg = prof.get("profile_background") or ""
    bg_url = f"/api/profile/bg/{prof['id']}" if bg else ""
    steam_snap = None
    try:
        steam_snap = auth_db.get_steam_profile_snapshot(int(prof["id"]))
    except Exception:
        steam_snap = None
    showcases = []
    try:
        showcases = auth_db.profile_showcase_list(int(prof["id"]))
    except Exception:
        showcases = []
    return {
        "ok": True,
        "is_owner": is_owner,
        "profile": {
            **{k: v for k, v in prof.items() if k != "email"},
            "avatar_url": av_url,
            "background_url": bg_url,
            "username": prof.get("profile_username"),
            "steam": steam_snap,
            "snapshot": auth_db.get_profile_builder_snapshot(int(prof["id"])),
            "showcases": showcases,
        },
    }


@router.get("/api/profile/{username}/showcases")
def api_profile_showcases(username: str, request: Request):
    prof = auth_db.get_public_profile(username)
    if not prof:
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    viewer = _auth_user(request)
    is_owner = bool(viewer and int(viewer["id"]) == int(prof["id"]))
    vis = (prof.get("profile_visibility") or "public").lower()
    if vis == "private" and not is_owner:
        return JSONResponse({"ok": False, "msg": "Private"}, status_code=403)
    items = auth_db.profile_showcase_list(int(prof["id"]))
    # resolve file URLs
    for it in items:
        files = (it.get("data") or {}).get("files") or []
        urls = []
        for f in files:
            urls.append(f"/api/profile/file/{prof['id']}/{Path(str(f)).name}")
        it["urls"] = urls
    return {"ok": True, "showcases": items, "is_owner": is_owner}
