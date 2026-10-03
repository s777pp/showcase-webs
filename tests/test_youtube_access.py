"""YouTube asks datacenter IPs to sign in (2026-10-03): cookies, proxy and a clear reply."""
import json

from smweb import admin_notify
from smweb.routers import media


def test_cookies_and_proxy_reach_yt_dlp(tmp_path, monkeypatch):
    cookies = tmp_path / "yt-cookies.txt"
    monkeypatch.setenv("YTDLP_COOKIES_FILE", str(cookies))
    monkeypatch.delenv("YTDLP_PROXY", raising=False)
    assert "cookiefile" not in media._ytdlp_access({}), "a missing file is not passed"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setenv("YTDLP_PROXY", "http://proxy.example:8080")
    opts = media._ytdlp_access({"quiet": True})
    assert opts["cookiefile"] == str(cookies) and opts["proxy"] == "http://proxy.example:8080" and opts["quiet"]


def test_bot_check_gets_its_own_code_and_tells_the_owner(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(admin_notify, "youtube_blocked", lambda with_cookies: sent.append(with_cookies))
    monkeypatch.setenv("YTDLP_COOKIES_FILE", str(tmp_path / "none.txt"))
    error = Exception("ERROR: [youtube] jNQXAC9IVRw: Sign in to confirm you’re not a bot. Use --cookies")
    assert media._is_bot_check(error) and not media._is_bot_check(Exception("Requested format is not available"))
    out_dir = tmp_path / "job"
    out_dir.mkdir()
    reply = media._blocked_reply(out_dir)
    body = json.loads(reply.body)
    assert reply.status_code == 503 and body["code"] == "youtube_blocked" and not out_dir.exists()
    assert sent == [False]


def test_youtube_formats_merge_video_and_audio():
    source = open(media.__file__, encoding="utf-8").read()
    assert "best[height<=720]/best" not in source, "YouTube has no combined files any more"
    assert '"vcodec:h264"' in source
