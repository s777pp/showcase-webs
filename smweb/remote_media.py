"""Bounded Steam media downloads; validate redirects before following them."""
from urllib.parse import urljoin, urlsplit

import requests


STEAM_HOSTS = (
    "images.steamusercontent.com",
    "steamuserimages-a.akamaihd.net",
    "steamcommunity-a.akamaihd.net",
)
STEAM_SUFFIXES = (".steamstatic.com", ".steampowered.com")


def validate_media_url(url, *, hosts=STEAM_HOSTS, suffixes=STEAM_SUFFIXES,
                       schemes=("https", "http")):
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        valid = (parsed.scheme in schemes and not parsed.username and not parsed.password
                 and parsed.port in (None, 443 if parsed.scheme == "https" else 80)
                 and (host in hosts or any(host.endswith(s) for s in suffixes)))
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ValueError("media_url_not_allowed")


def fetch_media(url, *, max_bytes, hosts=STEAM_HOSTS, suffixes=STEAM_SUFFIXES,
                schemes=("https", "http"), timeout=(5, 15), user_agent="ShowcaseMaker/1.0"):
    """Return bytes and MIME type, closing every response, including failures.

    Do not trust Content-Length alone: streamed/decompressed bytes are bounded too.
    Never let requests follow a redirect to an unvalidated destination.
    """
    for hop in range(4):
        validate_media_url(url, hosts=hosts, suffixes=suffixes, schemes=schemes)
        with requests.get(url, timeout=timeout, stream=True, allow_redirects=False,
                          headers={"User-Agent": user_agent}) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location or hop == 3:
                    raise ValueError("media_redirect_limit")
                url = urljoin(url, location)
                continue
            if response.status_code != 200:
                raise ValueError("media_upstream_error")
            if int(response.headers.get("Content-Length", "0")) > max_bytes:
                raise ValueError("media_too_large")
            content_type = response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0].strip().lower()
            if not (content_type.startswith("image/") or content_type in ("video/webm", "video/mp4")):
                raise ValueError("media_type_not_allowed")
            body = bytearray()
            for chunk in response.iter_content(65536):
                if len(body) + len(chunk) > max_bytes:
                    raise ValueError("media_too_large")
                body.extend(chunk)
            return bytes(body), content_type
    raise ValueError("media_redirect_limit")
