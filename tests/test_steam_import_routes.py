import pytest

import steam_catalog
import steam_profile_guard

FULL = '<script>g_rgProfileData = {"steamid":"76561190000000000","personaname":"x"};</script>'


def _routes(monkeypatch, **fetchers):
    monkeypatch.setattr(steam_catalog, "_profile_routes", lambda progress: list(fetchers.items()))


def test_rate_limited_server_falls_through_to_relay_and_pauses_itself(tmp_path, monkeypatch):
    gate = tmp_path / "g.sqlite3"

    def server(url):
        raise steam_profile_guard.RateLimited(300)

    _routes(monkeypatch, server=server, relay=lambda url: FULL)
    stages = []
    html, route, error = steam_catalog._page_via_routes("https://steamcommunity.com/id/x", lambda s, p: stages.append(s), gate)
    assert (html, route, error) == (FULL, "relay", None)
    assert stages == ["via_server", "via_relay"]
    assert steam_profile_guard.route_wait(gate, "server") > 200
    # The next import skips the paused route entirely.
    stages.clear()
    steam_catalog._page_via_routes("https://steamcommunity.com/id/x", lambda s, p: stages.append(s), gate)
    assert stages == ["via_relay"]


def test_throttled_shell_page_is_not_accepted_as_a_profile(tmp_path, monkeypatch):
    _routes(monkeypatch, server=lambda url: '<div class="profile_page">429</div>', relay=lambda url: FULL)
    html, route, _ = steam_catalog._page_via_routes("https://steamcommunity.com/id/x", None, tmp_path / "g.sqlite3")
    assert route == "relay"


def test_every_route_limited_raises_so_the_cache_can_answer(tmp_path, monkeypatch):
    def limited(url):
        raise steam_profile_guard.RateLimited(120)

    _routes(monkeypatch, server=limited, relay=limited)
    with pytest.raises(steam_profile_guard.RateLimited):
        steam_catalog._page_via_routes("https://steamcommunity.com/id/x", None, tmp_path / "g.sqlite3")


def test_limit_exemption_is_env_only(monkeypatch):
    from smweb.core import _is_limit_exempt

    monkeypatch.delenv("RATE_LIMIT_EXEMPT_EMAILS", raising=False)
    assert not _is_limit_exempt({"email": "owner@example.com"})
    monkeypatch.setenv("RATE_LIMIT_EXEMPT_EMAILS", "Owner@Example.com, other@example.com")
    assert _is_limit_exempt({"email": "owner@example.com"})
    assert not _is_limit_exempt({"email": "someone@example.com"})
    assert not _is_limit_exempt(None)
