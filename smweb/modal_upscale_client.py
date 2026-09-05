"""Small HTTP client for the protected Modal upscale service."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import requests


BASE_URL = (os.environ.get("MODAL_UPSCALE_URL") or "").strip().rstrip("/")
TOKEN_ID = (os.environ.get("MODAL_PROXY_TOKEN_ID") or "").strip()
TOKEN_SECRET = (os.environ.get("MODAL_PROXY_TOKEN_SECRET") or "").strip()


def configured() -> bool:
    if not (BASE_URL and TOKEN_ID and TOKEN_SECRET):
        return False
    parsed = urlparse(BASE_URL)
    return parsed.scheme == "https" and (
        (parsed.hostname or "").endswith(".modal.run")
        or (parsed.hostname or "").endswith(".modal.direct")
    )


def _headers() -> dict[str, str]:
    if not configured():
        raise RuntimeError("Modal upscale service is not configured")
    return {
        "Modal-Key": TOKEN_ID,
        "Modal-Secret": TOKEN_SECRET,
        "Accept": "application/json",
    }


def submit(payload: dict) -> str:
    response = requests.post(
        f"{BASE_URL}/submit",
        json=payload,
        headers=_headers(),
        timeout=(10, 45),
    )
    response.raise_for_status()
    data = response.json()
    call_id = str(data.get("call_id") or "")
    if not call_id.startswith("fc-"):
        raise RuntimeError("Modal returned an invalid call id")
    return call_id


def result(call_id: str) -> tuple[bool, dict]:
    response = requests.get(
        f"{BASE_URL}/result/{call_id}",
        headers=_headers(),
        timeout=(10, 30),
    )
    if response.status_code == 202:
        return False, response.json()
    response.raise_for_status()
    return True, response.json()
