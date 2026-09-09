"""Language URL and request helpers for public Showcase Maker pages.

The visible locale lives in the URL.  A small cookie remembers a manual choice
for legacy/unprefixed links; otherwise the first visit follows Accept-Language.
"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import Request


SUPPORTED_LANGUAGES = ("en", "ru", "de", "tr", "fr", "uk", "es", "pt")
DEFAULT_LANGUAGE = "en"


def normalize_language(value: str | None) -> str | None:
    code = str(value or "").strip().lower().replace("_", "-").split("-", 1)[0]
    return code if code in SUPPORTED_LANGUAGES else None


def request_language(request: Request) -> str:
    """Return a saved locale or the best supported browser locale."""
    saved = normalize_language(request.cookies.get("sm_lang"))
    if saved:
        return saved

    weighted: list[tuple[float, int, str]] = []
    for index, part in enumerate(request.headers.get("accept-language", "").split(",")):
        token, *params = part.strip().split(";")
        code = normalize_language(token)
        if not code:
            continue
        quality = 1.0
        for param in params:
            if param.strip().startswith("q="):
                try:
                    quality = float(param.strip()[2:])
                except ValueError:
                    quality = 0.0
        weighted.append((quality, -index, code))
    return max(weighted, default=(0.0, 0, DEFAULT_LANGUAGE))[2]


def localized_path(language: str, path: str = "/") -> str:
    language = normalize_language(language) or DEFAULT_LANGUAGE
    path = "/" + str(path or "/").lstrip("/")
    return f"/{language}" + ("/" if path == "/" else path)


def localized_request_url(request: Request, path: str | None = None) -> str:
    target = localized_path(request_language(request), path or request.url.path)
    if request.url.query:
        target += "?" + request.url.query
    return target
