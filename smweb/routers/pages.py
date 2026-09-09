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
from urllib.parse import quote, urlparse

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db


from fastapi import APIRouter


from smweb.core import JOBS, STATIC, _auth_user
from smweb.job_access import browser_owns_job
from smweb.locales import SUPPORTED_LANGUAGES, localized_path, localized_request_url



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


# The HTML shell must not be cached: it carries the ?v= tags that bust the
# 7-day cache nginx puts on /static/. A stale shell keeps pointing at the old
# JS, which is how a deployed frontend fix can stay invisible for a week.
_HTML_HEADERS = {"Cache-Control": "no-cache"}


def _html(content: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(content, status_code=status_code, headers=_HTML_HEADERS)


def _localized_html(filename: str, language: str, route_path: str = "/", status_code: int = 200) -> HTMLResponse:
    content = _page(STATIC / filename)
    content = re.sub(r'<html\b([^>]*?)\blang="[^"]*"', rf'<html\1lang="{language}"', content, count=1, flags=re.I)
    content = content.replace('href="/"', f'href="{localized_path(language, "/")}"')
    if 'rel="canonical"' not in content:
        canonical_path = localized_path(language, route_path)
        locale_links = [f'<link rel="alternate" hreflang="{code}" href="https://showcasemaker.com{localized_path(code, route_path)}">' for code in SUPPORTED_LANGUAGES]
        locale_links.append(f'<link rel="alternate" hreflang="x-default" href="https://showcasemaker.com{localized_path("en", route_path)}">')
        metadata = f'<link rel="canonical" href="https://showcasemaker.com{canonical_path}">\n' + "\n".join(locale_links) + "\n"
        content = content.replace("</head>", metadata + "</head>", 1)
    response = _html(content, status_code=status_code)
    response.headers["Content-Language"] = language
    return response


def _legacy_redirect(request: Request, path: str | None = None) -> RedirectResponse:
    return RedirectResponse(localized_request_url(request, path), status_code=307,
                            headers={"Cache-Control": "no-cache", "Vary": "Accept-Language, Cookie"})


@router.get("/", include_in_schema=False)
def index(request: Request):
    return _legacy_redirect(request, "/")


@router.get("/app", include_in_schema=False)
def app_page(request: Request):
    return _legacy_redirect(request, "/app")


@router.get("/privacy", response_class=HTMLResponse)
@router.get("/privacy/", response_class=HTMLResponse, include_in_schema=False)
def privacy_page(request: Request, lang: str = ""):
    # Keep ?lang= links from old extension releases working, but make the
    # canonical destination an explicit language URL.
    if lang in SUPPORTED_LANGUAGES:
        return RedirectResponse(localized_path(lang, "/privacy"), status_code=307,
                                headers={"Cache-Control": "no-cache"})
    return _legacy_redirect(request, "/privacy")


@router.get("/profile", response_class=HTMLResponse)
@router.get("/profile/", response_class=HTMLResponse)
async def profile_me(request: Request):
    return _legacy_redirect(request, "/profile")


@router.get("/profile/{username}", response_class=HTMLResponse)
async def profile_public(username: str, request: Request):
    return _legacy_redirect(request, "/profile/" + quote(username, safe=""))


@router.get("/preview/{job_id}", response_class=HTMLResponse)
def preview_page(job_id: str, request: Request):
    if not re.fullmatch(r"[a-f0-9]{32}", job_id or ""):
        return _html("<h3>Preview not found</h3>", status_code=404)
    path = JOBS / job_id / "preview.html"
    if not browser_owns_job(path.parent, request) or not path.is_file():
        return _html("<h3>Preview not found</h3>", status_code=404)
    return _html(path.read_text(encoding="utf-8"))


@router.get("/gallery", include_in_schema=False)
def gallery_page(request: Request):
    return _legacy_redirect(request, "/gallery")


def _landing(language: str):
    return _localized_html("index.html", language, "/")


def _app(language: str):
    filename = "app.html" if (STATIC / "app.html").is_file() else "index.html"
    return _localized_html(filename, language, "/app")


def _privacy(language: str):
    filename = f"privacy-{language}.html"
    if not (STATIC / filename).is_file():
        filename = "privacy-en.html"
    return _localized_html(filename, language, "/privacy")


def _profile(language: str):
    if not (STATIC / "profile.html").is_file():
        return _html("profile.html missing", status_code=404)
    return _localized_html("profile.html", language, "/profile")


def _public_profile(language: str, username: str):
    filename = "profile-view.html" if (STATIC / "profile-view.html").is_file() else "profile.html"
    if not (STATIC / filename).is_file():
        return _html("profile page missing", status_code=404)
    return _localized_html(filename, language, "/profile/" + quote(username, safe=""))


def _gallery(language: str):
    if (STATIC / "gallery.html").is_file():
        return _localized_html("gallery.html", language, "/gallery")
    return _html("<h1>Gallery</h1>", status_code=404)


# Register concrete prefixes instead of a catch-all /{lang} route.  This keeps
# /api, /static and future one-segment routes impossible to shadow.
def _language_page(handler, language: str):
    def serve():
        return handler(language)
    return serve


def _language_profile(language: str):
    def serve(username: str):
        return _public_profile(language, username)
    return serve


for _language in SUPPORTED_LANGUAGES:
    router.add_api_route(f"/{_language}", _language_page(_landing, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/", _language_page(_landing, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/app", _language_page(_app, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/privacy", _language_page(_privacy, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/profile", _language_page(_profile, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/profile/", _language_page(_profile, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/profile/{{username}}", _language_profile(_language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    router.add_api_route(f"/{_language}/gallery", _language_page(_gallery, _language),
                         methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
