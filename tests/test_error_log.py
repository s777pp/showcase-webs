"""Server errors stored in the database (smweb/error_log.py, 2026-10-01)."""
import logging
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import auth_db
from smweb import admin_notify, error_log
from tests.test_admin_control_center import _client, _isolate, _login, _mutation_headers


def _logger(name="sm.test-errors"):
    log = logging.getLogger(name)
    handler = error_log._Handler(level=logging.ERROR)
    log.addHandler(handler)
    log.propagate = False
    return log, handler


def _rows():
    error_log.flush()
    return error_log.listing("all")["items"]


def _fail(token):
    raise RuntimeError(f"upload to https://bucket.example/x?X-Amz-Signature={token} failed")


def test_same_bug_is_one_row_with_a_counter_and_no_secrets(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    log, handler = _logger()
    try:
        for token in ("secret-one", "secret-two"):
            try:
                _fail(token)
            except RuntimeError:
                log.exception("upload failed")
        rows = _rows()
    finally:
        log.removeHandler(handler)
    assert len(rows) == 1 and rows[0]["count"] == 2 and rows[0]["kind"] == "exception"
    stored = " ".join(str(rows[0][key]) for key in ("title", "message", "trace"))
    assert "secret-one" not in stored and "secret-two" not in stored and "X-Amz-Signature" not in stored
    assert "test_error_log.py" in rows[0]["location"] and "_fail" in rows[0]["location"]


def test_resolved_error_comes_back_and_is_reported_again(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    sent = []
    monkeypatch.setattr(admin_notify, "configured", lambda: True)
    monkeypatch.setattr(admin_notify, "_throttled", lambda key, window: (True, 0))
    monkeypatch.setattr(admin_notify, "send", lambda text, buttons=None: sent.append(text))
    log, handler = _logger()
    try:
        log.error("payment webhook rejected for order 1234")
        _rows()
        assert error_log.resolve(None) == 1 and error_log.listing("open")["open"] == 0
        log.error("payment webhook rejected for order 98765")  # numbers do not split a group
        rows = _rows()
    finally:
        log.removeHandler(handler)
    assert len(rows) == 1 and rows[0]["count"] == 2 and rows[0]["resolved_at"] is None
    assert len(sent) == 2 and "Новая" in sent[0] and "вернулась" in sent[1]


def test_middleware_records_unexplained_5xx_and_request_of_logged_errors(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    log, handler = _logger()
    app = FastAPI()

    @app.get("/api/silent/{item}")
    def silent(item: int):
        return JSONResponse({"ok": False}, status_code=500)

    @app.get("/api/handled")
    def handled():
        try:
            {}["missing"]
        except KeyError:
            log.exception("lookup failed")
        return JSONResponse({"ok": False}, status_code=500)

    @app.get("/api/busy")
    def busy():
        return JSONResponse({"ok": False}, status_code=503)

    @app.exception_handler(Exception)
    async def unhandled(request, exc):
        log.exception("unhandled error")
        return JSONResponse({"ok": False}, status_code=500)

    @app.get("/api/crash")
    def crash():
        raise ValueError("boom")

    app.add_middleware(error_log.ErrorCaptureMiddleware)
    client = TestClient(app, raise_server_exceptions=False)
    try:
        assert client.get("/api/silent/1").status_code == 500
        assert client.get("/api/silent/2").status_code == 500
        assert client.get("/api/handled").status_code == 500
        assert client.get("/api/busy").status_code == 503
        assert client.get("/api/crash").status_code == 500
        rows = {row["title"].split(":")[0]: row for row in _rows()}
    finally:
        log.removeHandler(handler)
    http = rows["HTTP 500 без записи в логе"]
    assert http["count"] == 2 and http["path"].startswith("/api/silent/")
    assert rows["KeyError"]["path"] == "/api/handled" and rows["KeyError"]["method"] == "GET"
    assert rows["ValueError"]["path"] == "/api/crash", "the global handler runs outside the middleware"
    assert len(rows) == 3, "a 503 is deliberate and a logged 500 is not recorded twice"


def test_cleanup_and_admin_endpoints(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    log, handler = _logger()
    try:
        log.error("first problem")
        log.error("second problem")
        _rows()
    finally:
        log.removeHandler(handler)
    c = auth_db._conn()
    try:
        c.execute("UPDATE server_errors SET last_seen=? WHERE title='first problem'", (time.time() - 30 * 86400,))
        c.commit()
    finally:
        c.close()
    error_log.cleanup()
    assert [row["title"] for row in error_log.listing("all")["items"]] == ["second problem"]

    client = _client()
    assert client.get("/api/admin/control/errors").status_code == 403
    csrf = _login(client)
    listed = client.get("/api/admin/control/errors").json()
    assert listed["open"] == 1 and listed["items"][0]["title"] == "second problem"
    error_id = listed["items"][0]["id"]
    assert client.post(f"/api/admin/control/errors/{error_id}/resolve", headers=_mutation_headers(csrf)).json()["ok"]
    assert client.get("/api/admin/control/errors").json()["open"] == 0
    assert client.delete("/api/admin/control/errors/resolved", headers=_mutation_headers(csrf)).json()["count"] == 1
    assert client.get("/api/admin/control/errors?status=all").json()["items"] == []
