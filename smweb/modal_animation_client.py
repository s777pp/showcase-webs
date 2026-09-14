"""Owner-only test client. Does not share the upscale URL or modify its client."""
import os
from urllib.parse import urlsplit

import requests

from smweb.animation_experiment import keys


class AnimationServiceError(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class AnimationClient:
    def __init__(self):
        self.base = os.environ.get("MODAL_ANIMATE_URL", "").strip().rstrip("/")
        try:
            parsed = urlsplit(self.base)
            valid = (parsed.scheme == "https" and not parsed.username and not parsed.password
                     and parsed.port in (None, 443) and not parsed.query and not parsed.fragment
                     and parsed.path in ("", "/") and (parsed.hostname or "").endswith((".modal.run", ".modal.direct")))
        except ValueError:
            valid = False
        token_id = os.environ.get("MODAL_PROXY_TOKEN_ID", "").strip()
        token_secret = os.environ.get("MODAL_PROXY_TOKEN_SECRET", "").strip()
        if not valid or not token_id or not token_secret:
            raise AnimationServiceError("Set MODAL_ANIMATE_URL and the existing Modal proxy credentials")
        self.headers = {"Modal-Key": token_id, "Modal-Secret": token_secret, "Accept": "application/json"}

    def _request(self, method, path, **kwargs):
        try:
            response = requests.request(method, self.base + path, headers=self.headers,
                                        allow_redirects=False, timeout=(10, 45), **kwargs)
            if response.status_code not in (200, 202):
                raise AnimationServiceError(f"Animation service returned HTTP {response.status_code}", response.status_code)
            data = response.json()
            if not isinstance(data, dict):
                raise AnimationServiceError("Invalid animation service response")
            return response.status_code, data
        except (requests.RequestException, ValueError):
            raise AnimationServiceError("Animation service unavailable; no automatic resubmission") from None

    def health(self):
        return self._request("GET", "/health")[1]

    def submit(self, payload):
        data = self._request("POST", "/submit", json=payload)[1]
        if data.get("request_id") != payload["request_id"] or not str(data.get("call_id", "")).startswith("fc-"):
            raise AnimationServiceError("Invalid submission response; check request status")
        return data

    def result(self, request_id):
        keys(request_id)
        status, data = self._request("GET", f"/result/{request_id}")
        return status == 200, data

    def cancel(self, request_id):
        keys(request_id)
        return self._request("POST", f"/cancel/{request_id}")[1]
