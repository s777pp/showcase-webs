import io
import time
import zipfile

from PIL import Image

import redis_store as rs
from smweb import admin_jobs, job_diagnostics, jobs as jobs_module
from tests.test_admin_control_center import _client, _isolate, _login, _mutation_headers


def _png(color="#2080c0", size=(40, 20)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _prepare(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(admin_jobs, "DATA", tmp_path)
    monkeypatch.setattr(admin_jobs, "JOBS", tmp_path / "jobs")
    monkeypatch.setattr(rs, "_r", lambda: None)
    rs._local_jobs.clear()
    (tmp_path / "jobs").mkdir()


def test_explanations_name_the_cause_and_who_is_at_fault():
    fit = job_diagnostics.explain({"status": "error", "error": "Failed: a.mp4: RuntimeError: Workshop cannot fit all synchronized panels under 5 MB"})
    assert fit["category"] == "steam_limit" and fit["fault"] == "user"
    broken = job_diagnostics.explain({"status": "error", "error": "UnidentifiedImageError: cannot identify image file"})
    assert broken["category"] == "broken_file"
    server = job_diagnostics.explain({"status": "error", "error": "No files"})
    assert server["fault"] == "server"
    stale = job_diagnostics.explain({"status": "running", "updated": time.time() - 4000})
    assert stale["category"] == "stale"
    partial = job_diagnostics.explain({"status": "done", "errors": ["b.heic: unsupported format"]})
    assert partial["partial"] and partial["category"] == "format"
    assert job_diagnostics.explain({"status": "done"}) is None
    unknown = job_diagnostics.explain({"status": "error", "error": "Something odd"})
    assert unknown["category"] == "unknown"
    # ffmpeg frame counters must not be mistaken for an HTTP 429.
    assert (job_diagnostics.classify("frame=  429 fps=0.0 q=-0.0 Lsize=N/A") or ("",))[0] != "steam_profile"


def test_scrub_hides_urls_tokens_and_paths(tmp_path):
    text = f"Error at {tmp_path}/x.gif https://r2.example/obj?X-Amz-Signature=abc token=secret123"
    clean = job_diagnostics.scrub(text, tmp_path)
    assert "https://" not in clean and "secret123" not in clean and str(tmp_path) not in clean


def test_failed_process_job_keeps_the_source_and_records_a_trace(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs_module, "JOBS", tmp_path)
    monkeypatch.setattr(jobs_module, "_record_process_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(rs, "_r", lambda: None)
    rs._local_jobs.clear()
    jid = "c" * 24
    job_dir = tmp_path / jid
    job_dir.mkdir()
    source = job_dir / "00_broken.png"
    source.write_bytes(b"this is not an image")
    opts = {"modes": ["workshop"], "text": "", "opacity": 0, "color": "#ffffff", "corner": "bl", "scale": 1.0,
            "wm_x": None, "wm_y": None, "do_ac": False, "size_i": 750, "fps": 12, "enc": "ffmpeg", "wm_font": "lap"}
    jobs_module._run_process_job(jid, [("broken.png", source, 0)], opts)
    job = rs.job_get(jid)
    assert job["status"] == "error"
    assert source.is_file(), "the user's file must survive a failure for reproduction and retry"
    assert job["error_traces"] and "UnidentifiedImageError" in job["error_traces"][0]
    assert job_diagnostics.explain(job)["category"] == "broken_file"


def test_admin_jobs_list_detail_and_files(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)
    jid = "d" * 24
    job_dir = tmp_path / "jobs" / jid
    job_dir.mkdir()
    source = job_dir / "00_art.png"
    source.write_bytes(_png("#ff0000", (100, 50)))
    zip_path = job_dir / "result.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("art_workshop/part_1.png", _png())
        archive.writestr("art_workshop/full_with_bars.png", _png("#00ff00"))
    rs.job_create(jid, {"kind": "process", "status": "done", "user_key": "203.0.113.9", "created": time.time(),
                        "files": [{"name": "art.png", "path": str(source), "size": source.stat().st_size},
                                  {"name": "escape.png", "path": "/etc/hosts", "size": 1}],
                        "opts": {"modes": ["workshop"], "fps": 12, "size_i": 750, "enc": "gifski"},
                        "zip_path": str(zip_path)}, enqueue=False)
    client = _client()
    assert client.get("/api/admin/control/jobs").status_code == 403
    _login(client)

    listed = client.get("/api/admin/control/jobs").json()
    item = listed["items"][0]
    assert item["user"]["name"].startswith("Гость #") and "203.0.113.9" not in str(item)
    assert item["preview"]["url"].endswith("/output/1"), "full_with_bars is the preferred preview"
    assert listed["summary"]["counts"]["done"] == 1

    detail = client.get(f"/api/admin/control/jobs/{jid}").json()
    assert [source["name"] for source in detail["sources"]] == ["art.png"], "paths outside DATA are never exposed"
    assert detail["sources"][0]["width"] == 100 and detail["sources"][0]["format"] == "png"
    assert len(detail["outputs"]) == 2

    output = client.get(f"/api/admin/control/jobs/{jid}/output/0")
    assert output.status_code == 200 and output.headers["content-type"] == "image/png"
    assert "sandbox" in output.headers["content-security-policy"]
    original = client.get(f"/api/admin/control/jobs/{jid}/source/0?download=1")
    assert original.status_code == 200 and original.content == source.read_bytes()
    assert original.headers["content-disposition"].startswith("attachment")
    assert client.get(f"/api/admin/control/jobs/{jid}/source/1").status_code == 404
    assert client.get("/api/admin/control/jobs/../../etc").status_code == 404
    assert client.get(f"/api/admin/control/jobs/{jid}/result").headers["content-type"] == "application/zip"


def test_admin_retry_copies_sources_into_a_new_job(monkeypatch, tmp_path):
    _prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(jobs_module, "_worker_mode", lambda: "embedded")
    submitted = []
    monkeypatch.setattr(jobs_module._job_pool, "submit", lambda func, *args: submitted.append(args))
    jid = "e" * 24
    job_dir = tmp_path / "jobs" / jid
    job_dir.mkdir()
    source = job_dir / "00_art.png"
    source.write_bytes(_png())
    rs.job_create(jid, {"kind": "process", "status": "error", "error": "boom", "error_traces": ["t"],
                        "user_key": "7", "files": [{"name": "art.png", "path": str(source), "size": 10}],
                        "opts": {"modes": ["workshop"]}}, enqueue=False)
    client = _client()
    csrf = _login(client)
    response = client.post(f"/api/admin/control/jobs/{jid}/retry", headers=_mutation_headers(csrf))
    assert response.status_code == 200
    new_id = response.json()["job_id"]
    new_job = rs.job_get(new_id)
    assert new_job["retry_of"] == jid and "error_traces" not in new_job and "error" not in new_job
    copied = new_job["files"][0]["path"]
    assert copied != str(source) and open(copied, "rb").read() == source.read_bytes()
    assert submitted and submitted[0][0] == new_id
