from smweb import admin_control, health_checks


def _by_key(items):
    return {item["key"]: item for item in items}


def test_probes_report_green_red_and_explain(monkeypatch):
    health_checks._CACHE.update(at=0, items=[])
    monkeypatch.setenv("MIRROR_HOSTS", "ru.example.com")
    monkeypatch.setenv("STEAM_RELAY_URL", "http://relay.example:8787")
    monkeypatch.setenv("MODAL_UPSCALE_URL", "https://modal.example")
    monkeypatch.setenv("MODAL_PROXY_TOKEN_ID", "id")
    monkeypatch.setenv("MODAL_PROXY_TOKEN_SECRET", "secret")
    monkeypatch.setenv("ADMIN_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ADMIN_BOT_CHAT_ID", "42")
    monkeypatch.delenv("BOT_ADMIN_SECRET", raising=False)

    def fake_get(url, headers=None, timeout=6):
        if "ru.example.com" in url:
            return 200, b'{"ok":true}'
        if "relay.example" in url:
            return 0, b""  # relay down
        if "modal.example" in url:
            return 200, b""
        if "api.telegram.org" in url:
            return 200, b'{"ok":true,"result":{"username":"SteamMakerBot"}}'
        return 0, b""

    monkeypatch.setattr(health_checks, "_get", fake_get)
    items = _by_key(health_checks.components(admin_control._component))
    assert items["mirror"]["state"] == "ok"
    assert items["relay"]["state"] == "down" and items["relay"]["action"]
    assert items["upscale"]["state"] == "ok"
    assert items["notify"]["state"] == "ok" and "@SteamMakerBot" in items["notify"]["summary"]
    assert items["bot_api"]["state"] == "warn"
    assert all(item["summary"] and item["impact"] for item in items.values())
    # cached for a minute: no second round of network calls
    monkeypatch.setattr(health_checks, "_get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("not cached")))
    assert _by_key(health_checks.components(admin_control._component))["mirror"]["state"] == "ok"
    health_checks._CACHE.update(at=0, items=[])
