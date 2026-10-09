"""Page text in the visitor's language already in the HTML the server sends (2026-10-09).

The landing, Tools, gallery and extension pages are authored in English and translated by scripts in the browser.
People never notice, but a search engine that does not run scripts (Yandex, often) read English on /ru/, /de/...
``translate()`` swaps English text nodes of the page body for the text the browser would show, from maps recorded
by scripts/build_server_copy.py (``smweb/server_copy/<lang>.json``: {route: {english: translated}}).

Only text between tags is touched (never attributes, scripts, styles, code, SVG or ``data-no-translate`` parts),
so markup, ids and data-i keys stay exactly as the page scripts expect; they then set the same text again.
A text the map does not know stays English, as before. Results are cached per page version and language.
SERVER_COPY=0 in the environment switches it off (emergency switch; the browser then translates as before).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent / "server_copy"
_TOKENS = re.compile(r"(<!--.*?-->|<![^>]*>|<[^>]+>)", re.S)
_TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9-]*)([^>]*)>", re.S)
_SKIP_TAGS = {"script", "style", "noscript", "textarea", "code", "pre", "svg", "title", "head"}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_CACHE: dict[tuple, str] = {}


@lru_cache(maxsize=16)
def _map(language: str) -> dict:
    try:
        data = json.loads((DIR / f"{language}.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _walk(content: str):
    """Yield (index, token, skipped) for every token; text tokens are checked against the open-element stack."""
    stack: list[bool] = []          # True = this element (or an ancestor) is skipped
    in_body = "<body" not in content
    for index, token in enumerate(_TOKENS.split(content)):
        if not token:
            continue
        if token.startswith("<!"):
            yield index, token, True
            continue
        match = _TAG.match(token) if token.startswith("<") else None
        if match:
            closing, name, rest = match.group(1), match.group(2).lower(), match.group(3)
            if name == "body":
                in_body = not closing
            if closing:
                if stack:
                    stack.pop()
            elif name not in _VOID and not rest.rstrip().endswith("/"):
                parent = stack[-1] if stack else False
                stack.append(parent or name in _SKIP_TAGS or "data-no-translate" in rest)
            yield index, token, True
            continue
        yield index, token, (not in_body) or (stack[-1] if stack else False)


def source_texts(content: str) -> set[str]:
    """Visible body texts of a page as the generator compares them (unescaped, trimmed)."""
    return {html.unescape(token).strip() for _i, token, skipped in _walk(content)
            if not skipped and not token.startswith("<") and token.strip()}


def translate(content: str, language: str, route: str) -> str:
    if language == "en" or os.environ.get("SERVER_COPY", "").strip() == "0":
        return content
    table = _map(language).get(route)
    if not table:
        return content
    key = (language, route, len(content), hashlib.sha1(content.encode("utf-8")).hexdigest())
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    parts = _TOKENS.split(content)
    for index, token, skipped in _walk(content):
        if skipped or token.startswith("<"):
            continue
        core = html.unescape(token).strip()
        other = table.get(core)
        if other:
            lead = token[: len(token) - len(token.lstrip())]
            tail = token[len(token.rstrip()):]
            parts[index] = lead + html.escape(other, quote=False) + tail
    result = "".join(parts)
    if len(_CACHE) > 64:
        _CACHE.clear()
    _CACHE[key] = result
    return result
