"""IndexNow: tell Yandex and Bing (and the other IndexNow engines) about changed pages right away (2026-10-09).

Without it a search engine finds a changed page only when it next re-reads the sitemap. With it:

* a news post is announced the moment it is published (routers/admin.py news save -> ``announce``);
* once an hour the job cleaner compares the sitemap's last-change dates (pages.sitemap_entries) with the newest
  date already announced (``DATA/indexnow.json``) and announces only what changed - after a deploy that is the
  pages whose files changed, plus scheduled news that went live. The very first run announces the whole sitemap.

The key proves the site owns the URLs. It is derived from SECRET_KEY (or INDEXNOW_KEY when set), so nothing has to
be added to .env, and served at ``/<key>.txt`` (pages.py). Only the production site announces: APP_URL must be
https://showcasemaker.com, or INDEXNOW=1; INDEXNOW=0 switches it off. Several processes run the job cleaner, so a
Redis lock lets only one of them announce per hour. Network errors are logged and retried on the next hour.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

LOG = logging.getLogger("sm.indexnow")
HOST = "showcasemaker.com"
SITE = f"https://{HOST}"
# One call to api.indexnow.org is shared with every IndexNow engine; Yandex is also called directly (Russian audience).
ENDPOINTS = ("https://yandex.com/indexnow", "https://api.indexnow.org/indexnow")
BATCH = 1000
INTERVAL = 3600
_last_check = 0.0
_check_lock = threading.Lock()


def key() -> str:
    """8-128 characters of [a-zA-Z0-9-]; stable for as long as SECRET_KEY / INDEXNOW_KEY stay the same."""
    own = (os.environ.get("INDEXNOW_KEY") or "").strip()
    if own and 8 <= len(own) <= 128 and all(ch.isalnum() or ch == "-" for ch in own):
        return own
    secret = (os.environ.get("SECRET_KEY") or "showcasemaker").encode("utf-8")
    return hmac.new(secret, b"indexnow-key", hashlib.sha256).hexdigest()[:32]


def enabled() -> bool:
    if "PYTEST_CURRENT_TEST" in os.environ:
        return False  # tests never talk to search engines
    flag = (os.environ.get("INDEXNOW") or "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    if flag in ("1", "true", "yes", "on"):
        return True
    return (os.environ.get("APP_URL") or "").strip().rstrip("/") == SITE


def _state_path() -> Path:
    import auth_db
    return Path(auth_db.DATA) / "indexnow.json"


def _read_state() -> dict:
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(state: dict) -> None:
    path = _state_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state), encoding="utf-8")
    os.replace(temporary, path)


def submit(urls: list[str]) -> bool:
    """POST the URLs (own host only) to the IndexNow endpoints. True when at least one engine accepted them."""
    urls = [url for url in dict.fromkeys(urls) if url.startswith(SITE + "/")]
    if not urls:
        return True
    accepted = False
    for start in range(0, len(urls), BATCH):
        body = json.dumps({"host": HOST, "key": key(), "keyLocation": f"{SITE}/{key()}.txt",
                           "urlList": urls[start:start + BATCH]}).encode("utf-8")
        for endpoint in ENDPOINTS:
            request = urllib.request.Request(endpoint, data=body, method="POST", headers={
                "Content-Type": "application/json; charset=utf-8", "User-Agent": "ShowcaseMaker/1.0"})
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    accepted = accepted or response.status in (200, 202)
            except urllib.error.HTTPError as exc:
                # 403: key not found yet (deploy in progress), 422: URL not of this host, 429: too often.
                LOG.warning("indexnow %s: HTTP %s", endpoint.split("/")[2], exc.code)
            except Exception as exc:
                LOG.warning("indexnow %s unreachable: %s", endpoint.split("/")[2], type(exc).__name__)
    if accepted:
        LOG.info("indexnow: announced %d url(s)", len(urls))
    return accepted


def announce(urls: list[str]) -> None:
    """Fire and forget (route handlers must not wait for search engines)."""
    if enabled() and urls:
        threading.Thread(target=submit, args=(list(urls),), daemon=True, name="indexnow").start()


def _lock() -> bool:
    try:
        import redis_store as rs
        r = rs._r()
        if r:
            return bool(r.set("sm:lock:indexnow", "1", nx=True, ex=INTERVAL - 60))
    except Exception:
        LOG.debug("indexnow lock", exc_info=True)
    return True


def changed_since(entries: list[tuple[str, float | None]], since: float) -> list[str]:
    return [url for url, changed in entries if changed and changed > since]


def run_once(now: float | None = None) -> int:
    """Announce the sitemap pages changed since the last announcement. Returns how many were sent."""
    from smweb.routers.pages import sitemap_entries
    entries = sitemap_entries()
    state = _read_state()
    since = float(state.get("announced_until") or 0)
    urls = [url for url, _changed in entries] if not since else changed_since(entries, since)
    newest = max((changed for _url, changed in entries if changed), default=since)
    if urls and not submit(urls):
        return 0
    _write_state({"announced_until": max(newest, since), "at": now or time.time(), "count": len(urls)})
    return len(urls)


def maybe_run() -> None:
    """Called from the job cleaner every 30 s; does real work at most once an hour, in one process."""
    global _last_check
    if not enabled():
        return
    now = time.time()
    if now - _last_check < INTERVAL or not _check_lock.acquire(blocking=False):
        return
    try:
        _last_check = now
        if _lock():
            run_once(now)
    except Exception:
        LOG.warning("indexnow run failed", exc_info=True)
    finally:
        _check_lock.release()
