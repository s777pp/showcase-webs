from pathlib import Path


def test_nginx_re_resolves_compose_app_after_recreation():
    config = (Path(__file__).resolve().parents[1] / "nginx" / "nginx.conf").read_text(
        encoding="utf-8"
    )
    assert "resolver 127.0.0.11" in config
    assert "zone app_upstream" in config
    assert "server app:8080 resolve;" in config
