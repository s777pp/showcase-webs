"""Cooperative cancellation for local encoders and remote job loops."""
from __future__ import annotations

import contextlib
import os
import subprocess
import threading
from typing import Iterator

import redis_store as rs


class JobCancelled(RuntimeError):
    pass


_state = threading.local()


@contextlib.contextmanager
def job_context(jid: str) -> Iterator[None]:
    previous = getattr(_state, "jid", "")
    _state.jid = str(jid or "")
    try:
        yield
    finally:
        _state.jid = previous


def current_job() -> str:
    return str(getattr(_state, "jid", "") or "")


def cancelled(jid: str | None = None) -> bool:
    identifier = str(jid or current_job())
    if not identifier:
        return False
    job = rs.job_get(identifier) or {}
    return bool(job.get("cancel_requested") or job.get("status") == "cancelled")


def checkpoint(jid: str | None = None) -> None:
    if cancelled(jid):
        raise JobCancelled("Job cancelled")


def mark_cancelled(jid: str) -> None:
    rs.job_update(jid, status="cancelled", pct=100, stage="cancelled", error="")


def run(command: list[str], *, check: bool = False, capture_output: bool = False,
        text: bool = False, job_id: str | None = None, **kwargs) -> subprocess.CompletedProcess:
    """Run a subprocess while polling its persisted cancellation flag.

    This works in the external worker too: the API writes the flag to Redis and
    the worker terminates FFmpeg/gifski without requiring an in-process handle.
    """
    identifier = str(job_id or current_job())
    checkpoint(identifier)
    if capture_output:
        kwargs.setdefault("stdout", subprocess.PIPE)
        kwargs.setdefault("stderr", subprocess.PIPE)
    if text:
        kwargs.setdefault("text", True)
    if os.name == "nt":
        kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
    proc = subprocess.Popen(command, **kwargs)
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=0.35)
            break
        except subprocess.TimeoutExpired:
            if cancelled(identifier):
                proc.terminate()
                try:
                    proc.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                raise JobCancelled("Job cancelled")
    result = subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command, output=stdout, stderr=stderr)
    return result
