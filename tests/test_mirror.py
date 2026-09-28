from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.testclient import TestClient

from smweb import mirror

ENV = {"R2_PUBLIC_BASE_URL": "https://media.example.com", "R2_ACCOUNT_ID": "acct", "APP_URL": "https://main.example.com"}


def _client():
    app = FastAPI()

    @app.get("/json")
    def json_view():
        resp = JSONResponse({"img": "https://media.example.com/a.png", "origin": mirror.current_origin()})
        resp.set_cookie("one", "1")
        resp.set_cookie("two", "2")
        return resp

    @app.get("/file")
    def file_view():
        return RedirectResponse("https://acct.r2.cloudflarestorage.com/private/jobs/x.gif?X-Amz-Signature=s")

    app.add_middleware(mirror.MirrorMiddleware)
    return TestClient(app)


def test_mirror_host_rewrites_r2_links_and_keeps_every_cookie():
    with patch.dict("os.environ", ENV), patch.object(mirror, "MIRROR_HOSTS", {"ru.example.com"}):
        client = _client()
        resp = client.get("/json", headers={"host": "ru.example.com"})
        assert resp.json() == {"img": "/r2m/a.png", "origin": "https://ru.example.com"}
        assert len(resp.headers.get_list("set-cookie")) == 2
        redirect = client.get("/file", headers={"host": "ru.example.com"}, follow_redirects=False)
        assert redirect.headers["location"] == "/r2s/private/jobs/x.gif?X-Amz-Signature=s"


def test_main_host_is_untouched():
    with patch.dict("os.environ", ENV), patch.object(mirror, "MIRROR_HOSTS", {"ru.example.com"}):
        resp = _client().get("/json", headers={"host": "main.example.com"})
        assert resp.json() == {"img": "https://media.example.com/a.png", "origin": ""}


def test_login_return_urls_follow_the_mirror():
    from smweb.oauth_util import _app_origin, _google_redirect_uri

    with patch.dict("os.environ", {**ENV, "GOOGLE_REDIRECT_URI": "https://main.example.com/api/auth/google/callback"}):
        assert _app_origin() == "https://main.example.com"
        token = mirror._current.set("https://ru.example.com")
        try:
            assert _app_origin() == "https://ru.example.com"
            assert _google_redirect_uri() == "https://ru.example.com/api/auth/google/callback"
        finally:
            mirror._current.reset(token)
