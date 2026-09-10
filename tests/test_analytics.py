import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from smweb import analytics
from smweb.routers import analytics as analytics_router


DDL = """
CREATE TABLE analytics_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_key TEXT UNIQUE NOT NULL,
 event_name TEXT NOT NULL, session_hash TEXT, user_hash TEXT, language TEXT NOT NULL,
 path TEXT, tool TEXT, mode TEXT, method TEXT, reason TEXT, file_type TEXT,
 size_bucket TEXT, value_int INTEGER NOT NULL DEFAULT 0, day_key TEXT NOT NULL,
 created_at REAL NOT NULL
)
"""


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "analytics.db"
        db = sqlite3.connect(self.db_path)
        db.execute(DDL)
        db.commit()
        db.close()
        analytics._last_cleanup = time.time()

        def connection():
            db = sqlite3.connect(self.db_path)
            db.row_factory = sqlite3.Row
            return db

        self.connection_patch = patch.object(analytics, "_open_connection", side_effect=connection)
        self.connection_patch.start()
        app = FastAPI()
        app.include_router(analytics_router.router)
        self.admin_patch = patch.object(
            analytics_router, "_admin_ok",
            side_effect=lambda request: request.headers.get("x-admin-secret") == "test-secret",
        )
        self.admin_patch.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.admin_patch.stop()
        self.connection_patch.stop()
        self.temp.cleanup()

    def test_public_endpoint_requires_consent_and_allowlisted_event(self):
        base = {"event_key": "a" * 32, "session_id": "b" * 32, "language": "ru", "path": "/ru/app"}
        self.assertEqual(self.client.post("/api/analytics/event", json={**base, "event": "home_view"}).status_code, 400)
        self.assertEqual(self.client.post("/api/analytics/event", json={**base, "event": "pro_activated", "consent": True}).status_code, 400)
        response = self.client.post("/api/analytics/event", json={**base, "event": "home_view", "consent": True})
        self.assertEqual(response.status_code, 202)

    def test_identifiers_are_hashed_and_payload_is_sanitized(self):
        raw_session = "0123456789abcdef0123456789abcdef"
        response = self.client.post("/api/analytics/event", json={
            "event": "file_added", "event_key": "c" * 32, "session_id": raw_session,
            "language": "en", "path": "/en/app?private=yes", "consent": True,
            "properties": {"file_type": "image", "size_bucket": "1_5mb", "filename": "private.gif", "email": "x@example.com"},
        })
        self.assertEqual(response.status_code, 202)
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM analytics_events").fetchone()
        columns = {item[1] for item in db.execute("PRAGMA table_info(analytics_events)")}
        db.close()
        self.assertNotEqual(row["session_hash"], raw_session)
        self.assertEqual(row["path"], "/app")
        self.assertNotIn("filename", columns)
        self.assertNotIn("email", columns)
        self.assertNotIn("ip", columns)

    def test_duplicate_key_is_idempotent_and_admin_report_is_aggregate_only(self):
        for _ in range(2):
            analytics.record("tool_open", session_id="d" * 32, language="de", properties={"tool": "process"}, event_key="e" * 32)
        self.assertEqual(self.client.get("/api/admin/analytics").status_code, 403)
        response = self.client.get("/api/admin/analytics?days=7", headers={"X-Admin-Secret": "test-secret"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["totals"]["tool_open"]["total"], 1)
        self.assertEqual(data["tools"][0]["tool"], "process")
        self.assertNotIn("rows", data)
        self.assertNotIn("session_hash", response.text)


if __name__ == "__main__":
    unittest.main()
