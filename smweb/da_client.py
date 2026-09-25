"""DeviantArt token refresh and upload helpers.

Moved out of main.py unchanged.
"""


from __future__ import annotations

import os
from pathlib import Path


import auth_db


def _da_guess_mime(name: str) -> str:
    ext = Path(name or "").suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
    }.get(ext, "application/octet-stream")


def _da_refresh_token(user: dict) -> str | None:
    """Try refresh DA access token. Returns new access token or None."""
    refresh = (user.get("da_refresh_token") or "").strip()
    if not refresh:
        return None
    cid = (user.get("da_client_id") or "").strip() or (os.environ.get("DA_CLIENT_ID") or "").strip()
    sec = (user.get("da_client_secret") or "").strip() or (os.environ.get("DA_CLIENT_SECRET") or "").strip()
    if not cid or not sec:
        return None
    try:
        import requests as rq
        r = rq.post(
            "https://www.deviantart.com/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": cid,
                "client_secret": sec,
                "refresh_token": refresh,
            },
            timeout=30,
        )
        if r.status_code != 200:
            print("da refresh fail", r.status_code, r.text[:200])
            return None
        data = r.json()
        access = data.get("access_token")
        new_refresh = data.get("refresh_token") or refresh
        if access:
            auth_db.set_da_tokens(int(user["id"]), access, new_refresh)
            return access
    except Exception as e:
        print("da refresh error", e)
    return None


# ====================== DeviantArt OAuth + Sta.sh (per-user keys, like desktop) ======================
_da_pending: dict[str, dict] = {}  # state -> {verifier, user_id, client_id, client_secret, ts}
