"""Direct-access mirror (e.g. ru.showcasemaker.com) for visitors who cannot reach Cloudflare.

The main domain goes through a Cloudflare tunnel, and Cloudflare addresses are
often blocked in Russia.  A mirror host points straight at the VPS, where Caddy
terminates TLS (deploy/mirror).  Two things would still leak to Cloudflare:

* redirects and URLs that point at R2 (media.showcasemaker.com and presigned
  *.r2.cloudflarestorage.com links) -- rewritten here to /r2m/ and /r2s/,
  which Caddy on the mirror proxies server-side;
* login return URLs built from APP_URL -- while a mirror request is being
  handled, ``current_origin()`` returns the mirror origin instead.

Nothing changes for requests on the main domain.
"""
from __future__ import annotations

import os
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

MIRROR_HOSTS = {h.strip().lower() for h in (os.environ.get("MIRROR_HOSTS") or "").split(",") if h.strip()}
_current: ContextVar[str] = ContextVar("mirror_origin", default="")
_REWRITE_TYPES = ("json", "html", "javascript", "text/css", "text/plain")
_REWRITE_LIMIT = 8 * 1024 * 1024


def current_origin() -> str:
    """Mirror origin (https://host) while serving a mirror request, else ""."""
    return _current.get()


def _targets() -> list[tuple[bytes, bytes]]:
    pairs = []
    media = (os.environ.get("R2_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if media:
        pairs.append((media.encode(), b"/r2m"))
    endpoint = (os.environ.get("R2_ENDPOINT") or "").strip().rstrip("/")
    account = (os.environ.get("R2_ACCOUNT_ID") or "").strip()
    if not endpoint and account:
        endpoint = f"https://{account}.r2.cloudflarestorage.com"
    if endpoint:
        pairs.append((endpoint.encode(), b"/r2s"))
    return pairs


def rewrite(data: bytes) -> bytes:
    for old, new in _targets():
        data = data.replace(old, new)
    return data


class MirrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        host = (request.headers.get("host") or "").split(":")[0].strip().lower()
        if host not in MIRROR_HOSTS:
            return await call_next(request)
        token = _current.set(f"https://{host}")
        try:
            response = await call_next(request)
        finally:
            _current.reset(token)
        location = response.headers.get("location")
        if location:
            response.headers["location"] = rewrite(location.encode()).decode()
        ctype = (response.headers.get("content-type") or "").lower()
        size = int(response.headers.get("content-length") or 0)
        if (not any(t in ctype for t in _REWRITE_TYPES) or size > _REWRITE_LIMIT
                or response.headers.get("content-encoding")):
            return response
        body = rewrite(b"".join([chunk async for chunk in response.body_iterator]))
        rewritten = Response(body, status_code=response.status_code)
        # raw_headers keeps repeated headers such as several Set-Cookie lines.
        rewritten.raw_headers = [(k, v) for k, v in response.raw_headers if k.lower() != b"content-length"]
        rewritten.raw_headers.append((b"content-length", str(len(body)).encode()))
        return rewritten
