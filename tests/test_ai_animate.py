"""AI animation beta (smweb/ai_animate.py, ai_animate_jobs.py, routers/ai_animate.py). fal.ai is never called:
``generate`` is replaced by a synthetic clip, everything after it (background, loop, MP4, GIF) runs for real."""
import io
import math
import subprocess

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

import processor as proc
from smweb import ai_animate, ai_animate_jobs, job_diagnostics
from smweb.routers import ai_animate as api

HAS_MEDIA = bool(proc.find_ffmpeg() and proc.find_gifski())


def _still(size=(320, 480)):
    image = Image.new("RGB", size, (20, 40, 90))
    draw = ImageDraw.Draw(image)
    for x in range(0, size[0], 16):
        draw.line((x, 0, x, size[1]), fill=(40, 70, 130))
    draw.ellipse((120, 160, 200, 240), fill=(240, 180, 200))
    return image


def _clip(path, seconds=5, fps=24, size=(320, 480)):
    """A 'model output': the still with a circle that swings and comes back (an honest loop)."""
    frames_dir = path.parent / "clip_frames"
    frames_dir.mkdir(exist_ok=True)
    total = seconds * fps
    for i in range(total):
        image = _still(size)
        dx = round(30 * math.sin(2 * math.pi * i / total))
        ImageDraw.Draw(image).ellipse((120 + dx, 160, 200 + dx, 240), fill=(255, 210, 120))
        image.save(frames_dir / f"f_{i + 1:04d}.png")
    subprocess.run([proc.find_ffmpeg(), "-y", "-v", "error", "-framerate", str(fps), "-i", str(frames_dir / "f_%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def _png_bytes(image):
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


# ---------------------------------------------------------------- prompt
def test_prompt_follows_mode_motions_and_wish():
    calm = ai_animate.build_prompt("calm", ["hair", "blink", "nonsense"], "the ribbon flutters")
    assert "do not change" in calm and "The hair sways" in calm and "blinks" in calm
    assert "nonsense" not in calm and calm.endswith("Also: the ribbon flutters.")
    lively = ai_animate.build_prompt("lively", [])
    assert "Lively natural motion" in lively and "Static camera" in lively
    assert ai_animate.build_prompt("whatever", []) == ai_animate.build_prompt("calm", [])
    assert len(ai_animate.clean_wish("x" * 900)) == ai_animate.WISH_MAX


def test_wish_goes_as_is_without_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert ai_animate.rewrite_wish("  волосы  развеваются ") == "волосы развеваются"
    assert ai_animate.rewrite_wish("") == ""


def test_request_loops_back_to_the_picture_and_turns_the_checker_off():
    body = ai_animate.request_body("data:image/jpeg;base64,AAA", "p")
    assert body["end_image_url"] == body["image_url"] and body["enable_safety_checker"] is False
    assert body["duration"] == 5 and body["resolution"] == "768P" and body["prompt_expansion_mode"] == "disabled"


# ---------------------------------------------------------------- beta allowance
def _reset(*uids):
    import auth_db
    c = auth_db._conn()
    try:
        for uid in uids:
            c.execute("DELETE FROM ai_animate_allowance WHERE user_id=?", (uid,))
        c.commit()
    finally:
        c.close()


def test_beta_allowance_site_budget_and_refunds(monkeypatch):
    _reset(90001, 90002, 90003, 90004)
    monkeypatch.setattr(ai_animate.rs, "_r", lambda: None)
    monkeypatch.setattr(ai_animate, "_LOCAL", {})
    monkeypatch.setenv("AI_ANIMATE_BETA_FREE", "1")
    monkeypatch.setenv("AI_ANIMATE_GLOBAL_DAILY", "3")
    first, _ = ai_animate.take(90001)
    assert first and ai_animate.take(90001) == (None, "user")      # one for the whole beta
    ai_animate.give_back(first)                                     # a failed animation comes back
    again, _ = ai_animate.take(90001)
    assert again and ai_animate.allowance(90001) == {"used": 1, "extra": 0, "total": 1, "left": 0}
    assert ai_animate.grant(90001, 2)["left"] == 2                  # the owner adds two from the admin card
    assert ai_animate.take(90001)[0] and ai_animate.take(90001)[0]  # site budget: 3 of 3 used now
    assert ai_animate.take(90002) == (None, "site")
    assert ai_animate.allowance(90002)["used"] == 0                 # the refused one is not counted
    assert ai_animate.take(90003, exempt=True) == (None, "site")    # exempt accounts still respect the site budget
    assert ai_animate.grant(90004, -5)["extra"] == 0                # never below zero


def test_owner_grants_from_the_admin_console(monkeypatch):
    import auth_db
    from smweb import admin_control
    monkeypatch.setattr(admin_control, "audit", lambda *a, **k: None)
    email = "aianim-grant@example.com"
    if not auth_db.user_exists(email):
        auth_db.register(email, "a-long-password-1")
    c = auth_db._conn()
    try:
        uid = int(dict(c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone())["id"])
    finally:
        c.close()
    _reset(uid)
    monkeypatch.setenv("AI_ANIMATE_BETA_FREE", "1")
    assert admin_control.user_action(uid, "aianim_grant", {"count": 5})["aianim"]["total"] == 6
    assert admin_control.user_detail(uid)["aianim"]["left"] == 6
    assert admin_control.user_action(uid, "aianim_clear", {})["aianim"] == {"used": 0, "extra": 0, "total": 1, "left": 1}


# ---------------------------------------------------------------- loop helpers
def test_loop_window_ends_where_it_starts():
    small = [np.full((4, 4, 3), 100 * math.sin(math.pi * i / 10) ** 2, np.float32) for i in range(30)]
    start, end = ai_animate.pick_loop(small, 11)
    assert end - start == 11 and abs(float(small[end - 1].mean() - small[start].mean())) < 1
    assert ai_animate.pick_loop(small, 50) == (0, 30)
    frames = [np.full((2, 2, 3), i * 10, np.uint8) for i in range(12)]
    looped = ai_animate.crossfade_loop(frames, 3)
    assert len(looped) == 9 and int(looped[-1][0, 0, 0]) == int(frames[2][0, 0, 0])


@pytest.mark.skipif(not HAS_MEDIA, reason="FFmpeg and gifski are required")
def test_render_keeps_the_background_and_fits_steam(tmp_path):
    source = tmp_path / "source.png"
    _still().save(source)
    clip = _clip(tmp_path / "clip.mp4")
    result = ai_animate.render(clip, source, tmp_path, keep_background=True, stem="art")
    gif = Image.open(result["gif"])
    # The whole 5 s clip as the model made it (no loop window): 16 fps, 80 frames, no cross-fade.
    assert gif.n_frames == 80 and result["gif_bytes"] <= 5 * 1024 * 1024 and result["fps"] == 16 and result["crossfade"] == 0
    short = ai_animate.render(clip, source, tmp_path, keep_background=True, stem="short", loop_seconds=2)
    assert short["fps"] == 24 and Image.open(short["gif"]).n_frames < 60
    assert result["moving_pct"] < 40                      # only the swinging circle moves
    # The corner is the original still pixel for pixel (no model shimmer there).
    frame = np.asarray(gif.convert("RGB"), dtype=np.int16)
    corner = np.asarray(_still().resize((gif.width, gif.height)), dtype=np.int16)[:20, :20]
    assert np.abs(frame[:20, :20] - corner).mean() < 6
    assert (tmp_path / "art.mp4").stat().st_size > 1000


# ---------------------------------------------------------------- API
def _app(tmp_path, monkeypatch, *, user=None, pro=True, configured=True, clip=None, refuse=False):
    monkeypatch.setattr(api, "DATA", tmp_path)
    monkeypatch.setattr(api, "_auth_user", lambda request: user)
    monkeypatch.setattr(api.auth_db, "effective_pro", lambda u: pro)
    monkeypatch.setattr(api, "_is_limit_exempt", lambda u: False)
    monkeypatch.setattr(api, "owner_key", lambda request, u=None: str(u["id"]) if u else "g:guest")
    monkeypatch.setattr(api, "_worker_mode", lambda: "embedded")
    monkeypatch.setattr(api._job_pool, "submit", lambda func, *args: func(*args))
    monkeypatch.setattr(ai_animate, "configured", lambda: configured)
    monkeypatch.setattr(ai_animate.rs, "_r", lambda: None)
    monkeypatch.setattr(ai_animate, "_LOCAL", {})
    monkeypatch.setattr(ai_animate_jobs.saved_results, "save_job_result", lambda *a, **k: None)
    monkeypatch.setenv("AI_ANIMATE_BETA_FREE", "2")
    monkeypatch.setenv("AI_ANIMATE_GLOBAL_DAILY", "30")
    if user:
        _reset(user["id"])

    def fake_generate(image_path, prompt, dest, jid="", progress=None):
        if refuse:
            raise ai_animate.Refused("moderated")
        if progress:
            progress("IN_PROGRESS", 30)
        dest.write_bytes(clip.read_bytes())
        return {"seconds": 1.0}

    monkeypatch.setattr(ai_animate, "generate", fake_generate)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_guests_free_users_and_a_missing_key_are_turned_away(tmp_path, monkeypatch):
    picture = _png_bytes(_still())
    with _app(tmp_path, monkeypatch, user=None) as client:
        assert client.get("/api/ai-animate/info").json()["signed_in"] is False
        assert client.post("/api/ai-animate/start", files={"file": ("a.png", picture)}).status_code == 401
    with _app(tmp_path, monkeypatch, user={"id": 90005}, pro=False) as client:
        answer = client.post("/api/ai-animate/start", files={"file": ("a.png", picture)})
        assert answer.status_code == 403 and answer.json()["limit"]["kind"] == "beta"
    with _app(tmp_path, monkeypatch, user={"id": 90005}, configured=False) as client:
        assert client.get("/api/ai-animate/info").json()["available"] is False
        assert client.post("/api/ai-animate/start", files={"file": ("a.png", picture)}).json()["code"] == "unavailable"


def test_bad_pictures_are_rejected_before_a_use_is_taken(tmp_path, monkeypatch):
    with _app(tmp_path, monkeypatch, user={"id": 90005}) as client:
        assert client.post("/api/ai-animate/start", files={"file": ("a.png", b"not a picture")}).json()["code"] == "bad_image"
        tiny = _png_bytes(Image.new("RGB", (60, 60)))
        assert client.post("/api/ai-animate/start", files={"file": ("a.png", tiny)}).json()["code"] == "too_small"
        assert client.get("/api/ai-animate/info").json()["quota"]["left"] == 2


@pytest.mark.skipif(not HAS_MEDIA, reason="FFmpeg and gifski are required")
def test_a_pro_animation_runs_and_the_daily_cap_holds(tmp_path, monkeypatch):
    clip = _clip(tmp_path / "model.mp4")
    picture = _png_bytes(_still())
    with _app(tmp_path, monkeypatch, user={"id": 90005}, clip=clip) as client:
        started = client.post("/api/ai-animate/start", data={"mode": "lively", "motions": "hair,breath,evil",
                                                              "wish": "ribbon flutters"},
                              files={"file": ("My art.png", picture, "image/png")})
        assert started.status_code == 202, started.text
        jid = started.json()["job_id"]
        state = client.get(f"/api/ai-animate/status/{jid}").json()
        assert state["status"] == "done" and state["out_fps"] == 16 and "seconds" not in state
        gif = client.get(state["gif_download"])
        assert gif.status_code == 200 and gif.content[:6] == b"GIF89a"
        assert "My_art_ai.gif" in gif.headers["content-disposition"]
        assert client.get(state["mp4_download"]).status_code == 200
        assert client.get(f"/api/ai-animate/file/{jid}/../../etc").status_code == 404
        job = api.rs.job_get(jid)
        assert job["motions"] == ["hair", "breath"] and "ribbon flutters" in job["prompt"]
        assert client.get("/api/ai-animate/info").json()["quota"]["left"] == 1
        client.post("/api/ai-animate/start", files={"file": ("b.png", picture)})
        capped = client.post("/api/ai-animate/start", files={"file": ("c.png", picture)})
        assert capped.status_code == 429 and capped.json()["code"] == "ai_beta_used" and "limit" not in capped.json()


def test_a_refused_picture_gives_the_use_back(tmp_path, monkeypatch):
    with _app(tmp_path, monkeypatch, user={"id": 90005}, refuse=True) as client:
        jid = client.post("/api/ai-animate/start", files={"file": ("a.png", _png_bytes(_still()))}).json()["job_id"]
        state = client.get(f"/api/ai-animate/status/{jid}").json()
        assert state["status"] == "error" and state["error_code"] == "ai_moderated"
        assert client.get("/api/ai-animate/info").json()["quota"]["left"] == 2
    assert job_diagnostics.public_error(ai_animate_jobs.REFUSED_TEXT) == {"error_kind": "user", "error_code": "ai_moderated"}


def test_other_owners_cannot_see_a_job(tmp_path, monkeypatch):
    monkeypatch.setattr(api.rs, "job_get", lambda jid: {"kind": "ai_animate", "user_key": "9", "status": "done"})
    with _app(tmp_path, monkeypatch, user={"id": 90005}) as client:
        assert client.get("/api/ai-animate/status/" + "a" * 32).status_code == 404


def test_cancelling_a_queued_job_returns_the_use(tmp_path, monkeypatch):
    with _app(tmp_path, monkeypatch, user={"id": 90005}) as client:
        monkeypatch.setattr(api._job_pool, "submit", lambda func, *args: None)   # stays queued
        jid = client.post("/api/ai-animate/start", files={"file": ("a.png", _png_bytes(_still()))}).json()["job_id"]
        assert client.get("/api/ai-animate/info").json()["quota"]["left"] == 1
        assert client.post(f"/api/ai-animate/cancel/{jid}").json()["status"] == "cancelled"
        assert client.get("/api/ai-animate/info").json()["quota"]["left"] == 2
