"""HTTP session and Pinterest scraping used by /api/download-url.

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


def _dl_session():
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def _download_pinterest(url: str, out_dir: Path) -> Path:
    """Картинки Pinterest — чистим URL и качаем с нормальными заголовками."""
    import re
    from urllib.parse import urlparse, unquote

    def clean_img_url(u: str) -> str:
        u = unquote(u).replace("&amp;", "&").replace("\\/", "/").strip()
        # обрезать CSS/мусор после расширения
        m = re.search(
            r"(https?://[^\s\"'<>]+?\.(?:jpg|jpeg|png|webp|gif))",
            u,
            re.I,
        )
        if m:
            return m.group(1)
        # pinimg path without query garbage
        m = re.search(r"(https?://i\.pinimg\.com/[^\s\"'<>]+)", u, re.I)
        if m:
            return re.split(r"[\"'\s<>{]", m.group(1))[0]
        return u.split()[0] if u else u

    s = _dl_session()
    s.headers.update({
        "Referer": "https://www.pinterest.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
    })
    html = s.get(url, timeout=30).text

    candidates = []
    for pat in (
        r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
        r'"url"\s*:\s*"(https://i\.pinimg\.com[^"]+)"',
        r"(https://i\.pinimg\.com/[^\s\"'<>]+)",
    ):
        for m in re.finditer(pat, html, re.I):
            candidates.append(clean_img_url(m.group(1)))

    def score(u: str) -> int:
        ul = u.lower()
        sc = 0
        if "originals" in ul:
            sc += 80
        if "/1200x" in ul or "1200x" in ul:
            sc += 40
        if "736x" in ul:
            sc += 20
        if any(x in ul for x in ("236x", "474x", "60x60", "75x75")):
            sc -= 20
        if ul.endswith((".png", ".jpg", ".jpeg", ".webp")):
            sc += 5
        return sc

    seen, ordered = set(), []
    for u in candidates:
        u = clean_img_url(u)
        if not u.startswith("http") or u in seen:
            continue
        seen.add(u)
        ordered.append(u)
    ordered.sort(key=score, reverse=True)
    if not ordered:
        raise RuntimeError("не найдено изображение на странице")

    last_err = None
    for img_url in ordered[:8]:
        try:
            # originals часто 403 → пробуем 1200x
            tries = [img_url]
            if "originals" in img_url:
                tries.append(
                    re.sub(r"/originals/", "/1200x/", img_url, count=1, flags=re.I)
                )
                tries.append(
                    re.sub(r"/originals/", "/736x/", img_url, count=1, flags=re.I)
                )
            for turl in tries:
                turl = clean_img_url(turl)
                rr = s.get(
                    turl,
                    timeout=60,
                    stream=True,
                    headers={
                        **s.headers,
                        "Referer": "https://www.pinterest.com/",
                        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        "Sec-Fetch-Dest": "image",
                        "Sec-Fetch-Mode": "no-cors",
                    },
                )
                if rr.status_code == 403:
                    last_err = f"403 {turl[:80]}"
                    continue
                rr.raise_for_status()
                ct = (rr.headers.get("Content-Type") or "").lower()
                if "html" in ct:
                    last_err = "got html"
                    continue
                ext = ".jpg"
                if "png" in ct or turl.lower().endswith(".png"):
                    ext = ".png"
                elif "webp" in ct or turl.lower().endswith(".webp"):
                    ext = ".webp"
                elif "gif" in ct or turl.lower().endswith(".gif"):
                    ext = ".gif"
                dest = out_dir / f"pinterest_{uuid.uuid4().hex[:8]}{ext}"
                with open(dest, "wb") as f:
                    for chunk in rr.iter_content(64 * 1024):
                        if chunk:
                            f.write(chunk)
                if dest.stat().st_size < 800:
                    dest.unlink(missing_ok=True)
                    last_err = "too small"
                    continue
                return dest
        except Exception as e:
            last_err = str(e)
            continue
    raise RuntimeError(last_err or "download failed")
