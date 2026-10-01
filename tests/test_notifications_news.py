"""Notifications, news and support threads (2026-10-01)."""
import json
import secrets
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth_db
from smweb import news, notify, support_threads


def _user():
    email = f"n-{secrets.token_hex(4)}@example.com"
    auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        row = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    finally:
        c.close()
    return int(row["id"]), email


def _unread(uid):
    return auth_db.notifications_unread_count(uid)


def test_news_html_is_cleaned_and_slugged():
    body = news.clean_html('<h1>Big</h1><p onclick="x">Hi <script>evil()</script><a href="javascript:1">no</a>'
                           '<a href="https://ko-fi.com/x">yes</a><img src="https://evil/x.png"><img src="/api/news/media/abc.webp"></p>')
    assert "<h2>Big</h2>" in body and "onclick" not in body and "script" not in body
    assert "javascript" not in body and 'href="https://ko-fi.com/x"' in body and 'rel="noopener noreferrer"' in body
    assert "evil/x.png" not in body and '<img src="/api/news/media/abc.webp"' in body
    assert news._slug("Обновление v1.8 — новый редактор") == "obnovlenie-v1-8-novyy-redaktor"


def test_news_publish_list_and_unread_for_the_bell():
    uid, _ = _user()
    user = {"id": uid}
    before = news.unread_count(user)
    saved = news.save({"title_ru": "Тест", "title_en": "Test", "summary_en": "Short", "body_en": "<p>Body</p>",
                       "category": "feature", "status": "published", "notify": True})
    post = news.by_slug(saved["slug"])
    assert post and news.localized(post, "de")["title"] == "Test" and news.localized(post, "ru")["title"] == "Тест"
    assert news.unread_count(user) == before + 1
    items = news.bell_items(user, "en")
    assert any(i["id"] == "news:" + saved["id"] and not i["is_read"] for i in items)
    news.mark_seen(uid)
    assert news.unread_count(user) == 0
    draft = news.save({"title_en": "Draft", "status": "draft"})
    assert news.by_slug(draft["slug"]) is None, "drafts are not public"
    future = news.save({"title_en": "Later", "status": "published", "published_at": time.time() + 3600})
    assert news.by_slug(future["slug"]) is None, "scheduled posts wait for their time"
    assert news.delete(saved["id"]) and news.delete(draft["id"]) and news.delete(future["id"])


def test_job_error_gets_a_plain_reason_and_one_row_per_job(monkeypatch):
    uid, _ = _user()
    jobs = {"j1": {"kind": "steam_profile_import", "user_key": str(uid), "status": "error", "error": "steam_private: profile is private"},
            "j2": {"kind": "process", "user_key": str(uid), "status": "done"},
            "j3": {"kind": "upscale", "user_key": str(uid), "status": "done"},
            "j4": {"kind": "process", "user_key": "g:guest", "status": "error", "error": "x"}}
    import redis_store
    monkeypatch.setattr(redis_store, "job_get", lambda jid: jobs.get(jid))
    for jid, job in jobs.items():
        notify.job_finished(jid, {"status": job["status"]})
    notify.job_finished("j1", {"status": "error"})
    rows = auth_db.notifications_list(uid)
    kinds = sorted(r["kind"] for r in rows)
    assert kinds == ["job_done", "job_error"], "quick successful jobs and guests are not notified"
    error = next(r for r in rows if r["kind"] == "job_error")
    assert json.loads(error["meta_json"])["code"] == "steam_private"
    assert notify.error_code({"error": "Too Many Requests HTTP 429"}) == "steam_busy"
    assert notify.error_code({"error": "This animation cannot fit under 5 MB"}) == "steam_limit"
    assert notify.error_code({"error": "MemoryError"}) == "server"


def test_downloads_are_summed_per_window():
    uid, _ = _user()
    c = auth_db._conn()
    try:
        cur = c.execute("INSERT INTO gallery(user_id,title,mode,image_path,status,created_at) VALUES (?,?,?,?,?,?)",
                        (uid, "Pink", "workshop", "x.png", "approved", time.time()))
        c.commit()
        item_id = cur.lastrowid or c.execute("SELECT MAX(id) AS id FROM gallery").fetchone()["id"]
    finally:
        c.close()
    for _ in range(3):
        notify.gallery_downloaded(int(item_id))
    rows = [r for r in auth_db.notifications_list(uid) if r["kind"] == "downloads"]
    assert len(rows) == 1 and json.loads(rows[0]["meta_json"])["count"] == 3


def test_support_thread_reply_notifies_and_user_can_answer(monkeypatch):
    uid, email = _user()
    other, _ = _user()
    from smweb import admin_content
    ticket = admin_content.create_ticket(user_id=uid, email=email, message="Help me with the import please",
                                         page="/ru/profile", context={})["ticket_id"]
    import mailer
    sent = []
    monkeypatch.setattr(mailer, "send_email", lambda *a, **k: (sent.append(a) or True, ""))
    result = support_threads.reply_from_support(ticket, "Open your profile privacy settings.")
    assert result["notified"] and result["emailed"] and sent
    assert _unread(uid) >= 1
    thread = support_threads.user_thread(ticket, uid)
    assert [m["author"] for m in thread["messages"]] == ["user", "support"]
    assert support_threads.user_thread(ticket, other) is None, "someone else's ticket stays private"
    support_threads.reply_from_user(ticket, uid, "Thanks, it worked")
    assert support_threads.user_thread(ticket, uid)["status"] == "new"
    assert support_threads.user_tickets(uid)[0]["replies"] == 1


def test_bell_api_merges_news_and_marks_everything_read(monkeypatch):
    uid, _ = _user()
    from smweb.routers import gallery
    monkeypatch.setattr(gallery, "_auth_user", lambda request: {"id": uid})
    notify.add(uid, "pro_expiring", title="Pro", meta={"stage": "3d"}, group_key="pro:test")
    saved = news.save({"title_en": "Bell news", "status": "published", "notify": True})
    app = FastAPI()
    app.include_router(gallery.router)
    client = TestClient(app)
    data = client.get("/api/notifications?lang=en").json()
    kinds = {i["kind"] for i in data["items"]}
    assert {"news", "pro_expiring"} <= kinds and data["unread"] >= 2 and data["news_dot"] is True
    after = client.post("/api/notifications/read", json={"all": True}).json()
    assert after["unread"] == 0 and after["news_dot"] is False
    news.delete(saved["id"])


def test_backdated_post_goes_to_the_feed_without_bell_or_dot():
    uid, _ = _user()
    user = {"id": uid}
    c = auth_db._conn()
    try:
        c.execute("UPDATE users SET created_at=?, news_seen_at=NULL WHERE id=?", (time.time() - 30 * 86400, uid))
        c.commit()
    finally:
        c.close()
    two_days_ago = time.time() - 2 * 86400
    saved = news.save({"title_ru": "Старый список изменений", "title_en": "Old changelog", "status": "published",
                       "notify": True, "published_at": two_days_ago})
    post = news.by_slug(saved["slug"])
    assert post and not post["notify"] and abs(post["published_at"] - two_days_ago) < 1
    assert news.unread_count(user) == 0 and news.latest_unread_at(user) == 0
    assert all(i["id"] != "news:" + saved["id"] for i in news.bell_items(user, "ru"))
    assert any(p["id"] == saved["id"] for p in news.published())
    # Re-saving with the same date keeps the owner's explicit choice.
    news.save({"id": saved["id"], "title_en": "Old changelog", "status": "published", "notify": True,
               "published_at": two_days_ago})
    assert news.by_slug(saved["slug"])["notify"]
    news.delete(saved["id"])
