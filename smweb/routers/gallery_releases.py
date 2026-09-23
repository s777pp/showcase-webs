"""Community work releases: public previews, private downloadable ZIPs and author profiles."""
from __future__ import annotations

import io
import re
import secrets
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

import auth_db
from smweb import object_store
from smweb.steam_readiness import Candidate, analyze_group
import redis_store as rs
from smweb.core import DATA, LOGGER, _auth_user, _safe_data_path

router = APIRouter()
MODES = {"workshop", "split", "featured"}
PREVIEW_LIMIT = 24 * 1024 * 1024
ARCHIVE_LIMIT = 80 * 1024 * 1024
FREE_STORAGE_LIMIT = 1024 * 1024 * 1024
PRO_STORAGE_LIMIT = 5 * FREE_STORAGE_LIMIT
SOCIALS = ("steam", "discord", "telegram", "website", "deviantart", "boosty")


async def _read_bounded(upload: UploadFile | None, limit: int) -> bytes:
    if upload is None:
        return b""
    data = bytearray()
    while chunk := await upload.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > limit:
            raise ValueError("File is too large")
    return bytes(data)


def _https(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if len(value) > 1000:
        raise ValueError("Link is too long")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use a full https:// link")
    return value


def _preview_type(data: bytes) -> tuple[str, bool]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", False
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", False
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        try:
            with Image.open(io.BytesIO(data)) as image:
                return ".webp", getattr(image, "n_frames", 1) > 1
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Could not read the preview") from exc
    if data[:6] in (b"GIF87a", b"GIF89a"):
        try:
            with Image.open(io.BytesIO(data)) as image:
                return ".gif", getattr(image, "n_frames", 1) > 1
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Could not read the preview") from exc
    if data[4:8] == b"ftyp":
        return ".mp4", True
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm", True
    raise ValueError("Preview must be PNG, JPG, WebP, GIF, MP4 or WebM")


def _preview_thumb(data: bytes, suffix: str) -> bytes:
    if suffix in (".mp4", ".webm"):
        # MP4 often keeps its metadata at the end and cannot be read reliably
        # from stdin. Use a bounded temporary file; never pass user text to a shell.
        with tempfile.TemporaryDirectory(prefix="sm_gallery_preview_") as work:
            source_path = Path(work) / f"source{suffix}"
            source_path.write_bytes(data)
            result = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(source_path), "-frames:v", "1",
                 "-vf", "scale=640:-2", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
                capture_output=True, timeout=12, check=False,
            )
        if result.returncode or not result.stdout:
            raise ValueError("Could not read the video preview")
        source = result.stdout
    else:
        source = data
    try:
        with Image.open(io.BytesIO(source)) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError("Preview dimensions are too large")
            image.seek(0)
            image.thumbnail((640, 800), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            image.convert("RGB").save(out, "JPEG", quality=82, optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("Could not read the preview") from exc


def _check_archive(data: bytes, mode: str) -> None:
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError("Upload a ZIP with ready Steam files")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            seen_names = set()
            for entry in archive.infolist():
                member = entry.filename.replace("\\", "/").rstrip("/")
                parts = member.split("/")
                file_type = (entry.external_attr >> 16) & 0o170000
                if (not member or member.startswith("/") or re.match(r"^[A-Za-z]:", member)
                        or any(part in ("", ".", "..") for part in parts)
                        or any(ord(char) < 32 or char in '<>:"|?*' for char in member)
                        or file_type not in (0, 0o040000, 0o100000)
                        or member.casefold() in seen_names):
                    raise ValueError("ZIP contains an unsafe file path")
                seen_names.add(member.casefold())
            files = [entry for entry in archive.infolist() if not entry.is_dir()]
            if not files or len(files) > 120:
                raise ValueError("ZIP must contain 1–120 files")
            total = 0
            groups: dict[str, list[Candidate]] = {}
            for entry in files:
                name = Path(entry.filename.replace("\\", "/")).name
                if not name or Path(name).suffix.lower() not in {".png", ".jpg", ".jpeg", ".gif"}:
                    raise ValueError("ZIP may contain only Steam image/GIF files")
                if entry.flag_bits & 1:
                    raise ValueError("Password-protected ZIPs are not supported")
                total += entry.file_size
                if entry.file_size > 25 * 1024 * 1024 or total > 160 * 1024 * 1024:
                    raise ValueError("Unpacked files are too large")
                if entry.compress_size and entry.file_size / entry.compress_size > 250:
                    raise ValueError("ZIP compression ratio is too high")
                with archive.open(entry) as member:
                    raw = member.read(25 * 1024 * 1024 + 1)
                if len(raw) != entry.file_size:
                    raise ValueError("ZIP file size does not match its contents")
                group = str(Path(entry.filename.replace("\\", "/")).parent).replace("\\", "/")
                groups.setdefault(group, []).append(Candidate(entry.filename, raw))
            for candidates in groups.values():
                report = analyze_group("Files", candidates, mode)
                required = {check["id"]: check["state"] for check in report["checks"]}
                if any(required.get(key) != "pass" for key in ("format", "weight", "geometry", "set", "sync")):
                    raise ValueError("ZIP is not a complete Steam-ready set for this showcase type")
                if any(issue["code"] == "unreadable" for item in report["files"] for issue in item["issues"]):
                    raise ValueError("ZIP contains an unreadable image or GIF")
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError("ZIP is damaged") from exc


def _job_archive(request: Request, job_id: str) -> bytes:
    from smweb.routers.process import _process_job_for
    job = _process_job_for(request, job_id)
    user = _auth_user(request)
    if not job or not user or str(job.get("user_key")) != str(user["id"]) or job.get("status") != "done":
        raise ValueError("Finished processing job not found")
    path = Path(str(job.get("zip_path") or ""))
    if path.is_file():
        if path.stat().st_size > ARCHIVE_LIMIT:
            raise ValueError("ZIP is too large")
        return path.read_bytes()
    key = job.get("result_key")
    if key and object_store.configured():
        data = object_store.get_bytes(key, public=False)
        if len(data) <= ARCHIVE_LIMIT:
            return data
    raise ValueError("Processing result expired. Download and upload the ZIP manually")


def _preview_from_archive(data: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = [entry for entry in archive.infolist() if not entry.is_dir() and
                 Path(entry.filename).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}]
        def priority(entry):
            name = entry.filename.lower()
            return (0 if "full_with_bars" in name or "full_with_watermark" in name else
                    1 if "full_original" in name else 2, name)
        files.sort(key=priority)
        for entry in files:
            if entry.file_size <= PREVIEW_LIMIT:
                with archive.open(entry) as member:
                    preview = member.read(PREVIEW_LIMIT + 1)
                    # Steam's HEX 21 patch replaces the GIF trailer. Restore it
                    # for the public browser preview without touching the ZIP.
                    if preview.startswith((b"GIF87a", b"GIF89a")) and preview.endswith(b"\x21"):
                        preview = preview[:-1] + b";"
                    return preview
    raise ValueError("Add a preview image or GIF")


def _work(item: dict, viewer_id: int | None = None) -> dict:
    uid = int(item.get("user_id") or 0)
    username = item.get("profile_username") or (auth_db.ensure_profile_username(uid) if uid else "")
    profile = auth_db.get_public_profile(username) if uid and "display_name" not in item else None
    avatar_path = item.get("avatar_path") or (profile or {}).get("avatar_path")
    return {
        "id": int(item["id"]), "title": item.get("title") or "", "description": item.get("description") or "",
        "mode": item.get("mode") or "workshop", "animated": bool(item.get("is_animated")),
        "video_preview": Path(str(item.get("image_path") or "")).suffix.lower() in {".mp4", ".webm"},
        "adult": bool(item.get("is_adult")), "paid": bool(item.get("is_paid")),
        "sale_url": item.get("sale_url") or "", "background_url": item.get("background_url") or "",
        "downloads": int(item.get("download_count") or 0), "likes": int(item.get("likes") or 0),
        "author": item.get("display_name") or (profile or {}).get("display_name") or username or "Author", "username": username,
        "avatar_url": f"/api/auth/avatar/{uid}" if uid and avatar_path else "", "author_url": f"/gallery?author={username}" if username else "",
        "preview_url": f"/api/gallery/image/{int(item['id'])}",
        "thumb_url": f"/api/gallery/works/{int(item['id'])}/thumb" if item.get("thumb_path") else "",
        "download_url": f"/api/gallery/works/{int(item['id'])}/download" if item.get("archive_path") and not item.get("is_paid") else "",
        "owner": uid == viewer_id if viewer_id else False, "created_at": item.get("created_at"),
    }


@router.get("/api/gallery/works")
def works(request: Request, mode: str = "", animation: str = "", author: str = "", sort: str = "new",
          limit: int = 24, offset: int = 0):
    profile = auth_db.get_public_profile(author) if author else None
    if author and not profile:
        return JSONResponse({"ok": False, "msg": "Author not found"}, status_code=404)
    viewer = _auth_user(request)
    viewer_id = int(viewer["id"]) if viewer else None
    if profile and profile.get("profile_visibility") == "private" and viewer_id != profile["id"]:
        return JSONResponse({"ok": False, "msg": "Private profile"}, status_code=403)
    rows, total = auth_db.gallery_release_list(mode=mode, animation=animation,
        author_id=profile["id"] if profile else None, sort=sort, limit=limit, offset=offset)
    liked = auth_db.gallery_user_liked(viewer_id, [int(row["id"]) for row in rows]) if viewer_id else set()
    out = []
    for row in rows:
        item = _work(row, viewer_id)
        item["liked"] = item["id"] in liked
        out.append(item)
    author_info = None
    if profile:
        uid = profile["id"]
        author_info = {"username": profile["profile_username"], "name": profile["display_name"],
            "bio": profile["profile_summary"], "avatar_url": f"/api/auth/avatar/{uid}" if profile.get("avatar_path") else "",
            "links": auth_db.get_author_links(uid), "stats": auth_db.gallery_author_stats(uid),
            "owner": uid == viewer_id}
    return {"ok": True, "items": out, "total": total, "author": author_info, "logged_in": bool(viewer)}


@router.get("/api/gallery/works/{item_id}")
def work_detail(item_id: int, request: Request):
    row = auth_db.gallery_get(item_id)
    if not row or row.get("status") != "approved" or row.get("release_version") != 2:
        return JSONResponse({"ok": False, "msg": "Work not found"}, status_code=404)
    viewer = _auth_user(request)
    item = _work(row, int(viewer["id"]) if viewer else None)
    stats = auth_db.gallery_item_stats(item_id, int(viewer["id"]) if viewer else None)
    item.update({"likes": stats.get("likes", 0), "liked": stats.get("liked", False)})
    return {"ok": True, "item": item}


@router.get("/api/gallery/works/{item_id}/thumb")
def work_thumb(item_id: int):
    row = auth_db.gallery_get(item_id)
    if not row or row.get("status") != "approved" or row.get("release_version") != 2:
        return Response(status_code=404)
    key = row.get("thumb_path")
    if not key:
        return Response(status_code=404)
    if object_store.configured():
        url = object_store.public_url(object_store.key_from_stored(key))
        if url:
            return RedirectResponse(url, status_code=307)
    path = _safe_data_path(str(key))
    return FileResponse(path, media_type="image/jpeg") if path and path.is_file() else Response(status_code=404)


@router.get("/api/gallery/works/{item_id}/download")
def work_download(item_id: int, request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Sign in to download"}, status_code=401)
    row = auth_db.gallery_get(item_id)
    if not row or row.get("status") != "approved" or row.get("release_version") != 2:
        return JSONResponse({"ok": False, "msg": "Work not found"}, status_code=404)
    if row.get("is_paid") or not row.get("archive_path"):
        return JSONResponse({"ok": False, "msg": "ZIP is not available here"}, status_code=403)
    stored = str(row["archive_path"])
    path = _safe_data_path(stored)
    if path and path.is_file():
        auth_db.gallery_release_downloaded(item_id)
        return FileResponse(path, filename=f"showcase-{item_id}.zip", media_type="application/zip",
                            headers={"Cache-Control": "private, no-store"})
    if object_store.configured():
        try:
            url = object_store.presigned_get_url(object_store.key_from_stored(stored), public=False,
                expires=120, download_name=f"showcase-{item_id}.zip", media_type="application/zip")
            auth_db.gallery_release_downloaded(item_id)
            return RedirectResponse(url, status_code=307, headers={"Cache-Control": "private, no-store"})
        except Exception:
            LOGGER.exception("gallery ZIP unavailable for %s", item_id)
    return JSONResponse({"ok": False, "msg": "ZIP is temporarily unavailable"}, status_code=503)


@router.post("/api/gallery/works")
async def work_publish(request: Request, title: str = Form(""), description: str = Form(""),
                       mode: str = Form("workshop"), background_url: str = Form(""),
                       sale_url: str = Form(""), is_paid: bool = Form(False), is_adult: bool = Form(False),
                       rights_confirmed: bool = Form(False), job_id: str = Form(""),
                       preview: UploadFile | None = File(None), archive: UploadFile | None = File(None)):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Sign in to publish"}, status_code=401)
    allowed, _ = rs.rate_limit(f"gallery:publish:{int(user['id'])}", 30, 3600)
    if not allowed:
        return JSONResponse({"ok": False, "msg": "Publishing limit reached. Try again later"}, status_code=429)
    title = title.strip()
    if not title or len(title) > 80 or mode not in MODES or not rights_confirmed:
        return JSONResponse({"ok": False, "msg": "Check the title, showcase type and publishing rights"}, status_code=400)
    try:
        background_url = _https(background_url)
        sale_url = _https(sale_url)
        if is_paid and not sale_url:
            raise ValueError("Add a purchase link")
        if job_id:
            if not re.fullmatch(r"[a-f0-9]{24}", job_id):
                raise ValueError("Invalid processing result")
            zip_data = await run_in_threadpool(_job_archive, request, job_id)
        else:
            zip_data = await _read_bounded(archive, ARCHIVE_LIMIT)
        if not is_paid and not zip_data:
            raise ValueError("Add the ready ZIP")
        if zip_data:
            await run_in_threadpool(_check_archive, zip_data, mode)
        preview_data = await _read_bounded(preview, PREVIEW_LIMIT)
        if not preview_data and zip_data:
            preview_data = await run_in_threadpool(_preview_from_archive, zip_data)
        if not preview_data:
            raise ValueError("Add a preview image, GIF or video")
        suffix, animated = _preview_type(preview_data)
        thumb = await run_in_threadpool(_preview_thumb, preview_data, suffix)
        storage_bytes = len(preview_data) + len(thumb) + (len(zip_data) if not is_paid else 0)
        storage_limit = PRO_STORAGE_LIMIT if auth_db.effective_pro(user) else FREE_STORAGE_LIMIT
        if auth_db.gallery_release_storage_bytes(int(user["id"])) + storage_bytes > storage_limit:
            return JSONResponse({"ok": False, "code": "GALLERY_STORAGE_QUOTA",
                                 "msg": "Gallery storage is full. Delete an old work to free space"}, status_code=413)
    except ValueError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)
    except Exception:
        LOGGER.exception("gallery release validation failed")
        return JSONResponse({"ok": False, "msg": "Could not prepare the work"}, status_code=500)
    uid = int(user["id"])
    token = secrets.token_hex(12)
    prefix = f"gallery/u{uid}/{token}"
    preview_key = f"{prefix}/preview{suffix}"
    thumb_key = f"{prefix}/thumb.jpg"
    archive_key = f"gallery_releases/u{uid}/{token}/files.zip" if zip_data and not is_paid else None
    saved: list[Path] = []
    mirrored: list[tuple[str, bool]] = []
    try:
        for key, data in ((preview_key, preview_data), (thumb_key, thumb), (archive_key, zip_data)):
            if not key:
                continue
            path = Path(DATA) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            saved.append(path)
        if object_store.configured():
            await run_in_threadpool(object_store.put_bytes, preview_key, preview_data,
                                    media_type=object_store.content_type(preview_key), immutable=True)
            mirrored.append((preview_key, True))
            await run_in_threadpool(object_store.put_bytes, thumb_key, thumb,
                                    media_type="image/jpeg", immutable=True)
            mirrored.append((thumb_key, True))
            if archive_key:
                try:
                    await run_in_threadpool(object_store.put_bytes, archive_key, zip_data,
                                            public=False, media_type="application/zip")
                    mirrored.append((archive_key, False))
                except Exception:
                    # The private bucket may not be provisioned yet. The ZIP
                    # remains protected on the persistent DATA volume and is
                    # only served through the authenticated download endpoint.
                    LOGGER.exception("gallery private R2 mirror unavailable for user %s", uid)
        gid = auth_db.gallery_release_create(uid, title=title, mode=mode, image_path=preview_key,
            thumb_path=thumb_key, archive_path=archive_key, description=description,
            background_url=background_url, sale_url=sale_url, is_paid=is_paid,
            is_adult=is_adult, is_animated=animated, storage_bytes=storage_bytes)
        return {"ok": True, "id": gid, "url": f"/gallery?work={gid}"}
    except Exception:
        LOGGER.exception("gallery release publish failed")
        for path in saved:
            path.unlink(missing_ok=True)
        for key, public in mirrored:
            try:
                object_store.delete(key, public=public)
            except Exception:
                LOGGER.exception("gallery mirror cleanup failed for %s", key)
        return JSONResponse({"ok": False, "msg": "Could not publish the work"}, status_code=500)


@router.put("/api/gallery/works/{item_id}")
async def work_edit(item_id: int, request: Request):
    user = _auth_user(request)
    row = auth_db.gallery_get(item_id)
    if not user or not row or int(row.get("user_id") or 0) != int(user["id"]) or row.get("release_version") != 2:
        return JSONResponse({"ok": False, "msg": "Work not found"}, status_code=404)
    try:
        data = await request.json()
    except ValueError:
        return JSONResponse({"ok": False, "msg": "Invalid work details"}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"ok": False, "msg": "Invalid work details"}, status_code=400)
    title = str(data.get("title") or "").strip()
    mode = str(data.get("mode") or "")
    if not title or len(title) > 80 or mode not in MODES:
        return JSONResponse({"ok": False, "msg": "Check title and showcase type"}, status_code=400)
    try:
        sale_url = _https(data.get("sale_url") or "")
        background_url = _https(data.get("background_url") or "")
    except ValueError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)
    paid = bool(data.get("is_paid"))
    if paid and not sale_url:
        return JSONResponse({"ok": False, "msg": "Add a purchase link"}, status_code=400)
    if not paid and not row.get("archive_path"):
        return JSONResponse({"ok": False, "msg": "This work has no ZIP. Publish a new free release with files"}, status_code=400)
    if not paid and mode != row.get("mode"):
        stored = str(row["archive_path"])
        path = _safe_data_path(stored)
        try:
            if path and path.is_file():
                zip_data = await run_in_threadpool(path.read_bytes)
            elif object_store.configured():
                zip_data = await run_in_threadpool(object_store.get_bytes,
                    object_store.key_from_stored(stored), public=False)
            else:
                raise ValueError("ZIP is temporarily unavailable")
            await run_in_threadpool(_check_archive, zip_data, mode)
        except ValueError as exc:
            return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)
        except Exception:
            LOGGER.exception("gallery mode validation failed for %s", item_id)
            return JSONResponse({"ok": False, "msg": "Could not check the ZIP for this showcase type"}, status_code=503)
    ok = auth_db.gallery_release_update(item_id, int(user["id"]), title=title,
        description=str(data.get("description") or "")[:2000], mode=mode,
        background_url=background_url, sale_url=sale_url, is_paid=int(paid),
        is_adult=int(bool(data.get("is_adult"))))
    return {"ok": ok}


@router.delete("/api/gallery/works/{item_id}")
def work_remove(item_id: int, request: Request):
    user = _auth_user(request)
    row = auth_db.gallery_get(item_id)
    if not user or not row or int(row.get("user_id") or 0) != int(user["id"]) or row.get("release_version") != 2:
        return JSONResponse({"ok": False, "msg": "Work not found"}, status_code=404)
    if not auth_db.gallery_set_status(item_id, "rejected"):
        return JSONResponse({"ok": False, "msg": "Could not remove"}, status_code=500)
    # Status changes first, so a storage failure never leaves the work public.
    for field, public in (("image_path", True), ("thumb_path", True), ("archive_path", False)):
        stored = row.get(field)
        if not stored:
            continue
        try:
            path = _safe_data_path(str(stored))
            if path:
                path.unlink(missing_ok=True)
            if object_store.configured():
                object_store.delete(object_store.key_from_stored(str(stored)), public=public)
        except Exception:
            LOGGER.exception("gallery release cleanup failed for %s", item_id)
    return {"ok": True}


@router.get("/api/gallery/author/{username}")
def author_profile(username: str, request: Request):
    profile = auth_db.get_public_profile(username)
    if not profile:
        return JSONResponse({"ok": False, "msg": "Author not found"}, status_code=404)
    viewer = _auth_user(request)
    if profile.get("profile_visibility") == "private" and (not viewer or int(viewer["id"]) != profile["id"]):
        return JSONResponse({"ok": False, "msg": "Private profile"}, status_code=403)
    uid = profile["id"]
    return {"ok": True, "name": profile["display_name"], "username": profile["profile_username"],
            "bio": profile["profile_summary"], "avatar_url": f"/api/auth/avatar/{uid}" if profile.get("avatar_path") else "",
            "links": auth_db.get_author_links(uid), "stats": auth_db.gallery_author_stats(uid),
            "owner": bool(viewer and int(viewer["id"]) == uid)}


@router.put("/api/gallery/author/me")
async def author_profile_update(request: Request):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Sign in first"}, status_code=401)
    try:
        data = await request.json()
    except ValueError:
        return JSONResponse({"ok": False, "msg": "Invalid profile details"}, status_code=400)
    if not isinstance(data, dict) or not isinstance(data.get("links", {}), dict):
        return JSONResponse({"ok": False, "msg": "Invalid profile details"}, status_code=400)
    links = {}
    try:
        for key in SOCIALS:
            links[key] = _https((data.get("links") or {}).get(key) or "")
    except (ValueError, AttributeError) as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)
    display_name = str(data.get("name") or "").strip()[:40]
    bio = str(data.get("bio") or "").strip()[:1000]
    username = str(data.get("username") or "").strip()
    fields = {"display_name": display_name, "profile_summary": bio}
    if username:
        fields["profile_username"] = username
    ok, msg = auth_db.update_steam_profile(int(user["id"]), **fields)
    if not ok:
        return JSONResponse({"ok": False, "msg": msg}, status_code=400)
    auth_db.set_author_links(int(user["id"]), links)
    return {"ok": True, "username": auth_db.ensure_profile_username(int(user["id"]))}


@router.post("/api/gallery/author/avatar")
async def author_avatar_upload(request: Request, file: UploadFile = File(...)):
    user = _auth_user(request)
    if not user:
        return JSONResponse({"ok": False, "msg": "Sign in first"}, status_code=401)
    try:
        raw = await _read_bounded(file, 5 * 1024 * 1024)
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > 16_000_000:
                raise ValueError("Avatar dimensions are too large")
            image.load()
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            image.convert("RGB").save(out, "JPEG", quality=88, optimize=True)
            data = out.getvalue()
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return JSONResponse({"ok": False, "msg": "Upload a PNG, JPG or WebP under 5 MB"}, status_code=400)
    uid = int(user["id"])
    key = f"avatars/{uid}_{secrets.token_hex(8)}.jpg"
    path = Path(DATA) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    old_key = auth_db.user_avatar_path(uid)
    try:
        if object_store.configured():
            await run_in_threadpool(object_store.put_bytes, key, data, media_type="image/jpeg", immutable=True)
        ok, _ = auth_db.update_steam_profile(uid, avatar_path=key)
        if not ok:
            raise RuntimeError("avatar save failed")
    except Exception:
        path.unlink(missing_ok=True)
        if object_store.configured():
            try:
                await run_in_threadpool(object_store.delete, key, public=True)
            except Exception:
                LOGGER.exception("author avatar mirror cleanup failed")
        LOGGER.exception("author avatar upload failed")
        return JSONResponse({"ok": False, "msg": "Could not save avatar"}, status_code=500)
    if re.fullmatch(rf"avatars/{uid}_[a-f0-9]{{16}}\.jpg", old_key) and old_key != key:
        old_path = _safe_data_path(old_key)
        if old_path:
            old_path.unlink(missing_ok=True)
        if object_store.configured():
            try:
                await run_in_threadpool(object_store.delete, old_key, public=True)
            except Exception:
                LOGGER.exception("previous author avatar cleanup failed for %s", uid)
    return {"ok": True, "avatar_url": f"/api/auth/avatar/{uid}?v={secrets.token_hex(4)}"}
