"""HTML pages: landing, app, profile, gallery, preview.

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
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db


from fastapi import APIRouter


from smweb.core import JOBS, STATIC, _auth_user



router = APIRouter()


# ---- page cache ---------------------------------------------------------
# Every page handler used to read its HTML off disk on every single request.
# On Railway the app directory is a network volume, so that is a syscall round
# trip per page view for a file that changes only on deploy - and in the two
# async handlers below it blocked the event loop while it happened.
#
# Keyed on (mtime, size) so editing a file during development still shows up
# without a restart. Only the fixed pages under static/ are cached; a job's
# preview.html is not, because job ids are unbounded and would grow this dict
# forever.
_PAGE_CACHE: dict[str, tuple[float, int, str]] = {}


def _page(path: Path) -> str:
    """Read an HTML page, reusing the cached text while the file is unchanged."""
    key = str(path)
    try:
        st = path.stat()
    except OSError:
        _PAGE_CACHE.pop(key, None)
        raise
    hit = _PAGE_CACHE.get(key)
    if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
        return hit[2]
    text = path.read_text(encoding="utf-8")
    _PAGE_CACHE[key] = (st.st_mtime, st.st_size, text)
    return text


@router.get("/", response_class=HTMLResponse)
def index():
    """Лендинг (как kant.tools)."""
    path = STATIC / "index.html"
    return HTMLResponse(_page(path))


@router.get("/app", response_class=HTMLResponse)
def app_page():
    """Рабочая панель инструментов."""
    path = STATIC / "app.html"
    if not path.is_file():
        path = STATIC / "index.html"
    return HTMLResponse(_page(path))


@router.get("/profile", response_class=HTMLResponse)
@router.get("/profile/", response_class=HTMLResponse)
async def profile_me(request: Request):
    """Owner shortcut → /profile/{username} or login prompt page."""
    user = _auth_user(request)
    p = STATIC / "profile.html"
    if not p.is_file():
        return HTMLResponse("profile.html missing", status_code=404)
    html = _page(p)
    return HTMLResponse(html)


@router.get("/profile/{username}", response_class=HTMLResponse)
async def profile_public(username: str, request: Request):
    """Public full-page profile (not the editor)."""
    p = STATIC / "profile-view.html"
    if not p.is_file():
        p = STATIC / "profile.html"
    if not p.is_file():
        return HTMLResponse("profile page missing", status_code=404)
    return HTMLResponse(_page(p))


@router.get("/preview/{job_id}", response_class=HTMLResponse)
def preview_page(job_id: str):
    job_id = "".join(c for c in job_id if c.isalnum())[:16]
    path = JOBS / job_id / "preview.html"
    if not path.is_file():
        return HTMLResponse("<h3>Preview not found</h3>", status_code=404)
    return HTMLResponse(path.read_text(encoding="utf-8"))


@router.get("/gallery", response_class=HTMLResponse)
def gallery_page():
    path = STATIC / "gallery.html"
    if path.is_file():
        return HTMLResponse(_page(path))
    return HTMLResponse("<h1>Gallery</h1><p>Add static/gallery.html</p>")
