"""Cloudflare R2 object storage with a local development fallback."""
from __future__ import annotations

import mimetypes
import os
import threading
import time
from functools import lru_cache
from pathlib import Path


# Gallery objects get a fresh random filename per upload, so they may be cached
# forever.  Avatars, profile backgrounds and profile assets are overwritten in
# place under a stable key: caching those for a year means a user who changes
# their avatar keeps seeing the old one until the URL changes, which it never
# does.  Anything overwritable must therefore use MUTABLE_CACHE.
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
MUTABLE_CACHE = "public, max-age=60"


ACCOUNT_ID = (os.environ.get("R2_ACCOUNT_ID") or "").strip()
ACCESS_KEY = (os.environ.get("R2_ACCESS_KEY_ID") or "").strip()
SECRET_KEY = (os.environ.get("R2_SECRET_ACCESS_KEY") or "").strip()
ENDPOINT = (os.environ.get("R2_ENDPOINT") or "").strip()
PUBLIC_BUCKET = (os.environ.get("R2_PUBLIC_BUCKET") or "showcasemaker-public").strip()
PRIVATE_BUCKET = (os.environ.get("R2_PRIVATE_BUCKET") or "showcasemaker-private").strip()
PUBLIC_BASE = (os.environ.get("R2_PUBLIC_BASE_URL") or "").strip().rstrip("/")
REGION = (os.environ.get("R2_REGION") or "auto").strip()


def configured() -> bool:
    return bool(ACCESS_KEY and SECRET_KEY and (ENDPOINT or ACCOUNT_ID))


@lru_cache(maxsize=1)
def client():
    if not configured():
        return None
    import boto3
    endpoint = ENDPOINT or f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name=REGION,
    )


def clean_key(key: str) -> str:
    value = str(key or "").replace("\\", "/").lstrip("/")
    parts = [p for p in value.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise ValueError("Invalid object key")
    return "/".join(parts)


def key_from_stored(value: str) -> str:
    """Turn old /data/... database paths into stable R2 object keys."""
    raw = str(value or "").replace("\\", "/")
    if "/data/" in raw:
        raw = raw.split("/data/", 1)[1]
    return clean_key(raw)


def content_type(name: str, fallback: str = "application/octet-stream") -> str:
    return mimetypes.guess_type(str(name))[0] or fallback


def put_bytes(
    key: str,
    data: bytes,
    *,
    public: bool = True,
    media_type: str | None = None,
    immutable: bool = False,
) -> str:
    key = clean_key(key)
    c = client()
    if not c:
        raise RuntimeError("R2 is not configured")
    bucket = PUBLIC_BUCKET if public else PRIVATE_BUCKET
    if not public:
        cache = "private, no-store"
    else:
        cache = IMMUTABLE_CACHE if immutable else MUTABLE_CACHE
    c.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=media_type or content_type(key),
        CacheControl=cache,
    )
    return key


def get_bytes(key: str, *, public: bool = True) -> bytes:
    c = client()
    if not c:
        raise RuntimeError("R2 is not configured")
    bucket = PUBLIC_BUCKET if public else PRIVATE_BUCKET
    return c.get_object(Bucket=bucket, Key=clean_key(key))["Body"].read()


def delete(key: str, *, public: bool = True) -> None:
    c = client()
    if c:
        c.delete_object(Bucket=PUBLIC_BUCKET if public else PRIVATE_BUCKET, Key=clean_key(key))


def public_url(key: str) -> str:
    key = clean_key(key)
    return f"{PUBLIC_BASE}/{key}" if PUBLIC_BASE else ""


def presigned_get_url(
    key: str,
    *,
    public: bool = False,
    expires: int = 3600,
    download_name: str | None = None,
) -> str:
    """Create a short-lived URL for one object without exposing R2 credentials."""
    c = client()
    if not c:
        raise RuntimeError("R2 is not configured")
    params: dict[str, str] = {
        "Bucket": PUBLIC_BUCKET if public else PRIVATE_BUCKET,
        "Key": clean_key(key),
    }
    if download_name:
        safe_name = str(download_name).replace('"', "").replace("\r", "").replace("\n", "")[:160]
        params["ResponseContentDisposition"] = f'attachment; filename="{safe_name}"'
    return c.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=max(60, min(int(expires), 86400)),
    )


def presigned_put_url(key: str, *, public: bool = False, expires: int = 3600) -> str:
    """Create a short-lived upload URL restricted to one exact object key."""
    c = client()
    if not c:
        raise RuntimeError("R2 is not configured")
    return c.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": PUBLIC_BUCKET if public else PRIVATE_BUCKET,
            "Key": clean_key(key),
        },
        ExpiresIn=max(60, min(int(expires), 86400)),
    )


_health_lock = threading.Lock()
_health_cache: tuple[float, bool, str | None] = (0.0, False, None)
_HEALTH_TTL = 30.0


def health(*, max_age: float = _HEALTH_TTL) -> tuple[bool, str | None]:
    """Two HEAD requests against R2. Cached: /api/health is polled by nginx,
    the smoke test and the status page, and each miss costs two round trips."""
    if not configured():
        return False, "R2 credentials are not configured"
    now = time.time()
    with _health_lock:
        ts, ok, err = _health_cache
        if now - ts < max_age:
            return ok, err
    try:
        client().head_bucket(Bucket=PUBLIC_BUCKET)
        client().head_bucket(Bucket=PRIVATE_BUCKET)
        result = (True, None)
    except Exception as exc:
        result = (False, f"{type(exc).__name__}: {exc}")
    with _health_lock:
        globals()["_health_cache"] = (now, result[0], result[1])
    return result


def upload_file(path: Path, key: str, *, public: bool = True, immutable: bool = False) -> str:
    return put_bytes(
        key,
        path.read_bytes(),
        public=public,
        media_type=content_type(path.name),
        immutable=immutable,
    )
