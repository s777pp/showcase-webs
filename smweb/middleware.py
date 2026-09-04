"""Request id, security headers, rate limits, compression, static caching.

The first three moved out of main.py unchanged; see docs/STRUCTURE.md. The last
two were added afterwards - nothing was compressing responses and nothing was
telling browsers they could keep a static asset.
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


from smweb.core import _ip


# ---- production middleware: request id + rate limits ----
import uuid as _uuid


from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("X-Request-ID") or _uuid.uuid4().hex[:16]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline security headers.

    docker-compose sets these in Nginx, but Railway runs the app with nothing
    in front of it, so in production nobody was sending them at all.

    The CSP is deliberately loose on inline script/style — the pages are HTML
    monoliths with inline handlers everywhere, and a strict policy would blank
    the whole UI. It still pins where scripts, frames and connections may come
    from, which is what stops an injected <script src> from calling out.
    """
    CSP = "; ".join((
        "default-src 'self'",
        # 'unsafe-inline'/'unsafe-eval' are required by the current inline JS.
        # telegram.org is the login widget, injected at runtime by sm-auth.js.
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://telegram.org",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob: https:",
        "media-src 'self' data: blob: https:",
        "connect-src 'self' https:",
        "frame-src 'self' https://telegram.org https://oauth.telegram.org",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'self'",
    ))

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "SAMEORIGIN")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        h.setdefault("Content-Security-Policy", self.CSP)
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
        if proto == "https":
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Light Redis/local rate limits on sensitive paths."""
    RULES = (
        ("/api/auth/login", 20, 60),
        ("/api/auth/register", 10, 60),
        # Guessing an access code was unlimited before: /api/unlock was simply
        # not on this list, so a script could try codes as fast as it liked.
        ("/api/unlock", 10, 60),
        # Wiping every account should not be reachable at machine speed even
        # with a leaked secret.
        ("/api/admin/", 5, 60),
        ("/api/process", 8, 60),
        ("/api/process/start", 8, 60),
        # Compose is the most expensive route in the app (minutes of FFmpeg per
        # call) and, like the endpoint it replaced, does not consume the daily
        # quota -- so this rule is what keeps it from being a free CPU faucet.
        ("/api/compose/start", 6, 60),
        ("/api/gallery/", 60, 60),
        ("/api/download-url", 5, 60),
    )
    async def dispatch(self, request, call_next):
        path = request.url.path
        # Same IP source as the quota. This used to read request.client.host
        # directly, which behind a proxy is the PROXY's address — so every user
        # shared one bucket and a single client could lock login for everyone.
        client = _ip(request)
        for prefix, limit, window in self.RULES:
            if path.startswith(prefix) and request.method in ("POST", "PUT", "DELETE", "PATCH"):
                ok, _left = rs.rate_limit(f"{prefix}:{client}", limit, window)
                if not ok:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        {"ok": False, "msg": "Too many requests. Slow down."},
                        status_code=429,
                    )
                break
        return await call_next(request)


# ---- compression --------------------------------------------------------
import gzip as _gzip

from starlette.datastructures import Headers, MutableHeaders


class GZipMiddleware:
    """Compress text responses; leave everything else byte-for-byte alone.

    Starlette's own GZipMiddleware compresses by size only, with no idea what
    it is compressing. Here that would be actively harmful: static/video holds
    two ~48 MB mp4 files, and compressing those would burn the whole CPU budget
    for no gain while destroying the Range requests the browser needs to seek.

    So the decision is made on the response Content-Type, which is only known
    once the handler has replied - hence the raw ASGI form rather than
    BaseHTTPMiddleware. Anything not in COMPRESSIBLE is passed through
    untouched, as is a partial response (206) or one that is already encoded.
    """

    COMPRESSIBLE = (
        "text/", "application/json", "application/javascript",
        "application/xml", "application/manifest+json", "image/svg+xml",
    )
    # Above this we stop buffering and fall back to sending it uncompressed:
    # holding a huge body in RAM is the failure mode we are trying to avoid.
    MAX_BUFFER = 4 * 1024 * 1024

    def __init__(self, app, minimum_size: int = 500, compresslevel: int = 6):
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        accept = Headers(scope=scope).get("accept-encoding", "")
        if "gzip" not in accept.lower():
            await self.app(scope, receive, send)
            return
        await _GZipResponder(self.app, self)(scope, receive, send)


class _GZipResponder:
    """Holds back response.start until the Content-Type is known."""

    def __init__(self, app, cfg: GZipMiddleware):
        self.app = app
        self.cfg = cfg
        self.send = None
        self.start = None      # withheld http.response.start
        self.buf = bytearray()
        self.mode = "deciding"  # deciding -> compress | passthrough

    async def __call__(self, scope, receive, send):
        self.send = send
        await self.app(scope, receive, self._send)

    def _compressible(self, message) -> bool:
        if message["status"] != 200:
            return False
        h = Headers(raw=message["headers"])
        if h.get("content-encoding"):
            return False
        ctype = h.get("content-type", "").split(";")[0].strip().lower()
        return ctype.startswith(self.cfg.COMPRESSIBLE)

    async def _flush_plain(self, more: bool) -> None:
        """Give up on compressing: send what we held back, unchanged."""
        self.mode = "passthrough"
        await self.send(self.start)
        await self.send({"type": "http.response.body",
                         "body": bytes(self.buf), "more_body": more})
        self.buf.clear()

    async def _send(self, message) -> None:
        if self.mode == "passthrough":
            await self.send(message)
            return

        if message["type"] == "http.response.start":
            if self._compressible(message):
                self.start = message
                self.mode = "deciding"
            else:
                self.mode = "passthrough"
                await self.send(message)
            return

        if message["type"] != "http.response.body":
            await self.send(message)
            return
        self.buf += message.get("body", b"")
        more = message.get("more_body", False)

        # Still streaming: keep buffering unless it is getting too big.
        if more:
            if len(self.buf) > self.cfg.MAX_BUFFER:
                await self._flush_plain(True)
            return

        # Last chunk: now the full body is known.
        if len(self.buf) < self.cfg.minimum_size:
            await self._flush_plain(False)
            return

        body = _gzip.compress(bytes(self.buf), self.cfg.compresslevel)
        if len(body) >= len(self.buf):      # incompressible after all
            await self._flush_plain(False)
            return

        h = MutableHeaders(raw=self.start["headers"])
        h["Content-Encoding"] = "gzip"
        h["Content-Length"] = str(len(body))
        # Same URL can now answer with two different encodings.
        vary = h.get("Vary")
        if not vary:
            h["Vary"] = "Accept-Encoding"
        elif "accept-encoding" not in vary.lower():
            h["Vary"] = vary + ", Accept-Encoding"
        self.mode = "passthrough"
        await self.send(self.start)
        await self.send({"type": "http.response.body", "body": body,
                         "more_body": False})
        self.buf.clear()


# ---- static asset caching -----------------------------------------------
class CachedStaticFiles(StaticFiles):
    """StaticFiles with a Cache-Control, which it does not send by default.

    Without it every asset is revalidated on every navigation: the browser has
    an ETag, so it gets a cheap 304 - but still pays a full round trip per file,
    and this app serves ~140 MB of static assets from the app process itself.

    Filenames are referenced with a ?v= query throughout the HTML, so a long
    max-age is safe: bumping the query is what invalidates a cache entry.
    HTML is deliberately excluded - a page must never be served stale.
    """

    POLICY = (
        ((".woff2", ".woff", ".ttf", ".otf", ".eot"),
         "public, max-age=31536000, immutable"),
        ((".css", ".js", ".mjs"), "public, max-age=2592000"),
        ((".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".svg", ".avif"),
         "public, max-age=604800"),
        ((".mp4", ".webm", ".mov", ".m4v", ".ogg", ".mp3", ".wav"),
         "public, max-age=604800"),
    )

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        lower = path.lower()
        for exts, value in self.POLICY:
            if lower.endswith(exts):
                response.headers.setdefault("Cache-Control", value)
                break
        else:
            if lower.endswith((".html", ".htm", ".json", ".txt")):
                response.headers.setdefault("Cache-Control", "no-cache")
        return response
