"""Human explanations and safe technical context for background jobs.

Used only by the private admin console. The raw ``error`` text a job stores is
often an encoder message ("RuntimeError: ... 5 MB ..."), which is precise but
hard to act on. ``explain()`` maps it to: what happened, the likely reason,
whether the user or the server is at fault, and what to do next.
"""
from __future__ import annotations

import os
import re
import socket
import time
import traceback
from pathlib import Path

STALE_SECONDS = 1800

_URL = re.compile(r"https?://\S+")
_SECRETISH = re.compile(r"(?i)(token|secret|signature|x-amz-[a-z-]+|key)=([^&\s]+)")


def scrub(text: str, *paths: Path | str) -> str:
    """Remove URLs, credential-like query values and server paths from text."""
    value = str(text or "")
    for path in paths:
        if path:
            value = value.replace(str(path), "[job]")
    try:
        from smweb.core import DATA
        value = value.replace(str(DATA), "[data]")
    except Exception:
        pass
    value = _URL.sub("[url]", value)
    return _SECRETISH.sub(lambda match: f"{match.group(1)}=[hidden]", value)


def trace_text(exc: BaseException, *paths: Path | str, limit: int = 2500) -> str:
    """Last part of a traceback for the admin console, without secrets or paths."""
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return scrub(text, *paths)[-limit:]


def runner_label() -> str:
    mode = (os.environ.get("WORKER_MODE") or "embedded").strip().lower()
    role = "worker" if os.environ.get("SM_PROCESS_ROLE") == "worker" else "app"
    try:
        host = socket.gethostname()[:40]
    except Exception:
        host = "?"
    return f"{role} · {mode} · {host}"


# Each rule: (category, regex over error text, explanation fields).
# Order matters: the first match wins, so specific patterns come first.
_RULES: list[tuple[str, str, dict]] = [
    ("steam_limit", r"cannot fit|under 5 ?MB|group encoding failed|SynchronizedGroupFit|fit all synchronized",
     {"title": "Не влезло в лимит Steam 5 МБ",
      "meaning": "Файл обработался, но даже на минимальном качестве и FPS результат больше 5 МБ, поэтому сайт остановился, чтобы не отдать файл, который Steam не примет.",
      "cause": "Слишком длинная, крупная или очень «шумная» анимация: много мелких деталей, зерно или быстрые смены кадра плохо сжимаются в GIF.",
      "fault": "user",
      "user_fix": "Сократить клип (4–6 с), выбрать меньший FPS или более спокойный фрагмент.",
      "admin_fix": "Скачай исходник и попробуй с меньшей длительностью. Если у тебя проходит, сравни настройки: FPS, длину, режим."}),
    ("upload_limit", r">\s*\d+\s*MB|must be under \d+ ?MB|too large|File too large|All sources together",
     {"title": "Исходник больше лимита загрузки",
      "meaning": "Файл превышает допустимый размер, поэтому до обработки дело не дошло.",
      "cause": "Пользователь загрузил слишком тяжёлое видео или картинку.",
      "fault": "user",
      "user_fix": "Сжать или обрезать видео, уменьшить картинку.",
      "admin_fix": "Ничего чинить не нужно. Если таких много, подумай о повышении MAX_UPLOAD_MB."}),
    ("format", r"unsupported format|Unsupported (source|file) format|unsupported target",
     {"title": "Формат файла не поддерживается",
      "meaning": "Расширение файла не входит в список поддерживаемых.",
      "cause": "Например HEIC с iPhone, AVIF, PSD или архив.",
      "fault": "user",
      "user_fix": "Сохранить как PNG, JPG, GIF, MP4 или WebM.",
      "admin_fix": "Если формат популярный, его можно добавить в список."}),
    ("animated_still", r"Animated image must be exported as GIF",
     {"title": "Анимированная картинка в неподходящем формате",
      "meaning": "Пришёл анимированный WebP/PNG там, где ожидалась обычная картинка.",
      "cause": "Анимированные WebP/APNG обрабатываются только как GIF или видео.",
      "fault": "user",
      "user_fix": "Конвертировать анимацию в GIF или MP4.",
      "admin_fix": "Можно научить инструмент принимать анимированный WebP."}),
    ("broken_file", r"cannot identify image|UnidentifiedImageError|Invalid data found|moov atom not found|truncated|broken data stream|image file is truncated|End of file|could not find codec|Decoder .* not found|cannot probe dimensions|unreadable",
     {"title": "Файл повреждён или это не тот формат",
      "meaning": "Декодер не смог прочитать файл.",
      "cause": "Файл скачался не полностью, расширение переименовано вручную (например .webp назван .png) или кодек не поддерживается (HEVC/ProRes).",
      "fault": "user",
      "user_fix": "Пересохранить файл в обычном редакторе или конвертере и загрузить снова.",
      "admin_fix": "Скачай исходник и проверь его: ffprobe покажет реальный формат и кодек."}),
    ("too_many_pixels", r"DecompressionBomb|exceeds limit of \d+ pixels",
     {"title": "Слишком большое разрешение",
      "meaning": "Картинка содержит больше пикселей, чем безопасно открывать на сервере.",
      "cause": "Очень большое разрешение (десятки мегапикселей).",
      "fault": "user",
      "user_fix": "Уменьшить картинку до 4K или меньше.",
      "admin_fix": "Ничего не нужно, это защита от перегрузки сервера."}),
    ("no_frames", r"produced no frames|no frames|crop produced no frames|too few frames|fragment is too short",
     {"title": "Из файла не получилось взять кадры",
      "meaning": "Выбранный отрезок пустой.",
      "cause": "Время начала больше длины видео, видео без видеодорожки или слишком короткий фрагмент.",
      "fault": "user",
      "user_fix": "Поставить начало раньше или выбрать другой фрагмент.",
      "admin_fix": "Проверь в карточке задания длительность исходника и параметр «начало»."}),
    ("duration", r"duration must be between|Animation duration",
     {"title": "Неподходящая длительность",
      "meaning": "Длина анимации вне допустимого диапазона.",
      "cause": "Слишком короткое или слишком длинное видео для этого инструмента.",
      "fault": "user",
      "user_fix": "Выбрать фрагмент нужной длины.",
      "admin_fix": ""}),
    ("ffmpeg_missing", r"FFmpeg (not|is) (found|available|unavailable)|FFprobe is unavailable|FFmpeg не найден|ffmpeg not found",
     {"title": "На сервере не найден FFmpeg",
      "meaning": "Видео и GIF не могут обрабатываться вообще.",
      "cause": "Проблема окружения: контейнер собран без FFmpeg или бинарник недоступен.",
      "fault": "server",
      "user_fix": "Пользователь ничего сделать не может.",
      "admin_fix": "Проверь «Состояние системы» и образ контейнера worker/app, пересобери образ."}),
    ("gifski", r"gifski",
     {"title": "Ошибка кодировщика gifski",
      "meaning": "Высококачественный GIF-кодировщик завершился с ошибкой.",
      "cause": "gifski не установлен в контейнере, либо не хватило памяти на большом количестве кадров.",
      "fault": "server",
      "user_fix": "Выбрать кодировщик FFmpeg или уменьшить FPS/длину.",
      "admin_fix": "Проверь «Состояние системы» (gifski) и память контейнера worker."}),
    ("timeout", r"TimeoutExpired|timed out|Timeout",
     {"title": "Обработка не уложилась по времени",
      "meaning": "Операция была прервана по таймауту.",
      "cause": "Очень тяжёлый файл, перегруженный сервер или медленный внешний сервис (Modal, Steam).",
      "fault": "server",
      "user_fix": "Попробовать ещё раз позже или с файлом покороче.",
      "admin_fix": "Посмотри нагрузку и очередь. Если таймауты массовые, проверь worker и внешний сервис."}),
    ("memory", r"MemoryError|Cannot allocate|out of memory|Killed",
     {"title": "Серверу не хватило памяти",
      "meaning": "Процесс обработки был остановлен из-за нехватки памяти.",
      "cause": "Большое разрешение и много кадров одновременно, или несколько тяжёлых задач параллельно.",
      "fault": "server",
      "user_fix": "Попробовать файл меньшего разрешения или покороче.",
      "admin_fix": "Проверь память VPS и MAX_JOB_WORKERS. Возможно, стоит уменьшить параллельность."}),
    ("disk", r"No space left|Disk quota",
     {"title": "На сервере закончилось место",
      "meaning": "Результат не удалось записать на диск.",
      "cause": "Диск /data заполнен.",
      "fault": "server",
      "user_fix": "Пользователь ничего сделать не может.",
      "admin_fix": "Освободи место на VPS (старые задания, docker image prune) и проверь «Состояние системы»."}),
    ("no_source", r"^No files$|source missing|source not found|Исходные файлы уже удалены",
     {"title": "Исходник пропал до начала обработки",
      "meaning": "Когда обработчик взял задание, файла уже не было на диске.",
      "cause": "Очистка старых файлов, перезапуск контейнера или app и worker не видят общий volume /data.",
      "fault": "server",
      "user_fix": "Загрузить файл заново.",
      "admin_fix": "Проверь, что app и worker используют один volume appdata:/data. Посмотри, был ли рестарт."}),
    ("worker", r"Worker incompatible",
     {"title": "Версии сайта и обработчика не совпадают",
      "meaning": "Worker получил задание в формате, который не понимает.",
      "cause": "После деплоя пересобрали только app или только worker.",
      "fault": "server",
      "user_fix": "Повторить позже.",
      "admin_fix": "Пересобери и перезапусти оба контейнера: app и worker."}),
    ("gpu", r"GPU upscale|Modal|Upscale service|upscale",
     {"title": "Сбой GPU-апскейла (Modal)",
      "meaning": "Внешний GPU-сервис не вернул результат.",
      "cause": "Холодный старт или перегрузка Modal, закончились кредиты, неверные токены или слишком большой файл.",
      "fault": "external",
      "user_fix": "Повторить через пару минут.",
      "admin_fix": "Проверь дашборд Modal (логи, баланс) и переменные MODAL_* в .env."}),
    ("steam_profile", r"steam_private|profile is private|Steam profile|profile_unavailable|steam_profile|HTTP 429|Too Many Requests|steam_browser",
     {"title": "Не удалось открыть Steam-профиль",
      "meaning": "Импорт профиля не получил данные от Steam.",
      "cause": "Профиль закрыт, ссылка неверная, Steam ограничил запросы (429) или браузерный сервис Bright Data недоступен.",
      "fault": "external",
      "user_fix": "Сделать профиль публичным, проверить ссылку, повторить позже.",
      "admin_fix": "Если ошибка у всех, проверь BRIGHTDATA_* и баланс Bright Data."}),
    ("bg_removal", r"background removal|provider_unavailable|remove_bg",
     {"title": "Сервис удаления фона недоступен",
      "meaning": "remove.bg не ответил или лимит исчерпан.",
      "cause": "Нет ключа REMOVE_BG_API_KEY, закончились кредиты или сервис недоступен.",
      "fault": "external",
      "user_fix": "Повторить позже.",
      "admin_fix": "Проверь ключ и баланс remove.bg."}),
    ("loop", r"Loop processing failed|Invalid loop sequence",
     {"title": "Не получилось собрать зацикливание",
      "meaning": "Шаг склейки петли завершился с ошибкой.",
      "cause": "Обычно проблема с исходным видео (кодек, переменный FPS) или слишком короткий фрагмент.",
      "fault": "unknown",
      "user_fix": "Выбрать другой фрагмент или пересохранить видео в MP4 (H.264).",
      "admin_fix": "Технические детали ниже покажут точный шаг."}),
    ("ffmpeg_failed", r"ffmpeg|CalledProcessError|FFmpeg command failed|video convert failed|frame extract failed|image convert failed",
     {"title": "FFmpeg не смог обработать видео",
      "meaning": "Кодировщик завершился с ошибкой на этом файле.",
      "cause": "Необычный кодек или контейнер: HEVC, ProRes, видео с прозрачностью, переменный FPS, повреждённые кадры.",
      "fault": "user",
      "user_fix": "Перекодировать в MP4 (H.264) и загрузить снова.",
      "admin_fix": "Скачай исходник и повтори. Текст FFmpeg в технических деталях обычно называет проблему прямо."}),
    ("empty_output", r"empty file|empty output|produced an empty",
     {"title": "Результат получился пустым",
      "meaning": "Кодировщик отработал, но файл на выходе пустой.",
      "cause": "Нестандартный исходник или сбой кодировщика.",
      "fault": "unknown",
      "user_fix": "Повторить, при необходимости с другим файлом.",
      "admin_fix": "Повтори задачу с исходником и смотри технические детали."}),
]

_FAULT_LABEL = {"user": "Проблема в файле или настройках пользователя", "server": "Проблема на сервере",
                "external": "Сбой внешнего сервиса", "unknown": "Причина не определена"}


def _text(job: dict) -> str:
    parts = [str(job.get("error_detail") or ""), str(job.get("error") or ""),
             str(job.get("error_code") or job.get("code") or "")]
    parts += [str(item) for item in (job.get("errors") or [])]
    return "\n".join(part for part in parts if part)


def classify(text: str) -> tuple[str, dict] | None:
    for category, pattern, info in _RULES:
        if re.search(pattern, text or "", re.I | re.M):
            return category, info
    return None


def explain(job: dict, now: float | None = None) -> dict | None:
    """Return a human explanation for a failed, cancelled, stuck or partial job."""
    now = now or time.time()
    status = str(job.get("status") or "")
    updated = float(job.get("updated") or job.get("created") or 0)
    if status in {"queued", "running"} and updated and now - updated > STALE_SECONDS:
        return {"category": "stale", "severity": "critical", "title": "Задание зависло",
                "meaning": f"Статус «{status}» не менялся больше {int((now - updated) // 60)} минут.",
                "cause": "Worker перезапустился или упал во время обработки, либо задание осталось в очереди без живого обработчика.",
                "fault": "server", "fault_label": _FAULT_LABEL["server"],
                "user_fix": "Запустить обработку заново.",
                "admin_fix": "Проверь «Состояние системы» (worker) и логи: docker compose logs --tail=100 worker. Зависшее задание можно отменить.",
                "partial": False}
    if status == "cancelled":
        return {"category": "cancelled", "severity": "info", "title": "Отменено",
                "meaning": "Задание остановили до завершения.", "cause": "Отмена пользователем или администратором.",
                "fault": "user", "fault_label": "Отмена", "user_fix": "", "admin_fix": "", "partial": False}
    text = _text(job)
    partial = status == "done" and bool(job.get("errors"))
    if status != "error" and not partial:
        return None
    matched = classify(text)
    if matched:
        category, info = matched
    else:
        category, info = "unknown", {
            "title": "Неизвестная ошибка обработки",
            "meaning": "Сбой, который панель пока не умеет распознавать.",
            "cause": "Смотри технические детали: там исходный текст ошибки и трассировка.",
            "fault": "unknown", "user_fix": "Повторить. Если повторяется, написать в поддержку.",
            "admin_fix": "Скачай исходник и повтори задачу. Пришли мне текст из технических деталей, и я добавлю правило."}
    result = dict(info, category=category, fault_label=_FAULT_LABEL.get(info.get("fault", "unknown"), ""),
                  severity="warning" if partial or info.get("fault") == "user" else "critical", partial=partial)
    if partial:
        result["title"] = "Часть файлов не обработалась: " + result["title"][0].lower() + result["title"][1:]
    return result


def summarize(jobs: list[dict]) -> dict:
    """Counts for the jobs page header: totals and top failure reasons."""
    counts = {"total": len(jobs), "done": 0, "error": 0, "active": 0, "stale": 0}
    reasons: dict[str, dict] = {}
    for job in jobs:
        status = job.get("status")
        if status == "done":
            counts["done"] += 1
        elif status == "error":
            counts["error"] += 1
        elif status in {"queued", "running"}:
            counts["active"] += 1
        info = job.get("explanation")
        if info and info.get("category") == "stale":
            counts["stale"] += 1
        if info and info.get("category") not in {"cancelled", None}:
            bucket = reasons.setdefault(info["category"], {"category": info["category"], "title": info["title"],
                                                           "fault": info.get("fault"), "count": 0})
            bucket["count"] += 1
    finished = counts["done"] + counts["error"]
    counts["success_rate"] = round(counts["done"] / finished * 100) if finished else None
    return {"counts": counts, "reasons": sorted(reasons.values(), key=lambda item: -item["count"])[:8]}
