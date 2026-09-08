import time
from pathlib import Path

from PIL import Image

import auth_db
import processor
import smweb.jobs as jobs


def _isolated_auth_db(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_db, "USING_POSTGRES", False)
    monkeypatch.setattr(auth_db, "DB", tmp_path / "users.db")
    monkeypatch.setattr(auth_db, "_SCHEMA_READY", False)
    monkeypatch.setenv("SECRET_KEY", "test-email-code-secret-" * 3)


def test_clockwise_rotation_expands_without_stretching():
    source = Image.new("RGB", (2, 3), "black")
    source.putpixel((0, 0), (255, 0, 0))
    rotated = processor.rotate_image(source, 90)
    assert rotated.size == (3, 2)
    assert rotated.getpixel((2, 0)) == (255, 0, 0)
    assert processor.normalize_rotation(450) == 90


def test_process_job_applies_each_files_rotation(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, "JOBS", tmp_path)
    seen = []
    monkeypatch.setattr(
        jobs.proc,
        "process_image_workshop",
        lambda image, *_args, **_kwargs: seen.append(image.size) or {"part.png": b"ok"},
    )
    monkeypatch.setattr(jobs, "_job_set", lambda *_args, **_kwargs: None)
    source = tmp_path / "portrait.png"
    Image.new("RGB", (200, 400), "#123456").save(source)
    options = {
        "modes": ["workshop"], "text": "", "opacity": 0.0,
        "color": "#fff", "corner": "bl", "scale": 1.0,
        "wm_x": None, "wm_y": None, "do_ac": False,
        "outline_width": 0, "outline_color": "#fff", "size_i": 750,
        "fps": 12, "enc": "ffmpeg", "wm_font": "Fineday",
    }
    jobs._run_process_job("rotation-job", [("portrait.png", source, 90)], options)
    assert seen == [(750, 375)]


def test_email_code_is_keyed_one_time_and_registration_is_atomic(monkeypatch, tmp_path):
    _isolated_auth_db(monkeypatch, tmp_path)
    ok, _msg, code = auth_db.create_email_code("User@Example.com")
    assert ok and len(code) == 6

    connection = auth_db._conn()
    row = connection.execute(
        "SELECT code_hash FROM email_codes WHERE email=?", ("user@example.com",)
    ).fetchone()
    connection.close()
    assert code not in row["code_hash"]

    ok, _msg, reason = auth_db.register_with_email_code(
        "user@example.com", "short", code
    )
    assert not ok and reason == "weak_password"

    ok, _msg, reason = auth_db.register_with_email_code(
        "user@example.com", "a sufficiently long password", "000000"
    )
    assert not ok and reason == "invalid_code"

    ok, _msg, reason = auth_db.register_with_email_code(
        "user@example.com", "a sufficiently long password", code
    )
    assert ok and reason == "ok"
    assert auth_db.user_exists("user@example.com")

    ok, _msg, reason = auth_db.register_with_email_code(
        "user@example.com", "a sufficiently long password", code
    )
    assert not ok and reason == "account_unavailable"


def test_expired_email_code_cannot_register(monkeypatch, tmp_path):
    _isolated_auth_db(monkeypatch, tmp_path)
    ok, _msg, code = auth_db.create_email_code("expired@example.com")
    assert ok
    connection = auth_db._conn()
    connection.execute(
        "UPDATE email_codes SET expires_at=? WHERE email=?",
        (time.time() - 1, "expired@example.com"),
    )
    connection.commit()
    connection.close()

    ok, _msg, reason = auth_db.register_with_email_code(
        "expired@example.com", "a sufficiently long password", code
    )
    assert not ok and reason == "invalid_code"


def test_process_rotation_editor_is_below_preview_and_uses_active_file():
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "app.html").read_text(encoding="utf-8")
    script = (root / "static" / "js" / "app.js").read_text(encoding="utf-8")
    styles = (root / "static" / "css" / "tools-polish.css").read_text(encoding="utf-8")

    preview = html.index('id="wmPreviewCard"')
    rotation = html.index('id="processRotationPanel"')
    files = html.index('id="fileList"')
    assert preview < rotation < files
    assert "activeProcessFileIndex" in script
    assert "ctx.rotate(radians)" in script
    assert "--range-progress" in styles
    assert '.page-tools input[type="checkbox"]:checked::before' in styles


def test_process_preview_draws_the_selected_showcase_layout():
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "app.html").read_text(encoding="utf-8")
    script = (root / "static" / "js" / "app.js").read_text(encoding="utf-8")

    assert 'data-mode="workshop"' in html
    assert 'data-mode="featured"' in html
    assert 'data-mode="split"' in html
    assert "function drawShowcaseGuide(w, h)" in script
    assert "[0, .2, .4, .6, .8, 1]" in script
    assert "[0, 506 / 606, 1]" in script
    assert "drawShowcaseGuide(w, h);" in script
    assert "window.__wmRedraw" in script


def test_all_animation_tools_share_steam_fps_presets():
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "app.html").read_text(encoding="utf-8")
    expected = (
        '<option value="12" selected>12 FPS</option>'
        '<option value="15">15 FPS</option>'
        '<option value="18">18 FPS</option>'
        '<option value="20">20 FPS</option>'
        '<option value="24">24 FPS</option>'
    )
    assert html.count(expected) == 3
    assert 'type="number" id="fps"' not in html
    assert 'type="number" id="composeFps"' not in html


def test_slider_focus_ring_and_button_geometry_are_shared():
    root = Path(__file__).resolve().parents[1]
    controls = (root / "static" / "css" / "tools-polish.css").read_text(encoding="utf-8")
    shared = (root / "static" / "css" / "layout-refinement.css").read_text(encoding="utf-8")
    assert 'input[type="range"]:focus-visible' in controls
    assert "outline: none!important" in controls
    assert "--sm-action-radius:3px" in shared
    assert 'body a[role="button"]:not([data-sm-round]):not([data-sm-pill])' in shared
