"""'Now on the site' counter (smweb/presence.py, 2026-10-07)."""
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

import redis_store as rs
from smweb import presence
from smweb.middleware import RateLimitMiddleware
from smweb.routers import system


def test_ping_counts_each_visitor_once_and_forgets_the_silent(monkeypatch):
    monkeypatch.setattr(rs, "_r", lambda: None)
    monkeypatch.setattr(presence, "_local", {})
    assert presence.ping("g:a", now=1000) == 1
    assert presence.ping("g:a", now=1010) == 1, "the same browser is one visitor"
    assert presence.ping("g:b", now=1020) == 2
    assert presence.ping("g:c", now=1000 + presence.WINDOW + 15) == 2, "g:a went silent and dropped out"
    assert all("g:" not in key for key in presence._local), "only hashes are kept"


def test_route_answers_without_caching(monkeypatch):
    monkeypatch.setattr(rs, "_r", lambda: None)
    monkeypatch.setattr(presence, "_local", {})
    app = FastAPI()
    app.include_router(system.router)
    client = TestClient(app)
    response = client.post("/api/presence")
    assert response.status_code == 200 and response.json() == {"ok": True, "online": 1}
    assert response.headers["cache-control"] == "no-store"
    assert any(prefix == "/api/presence" for prefix, _, _ in RateLimitMiddleware.RULES)


def test_landing_has_the_badge_and_the_shell_pings():
    root = os.path.dirname(os.path.dirname(__file__))
    page = open(os.path.join(root, "static", "index.html"), encoding="utf-8").read()
    shell = open(os.path.join(root, "static", "ss-shell.js"), encoding="utf-8").read()
    assert 'id="homeOnline"' in page and "home-online.js" in page
    assert "/api/presence" in shell
