import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _probe(value: str) -> str:
    env = dict(os.environ)
    env.update({
        "ENABLE_API_DOCS": value,
        "DATABASE_URL": "",
        "REDIS_URL": "",
        "SECRET_KEY": "isolated-production-surface-test-key",
        "APP_URL": "http://127.0.0.1:8091",
    })
    code = "import main;print(main.app.docs_url, main.app.redoc_url, main.app.openapi_url)"
    return subprocess.check_output([sys.executable, "-c", code], env=env, text=True).strip()


def test_api_documentation_is_closed_by_default_and_explicitly_opt_in():
    assert _probe("").endswith("None None None")
    assert _probe("1").endswith("/docs /redoc /openapi.json")


def test_compose_requires_core_production_secrets():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD" in compose
    assert "SECRET_KEY:?Set SECRET_KEY" in compose
    assert "CLOUDFLARE_TUNNEL_TOKEN:?Set CLOUDFLARE_TUNNEL_TOKEN" in compose
    assert "POSTGRES_PASSWORD:-showcase_change_me" not in compose


def test_avatar_urls_are_assigned_as_dom_properties_not_html_fragments():
    profile = (ROOT / "static" / "js" / "profile.js").read_text(encoding="utf-8")
    gallery = (ROOT / "static" / "js" / "gallery.js").read_text(encoding="utf-8")
    assert "avatarImage.src=d.avatar_url" in profile
    assert "avatarImage.src = item.avatar_url" in gallery
    assert "'<img src=\"'+d.avatar_url" not in profile
    assert "`<img src=\"${item.avatar_url}" not in gallery
