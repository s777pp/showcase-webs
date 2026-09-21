from unittest.mock import patch

import pytest

from smweb.remote_media import fetch_media, validate_media_url


class Response:
    def __init__(self, status=200, headers=None, chunks=(b"image",)):
        self.status_code = status
        self.headers = {"Content-Type": "image/png", **(headers or {})}
        self.chunks = chunks
        self.closed = False
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def iter_content(self, size):
        for chunk in self.chunks:
            self.reads += 1
            yield chunk


@pytest.mark.parametrize("url", [
    "https://evilsteamstatic.com/a", "https://steamstatic.com.evil.test/a",
    "https://cdn.steamstatic.com:8443/a", "file:///etc/passwd",
    "https://user:secret@cdn.steamstatic.com/a", "http://127.0.0.1/a",
])
def test_rejects_untrusted_urls_before_network(url):
    with patch("smweb.remote_media.requests.get") as get:
        with pytest.raises(ValueError):
            fetch_media(url, max_bytes=10)
        get.assert_not_called()


def test_redirect_to_private_address_is_never_fetched():
    redirect = Response(302, {"Location": "http://169.254.169.254/latest/meta-data/"})
    with patch("smweb.remote_media.requests.get", return_value=redirect) as get:
        with pytest.raises(ValueError, match="not_allowed"):
            fetch_media("https://cdn.steamstatic.com/a", max_bytes=10)
        assert get.call_count == 1
    assert redirect.closed


def test_valid_relative_redirect_and_mime_parameters():
    responses = [Response(302, {"Location": "/b"}), Response(headers={"Content-Type": "video/webm; charset=binary"})]
    with patch("smweb.remote_media.requests.get", side_effect=responses) as get:
        assert fetch_media("https://cdn.steamstatic.com/a", max_bytes=10) == (b"image", "video/webm")
        assert get.call_args.args[0] == "https://cdn.steamstatic.com/b"
        assert get.call_args.kwargs["allow_redirects"] is False
    assert all(r.closed for r in responses)


@pytest.mark.parametrize("headers,chunks,reads", [
    ({"Content-Length": "100"}, (b"image",), 0),
    ({}, (b"123456", b"789012", b"never read"), 2),
])
def test_size_limit_closes_stream_early(headers, chunks, reads):
    response = Response(headers=headers, chunks=chunks)
    with patch("smweb.remote_media.requests.get", return_value=response):
        with pytest.raises(ValueError, match="too_large"):
            fetch_media("https://cdn.steamstatic.com/a", max_bytes=10)
    assert response.closed and response.reads == reads


@pytest.mark.parametrize("status,headers", [(503, {}), (200, {"Content-Type": "text/html"})])
def test_failure_closes_response_without_reading(status, headers):
    response = Response(status, headers)
    with patch("smweb.remote_media.requests.get", return_value=response):
        with pytest.raises(ValueError):
            fetch_media("https://cdn.steamstatic.com/a", max_bytes=10)
    assert response.closed and response.reads == 0


def test_redirect_cycle_is_bounded():
    responses = [Response(302, {"Location": "/a"}) for _ in range(4)]
    with patch("smweb.remote_media.requests.get", side_effect=responses) as get:
        with pytest.raises(ValueError, match="redirect_limit"):
            fetch_media("https://cdn.steamstatic.com/a", max_bytes=10)
        assert get.call_count == 4
    assert all(r.closed for r in responses)


def test_proxy_preserves_bytes_and_hides_network_error_details():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import tools_api

    app = FastAPI()
    app.include_router(tools_api.router)
    client = TestClient(app)
    url = "/api/steam/proxy-image?url=https://cdn.steamstatic.com/a"
    with patch("tools_api.fetch_media", return_value=(b"original", "image/png")):
        response = client.get(url)
        assert response.status_code == 200 and response.content == b"original"
    with patch("tools_api.fetch_media", side_effect=RuntimeError("private_network_detail")):
        response = client.get(url)
        assert response.status_code == 502
        assert "private_network_detail" not in response.text


def test_builder_rejects_lookalike_host_before_fetch(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import tools_api

    monkeypatch.setitem(tools_api._D, "quota_state", lambda request: {"pro": True})
    app = FastAPI()
    app.include_router(tools_api.router)
    with patch("tools_api.fetch_media") as fetch:
        response = TestClient(app).post("/api/builder/render", data={"background_url": "https://evilsteamstatic.com/a"})
        assert response.status_code == 400
        fetch.assert_not_called()
