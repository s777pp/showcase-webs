"""Steam-style public profiles + profile showcases."""
from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

import auth_db
from web import core

router = APIRouter()


def _profile_html() -> HTMLResponse:
    p = core.ROOT / "static" / "profile.html"
    if not p.is_file():
        return HTMLResponse("profile.html missing", status_code=404)
    return HTMLResponse(p.read_text(encoding="utf-8"))


@router.get("/profile", response_class=HTMLResponse)
@router.get("/profile/", response_class=HTMLResponse)
async def profile_me(request: Request):
    return _profile_html()


@router.get("/profile/{username}", response_class=HTMLResponse)
async def profile_public(username: str, request: Request):
    return _profile_html()


@router.get("/api/profile/me")
def api_profile_me(request: Request):
    user = core._auth_user(request)
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
        },
    }


@router.get("/api/profile/{username}")
def api_profile_get(username: str, request: Request):
    prof = auth_db.get_public_profile(username)
    if not prof:
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    viewer = core._auth_user(request)
    is_owner = bool(viewer and int(viewer["id"]) == int(prof["id"]))
    vis = (prof.get("profile_visibility") or "public").lower()
    if vis == "private" and not is_owner:
        return JSONResponse({"ok": False, "msg": "Private profile"}, status_code=403)
    av = prof.get("avatar_path") or ""
    av_url = f"/api/auth/avatar/{prof['id']}" if av else ""
    bg = prof.get("profile_background") or ""
    bg_url = f"/api/profile/bg/{prof['id']}" if bg else ""
    return {
        "ok": True,
        "is_owner": is_owner,
        "profile": {
            **{k: v for k, v in prof.items() if k != "email"},
            "avatar_url": av_url,
            "background_url": bg_url,
            "username": prof.get("profile_username"),
        },
    }


@router.post("/api/profile/update")
async def api_profile_update(request: Request):
    user = core._auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    auth_db.ensure_profile_username(int(user["id"]), user.get("display_name"))
    ct = (request.headers.get("content-type") or "").lower()
    fields: dict = {}
    try:
        if "multipart/form-data" in ct:
            form = await request.form()
            for key in core.PROFILE_EDITABLE_FIELDS:
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
                    bg_dir = Path(core.DATA) / "profile_bg"
                    bg_dir.mkdir(parents=True, exist_ok=True)
                    for old in bg_dir.glob(f"{user['id']}.*"):
                        try:
                            old.unlink()
                        except Exception:
                            pass
                    dest = bg_dir / f"{user['id']}{ext}"
                    dest.write_bytes(raw)
                    fields["profile_background"] = f"profile_bg/{user['id']}{ext}"
        else:
            body = await request.json()
            if isinstance(body, dict):
                # Whitelisted: `fields = body` handed the caller avatar_path and
                # profile_background, i.e. arbitrary file read via the image
                # endpoints that serve those columns.
                fields = {k: body[k] for k in core.PROFILE_EDITABLE_FIELDS if k in body}
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=400)
    ok, msg = auth_db.update_steam_profile(int(user["id"]), **fields)
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    un = auth_db.ensure_profile_username(int(user["id"]))
    return {"ok": True, "msg": msg, "username": un}


@router.get("/api/profile/bg/{user_id}")
def api_profile_bg(user_id: int):
    c = auth_db._conn()
    row = c.execute("SELECT profile_background FROM users WHERE id=?", (user_id,)).fetchone()
    c.close()
    if not row or not row["profile_background"]:
        return JSONResponse({"ok": False}, status_code=404)
    stored = str(row["profile_background"])
    path = core.safe_data_path(stored)
    if path is None:
        path = core.safe_data_path(Path(stored).name, subdir="profile_bg")
    if path is None:
        return JSONResponse({"ok": False}, status_code=404)
    media = "image/png"
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"):
        media = "image/jpeg"
    elif s == ".webp":
        media = "image/webp"
    elif s == ".gif":
        media = "image/gif"
    elif s == ".mp4":
        media = "video/mp4"
    elif s == ".webm":
        media = "video/webm"
    elif s == ".mov":
        media = "video/quicktime"
    return FileResponse(path, media_type=media)


@router.get("/api/profile/{username}/showcases")
def api_profile_showcases(username: str, request: Request):
    prof = auth_db.get_public_profile(username)
    if not prof:
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    viewer = core._auth_user(request)
    is_owner = bool(viewer and int(viewer["id"]) == int(prof["id"]))
    vis = (prof.get("profile_visibility") or "public").lower()
    if vis == "private" and not is_owner:
        return JSONResponse({"ok": False, "msg": "Private"}, status_code=403)
    items = auth_db.profile_showcase_list(int(prof["id"]))
    for it in items:
        files = (it.get("data") or {}).get("files") or []
        urls = []
        for f in files:
            urls.append(f"/api/profile/file/{prof['id']}/{Path(str(f)).name}")
        it["urls"] = urls
    return {"ok": True, "showcases": items, "is_owner": is_owner}


@router.get("/api/profile/my-library")
def api_profile_library(request: Request):
    user = core._auth_user(request)
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


@router.post("/api/profile/showcase/add")
async def api_profile_showcase_add(request: Request):
    """Add showcase: type=featured|artwork|workshop|split, optional file upload or gallery_id."""
    user = core._auth_user(request)
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
        if len(existing) >= 1:
            return JSONResponse({"ok": False, "msg": "Workshop showcase already exists — remove it to upload a new set (up to 3 images)"}, status_code=400)
    title = str(form.get("title") or sc_type)[:80]
    out_dir = Path(core.DATA) / "profile_sc" / str(uid)
    out_dir.mkdir(parents=True, exist_ok=True)

    import processor as proc

    files_saved: list[str] = []
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
                src = Path(core.DATA) / str(g["image_path"])
                if src.is_file():
                    class _F:
                        filename = src.name

                        async def read(self, _p=src):
                            return _p.read_bytes()
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

        else:  # artwork — store as-is
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
    except Exception as e:
        return JSONResponse({"ok": False, "msg": str(e)}, status_code=500)

    if not files_saved:
        return JSONResponse({"ok": False, "msg": "No output files"}, status_code=500)

    sid = auth_db.profile_showcase_add(uid, sc_type, title, {"files": files_saved})
    return {"ok": True, "id": sid, "files": files_saved, "type": sc_type}


@router.post("/api/profile/showcase/delete")
async def api_profile_showcase_delete(request: Request):
    user = core._auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    body = await request.json()
    sid = int(body.get("id") or 0)
    ok = auth_db.profile_showcase_delete(int(user["id"]), sid)
    return {"ok": ok}


@router.get("/api/profile/file/{user_id}/{name}")
def api_profile_file(user_id: int, name: str):
    name = Path(name).name
    path = Path(core.DATA) / "profile_sc" / str(user_id) / name
    if not path.is_file():
        return JSONResponse({"ok": False}, status_code=404)
    media = "image/png"
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"):
        media = "image/jpeg"
    elif s == ".webp":
        media = "image/webp"
    elif s == ".gif":
        media = "image/gif"
    return FileResponse(path, media_type=media)
