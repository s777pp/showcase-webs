""""My results": finished ZIPs kept for signed-in users beyond the job TTL.

Normal job folders disappear after ``JOB_RESULT_TTL_SECONDS`` (24 h).  When a
signed-in user's Process or Workshop Studio job finishes, the worker copies the
ZIP to durable storage (private R2 when configured, otherwise the shared
``/data/results/<user_id>`` folder) and records a row in ``saved_results``.
A small WebP thumbnail always stays on the data volume.

Everything here is best effort: a failed save never fails the job itself.
"""
from __future__ import annotations

import io
import logging
import os
import re
import secrets
import shutil
import time
import zipfile
from pathlib import Path

from PIL import Image, ImageSequence

import auth_db
from smweb import object_store

LOG = logging.getLogger(__name__)

KEEP_DAYS = max(1, int(os.environ.get("RESULTS_KEEP_DAYS") or 30))
MAX_PER_USER = max(1, int(os.environ.get("RESULTS_MAX_PER_USER") or 20))
MAX_ZIP_MB = max(1, int(os.environ.get("RESULTS_MAX_ZIP_MB") or 80))

ROOT = Path(auth_db.DATA) / "results"
RESULT_ID = re.compile(r"[a-f0-9]{24}")
_PREVIEW_NAME = re.compile(r"preview\.(?:png|gif|jpe?g|webp)", re.I)
_PANEL_NAME = re.compile(
    r"(?:part_[1-5]|row_[1-3]|featured_630|center_506|side_100)\.(?:png|gif|jpe?g|webp)", re.I
)
_THUMB_HEIGHT = 120
_THUMB_MAX_WIDTH = 640
_THUMB_BG = (8, 14, 22)


def owner_id(user_key: str) -> int | None:
    """Job ``user_key`` is the account id for signed-in users and an IP otherwise."""
    key = str(user_key or "").strip()
    return int(key) if key.isdigit() else None


def _user_dir(user_id: int) -> Path:
    return ROOT / str(int(user_id))


def thumb_path(user_id: int, result_id: str) -> Path | None:
    if not RESULT_ID.fullmatch(str(result_id or "")):
        return None
    path = _user_dir(user_id) / f"{result_id}.webp"
    return path if path.is_file() else None


def local_zip_path(row: dict) -> Path | None:
    """Resolve a local ZIP reference, refusing anything outside the owner's folder."""
    if row.get("storage") != "local":
        return None
    base = _user_dir(int(row["user_id"])).resolve()
    try:
        path = (base / Path(str(row.get("zip_ref") or "")).name).resolve()
        path.relative_to(base)
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None


def _first_frame(data: bytes) -> Image.Image:
    with Image.open(io.BytesIO(data)) as image:
        frame = next(ImageSequence.Iterator(image)).convert("RGBA")
    background = Image.new("RGBA", frame.size, _THUMB_BG + (255,))
    background.alpha_composite(frame)
    return background.convert("RGB")


def build_thumbnail(zip_path: Path) -> bytes | None:
    """A small strip of the first output group (or its ready-made preview)."""
    try:
        with zipfile.ZipFile(zip_path) as archive:
            entries = [e for e in archive.infolist() if not e.is_dir() and 0 < e.file_size <= 40 * 1024 * 1024]
            previews = [e for e in entries if _PREVIEW_NAME.fullmatch(Path(e.filename).name)]
            if previews:
                chosen = previews[:1]
            else:
                panels = [e for e in entries if _PANEL_NAME.fullmatch(Path(e.filename).name)]
                if not panels:
                    return None
                folder = str(Path(panels[0].filename).parent)
                chosen = sorted(
                    (e for e in panels if str(Path(e.filename).parent) == folder),
                    key=lambda e: Path(e.filename).name,
                )[:5]
            frames = []
            for entry in chosen:
                frame = _first_frame(archive.read(entry))
                width = max(1, round(frame.width * _THUMB_HEIGHT / max(1, frame.height)))
                frames.append(frame.resize((width, _THUMB_HEIGHT), Image.LANCZOS))
    except Exception:
        LOG.warning("saved result thumbnail failed", exc_info=True)
        return None
    gap = 4 if len(frames) > 1 else 0
    strip = Image.new("RGB", (sum(f.width for f in frames) + gap * (len(frames) - 1), _THUMB_HEIGHT), _THUMB_BG)
    x = 0
    for frame in frames:
        strip.paste(frame, (x, 0))
        x += frame.width + gap
    if strip.width > _THUMB_MAX_WIDTH:
        strip = strip.resize((_THUMB_MAX_WIDTH, max(1, round(strip.height * _THUMB_MAX_WIDTH / strip.width))), Image.LANCZOS)
    out = io.BytesIO()
    strip.save(out, "WEBP", quality=80, method=4)
    return out.getvalue()


def _delete_storage(row: dict) -> None:
    uid = int(row["user_id"])
    rid = str(row["id"])
    try:
        if row.get("storage") == "r2":
            object_store.delete(str(row["zip_ref"]), public=False)
        else:
            path = local_zip_path(row)
            if path:
                path.unlink(missing_ok=True)
    except Exception:
        LOG.warning("saved result storage cleanup failed id=%s", rid, exc_info=True)
    if RESULT_ID.fullmatch(rid):
        (_user_dir(uid) / f"{rid}.webp").unlink(missing_ok=True)


def save_job_result(jid: str, *, user_key: str, zip_path: Path, kind: str, mode: str = "",
                    title: str = "", file_count: int = 0) -> str | None:
    """Keep a finished job's ZIP for its signed-in owner. Returns the result id."""
    uid = owner_id(user_key)
    if uid is None:
        return None
    try:
        size = zip_path.stat().st_size
    except OSError:
        return None
    if not size or size > MAX_ZIP_MB * 1024 * 1024:
        return None
    rid = secrets.token_hex(12)
    folder = _user_dir(uid)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        if object_store.configured():
            storage, zip_ref = "r2", object_store.upload_file(zip_path, f"results/{uid}/{rid}.zip", public=False)
        else:
            storage, zip_ref = "local", f"{rid}.zip"
            shutil.copyfile(zip_path, folder / zip_ref)
        thumb = build_thumbnail(zip_path)
        if thumb:
            (folder / f"{rid}.webp").write_bytes(thumb)
        now = time.time()
        row = {
            "id": rid, "user_id": uid, "job_id": str(jid), "kind": kind, "mode": mode, "title": title,
            "storage": storage, "zip_ref": zip_ref, "size": size, "file_count": int(file_count or 0),
            "created_at": now, "expires_at": now + KEEP_DAYS * 86400,
        }
        for pruned in auth_db.add_saved_result(row, max_items=MAX_PER_USER):
            _delete_storage(pruned)
        if not auth_db.saved_result_get(uid, rid):
            # Same job saved before (retry of a cached job): drop the duplicate copy.
            _delete_storage(row)
            return None
        return rid
    except Exception:
        LOG.warning("saving result failed job=%s", str(jid)[:8], exc_info=True)
        return None


def delete_result(user_id: int, result_id: str) -> bool:
    row = auth_db.delete_saved_result(int(user_id), str(result_id))
    if not row:
        return False
    _delete_storage(row)
    return True


def cleanup_expired() -> int:
    removed = 0
    try:
        for row in auth_db.pop_expired_saved_results():
            _delete_storage(row)
            removed += 1
    except Exception:
        LOG.warning("saved results cleanup failed", exc_info=True)
    return removed


# The first pass waits one interval: the cleaner thread starts at import time.
_last_cleanup = time.time()


def maybe_cleanup(interval: float = 600.0) -> int:
    """Called from the job cleaner loop; runs the real cleanup every ``interval`` seconds."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < interval:
        return 0
    _last_cleanup = now
    return cleanup_expired()


def public_row(row: dict) -> dict:
    rid = str(row["id"])
    return {
        "id": rid,
        "kind": row.get("kind") or "",
        "mode": row.get("mode") or "",
        "title": row.get("title") or "",
        "size": int(row.get("size") or 0),
        "file_count": int(row.get("file_count") or 0),
        "created_at": float(row.get("created_at") or 0),
        "expires_at": float(row.get("expires_at") or 0),
        "download_url": f"/api/results/{rid}/download",
        "thumb_url": f"/api/results/{rid}/thumb" if thumb_path(int(row["user_id"]), rid) else "",
    }
