#!/usr/bin/env python3
"""Read-only production smoke test. Exits non-zero on a broken public route."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080").rstrip("/")
ROUTES = ("/", "/app", "/gallery", "/profile", "/api/health", "/api/bootstrap", "/api/gallery/list?limit=2")


def fetch(path: str):
    request = urllib.request.Request(BASE + path, headers={"User-Agent": "ShowcaseMaker-Smoke/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def main() -> int:
    failed = False
    health = None
    for route in ROUTES:
        try:
            status, content_type, body = fetch(route)
            valid = status == 200 and bool(body)
            print(f"{'OK' if valid else 'FAIL'} {status} {route} {content_type}")
            failed |= not valid
            if route == "/api/health":
                health = json.loads(body)
        except Exception as exc:
            failed = True
            print(f"FAIL {route}: {type(exc).__name__}: {exc}")
    if health:
        checks = {
            "db": health.get("db"), "redis": health.get("redis"),
            "worker": (health.get("worker") or {}).get("external_alive"),
            "ffmpeg": health.get("ffmpeg"), "gifski": health.get("gifski"),
            "postgresql": (health.get("storage") or {}).get("database_backend") == "postgresql",
            "r2": (health.get("r2") or {}).get("ok"),
        }
        for name, ok in checks.items():
            print(f"{'OK' if ok else 'FAIL'} dependency:{name}")
            failed |= not bool(ok)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
