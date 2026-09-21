"""Private administration module behind a small, auditable interface."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import secrets
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import auth_db
import processor as proc
import redis_store as rs
from smweb import admin_content, analytics, maintenance, object_store, runtime_settings, user_limits
from smweb.jobs import MAX_JOB_WORKERS, _job_pool, _run_process_job_from_payload, _worker_mode


ADMIN_COOKIE = "sm_admin"
SESSION_SECONDS = 8 * 3600
STARTED_AT = time.time()
ACCESS_FILE = Path(auth_db.DATA) / "access_codes.json"


def _secret() -> str:
    return (os.environ.get("ADMIN_SECRET") or "").strip()


def secret_valid(candidate: str) -> bool:
    expected = _secret()
    return bool(expected and candidate and secrets.compare_digest(expected, str(candidate).strip()))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session() -> tuple[str, str, float]:
    if len(_secret()) < 16:
        raise RuntimeError("ADMIN_SECRET is missing or too short")
    expires_at = time.time() + SESSION_SECONDS
    csrf = secrets.token_urlsafe(24)
    payload = _b64(json.dumps({"exp": expires_at, "csrf": csrf}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}", csrf, expires_at


def session_data(token: str) -> dict | None:
    try:
        payload, signature = str(token or "").split(".", 1)
        expected = _b64(hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).digest())
        if not _secret() or not secrets.compare_digest(signature, expected):
            return None
        data = json.loads(_unb64(payload))
        if float(data.get("exp") or 0) <= time.time() or not data.get("csrf"):
            return None
        return data
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def authorised(request, *, mutation: bool = False) -> bool:
    data = session_data(request.cookies.get(ADMIN_COOKIE) or "")
    if not data:
        return False
    if not mutation:
        return True
    token = request.headers.get("x-admin-csrf") or ""
    return bool(token and secrets.compare_digest(str(data["csrf"]), str(token)))


def origin_allowed(request) -> bool:
    origin = (request.headers.get("origin") or "").rstrip("/")
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    host = (request.headers.get("host") or request.url.netloc).strip()
    allowed = {f"{proto}://{host}".rstrip("/")}
    app_url = (os.environ.get("APP_URL") or "").strip().rstrip("/")
    if app_url:
        allowed.add(app_url)
    return bool(origin and origin in allowed and request.headers.get("sec-fetch-site", "same-origin") != "cross-site")


def audit(action: str, target: str = "", details: dict | None = None) -> None:
    connection = auth_db._conn()
    try:
        connection.execute(
            "INSERT INTO admin_audit(action,target,details_json,created_at) VALUES (?,?,?,?)",
            (str(action)[:80], str(target)[:160], json.dumps(details or {}, ensure_ascii=False)[:4000], time.time()),
        )
        connection.commit()
    finally:
        connection.close()


def audit_rows(limit: int = 100) -> list[dict]:
    connection = auth_db._conn()
    try:
        rows = connection.execute(
            "SELECT id,action,target,details_json,created_at FROM admin_audit ORDER BY created_at DESC LIMIT ?",
            (max(1, min(250, int(limit))),),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["details"] = json.loads(item.pop("details_json") or "{}")
            except (ValueError, TypeError):
                item["details"] = {}
            result.append(item)
        return result
    finally:
        connection.close()


def _component(key: str, title: str, state: str, summary: str, impact: str, action: str = "", technical: str = "") -> dict:
    return {"key": key, "title": title, "state": state, "summary": summary,
            "impact": impact, "action": action, "technical": technical}


def system_snapshot() -> dict:
    components: list[dict] = []
    started = time.perf_counter()
    try:
        connection = auth_db._conn()
        connection.execute("SELECT 1")
        connection.close()
        db_ms = round((time.perf_counter() - started) * 1000)
        components.append(_component("database", "Аккаунты и данные", "ok", "База отвечает", "Вход, профили и проекты работают.", technical=f"{'PostgreSQL' if auth_db.USING_POSTGRES else 'SQLite'} · {db_ms} мс"))
    except Exception:
        components.append(_component("database", "Аккаунты и данные", "down", "База не отвечает", "Пользователи не смогут войти и сохранить изменения.", "Перезапусти postgres и app, затем обнови проверку."))

    redis_ok = False
    try:
        redis_ok = rs.redis_ok()
    except Exception:
        redis_ok = False
    components.append(_component(
        "redis", "Очередь заданий", "ok" if redis_ok else "down",
        "Очередь доступна" if redis_ok else "Очередь недоступна",
        "Задания распределяются между обработчиками." if redis_ok else "Новые тяжёлые задания могут не запускаться.",
        "Перезапусти контейнер redis." if not redis_ok else "",
        "Redis",
    ))
    worker_mode = _worker_mode()
    worker_alive = bool(redis_ok and rs.worker_alive()) if worker_mode == "external" else True
    components.append(_component(
        "worker", "Обработка файлов", "ok" if worker_alive else "down",
        "Обработчик готов" if worker_alive else "Обработчик не отвечает",
        "GIF, видео и изображения обрабатываются." if worker_alive else "Задания будут ждать или выполняться внутри сайта медленнее.",
        "Выполни docker compose restart worker." if not worker_alive else "",
        f"{worker_mode} · до {MAX_JOB_WORKERS} одновременно",
    ))
    ffmpeg = bool(proc.find_ffmpeg())
    gifski = bool(proc.find_gifski()) if hasattr(proc, "find_gifski") else False
    engine_state = "ok" if ffmpeg and gifski else ("warn" if ffmpeg else "down")
    components.append(_component(
        "media", "Движок качества", engine_state,
        "FFmpeg и gifski готовы" if engine_state == "ok" else ("gifski не найден" if ffmpeg else "FFmpeg не найден"),
        "Все режимы и качественный GIF доступны." if engine_state == "ok" else ("Видео работает, но часть GIF может собираться иначе." if ffmpeg else "Обработка медиа не сможет работать."),
        "Проверь установку gifski в Dockerfile." if ffmpeg and not gifski else ("Проверь FFmpeg в контейнере app." if not ffmpeg else ""),
        f"FFmpeg: {'да' if ffmpeg else 'нет'} · gifski: {'да' if gifski else 'нет'}",
    ))
    try:
        usage = shutil.disk_usage(auth_db.DATA)
        free_pct = usage.free / max(1, usage.total) * 100
        storage_state = "ok" if auth_db.DATA_WRITABLE and free_pct >= 12 else ("warn" if auth_db.DATA_WRITABLE and free_pct >= 5 else "down")
        free_gb = usage.free / 1024 ** 3
        components.append(_component(
            "storage", "Место для файлов", storage_state,
            f"Свободно {free_gb:.1f} ГБ",
            "Загрузки и результаты можно сохранять." if storage_state == "ok" else "При заполнении диска обработка и загрузки остановятся.",
            "Удали старые временные файлы или увеличь диск." if storage_state != "ok" else "",
            f"{free_pct:.0f}% свободно · запись: {'да' if auth_db.DATA_WRITABLE else 'нет'}",
        ))
    except Exception:
        components.append(_component("storage", "Место для файлов", "down", "Хранилище недоступно", "Загрузки и результаты не сохранятся.", "Проверь volume appdata и права на /data."))
    try:
        r2_ok, _ = object_store.health()
        r2_configured = object_store.configured()
    except Exception:
        r2_ok, r2_configured = False, object_store.configured()
    components.append(_component(
        "r2", "Облачные файлы", "ok" if r2_ok else ("warn" if not r2_configured else "down"),
        "Cloudflare R2 доступен" if r2_ok else ("R2 не подключён" if not r2_configured else "R2 не отвечает"),
        "Результаты хранятся надёжно и быстро отдаются пользователям." if r2_ok else "Сайт использует локальный диск; это допустимо, но менее надёжно.",
        "Проверь R2-переменные в .env." if r2_configured and not r2_ok else "",
        "R2",
    ))
    modal_ready = all((os.environ.get(name) or "").strip() for name in ("MODAL_UPSCALE_URL", "MODAL_PROXY_TOKEN_ID", "MODAL_PROXY_TOKEN_SECRET"))
    components.append(_component(
        "upscale", "AI-апскейл", "ok" if modal_ready else "warn",
        "Modal подключён" if modal_ready else "Modal не настроен",
        "Апскейл доступен Pro-пользователям." if modal_ready else "Обычная обработка работает, но апскейл недоступен.",
        "Добавь MODAL_UPSCALE_URL и токены в .env." if not modal_ready else "",
        "Modal",
    ))
    severity = {"ok": 0, "warn": 1, "down": 2}
    worst = max((severity[item["state"]] for item in components), default=0)
    overall = "ok" if worst == 0 else ("warn" if worst == 1 else "down")
    queue_depths = rs.queue_depths() if redis_ok else {"media": 0, "profile": 0, "gpu": 0}
    return {
        "overall": overall,
        "headline": "Всё работает штатно" if overall == "ok" else ("Сайт работает, но есть замечания" if overall == "warn" else "Есть проблема, влияющая на пользователей"),
        "components": components,
        "queues": queue_depths,
        "uptime_seconds": max(0, int(time.time() - STARTED_AT)),
        "checked_at": time.time(),
    }


def account_summary() -> dict:
    now = time.time()
    day = now - 86400
    connection = auth_db._conn()
    try:
        row = connection.execute(
            """SELECT COUNT(*) AS total,
               SUM(CASE WHEN created_at>=? THEN 1 ELSE 0 END) AS new_today,
               SUM(CASE WHEN is_pro=1 AND (pro_until IS NULL OR pro_until>?) THEN 1 ELSE 0 END) AS pro,
               SUM(CASE WHEN COALESCE(is_suspended,0)=1 AND (suspended_until IS NULL OR suspended_until>?) THEN 1 ELSE 0 END) AS suspended
               FROM users""",
            (day, now, now),
        ).fetchone()
        pending = connection.execute("SELECT COUNT(*) AS n FROM gallery WHERE status='pending'").fetchone()["n"]
        projects = connection.execute("SELECT COUNT(*) AS n FROM builder_projects").fetchone()["n"]
        return {"total": int(row["total"] or 0), "new_today": int(row["new_today"] or 0),
                "pro": int(row["pro"] or 0), "suspended": int(row["suspended"] or 0),
                "gallery_pending": int(pending or 0), "builder_projects": int(projects or 0)}
    finally:
        connection.close()


def overview(days: int = 30) -> dict:
    return {"ok": True, "system": system_snapshot(), "accounts": account_summary(),
            "analytics": analytics.report(days), "maintenance": maintenance.get_state(),
            "settings": runtime_settings.snapshot(), "attention": attention_items()}


def attention_items() -> list[dict]:
    """Rank the small number of situations that need an operator decision."""
    items = []
    system = system_snapshot()
    for component in system["components"]:
        if component["state"] != "ok":
            items.append({"kind": "system", "severity": "critical" if component["state"] == "down" else "warning",
                          "title": component["summary"], "detail": component["impact"],
                          "action": component.get("action") or "Открой состояние системы.", "target": "system"})
    recent_jobs = jobs(100)["items"]
    failed = [job for job in recent_jobs if job["status"] == "error"]
    stale = [job for job in recent_jobs if job["status"] in {"queued", "running"} and time.time() - job["updated"] > 1800]
    if failed:
        items.append({"kind": "jobs", "severity": "warning", "title": f"Заданий с ошибкой: {len(failed)}",
                      "detail": "Пользователь мог не получить готовый файл.", "action": "Проверь причину и возможность повтора.", "target": "jobs"})
    if stale:
        items.append({"kind": "jobs", "severity": "critical", "title": f"Долго не обновляются: {len(stale)}",
                      "detail": "Задания остаются активными больше 30 минут.", "action": "Проверь worker и очередь.", "target": "jobs"})
    open_tickets = admin_content.tickets("open", 250)
    if open_tickets:
        items.append({"kind": "support", "severity": "info", "title": f"Новых обращений: {len(open_tickets)}",
                      "detail": "Пользователи ждут ответа или решения.", "action": "Открой обращения.", "target": "support"})
    summary = account_summary()
    if summary["gallery_pending"]:
        items.append({"kind": "gallery", "severity": "info", "title": f"На модерации: {summary['gallery_pending']}",
                      "detail": "Работы ещё не опубликованы.", "action": "Проверь галерею.", "target": "gallery"})
    backup = admin_content.backup_snapshot()
    if backup["state"] != "ok":
        items.append({"kind": "backup", "severity": "warning", "title": "Свежая резервная копия не найдена",
                      "detail": "Последняя копия старше 36 часов или каталог пуст.",
                      "action": "Проверь backup-задачу на VPS.", "target": "backups"})
    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(items, key=lambda item: order.get(item["severity"], 3))


def users(query: str = "", page: int = 1, per_page: int = 30) -> dict:
    query = str(query or "").strip().lower()[:120]
    page = max(1, int(page or 1))
    per_page = max(10, min(100, int(per_page or 30)))
    where = ""
    params: list[Any] = []
    if query:
        where = "WHERE lower(u.email) LIKE ? OR lower(COALESCE(u.display_name,'')) LIKE ? OR lower(COALESCE(u.profile_username,'')) LIKE ? OR COALESCE(u.steam_id,'') LIKE ?"
        params = [f"%{query}%"] * 4
    connection = auth_db._conn()
    try:
        total = connection.execute(f"SELECT COUNT(*) AS n FROM users u {where}", params).fetchone()["n"]
        rows = connection.execute(
            f"""SELECT u.id,u.email,u.display_name,u.profile_username,u.avatar_path,u.steam_id,u.created_at,
                u.is_pro,u.pro_until,u.email_verified,COALESCE(u.is_suspended,0) AS is_suspended,
                u.suspended_reason,u.suspended_until,u.discord_id,u.google_id,u.telegram_id,
                (SELECT MAX(s.created_at) FROM sessions s WHERE s.user_id=u.id) AS last_active,
                (SELECT COUNT(*) FROM builder_projects b WHERE b.user_id=u.id) AS project_count,
                (SELECT COUNT(*) FROM gallery g WHERE g.user_id=u.id) AS gallery_count
                FROM users u {where} ORDER BY u.created_at DESC LIMIT ? OFFSET ?""",
            [*params, per_page, (page - 1) * per_page],
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["is_pro"] = bool(item.get("is_pro") and (item.get("pro_until") is None or float(item.get("pro_until") or 0) > time.time()))
            item["is_suspended"] = bool(item.get("is_suspended") and (item.get("suspended_until") is None or float(item.get("suspended_until") or 0) > time.time()))
            item["providers"] = [name for name, key in (("Discord", "discord_id"), ("Google", "google_id"), ("Telegram", "telegram_id"), ("Steam", "steam_id")) if item.get(key)]
            for key in ("discord_id", "google_id", "telegram_id"):
                item.pop(key, None)
            items.append(item)
        return {"ok": True, "items": items, "page": page, "pages": max(1, math.ceil(int(total or 0) / per_page)), "total": int(total or 0)}
    finally:
        connection.close()


def user_detail(user_id: int) -> dict:
    uid = int(user_id)
    connection = auth_db._conn()
    try:
        user = connection.execute(
            """SELECT id,email,display_name,profile_username,avatar_path,steam_id,created_at,is_pro,pro_until,
                      email_verified,COALESCE(is_suspended,0) AS is_suspended,suspended_reason,suspended_until
               FROM users WHERE id=?""", (uid,),
        ).fetchone()
        if not user:
            raise LookupError("Account not found")
        projects = connection.execute(
            """SELECT id,name,showcase_mode,created_at,updated_at,expires_at
               FROM builder_projects WHERE user_id=? ORDER BY updated_at DESC LIMIT 30""", (uid,),
        ).fetchall()
        gallery = connection.execute(
            """SELECT id,title,mode,status,created_at FROM gallery
               WHERE user_id=? ORDER BY created_at DESC LIMIT 30""", (uid,),
        ).fetchall()
        session_row = connection.execute(
            "SELECT COUNT(*) AS total,MAX(created_at) AS last_active FROM sessions WHERE user_id=?", (uid,),
        ).fetchone()
        audit_items = connection.execute(
            """SELECT action,target,details_json,created_at FROM admin_audit
               WHERE target=? ORDER BY created_at DESC LIMIT 30""", (f"user:{uid}",),
        ).fetchall()
    finally:
        connection.close()
    recent_jobs = [item for item in jobs(250)["items"] if str(item.get("user_id") or "") == str(uid)][:30]
    audit_safe = []
    for row in audit_items:
        value = dict(row)
        try:
            value["details"] = json.loads(value.pop("details_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            value["details"] = {}
        audit_safe.append(value)
    return {"ok": True, "user": dict(user), "projects": [dict(row) for row in projects],
            "gallery": [dict(row) for row in gallery], "jobs": recent_jobs,
            "sessions": {"count": int(session_row["total"] or 0), "last_active": session_row["last_active"]},
            "limits": user_limits.get(uid), "audit": audit_safe}


def user_action(user_id: int, action: str, payload: dict) -> dict:
    uid = int(user_id)
    action = str(action or "")
    connection = auth_db._conn()
    try:
        row = connection.execute("SELECT id,email FROM users WHERE id=?", (uid,)).fetchone()
        if not row:
            raise LookupError("Account not found")
        if action == "grant_pro":
            days = max(0.0, min(3650.0, float(payload.get("days") or 0)))
            until = time.time() + days * 86400 if days else None
            connection.execute("UPDATE users SET is_pro=1,pro_code=?,pro_until=? WHERE id=?", ("ADMIN-GRANT", until, uid))
        elif action == "revoke_pro":
            connection.execute("UPDATE users SET is_pro=0,pro_until=NULL WHERE id=?", (uid,))
        elif action == "revoke_sessions":
            connection.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        elif action == "suspend":
            days = max(0, min(3650, int(payload.get("days") or 0)))
            until = time.time() + days * 86400 if days else None
            reason = str(payload.get("reason") or "Administrative suspension").strip()[:240]
            connection.execute("UPDATE users SET is_suspended=1,suspended_reason=?,suspended_until=? WHERE id=?", (reason, until, uid))
            connection.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        elif action == "unsuspend":
            connection.execute("UPDATE users SET is_suspended=0,suspended_reason=NULL,suspended_until=NULL WHERE id=?", (uid,))
        elif action == "set_limits":
            connection.commit()
            limits = user_limits.set_limits(uid, free_daily_limit=payload.get("free_daily_limit"),
                                           max_jobs=payload.get("max_jobs"), note=payload.get("note", ""))
            audit("user.set_limits", f"user:{uid}", {"free_daily_limit": limits.get("free_daily_limit"),
                                                       "max_jobs": limits.get("max_jobs")})
            return {"ok": True, "limits": limits}
        elif action == "clear_limits":
            connection.commit()
            user_limits.clear(uid)
            audit("user.clear_limits", f"user:{uid}")
            return {"ok": True, "limits": user_limits.get(uid)}
        else:
            raise ValueError("Unknown action")
        connection.commit()
        audit(f"user.{action}", f"user:{uid}", {"email": str(row["email"]), "days": payload.get("days")})
        notification = None
        # Access is granted even if the optional notification provider is down.
        if action == "grant_pro":
            email = str(row["email"] or "").strip()
            if email and "@" in email:
                language = str(payload.get("language") or "ru").lower()
                language = language if language in {"ru", "en"} else "ru"
                try:
                    from mailer import send_pro_granted_email
                    days_val = max(0.0, min(3650.0, float(payload.get("days") or 0)))
                    delivered, _provider_message = send_pro_granted_email(email, days_val, lang=language)
                    notification = {"attempted": True, "delivered": bool(delivered), "language": language}
                except Exception:
                    notification = {"attempted": True, "delivered": False, "language": language}
                audit("email.pro_granted", f"user:{uid}", notification)
        return {"ok": True, "notification": notification}
    finally:
        connection.close()



def jobs(limit: int = 100) -> dict:
    items = []
    for jid, job in rs.job_list_all(limit):
        source_paths = [Path(str(item.get("path") or "")) for item in job.get("files") or []]
        status = str(job.get("status") or "queued")
        items.append({
            "id": jid, "kind": str(job.get("kind") or "process"), "status": status,
            "pct": int(job.get("pct") or 0), "stage": str(job.get("stage") or ""),
            "queue": str(job.get("queue") or rs.queue_for_kind(str(job.get("kind") or "process"))),
            "created": float(job.get("created") or 0), "updated": float(job.get("updated") or 0),
            "error": str(job.get("error") or "")[:240], "user_id": job.get("user_id"),
            "can_retry": str(job.get("kind") or "process") == "process" and status in {"done", "error", "cancelled"}
                         and bool(source_paths) and all(path.is_file() for path in source_paths),
            "stale": status in {"queued", "running"} and time.time() - float(job.get("updated") or job.get("created") or 0) > 1800,
        })
    return {"ok": True, "items": items, "queues": rs.queue_depths()}


def cancel_job(job_id: str) -> dict:
    result = rs.job_cancel(str(job_id))
    if not result:
        raise LookupError("Job not found")
    audit("job.cancel", f"job:{job_id}")
    return {"ok": True}


def retry_job(job_id: str) -> dict:
    old = rs.job_get(str(job_id))
    if not old:
        raise LookupError("Job not found")
    if str(old.get("kind") or "process") != "process":
        raise ValueError("Для этого типа нужно повторно загрузить исходник")
    paths = [Path(str(item.get("path") or "")) for item in old.get("files") or []]
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("Исходные файлы уже удалены — попроси пользователя загрузить их снова")
    jid = secrets.token_hex(12)
    payload = {key: value for key, value in old.items() if key not in {
        "status", "pct", "stage", "error", "updated", "result_path", "result_key", "zip_path",
        "processed", "errors", "listed", "readiness", "cancel_requested", "cache_hit",
    }}
    payload.update({"status": "queued", "pct": 1, "stage": "queued", "created": time.time(), "retry_of": str(job_id)})
    external = _worker_mode() == "external" and rs.redis_ok() and rs.worker_alive()
    rs.job_create(jid, payload, enqueue=external)
    if not external:
        _job_pool.submit(_run_process_job_from_payload, jid, payload)
    audit("job.retry", f"job:{job_id}", {"new_job_id": jid})
    return {"ok": True, "job_id": jid}


def _read_codes() -> dict:
    try:
        data = json.loads(ACCESS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def _write_codes(codes: dict) -> None:
    ACCESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="access-codes-", suffix=".json", dir=str(ACCESS_FILE.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(codes, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, ACCESS_FILE)
    finally:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError:
            pass


def codes() -> dict:
    source = _read_codes()
    connection = auth_db._conn()
    try:
        used = {str(row["code"]): dict(row) for row in connection.execute("SELECT code,user_id,used_at FROM used_codes").fetchall()}
    finally:
        connection.close()
    items = []
    for code, meta in source.items():
        meta = meta if isinstance(meta, dict) else {"type": "unlimited", "label": "Pro"}
        claim = used.get(code)
        items.append({"code": code, "type": meta.get("type", "unlimited"), "label": meta.get("label", "Pro"),
                      "hours": meta.get("hours"), "used": bool(claim), "user_id": claim.get("user_id") if claim else None,
                      "used_at": claim.get("used_at") if claim else None, "campaign": meta.get("campaign", ""),
                      "created_at": meta.get("created_at"), "expires_at": meta.get("expires_at"),
                      "expired": bool(meta.get("expires_at") and float(meta.get("expires_at")) <= time.time())})
    items.sort(key=lambda item: (item["used"], item["code"]))
    return {"ok": True, "items": items}


def generate_codes(count: int, duration_days: int, label: str = "Pro", campaign: str = "", expires_days: int = 0) -> dict:
    count = max(1, min(100, int(count or 1)))
    duration_days = max(0, min(3650, int(duration_days or 0)))
    source = _read_codes()
    created = []
    expires_days = max(0, min(3650, int(expires_days or 0)))
    expires_at = time.time() + expires_days * 86400 if expires_days else None
    while len(created) < count:
        code = f"SM-{'TRIAL' if duration_days else 'WEB'}-{secrets.token_hex(3).upper()}-{secrets.token_hex(2).upper()}"
        if code in source:
            continue
        meta = {"type": "trial", "label": str(label or "Pro")[:50], "hours": duration_days * 24} if duration_days else {"type": "unlimited", "label": str(label or "Pro")[:50]}
        meta.update({"campaign": str(campaign or "")[:80], "created_at": time.time(), "expires_at": expires_at})
        source[code] = meta
        created.append(code)
    _write_codes(source)
    audit("codes.generate", "access_codes", {"count": count, "duration_days": duration_days,
                                                "campaign": str(campaign or "")[:80], "expires_days": expires_days})
    return {"ok": True, "codes": created}


def revoke_code(code: str) -> dict:
    code = str(code or "").strip().upper()
    source = _read_codes()
    if code not in source:
        raise LookupError("Code not found or managed through environment variables")
    source.pop(code, None)
    _write_codes(source)
    audit("codes.revoke", "access_code", {"fingerprint": hashlib.sha256(code.encode()).hexdigest()[:12]})
    return {"ok": True}
