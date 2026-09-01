"""Showcase Maker Web — application entry point.

Everything used to live in this file (5338 lines, 85 routes). It now only wires
the pieces together: middleware, static mounts, and one include_router() per
area of the site. The code itself moved into smweb/ unchanged.

Route order matters: FastAPI matches in registration order, so a literal path
has to be registered before a parameterised one that could swallow it.
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


from smweb.core import (
    DATA,
    FONTS,
    FREE_LIMIT,
    HOST,
    JOBS,
    LOGGER,
    MAX_UPLOAD_MB,
    PORT,
    STATIC,
    _auth_user,
    quota_state,
)
from smweb.middleware import (
    CachedStaticFiles,
    GZipMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
)


from smweb import jobs  # noqa: F401  (starts the temp-file cleaner)


from smweb.routers import (
    pages,
    system,
    auth,
    oauth,
    billing,
    profile,
    gallery,
    process,
    media,
    preview,
    deviantart,
)


app = FastAPI(title="Showcase Maker Web")


app.add_middleware(SecurityHeadersMiddleware)


app.add_middleware(RateLimitMiddleware)


app.add_middleware(RequestIdMiddleware)


# Outermost, so it sees the finished response: add_middleware inserts at the
# front of the stack, so the last one added is the first one entered.
app.add_middleware(GZipMiddleware)


app.mount("/static", CachedStaticFiles(directory=str(STATIC)), name="static")


try:
    app.mount("/fonts", CachedStaticFiles(directory=str(FONTS)), name="fonts")
except Exception:
    pass


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    # Full detail to the logs, nothing to the client. Echoing str(exc) leaked
    # filesystem paths, SQL fragments and library internals to anyone who could
    # trigger an error. The request id ties a user report to the log line.
    rid = getattr(request.state, "request_id", "-")
    LOGGER.exception("unhandled error rid=%s path=%s", rid, request.url.path)
    # A too-large image is a client mistake, not a server fault — keep the 400
    # so the UI can still explain it.
    if isinstance(exc, (Image.DecompressionBombError, Image.DecompressionBombWarning)):
        return JSONResponse(
            {"ok": False, "msg": "Image is too large", "request_id": rid},
            status_code=400,
        )
    return JSONResponse(
        {"ok": False, "msg": "Internal error", "request_id": rid},
        status_code=500,
    )


# ---- routes -------------------------------------------------------------
app.include_router(pages.router)
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(billing.router)
app.include_router(profile.router)
app.include_router(gallery.router)
app.include_router(process.router)
app.include_router(media.router)
app.include_router(preview.router)
app.include_router(deviantart.router)


# ====================== Profile builder API (Steam catalogs, projects) ======================
try:
    import tools_api

    tools_api.init(
        quota_state=quota_state,
        auth_user=_auth_user,
        DATA=DATA,
        JOBS=JOBS,
        MAX_UPLOAD_MB=MAX_UPLOAD_MB,
        FREE_LIMIT=FREE_LIMIT,
    )
    app.include_router(tools_api.router)
    LOGGER.info("tools_api mounted")
except Exception as e:
    # The profile builder is optional and must never prevent the rest of the site from starting.
    LOGGER.exception("tools_api not mounted: %s", e)


if __name__ == "__main__":
    import uvicorn
    print(f"\n  Showcase Maker WEB  →  http://{HOST}:{PORT}")
    print(f"  FFmpeg: {proc.find_ffmpeg() or 'НЕ НАЙДЕН'}")
    print(f"  Free limit: {FREE_LIMIT}/day  |  Unlock: SHOWCASE-WEB-PRO\n")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
