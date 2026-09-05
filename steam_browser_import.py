"""Rendered Steam profile loader backed by Bright Data Browser API.

The rest of the application only needs one small interface: ``fetch_html``.
Credentials, the CDP connection, scrolling and anti-bot/error detection stay
inside this adapter.  No Steam login session is used; only public profiles are
read.
"""
from __future__ import annotations

import os
import re
from urllib.parse import quote, urlparse


class BrowserImportError(RuntimeError):
    """A rendered profile could not be collected safely or completely."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def configured() -> bool:
    return bool((os.environ.get("BRIGHTDATA_BROWSER_USERNAME") or "").strip() and
                (os.environ.get("BRIGHTDATA_BROWSER_PASSWORD") or "").strip())


def _endpoint() -> str:
    username = (os.environ.get("BRIGHTDATA_BROWSER_USERNAME") or "").strip()
    password = (os.environ.get("BRIGHTDATA_BROWSER_PASSWORD") or "").strip()
    host = (os.environ.get("BRIGHTDATA_BROWSER_HOST") or "brd.superproxy.io").strip()
    port = int(os.environ.get("BRIGHTDATA_BROWSER_PORT") or "9222")
    return "wss://{}:{}@{}:{}".format(
        quote(username, safe=""), quote(password, safe=""), host, port,
    )


def _public_profile_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or host not in {"steamcommunity.com", "www.steamcommunity.com"}:
        raise BrowserImportError("steam_profile_url", "Only public steamcommunity.com profiles are supported")
    if not re.fullmatch(r"/(id|profiles)/[^/?#]+/?", parsed.path, re.I):
        raise BrowserImportError("steam_profile_url", "Enter a public Steam profile URL")
    return "https://steamcommunity.com{}?l=english".format(parsed.path.rstrip("/"))


def fetch_html(url: str, progress=None) -> str:
    """Return the fully rendered and scrolled public Steam profile HTML."""
    if not configured():
        raise BrowserImportError("steam_browser_not_configured", "Browser import is not configured")

    target = _public_profile_url(url)
    timeout_ms = max(30_000, min(180_000, int(os.environ.get("STEAM_BROWSER_TIMEOUT_MS") or "90000")))

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserImportError("steam_browser_dependency", "Playwright is not installed") from exc

    def report(stage: str, pct: int) -> None:
        if progress:
            progress(stage, pct)

    report("browser_connect", 12)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(_endpoint(), timeout=timeout_ms)
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.pages[0] if context.pages else context.new_page()
                # The parser needs DOM attributes and Steam's scripts, not the
                # image/video bytes themselves. Blocking heavy media makes the
                # profile interactive sooner and sharply reduces Browser API
                # traffic without losing showcase URLs from page.content().
                page.route(
                    "**/*",
                    lambda route: route.abort()
                    if route.request.resource_type in {"image", "media", "font"}
                    else route.continue_(),
                )
                report("steam_open", 24)
                response = page.goto(target, wait_until="domcontentloaded", timeout=timeout_ms)
                if response and response.status >= 400:
                    raise BrowserImportError("steam_browser_http", f"Steam returned HTTP {response.status}")
                page.wait_for_selector(".profile_page", timeout=timeout_ms)
                report("steam_showcases", 42)

                stable = 0
                previous = (-1, -1)
                for _ in range(16):
                    current = page.evaluate("""() => {
                      const root = document.scrollingElement || document.documentElement;
                      window.scrollTo(0, root.scrollHeight);
                      return [root.scrollHeight, document.querySelectorAll('.profile_customization').length];
                    }""")
                    page.wait_for_timeout(180)
                    current_pair = (int(current[0]), int(current[1]))
                    stable = stable + 1 if current_pair == previous else 0
                    previous = current_pair
                    if stable >= 2:
                        break

                report("steam_media", 68)
                # One short settle is enough for DOM mutations triggered by the
                # final scroll; actual media downloads were blocked above.
                page.wait_for_timeout(250)
                html = page.content()
            finally:
                browser.close()
    except BrowserImportError:
        raise
    except Exception as exc:
        # Playwright connection errors can echo the full CDP endpoint, which
        # embeds the Browser API password. Never expose the original text.
        low = str(exc).lower()
        code = "steam_browser_auth" if any(x in low for x in ("401", "403", "407", "authentication")) else "steam_browser_unavailable"
        message = ("Remote browser authentication failed" if code == "steam_browser_auth"
                   else "Remote browser is unavailable")
        raise BrowserImportError(code, message) from exc

    low = html.lower()
    if "profile_page" not in low:
        if any(x in low for x in ("captcha", "challenge-platform", "access denied", "too many requests")):
            raise BrowserImportError("steam_browser_blocked", "Steam blocked the rendered browser session")
        raise BrowserImportError("steam_profile_incomplete", "Steam did not return a complete public profile")
    report("steam_parse", 78)
    return html
