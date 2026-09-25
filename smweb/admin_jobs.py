"""Admin view of background jobs: who made what, what came out, why it failed.

Everything here is read-only except ``retry``. Files are only ever served from
inside DATA_DIR (job folders, media assets) and with explicit media types, so a
crafted job record cannot make the console read arbitrary server files.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import auth_db
import processor as proc
import redis_store as rs
from smweb import job_diagnostics
from smweb.core import DATA, JOBS

JOB_ID = re.compile(r"[a-f0-9]{24,32}")

KIND_LABELS = {
    "process": "Обработка витрины", "workshop_studio": "Мастерская", "compose": "Персонаж",
    "seamless_loop": "Зацикливание", "upscale": "Апскейл", "builder_bg_remove": "Удаление фона",
    "steam_profile_import": "Импорт профиля", "profile_insight": "Оценка профиля", "steam_dna": "Steam DNA",
}
MODE_LABELS = {"workshop": "Workshop", "featured": "Featured", "split": "Artwork Split",
               "workshop_studio": "Мастерская", "rows": "ряды", "squares": "5 квадратов 150×150"}

# Result files that best show "what came out", in order of preference.
_PREVIEW_ORDER = (r"full_with_bars\.(gif|png)$", r"preview\.(gif|png)$", r"featured_630\.(gif|png)$",
                  r"row_1\.(gif|png)$", r"part_1\.(gif|png)$", r"\.(gif|png|jpe?g|webp)$")
_MEDIA_TYPES = {"png": "image/png", "gif": "image/gif", "jpeg": "image/jpeg", "webp": "image/webp",
                "mp4": "video/mp4", "webm": "video/webm", "mov": "video/quicktime"}


# ------------------------------------------------------------------ helpers
def _inside_data(path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(Path(DATA).resolve())
    except (OSError, ValueError):
        return False


def sniff(path: Path) -> str:
    """Real media type by magic bytes ('' when unknown)."""
    try:
        with path.open("rb") as handle:
            head = handle.read(16)
    except OSError:
        return ""
    if head.startswith(b"\x89PNG"):
        return "png"
    if head[:4] in (b"GIF8",):
        return "gif"
    if head.startswith(b"\xff\xd8"):
        return "jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[4:8] == b"ftyp":
        return "mov" if head[8:10] == b"qt" else "mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"
    return ""


def _sources(job: dict) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for item in job.get("files") or []:
        if isinstance(item, dict) and item.get("path"):
            found.append((str(item.get("name") or Path(str(item["path"])).name), Path(str(item["path"]))))
    for key, label in (("source_path", "Исходник"), ("background_path", "Фон"), ("character_path", "Персонаж")):
        if job.get(key):
            found.append((label, Path(str(job[key]))))
    return [(name, path) for name, path in found if _inside_data(path)]


def _zip_path(job: dict) -> Path | None:
    raw = str(job.get("zip_path") or "")
    path = Path(raw) if raw else None
    return path if path and path.is_file() and _inside_data(path) else None


def _result_path(job: dict) -> Path | None:
    raw = str(job.get("result_path") or "")
    path = Path(raw) if raw else None
    return path if path and path.is_file() and _inside_data(path) else None


def _zip_entries(path: Path) -> list[zipfile.ZipInfo]:
    try:
        with zipfile.ZipFile(path) as archive:
            return [entry for entry in archive.infolist() if not entry.is_dir()][:500]
    except (OSError, zipfile.BadZipFile):
        return []


def _preview_index(entries: list[zipfile.ZipInfo]) -> int | None:
    for pattern in _PREVIEW_ORDER:
        for index, entry in enumerate(entries):
            if re.search(pattern, entry.filename, re.I) and 0 < entry.file_size <= 32 * 1024 * 1024:
                return index
    return None


def _owner(job: dict, users: dict[int, dict]) -> dict:
    key = str(job.get("user_key") or "")
    uid = job.get("user_id") or (job.get("opts") or {}).get("_analytics", {}).get("user_id")
    if not uid:
        match = re.fullmatch(r"(?:[a-z-]+:)?(\d{1,12})", key)
        uid = int(match.group(1)) if match else None
    if uid:
        user = users.get(int(uid)) or {}
        return {"id": int(uid), "name": user.get("display_name") or user.get("profile_username") or user.get("email") or f"ID {uid}",
                "email": user.get("email") or "", "pro": bool(user.get("is_pro"))}
    # Anonymous: never show the IP; a short stable tag groups one visitor's jobs.
    tag = hashlib.sha256(key.encode()).hexdigest()[:6] if key else "------"
    return {"id": None, "name": f"Гость #{tag}", "email": "", "guest": tag}


def _users_for(jobs: list[tuple[str, dict]]) -> dict[int, dict]:
    ids = set()
    for _, job in jobs:
        uid = job.get("user_id") or (job.get("opts") or {}).get("_analytics", {}).get("user_id")
        match = re.fullmatch(r"(?:[a-z-]+:)?(\d{1,12})", str(job.get("user_key") or ""))
        for value in (uid, match.group(1) if match else None):
            try:
                if value:
                    ids.add(int(value))
            except (TypeError, ValueError):
                pass
    if not ids:
        return {}
    connection = auth_db._conn()
    try:
        marks = ",".join("?" * len(ids))
        rows = connection.execute(
            f"SELECT id,email,display_name,profile_username,is_pro,pro_until FROM users WHERE id IN ({marks})",
            list(ids),
        ).fetchall()
    finally:
        connection.close()
    now = time.time()
    result = {}
    for row in rows:
        item = dict(row)
        item["is_pro"] = bool(item.get("is_pro") and (item.get("pro_until") is None or float(item.get("pro_until") or 0) > now))
        result[int(item["id"])] = item
    return result


def settings_summary(job: dict) -> list[str]:
    """Short human list of the options a job ran with."""
    kind = str(job.get("kind") or "process")
    out: list[str] = []
    if kind == "process":
        opts = job.get("opts") or {}
        modes = opts.get("modes") or []
        out.append("Режим: " + (", ".join(MODE_LABELS.get(m, m) for m in modes) or "—"))
        if "workshop" in modes:
            out.append(f"Ширина {opts.get('size_i')} px")
        out.append(f"FPS {opts.get('fps')} · кодировщик {opts.get('enc')}")
        out.append("Водяной знак: " + (f"«{opts.get('text')}»" if opts.get("text") and opts.get("opacity") else "нет"))
        if opts.get("outline_width"):
            out.append(f"Обводка {opts.get('outline_width')} px {opts.get('outline_color')}")
        if opts.get("do_ac"):
            out.append("Автоконтраст")
        rotations = [item.get("rotation") for item in job.get("files") or [] if isinstance(item, dict) and item.get("rotation")]
        if rotations:
            out.append("Поворот: " + ", ".join(f"{r:g}°" for r in rotations))
    elif kind == "workshop_studio":
        options = job.get("options") or {}
        layout = options.get("layout") or "rows"
        out.append("Тип: " + MODE_LABELS.get(layout, layout) + ("" if layout == "squares" else f" · рядов {len(options.get('rows') or [])}"))
        out.append(f"FPS {options.get('fps')} · длина {options.get('duration')} с")
        if options.get("outline"):
            out.append("Обводка")
        if options.get("free_watermark"):
            out.append("Free: водяной знак")
        crop = options.get("crop")
        if isinstance(crop, dict):
            out.append("Кадр: x {x:.0%} · y {y:.0%} · ширина {w:.0%} · высота {h:.0%}".format(**crop))
    elif kind == "seamless_loop":
        out.append(f"Режим {job.get('mode')} · {str(job.get('output_format') or 'gif').upper()} · FPS {job.get('fps')}")
        out.append(f"Начало {job.get('start')} с · длина {job.get('duration')} с · переход {job.get('transition')} с")
    elif kind == "upscale":
        out.append(f"Пресет {job.get('preset')} · ×{job.get('scale')} · {job.get('media_kind')}")
    elif kind == "compose":
        options = job.get("options") or {}
        out.extend(f"{key}: {value}" for key, value in list(options.items())[:8] if not isinstance(value, (dict, list)))
    if job.get("retry_of"):
        out.append(f"Повтор задания {str(job['retry_of'])[:12]}")
    return [item for item in out if item]


def _safe_settings(job: dict) -> dict:
    """Raw options for the detail view, without identifiers or paths."""
    hidden = {"_analytics", "cache_key", "user_key", "path", "sha256", "job_dir", "source_key", "result_key",
              "source_path", "background_path", "character_path", "zip_path", "result_path"}

    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items() if key not in hidden}
        if isinstance(value, list):
            return [clean(item) for item in value[:20]]
        return value

    raw = {key: job.get(key) for key in ("opts", "options", "mode", "fps", "start", "duration", "transition",
                                         "output_format", "preset", "scale", "media_kind") if job.get(key) is not None}
    return clean(raw)


def _duration(job: dict) -> float | None:
    start = float(job.get("started") or job.get("created") or 0)
    end = float(job.get("finished") or (job.get("updated") if job.get("status") in {"done", "error", "cancelled"} else 0) or 0)
    return round(end - start, 1) if start and end and end >= start else None


def _summary(jid: str, job: dict, users: dict[int, dict]) -> dict:
    kind = str(job.get("kind") or "process")
    status = str(job.get("status") or "queued")
    sources = _sources(job)
    zip_path = _zip_path(job)
    entries = _zip_entries(zip_path) if zip_path else []
    preview = None
    if entries:
        index = _preview_index(entries)
        if index is not None:
            preview = {"url": f"/api/admin/control/jobs/{jid}/output/{index}", "type": sniff_name(entries[index].filename)}
    elif _result_path(job):
        preview = {"url": f"/api/admin/control/jobs/{jid}/result?inline=1", "type": sniff(_result_path(job))}
    source_preview = None
    for index, (_, path) in enumerate(sources):
        kind_of_file = sniff(path) if path.is_file() else ""
        if kind_of_file:
            source_preview = {"url": f"/api/admin/control/jobs/{jid}/source/{index}", "type": kind_of_file}
            break
    files = [{"name": str(item.get("name") or ""), "size": int(item.get("size") or 0)}
             for item in job.get("files") or [] if isinstance(item, dict)]
    if not files and job.get("filename"):
        files = [{"name": str(job.get("filename")), "size": int(job.get("input_size") or 0)}]
    explanation = job_diagnostics.explain(job)
    retry_kinds = {"process", "workshop_studio"}
    return {
        "id": jid, "kind": kind, "kind_label": KIND_LABELS.get(kind, kind), "status": status,
        "pct": int(job.get("pct") or 0), "stage": str(job.get("stage") or ""),
        "queue": str(job.get("queue") or rs.queue_for_kind(kind)),
        "created": float(job.get("created") or 0), "updated": float(job.get("updated") or 0),
        "duration": _duration(job), "error": str(job.get("error") or "")[:300],
        "user": _owner(job, users), "user_id": _owner(job, users).get("id"),
        "files": files[:12], "file_count": len(files), "total_size": sum(item["size"] for item in files),
        "settings": settings_summary(job), "explanation": explanation,
        "preview": preview, "source_preview": source_preview,
        "outputs": len(entries) or (1 if _result_path(job) else 0),
        "has_sources": any(path.is_file() for _, path in sources),
        "can_retry": kind in retry_kinds and status in {"done", "error", "cancelled"}
                     and bool(sources) and all(path.is_file() for _, path in sources),
        "stale": bool(explanation and explanation.get("category") == "stale"),
        "cached": bool(job.get("cache_hit")), "retry_of": str(job.get("retry_of") or ""),
    }


def sniff_name(name: str) -> str:
    suffix = Path(name).suffix.lower().lstrip(".")
    return "jpeg" if suffix == "jpg" else suffix


# ------------------------------------------------------------------- public
def list_jobs(limit: int = 150, status: str = "all", kind: str = "", query: str = "") -> dict:
    raw = rs.job_list_all(max(1, min(250, int(limit or 150))))
    users = _users_for(raw)
    items = [_summary(jid, job, users) for jid, job in raw]
    summary = job_diagnostics.summarize([dict(item, status=item["status"]) for item in items])
    query = str(query or "").strip().lower()
    if kind:
        items = [item for item in items if item["kind"] == kind]
    if status == "active":
        items = [item for item in items if item["status"] in {"queued", "running"}]
    elif status == "problem":
        items = [item for item in items if item["explanation"] and item["explanation"]["category"] != "cancelled"]
    elif status in {"done", "error", "cancelled"}:
        items = [item for item in items if item["status"] == status]
    if query:
        items = [item for item in items if query in item["id"] or query in json.dumps(item["user"], ensure_ascii=False).lower()
                 or any(query in file["name"].lower() for file in item["files"])]
    kinds = sorted({job.get("kind") or "process" for _, job in raw})
    return {"ok": True, "items": items, "summary": summary, "queues": rs.queue_depths(),
            "kinds": [{"key": key, "label": KIND_LABELS.get(key, key)} for key in kinds]}


def _probe(path: Path) -> dict:
    real = sniff(path)
    info: dict = {"size": path.stat().st_size, "format": real or "?"}
    if not real:
        # Not a known image/video signature: say so instead of trusting the extension.
        suffix = path.suffix.lower().lstrip(".") or "без расширения"
        info["problem"] = f"Содержимое не похоже на картинку или видео (расширение: .{suffix})"
        head = path.read_bytes()[:12]
        if head[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1", b"ftypavif"):
            info["problem"] = "Это HEIC/AVIF, такой формат сайт не принимает"
        return info
    if info["format"] in {"png", "gif", "jpeg", "webp"}:
        try:
            from PIL import Image
            with Image.open(path) as image:
                info.update(width=image.width, height=image.height, mode=image.mode,
                            frames=int(getattr(image, "n_frames", 1) or 1))
                if info["frames"] > 1:
                    total = 0
                    for frame in range(min(info["frames"], 2000)):
                        image.seek(frame)
                        total += int(image.info.get("duration") or 0)
                    info["duration"] = round(total / 1000, 2)
        except Exception as exc:
            info["problem"] = f"Pillow не открыл файл: {type(exc).__name__}"
        return info
    ffmpeg = proc.find_ffmpeg()
    probe = ffmpeg.replace("ffmpeg", "ffprobe") if ffmpeg else ""
    if not probe:
        return info
    try:
        raw = subprocess.run(
            [probe, "-v", "error", "-show_entries",
             "format=duration,format_name:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=8,
        )
        data = json.loads(raw.stdout or "{}")
        video = next((s for s in data.get("streams") or [] if s.get("codec_type") == "video"), {})
        info.update(width=video.get("width"), height=video.get("height"), codec=video.get("codec_name"),
                    pix_fmt=video.get("pix_fmt"), fps=video.get("r_frame_rate"),
                    duration=round(float((data.get("format") or {}).get("duration") or 0), 2) or None,
                    container=(data.get("format") or {}).get("format_name"))
        if not video:
            info["problem"] = "Нет видеодорожки или ffprobe не смог прочитать файл"
        if raw.returncode and raw.stderr:
            info["problem"] = job_diagnostics.scrub(raw.stderr.strip()[-300:], path.parent)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        info["problem"] = f"ffprobe: {type(exc).__name__}"
    return info


def job_detail(jid: str) -> dict:
    if not JOB_ID.fullmatch(jid or ""):
        raise LookupError("Job not found")
    job = rs.job_get(jid)
    if not job:
        raise LookupError("Job not found")
    users = _users_for([(jid, job)])
    summary = _summary(jid, job, users)
    sources = []
    for index, (name, path) in enumerate(_sources(job)):
        entry = {"index": index, "name": name, "exists": path.is_file()}
        if entry["exists"]:
            entry.update(_probe(path))
            entry["url"] = f"/api/admin/control/jobs/{jid}/source/{index}"
        sources.append(entry)
    outputs = []
    zip_path = _zip_path(job)
    if zip_path:
        for index, entry in enumerate(_zip_entries(zip_path)):
            outputs.append({"index": index, "name": entry.filename, "size": entry.file_size,
                            "type": sniff_name(entry.filename),
                            "url": f"/api/admin/control/jobs/{jid}/output/{index}"})
    elif _result_path(job):
        path = _result_path(job)
        outputs.append({"index": 0, "name": path.name, "size": path.stat().st_size, "type": sniff(path),
                        "url": f"/api/admin/control/jobs/{jid}/result?inline=1"})
    remote = bool(job.get("result_key")) and not zip_path and not _result_path(job)
    return {"ok": True, "job": summary, "sources": sources, "outputs": outputs,
            "result_download": f"/api/admin/control/jobs/{jid}/result" if zip_path or _result_path(job) or remote else "",
            "remote_result": remote,
            "errors": [str(item)[:600] for item in job.get("errors") or []][:20],
            "error_detail": str(job.get("error_detail") or ""),
            "traces": [str(item) for item in job.get("error_traces") or []][:3],
            "runner": str(job.get("runner") or ""), "started": job.get("started"), "finished": job.get("finished"),
            "raw_settings": _safe_settings(job), "readiness": job.get("readiness")}


def _job_or_missing(jid: str) -> dict:
    if not JOB_ID.fullmatch(jid or ""):
        raise LookupError("Job not found")
    job = rs.job_get(jid)
    if not job:
        raise LookupError("Job not found")
    return job


def output_entry(jid: str, index: int) -> tuple[bytes, str, str]:
    """(data, media type, file name) of one result entry inside the job ZIP."""
    job = _job_or_missing(jid)
    zip_path = _zip_path(job)
    if not zip_path:
        raise LookupError("Result expired")
    with zipfile.ZipFile(zip_path) as archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()][:500]
        if not 0 <= index < len(entries):
            raise LookupError("Entry not found")
        entry = entries[index]
        if entry.file_size > 64 * 1024 * 1024:
            raise ValueError("Entry too large")
        data = archive.read(entry)
    kind = sniff_name(entry.filename)
    return data, _MEDIA_TYPES.get(kind, "application/octet-stream"), Path(entry.filename).name


def source_file(jid: str, index: int) -> tuple[Path, str, str]:
    job = _job_or_missing(jid)
    sources = _sources(job)
    if not 0 <= index < len(sources):
        raise LookupError("Source not found")
    name, path = sources[index]
    if not path.is_file():
        raise LookupError("Source was already deleted")
    kind = sniff(path)
    return path, _MEDIA_TYPES.get(kind, "application/octet-stream"), Path(name).name or path.name


def result_file(jid: str) -> tuple[Path | None, str, str, str]:
    """(local path, media type, download name, remote key) for the whole result."""
    job = _job_or_missing(jid)
    zip_path = _zip_path(job)
    if zip_path:
        return zip_path, "application/zip", f"result-{jid[:8]}.zip", ""
    path = _result_path(job)
    if path:
        return path, _MEDIA_TYPES.get(sniff(path), "application/octet-stream"), path.name, ""
    if job.get("result_key"):
        name = str(job.get("download_name") or job.get("filename") or f"result-{jid[:8]}")
        return None, str(job.get("content_type") or "application/octet-stream"), name, str(job["result_key"])
    raise LookupError("Result expired")


def retry(jid: str) -> dict:
    """Run the same job again with copies of its sources (no quota is charged)."""
    from smweb.jobs import _job_pool, _run_process_job_from_payload, _worker_mode
    old = _job_or_missing(jid)
    kind = str(old.get("kind") or "process")
    if kind not in {"process", "workshop_studio"}:
        raise ValueError("Для этого типа нужно, чтобы пользователь загрузил исходник заново")
    sources = [Path(str(item.get("path") or "")) for item in old.get("files") or []]
    if not sources or any(not path.is_file() for path in sources):
        raise ValueError("Исходные файлы уже удалены, попроси пользователя загрузить их снова")
    new_id = secrets.token_hex(12)
    new_dir = JOBS / new_id
    new_dir.mkdir(parents=True, exist_ok=False)
    files = []
    try:
        for index, item in enumerate(old.get("files") or []):
            source = Path(str(item["path"]))
            target = new_dir / f"retry_{index}{source.suffix}"
            shutil.copyfile(source, target)
            files.append({**item, "path": str(target)})
    except OSError:
        shutil.rmtree(new_dir, ignore_errors=True)
        raise ValueError("Не удалось скопировать исходники")
    payload = {key: value for key, value in old.items() if key not in {
        "status", "pct", "stage", "error", "error_detail", "error_traces", "updated", "result_path", "result_key",
        "zip_path", "job_dir", "processed", "errors", "listed", "readiness", "cancel_requested", "cache_hit",
        "runner", "started", "finished",
    }}
    payload.update({"files": files, "status": "queued", "pct": 1, "stage": "queued", "created": time.time(),
                    "retry_of": jid, "admin_retry": True})
    external = _worker_mode() == "external" and rs.redis_ok() and rs.worker_alive()
    rs.job_create(new_id, payload, enqueue=external)
    if not external:
        if kind == "workshop_studio":
            from smweb.workshop_studio_jobs import run
            _job_pool.submit(run, new_id, payload)
        else:
            _job_pool.submit(_run_process_job_from_payload, new_id, payload)
    return {"ok": True, "job_id": new_id}
