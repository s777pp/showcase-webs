"""Gallery works that carry their "Create a design" project, so anyone can open a copy in the Builder and change
everything: background, character, frame, text, effects (owner, 2026-10-09).

Publishing: the author picks one of their saved Builder projects in the publish form and allows remixing.
``capture`` validates the project with the Builder's own rules and copies the author's private layer media
(``/api/builder/assets/<name>``, fields ``src`` and ``depthSource``) next to the work's ZIP:
``gallery_releases/u<uid>/<token>/remix/`` (local DATA + private R2, so deleting the work or the account removes it).
Inside the stored project those links become ``remix:<name>``; ``public_project`` turns them into
``/api/gallery/works/<id>/remix/<name>``, which the Builder accepts as a layer source (routers/builder._allowed_source).
Steam backgrounds keep their Steam links. A remix is a new project of the person who opens it; the work is untouched.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from smweb import core, object_store

LOGGER = logging.getLogger(__name__)
ASSET = re.compile(r"^/api/builder/assets/([a-f0-9]{32}\.(?:png|jpe?g|webp|gif|mp4|webm|mov))$", re.I)
NAME = re.compile(r"^[a-f0-9]{32}\.(?:png|jpe?g|webp|gif|mp4|webm|mov)$", re.I)
MEDIA_FIELDS = ("src", "depthSource")
MAX_BYTES = 150 * 1024 * 1024
TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif",
         ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"}


def _local(rel: str) -> Path:
    base = Path(core.DATA).resolve()
    path = (base / rel).resolve()
    if base not in path.parents:
        raise ValueError("bad path")
    return path


def _builder_asset(uid: int, name: str) -> bytes:
    rel = f"builder/{uid}/{name}"
    if object_store.configured():
        return object_store.get_bytes(rel, public=False)
    return _local(rel).read_bytes()


def capture(uid: int, project_id: str) -> tuple[dict, dict[str, bytes]]:
    """The author's saved project (validated) with media links replaced by remix:<name>, and the media bytes."""
    import auth_db
    from smweb.routers.builder import _validated_project
    row = next((item for item in auth_db.builder_projects_for_user(uid, is_pro=True) if item["id"] == project_id), None)
    if not row:
        raise ValueError("Project not found. Save it in Create a design first")
    project = _validated_project(row.get("project") or {})
    project["name"] = str(row.get("name") or "")[:80]
    files: dict[str, bytes] = {}
    total = 0
    for layer in project["layers"]:
        for field in MEDIA_FIELDS:
            match = ASSET.match(str(layer.get(field) or ""))
            if not match:
                continue
            name = match.group(1).lower()
            if name not in files:
                try:
                    files[name] = _builder_asset(uid, name)
                except Exception:
                    raise ValueError("A layer picture of this project is missing. Open and save the project again")
                total += len(files[name])
            layer[field] = "remix:" + name
    if total > MAX_BYTES:
        raise ValueError("The project media are too large to attach")
    if not project["layers"]:
        raise ValueError("The project is empty")
    return project, files


def store(folder: str, project: dict, files: dict[str, bytes]) -> int:
    """Write project.json and the media under ``folder``; returns the bytes stored."""
    target = _local(folder)
    target.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(project, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    (target / "project.json").write_bytes(payload)
    for name, data in files.items():
        (target / name).write_bytes(data)
    if object_store.configured():
        try:
            object_store.put_bytes(f"{folder}/project.json", payload, public=False, media_type="application/json")
            for name, data in files.items():
                object_store.put_bytes(f"{folder}/{name}", data, public=False,
                                       media_type=TYPES.get(Path(name).suffix.lower(), "application/octet-stream"))
        except Exception:
            # The DATA volume copy is enough to serve it; R2 is the backup for a rebuilt server.
            LOGGER.exception("gallery remix: private R2 mirror failed for %s", folder)
    return len(payload) + sum(len(data) for data in files.values())


def _read(folder: str, name: str) -> bytes:
    path = _local(f"{folder}/{name}")
    if path.is_file():
        return path.read_bytes()
    if object_store.configured():
        return object_store.get_bytes(f"{folder}/{name}", public=False)
    raise FileNotFoundError(name)


def public_project(item_id: int, folder: str) -> dict:
    project = json.loads(_read(folder, "project.json"))
    base = f"/api/gallery/works/{int(item_id)}/remix/"
    for layer in project.get("layers") or []:
        for field in MEDIA_FIELDS:
            value = str(layer.get(field) or "")
            if value.startswith("remix:"):
                layer[field] = base + value[6:]
    return project


def media(folder: str, name: str) -> tuple[bytes, str]:
    if not NAME.match(name or ""):
        raise FileNotFoundError(name)
    return _read(folder, name.lower()), TYPES.get(Path(name).suffix.lower(), "application/octet-stream")


def remove(folder: str) -> None:
    import shutil
    try:
        shutil.rmtree(_local(folder), ignore_errors=True)
    except ValueError:
        pass
    if object_store.configured():
        try:
            object_store.delete_prefix(folder, public=False)
        except Exception:
            LOGGER.exception("gallery remix: R2 cleanup failed for %s", folder)


GALLERY_SOURCE = re.compile(r"^/api/gallery/works/(\d{1,12})/remix/([a-f0-9]{32}\.(?:png|jpe?g|webp|gif|mp4|webm|mov))$", re.I)


def adopt(project: dict, uid: int) -> dict:
    """Saving a remixed project: copy the gallery work's media into the saver's own Builder assets, so the copy keeps
    working after the author deletes or edits the work. A link that cannot be read is left as it is."""
    import secrets
    import auth_db
    copied: dict[str, str] = {}
    rows: dict[int, dict | None] = {}
    for layer in project.get("layers") or []:
        for field in MEDIA_FIELDS:
            value = str(layer.get(field) or "")
            match = GALLERY_SOURCE.match(value)
            if not match:
                continue
            if value not in copied:
                item_id, name = int(match.group(1)), match.group(2).lower()
                if item_id not in rows:
                    row = auth_db.gallery_get(item_id)
                    usable = row and row.get("remix_path") and (row.get("status") == "approved"
                                                                or int(row.get("user_id") or 0) == int(uid))
                    rows[item_id] = row if usable else None
                row = rows[item_id]
                if not row:
                    continue
                try:
                    data, media_type = media(str(row["remix_path"]), name)
                except Exception:
                    continue
                own = secrets.token_hex(16) + Path(name).suffix.lower()
                rel = f"builder/{int(uid)}/{own}"
                if object_store.configured():
                    object_store.put_bytes(rel, data, public=False, media_type=media_type)
                else:
                    path = _local(rel)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                copied[value] = f"/api/builder/assets/{own}"
            if value in copied:
                layer[field] = copied[value]
    return project
