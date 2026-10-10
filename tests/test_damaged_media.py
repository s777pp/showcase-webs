"""Damaged uploads (production error 2026-10-09: FFmpeg exit status 69 on a GIF in Workshop Studio)."""
import subprocess

import pytest
from PIL import Image

from smweb import job_diagnostics, process_control
from smweb import workshop_studio_jobs as studio


def _gif(path, frames=6):
    images = [Image.new("RGB", (64, 48), (30 * i, 90, 160)) for i in range(frames)]
    images[0].save(path, save_all=True, append_images=images[1:], duration=80, loop=0)
    return path


def test_ffmpeg_commands_ignore_the_decode_error_rate():
    assert process_control.tolerant(["/usr/bin/ffmpeg", "-y", "-i", "a.gif", "b.mp4"])[:3] == \
        ["/usr/bin/ffmpeg", "-max_error_rate", "1"]
    assert process_control.tolerant(["C:/bin/ffmpeg.exe", "-i", "a"])[1:3] == ["-max_error_rate", "1"]
    already = ["ffmpeg", "-max_error_rate", "0.5", "-i", "a"]
    assert process_control.tolerant(already) == already
    assert process_control.tolerant(["gifski", "-o", "x.gif"]) == ["gifski", "-o", "x.gif"]


def test_process_control_run_passes_the_option(monkeypatch):
    seen = []

    class Fake:
        returncode = 0
        def __init__(self, command, **kwargs): seen.append(command)
        def communicate(self, timeout=None): return b"", b""

    monkeypatch.setattr(process_control.subprocess, "Popen", Fake)
    process_control.run(["ffmpeg", "-i", "x.gif", "y.mp4"], job_id="t")
    assert seen[0][:3] == ["ffmpeg", "-max_error_rate", "1"]


def test_a_rejected_gif_is_read_again_from_its_readable_frames(tmp_path, monkeypatch):
    source = _gif(tmp_path / "upload_1.gif")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if str(source) in command:   # the original file: FFmpeg gives up (status 69)
            raise subprocess.CalledProcessError(69, command, stderr=b"Decode error rate 0.9 exceeds maximum 0.666667")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(studio.subprocess, "run", fake_run)
    studio._run_on_source(["ffmpeg", "-i", str(source), "out.mp4"], source)
    assert len(calls) == 2 and "-max_error_rate" in calls[0]
    assert str(source) not in calls[1] and any(part.endswith("_readable.gif") for part in calls[1])
    assert not list(tmp_path.glob("*_readable.gif"))     # the temporary copy is removed


def test_an_unreadable_file_gives_a_clear_error_and_keeps_ffmpegs_words(tmp_path, monkeypatch):
    source = tmp_path / "upload_1.gif"
    source.write_bytes(b"GIF89a" + b"\x00" * 40)          # nothing Pillow can read either

    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(69, command, stderr=b"[gif] LZW decode failed")

    monkeypatch.setattr(studio.subprocess, "run", fake_run)
    with pytest.raises(ValueError) as caught:
        studio._run_on_source(["ffmpeg", "-i", str(source), "out.mp4"], source)
    assert str(caught.value) == studio.DAMAGED_SOURCE and len(str(caught.value)) <= 200
    trace = job_diagnostics.trace_text(caught.value)
    assert "LZW decode failed" in trace and "exit status 69" in trace
    assert job_diagnostics.public_error(str(caught.value)) == {"error_kind": "user", "error_code": "broken_file"}


def test_the_old_production_error_is_explained_as_a_damaged_file():
    text = ("Command '['/usr/bin/ffmpeg', '-y', '-i', '[data]/jobs/x/upload_1.gif']' "
            "returned non-zero exit status 69.")
    assert job_diagnostics.classify(text)[0] == "broken_file"
