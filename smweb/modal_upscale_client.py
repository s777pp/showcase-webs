"""Small HTTP client for the protected Modal upscale service."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import requests


BASE_URL = (os.environ.get("MODAL_UPSCALE_URL") or "").strip().rstrip("/")
TOKEN_ID = (os.environ.get("MODAL_PROXY_TOKEN_ID") or "").strip()
TOKEN_SECRET = (os.environ.get("MODAL_PROXY_TOKEN_SECRET") or "").strip()


class ModalUpscaleHTTPError(RuntimeError):
    """Safe HTTP error that never includes credentials or presigned URLs."""


def _raise_safe_http_error(response: requests.Response) -> None:
    if response.ok:
        return
    message = f"Upscale service rejected request (HTTP {response.status_code})"
    # FastAPI's 422 body identifies the invalid field. Only retain its location,
    # message and type; the omitted `input` field can contain signed R2 URLs.
    if response.status_code == 422:
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        safe_details: list[str] = []
        if isinstance(detail, list):
            for item in detail[:3]:
                if not isinstance(item, dict):
                    continue
                location = ".".join(str(part) for part in item.get("loc", []))
                reason = " ".join(str(item.get("msg") or "invalid value").split())[:160]
                error_type = " ".join(str(item.get("type") or "").split())[:80]
                safe_details.append(f"{location}: {reason}" + (f" [{error_type}]" if error_type else ""))
        if safe_details:
            message += ": " + "; ".join(safe_details)
    raise ModalUpscaleHTTPError(message)


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
    _raise_safe_http_error(response)
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
    _raise_safe_http_error(response)
    return True, response.json()
