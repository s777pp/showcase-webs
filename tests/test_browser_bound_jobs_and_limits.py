from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from smweb.job_access import bind_job, browser_owns_job
from smweb.middleware import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from smweb.oauth_util import _oauth_browser_matches
from smweb.routers import deviantart, gallery, media, oauth, process


def _request(*, token: str = "", ip: str = "127.0.0.1") -> Request:
    headers = []
    if token:
        headers.append((b"x-session-token", token.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": (ip, 12345),
            "server": ("testserver", 80),
        }
    )


def test_job_directory_is_bound_to_the_browser(tmp_path):
    job_dir = tmp_path / ("a" * 32)
    bind_job(job_dir, _request(token="owner"))

    assert browser_owns_job(job_dir, _request(token="owner"))
    assert not browser_owns_job(job_dir, _request(token="someone-else"))
    assert not browser_owns_job(tmp_path / ("b" * 32), _request(token="owner"))


def test_job_file_rejects_other_browser_and_dotfiles(tmp_path, monkeypatch):
    job_id = "c" * 32
    job_dir = tmp_path / job_id
    bind_job(job_dir, _request(token="owner"))
    (job_dir / "result.gif").write_bytes(b"GIF89a")
    monkeypatch.setattr(process, "JOBS", tmp_path)

    app = FastAPI()
    app.include_router(process.router)
    client = TestClient(app)

    assert client.get(
        f"/api/job-file/{job_id}/result.gif",
        headers={"X-Session-Token": "owner"},
    ).status_code == 200
    assert client.get(
        f"/api/job-file/{job_id}/result.gif",
        headers={"X-Session-Token": "someone-else"},
    ).status_code == 404
    assert client.get(
        f"/api/job-file/{job_id}/.owner",
        headers={"X-Session-Token": "owner"},
    ).status_code == 404


def test_oauth_callback_requires_the_browser_that_started_login(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "s" * 64)
    monkeypatch.setenv("APP_URL", "http://testserver")
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("DISCORD_CLIENT_ID", "client")
    monkeypatch.setenv("DISCORD_CLIENT_SECRET", "secret")

    app = FastAPI()
    app.include_router(oauth.router)
    client = TestClient(app)
    started = client.get("/api/auth/discord/login")

    assert started.status_code == 200
    assert "httponly" in started.headers["set-cookie"].lower()
    state = parse_qs(urlparse(started.json()["url"]).query)["state"][0]
    client.cookies.clear()
    rejected = client.get(
        "/api/auth/discord/callback", params={"state": state, "code": "unused"}
    )
    assert rejected.status_code == 400
    assert "bad state" in rejected.text


def test_steam_openid_keeps_state_in_return_url_and_cookie(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "s" * 64)
    monkeypatch.setenv("APP_URL", "http://testserver")
    monkeypatch.setenv("COOKIE_SECURE", "0")

    app = FastAPI()
    app.include_router(oauth.router)
    response = TestClient(app).get("/api/auth/steam/login")

    assert response.status_code == 200
    assert "sm_oauth_steam=" in response.headers["set-cookie"]
    provider_query = parse_qs(urlparse(response.json()["url"]).query)
    return_query = parse_qs(urlparse(provider_query["openid.return_to"][0]).query)
    assert return_query.get("state", [""])[0]


def test_deviantart_callback_is_bound_to_the_signed_in_browser(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "s" * 64)
    monkeypatch.setenv("APP_URL", "http://testserver")
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.setenv("DA_CLIENT_ID", "client")
    monkeypatch.setenv("DA_CLIENT_SECRET", "secret")
    monkeypatch.setattr(deviantart, "_auth_user", lambda _request: {"id": 7})

    app = FastAPI()
    app.include_router(deviantart.router)
    client = TestClient(app)
    started = client.get("/api/da/login")

    assert started.status_code == 200
    assert "sm_oauth_deviantart=" in started.headers["set-cookie"]
    assert "path=/api" in started.headers["set-cookie"].lower()
    state = parse_qs(urlparse(started.json()["url"]).query)["state"][0]

    @app.get("/api/da/browser-cookie-check")
    def browser_cookie_check(request: Request):
        return {"matches": _oauth_browser_matches(request, "deviantart", state)}

    assert client.get("/api/da/browser-cookie-check").json()["matches"] is True
    client.cookies.clear()
    rejected = client.get("/api/da/callback", params={"state": state, "code": "unused"})
    assert rejected.status_code == 400


def test_declared_oversized_body_is_rejected_before_route(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_MB", "1")
    app = FastAPI()
    app.add_middleware(RequestBodyLimitMiddleware)

    @app.post("/upload")
    def upload():
        return {"ok": True}

    response = TestClient(app).post(
        "/upload",
        content=b"x" * (1024 * 1024 + 1),
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 413
    assert response.json()["msg"] == "Request body is too large"


def test_gallery_image_never_serves_a_database_path_outside_data(tmp_path, monkeypatch):
    outside = tmp_path / "private.txt"
    outside.write_text("must not be public", encoding="utf-8")
    monkeypatch.setattr(
        gallery.auth_db,
        "gallery_get",
        lambda _item_id: {
            "id": 1,
            "status": "approved",
            "image_path": str(outside),
        },
    )
    monkeypatch.setattr(gallery.object_store, "configured", lambda: False)

    response = gallery.gallery_image(1)
    assert response.status_code == 404


def test_download_results_exclude_internal_job_metadata(tmp_path):
    (tmp_path / ".owner").write_text("fingerprint", encoding="ascii")
    (tmp_path / "download.zip").write_bytes(b"old")
    (tmp_path / "video.mp4").write_bytes(b"media")

    assert [path.name for path in media._job_output_files(tmp_path)] == ["video.mp4"]


def test_invalid_process_and_compose_ids_do_not_reach_job_store(monkeypatch):
    def unexpected_lookup(_job_id):
        raise AssertionError("invalid identifier reached the job store")

    monkeypatch.setattr(process, "_job_get", unexpected_lookup)
    monkeypatch.setattr(media.rs, "job_get", unexpected_lookup)

    request = _request(token="owner")
    assert process._process_job_for(request, "../redis-key") is None
    assert media._compose_job_for(request, "../redis-key") is None


def test_private_account_api_disables_shared_caching():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/bootstrap")
    def bootstrap():
        return {"ok": True}

    response = TestClient(app).get("/api/bootstrap")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
