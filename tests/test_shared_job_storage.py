import os
import time
from pathlib import Path

from PIL import Image

import smweb.jobs as jobs


def test_process_result_is_written_to_shared_jobs_volume(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "JOBS", tmp_path)
    monkeypatch.setattr(
        jobs.proc,
        "process_image_workshop",
        lambda *_args, **_kwargs: {"piece.png": b"processed"},
    )
    updates = []
    monkeypatch.setattr(jobs, "_job_set", lambda jid, **kw: updates.append((jid, kw)))

    jid = "shared-result"
    upload_dir = tmp_path / jid
    upload_dir.mkdir()
    source = upload_dir / "source.png"
    Image.new("RGB", (8, 8), "red").save(source)
    opts = {
        "modes": ["workshop"],
        "text": "",
        "opacity": 0.0,
        "color": "#ffffff",
        "corner": "bl",
        "scale": 1.0,
        "wm_x": None,
        "wm_y": None,
        "do_ac": False,
        "size_i": 750,
        "fps": 12,
        "enc": "ffmpeg",
        "wm_font": "Fineday",
    }

    jobs._run_process_job(jid, [("source.png", source)], opts)

    done = next(update for _job_id, update in updates if update.get("status") == "done")
    result = Path(done["zip_path"])
    assert result == tmp_path / jid / "result.zip"
    assert result.is_file()


def test_cleanup_preserves_active_shared_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "JOBS", tmp_path)
    active = tmp_path / "active"
    expired = tmp_path / "expired"
    active.mkdir()
    expired.mkdir()
    old = time.time() - 3600
    os.utime(active, (old, old))
    os.utime(expired, (old, old))

    states = {
        "active": {"status": "running", "updated": old},
        "expired": {"status": "done", "updated": old},
    }
    monkeypatch.setattr(jobs.rs, "job_get", lambda jid: states.get(jid))

    assert jobs._cleanup_old_jobs(max_age_sec=900) == 1
    assert active.is_dir()
    assert not expired.exists()
