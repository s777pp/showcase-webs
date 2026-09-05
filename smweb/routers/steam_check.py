"""Pro-only Steam readiness checker API."""
from __future__ import annotations

import io
import os
import re
import zipfile
from pathlib import PurePosixPath

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from smweb.core import MAX_UPLOAD_MB, quota_state
from smweb.steam_readiness import Candidate, analyze_groups


router = APIRouter()
_MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif"}
_MAX_FILES = 60
_MAX_ARCHIVE_BYTES = 250 * 1024 * 1024


def _safe_archive_name(value: str) -> str:
    value = (value or "file").replace("\\", "/")
    parts = [part for part in PurePosixPath(value).parts if part not in ("", ".", "..")]
    return "/".join(parts)[-240:] or "file"


def _group_name(filename: str) -> str:
    parent = str(PurePosixPath(filename).parent)
    return "Files" if parent in ("", ".") else parent[-120:]


def _archive_groups(raw: bytes) -> dict[str, list[Candidate]]:
    groups: dict[str, list[Candidate]] = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        if len(entries) > _MAX_FILES:
            raise ValueError("archive_file_limit")
        total = sum(max(0, int(entry.file_size)) for entry in entries)
        if total > _MAX_ARCHIVE_BYTES:
            raise ValueError("archive_size_limit")
        for entry in entries:
            name = _safe_archive_name(entry.filename)
            if PurePosixPath(name).suffix.lower() not in _MEDIA_EXTENSIONS:
                continue
            if entry.file_size > max(MAX_UPLOAD_MB, 10) * 1024 * 1024:
                raise ValueError("archive_entry_too_large")
            # Reject extreme compression ratios before decompression.
            if entry.file_size > 1024 * 1024 and entry.compress_size and entry.file_size / entry.compress_size > 200:
                raise ValueError("archive_ratio")
            data = archive.read(entry)
            groups.setdefault(_group_name(name), []).append(Candidate(name, data))
    return groups


@router.post("/api/steam-check")
async def steam_check(
    request: Request,
    mode: str = Form("auto"),
    files: list[UploadFile] = File(...),
):
    quota = quota_state(request)
    if not quota.get("email"):
        return JSONResponse({"ok": False, "msg": "Log in required", "code": "auth"}, status_code=401)
    if not quota.get("pro"):
        return JSONResponse({"ok": False, "msg": "Steam Check is available with Pro", "code": "pro"}, status_code=403)
    mode = (mode or "auto").strip().lower()
    if mode not in {"auto", "workshop", "featured", "split"}:
        return JSONResponse({"ok": False, "msg": "Unknown showcase type"}, status_code=400)
    if not files or len(files) > int(os.environ.get("STEAM_CHECK_MAX_UPLOADS", "20")):
        return JSONResponse({"ok": False, "msg": "Upload between 1 and 20 files"}, status_code=400)

    request_limit = int(os.environ.get("STEAM_CHECK_MAX_REQUEST_MB", "120")) * 1024 * 1024
    total = 0
    groups: dict[str, list[Candidate]] = {}
    try:
        for upload in files:
            chunks = []
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > request_limit:
                    return JSONResponse({"ok": False, "msg": "Total upload is too large", "code": "size"}, status_code=413)
                chunks.append(chunk)
            raw = b"".join(chunks)
            name = _safe_archive_name(upload.filename or "file")
            if name.lower().endswith(".zip"):
                nested = await run_in_threadpool(_archive_groups, raw)
                for group, items in nested.items():
                    groups.setdefault(group, []).extend(items)
            elif PurePosixPath(name).suffix.lower() in _MEDIA_EXTENSIONS:
                groups.setdefault("Files", []).append(Candidate(name, raw))
            else:
                return JSONResponse({"ok": False, "msg": f"Unsupported file: {name}", "code": "format"}, status_code=400)
        if not groups:
            return JSONResponse({"ok": False, "msg": "No PNG, JPG or GIF files found", "code": "empty"}, status_code=400)
        report = await run_in_threadpool(analyze_groups, groups, mode)
        return {"ok": True, "report": report}
    except zipfile.BadZipFile:
        return JSONResponse({"ok": False, "msg": "The ZIP archive is damaged", "code": "zip"}, status_code=400)
    except ValueError as exc:
        messages = {
            "archive_file_limit": "The ZIP contains too many files",
            "archive_size_limit": "The unpacked ZIP is too large",
            "archive_entry_too_large": "A file inside the ZIP is too large",
            "archive_ratio": "Unsafe ZIP compression ratio",
        }
        return JSONResponse({"ok": False, "msg": messages.get(str(exc), "Could not inspect ZIP"), "code": "zip"}, status_code=400)
