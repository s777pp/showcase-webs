"""Status of the services added around the core site, for the control centre.

Each check returns a component in admin_control's format (ok / warn / down
with a plain-language summary).  Network probes run in parallel with short
timeouts and are cached for a minute so opening the dashboard stays fast.
"""
from __future__ import annotations

import importlib.util
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_CACHE: dict = {"at": 0.0, "items": []}
TTL = 60


def _get(url: str, headers: dict | None = None, timeout: float = 6) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "showcasemaker-health", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(4096)
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception:
        return 0, b""


def _mirror(c):
    hosts = [h.strip() for h in (os.environ.get("MIRROR_HOSTS") or "").split(",") if h.strip()]
    if not hosts:
        return c("mirror", "Зеркало для России", "warn", "Зеркало не включено",
                 "Пользователи из России без VPN не смогут открыть сайт.", "Настрой deploy/mirror (MIRROR_HOSTS).")
    code, _ = _get(f"https://{hosts[0]}/api/health")
    ok = code == 200
    return c("mirror", "Зеркало для России", "ok" if ok else "down",
             f"{hosts[0]} открывается" if ok else f"{hosts[0]} не отвечает",
             "Сайт доступен из России без VPN." if ok else "Пользователи из России без VPN не попадут на сайт.",
             "" if ok else "Проверь контейнер caddy: docker compose logs caddy.", f"HTTP {code or 'нет ответа'}")


def _relay(c):
    base = (os.environ.get("STEAM_RELAY_URL") or "").strip().rstrip("/")
    if not base:
        return c("relay", "Ретранслятор Steam (Oracle)", "warn", "Не подключён",
                 "Когда Steam ограничит сервер, импорт уйдёт сразу в платный Bright Data.",
                 "Настрой deploy/steam-relay и STEAM_RELAY_URL.")
    code, body = _get(base + "/health")
    ok = code == 200 and body.strip() == b"ok"
    return c("relay", "Ретранслятор Steam (Oracle)", "ok" if ok else "down",
             "Отвечает" if ok else "Не отвечает",
             "Второй IP для импорта профилей работает." if ok else "Импорт профилей по ссылке чаще будет уходить в Bright Data.",
             "" if ok else "Проверь контейнер steam-relay на Oracle и порт 8787.", f"HTTP {code or 'нет ответа'}")


def _modal(c):
    base = (os.environ.get("MODAL_UPSCALE_URL") or "").strip().rstrip("/")
    token_id = (os.environ.get("MODAL_PROXY_TOKEN_ID") or "").strip()
    token_secret = (os.environ.get("MODAL_PROXY_TOKEN_SECRET") or "").strip()
    if not (base and token_id and token_secret):
        return c("upscale", "AI-апскейл (Modal)", "warn", "Modal не настроен",
                 "Обычная обработка работает, но апскейл недоступен.", "Добавь MODAL_UPSCALE_URL и токены в .env.", "Modal")
    code, _ = _get(base + "/health", {"Modal-Key": token_id, "Modal-Secret": token_secret}, timeout=12)
    if code == 200:
        return c("upscale", "AI-апскейл (Modal)", "ok", "Modal отвечает", "Апскейл доступен Pro-пользователям.", "", "Modal · HTTP 200")
    if code == 0:
        return c("upscale", "AI-апскейл (Modal)", "warn", "Modal не ответил за 12 с",
                 "Возможно, сервис просто «просыпается»; первый апскейл будет дольше.",
                 "Обнови проверку через минуту. Если не пройдёт — py -m modal deploy modal_upscale.py.", "Modal · таймаут")
    return c("upscale", "AI-апскейл (Modal)", "down", f"Modal ответил ошибкой {code}",
             "Апскейл не будет работать.", "Проверь токены Modal и выполни py -m modal deploy modal_upscale.py.", f"HTTP {code}")


def _bg_remove(c):
    from smweb import remove_bg_client

    names = remove_bg_client.providers()
    labels = {"modal": "Modal", "iloveapi": "iLoveAPI", "problembo": "Problembo", "removebg": "remove.bg"}
    chain = " → ".join(labels[n] for n in names) or "нет"
    name = "Удаление фона (ИИ)"
    if not names:
        return c("bg_remove", name, "warn", "Ни один сервис не настроен",
                 "Кнопка «Удалить фон» в «Создать дизайн» недоступна.",
                 "py -m modal deploy modal_bg_remove.py и MODAL_BG_REMOVE_URL в .env (или ILOVEAPI_PUBLIC_KEY / PROBLEMBO_API_TOKEN).",
                 "провайдеров нет")
    if "modal" not in names:
        return c("bg_remove", name, "warn", "Свой сервис Modal не настроен",
                 f"Работает через внешние сервисы: {chain}.",
                 "py -m modal deploy modal_bg_remove.py, затем MODAL_BG_REMOVE_URL в .env.", chain)
    base, token_id, token_secret = remove_bg_client._modal_settings()
    # /health runs on the CPU front only, it never starts a GPU container.
    code, _ = _get(base + "/health", {"Modal-Key": token_id, "Modal-Secret": token_secret}, timeout=12)
    if code == 200:
        return c("bg_remove", name, "ok", "Modal отвечает",
                 f"Порядок: {chain}. Первая картинка после простоя ждёт запуск GPU (~20-45 с).", "", f"Modal · HTTP 200 · {chain}")
    spare = len(names) > 1
    if code == 0:
        return c("bg_remove", name, "warn", "Modal не ответил за 12 с",
                 "Скорее всего, сервис просто просыпается." + (" Пока работают запасные: " + chain if spare else ""),
                 "Обнови проверку через минуту.", f"Modal · таймаут · {chain}")
    return c("bg_remove", name, "warn" if spare else "down", f"Modal: ошибка {code}",
             f"Работают запасные сервисы ({chain})." if spare else "Удаление фона не будет работать.",
             "Проверь токены Modal и выполни py -m modal deploy modal_bg_remove.py.", f"HTTP {code} · {chain}")


def _telegram(c):
    token = (os.environ.get("ADMIN_BOT_TOKEN") or "").strip()
    chat = (os.environ.get("ADMIN_BOT_CHAT_ID") or "").strip()
    if not (token and chat):
        return c("notify", "Уведомления в Telegram", "warn", "Не настроены",
                 "Новые обращения и ошибки не будут приходить в бот.", "Добавь ADMIN_BOT_TOKEN и ADMIN_BOT_CHAT_ID в .env.")
    code, body = _get(f"https://api.telegram.org/bot{token}/getMe")
    ok = code == 200
    name = ""
    if ok:
        try:
            name = "@" + json.loads(body).get("result", {}).get("username", "")
        except ValueError:
            pass
    problem = ("" if ok else "Проверь ADMIN_BOT_TOKEN (без кавычек и скобок)." if code in (401, 404)
               else "Telegram недоступен с сервера, повтори проверку позже.")
    return c("notify", "Уведомления в Telegram", "ok" if ok else "down",
             f"Приходят через {name}" if ok else "Telegram не принимает токен",
             "Обращения, ошибки обработки и нехватка места приходят в бот." if ok else "Уведомления не доходят.",
             problem, f"HTTP {code or 'нет ответа'}")


def _bot_api(c):
    ok = bool((os.environ.get("BOT_ADMIN_SECRET") or "").strip())
    return c("bot_api", "Админ-панель в боте", "ok" if ok else "warn",
             "Подключена" if ok else "Не подключена",
             "Из бота можно включать техработы, создавать ключи и отвечать на обращения." if ok
             else "Управление сайтом из бота не работает.", "" if ok else "Задай BOT_ADMIN_SECRET на сайте и в боте.")


def _loop_ai(c):
    torch = importlib.util.find_spec("torch") is not None
    cv2 = importlib.util.find_spec("cv2") is not None
    weights = Path(os.environ.get("RIFE_WEIGHTS") or Path(__file__).resolve().parents[1] / "models" / "flownet_v4.25.pkl")
    rife = torch and weights.is_file()
    state = "ok" if rife and cv2 else ("warn" if cv2 or rife else "down")
    summary = "RIFE и OpenCV на месте" if state == "ok" else ("RIFE недоступен — стык рисует OpenCV" if cv2 else
                                                            "OpenCV недоступен" if rife else "Нейросеть и OpenCV недоступны")
    return c("loop_ai", "Нейросеть для «Зациклить»", state, summary,
             "Стыки циклов дорисовываются без двоения." if state == "ok" else "Стык цикла будет заметнее обычного.",
             "" if state == "ok" else "Пересобери образ: docker compose up -d --build.",
             f"PyTorch: {'да' if torch else 'нет'} · веса RIFE: {'да' if weights.is_file() else 'нет'} · OpenCV: {'да' if cv2 else 'нет'}")


def _steam_import(c):
    import steam_browser_import
    import steam_catalog
    import steam_profile_guard
    cache_dir = steam_catalog._CACHE_PATH.parent if steam_catalog._CACHE_PATH else Path(os.environ.get("DATA_DIR", "data"))
    gate = cache_dir / "steam_profiles.sqlite3"
    try:
        wait = steam_profile_guard.route_wait(gate, "server")
    except Exception:
        wait = 0
    relay = steam_catalog._relay_configured()
    paid = steam_browser_import.configured()
    routes = "сервер" + (" → Oracle" if relay else "") + (" → Bright Data" if paid else "")
    if not wait:
        return c("steam_import", "Импорт профиля Steam", "ok", "Прямой импорт работает",
                 "Профили загружаются с сервера сайта, без затрат.", "", f"Цепочка: {routes}")
    return c("steam_import", "Импорт профиля Steam", "warn", f"Steam ограничил сервер ещё на {max(1, wait // 60)} мин",
             "Пока импорт идёт через " + ("ретранслятор Oracle." if relay else "Bright Data (платно)." if paid else "... ничего — импорт по ссылке недоступен."),
             "Ничего делать не нужно, пауза снимется сама." if relay or paid else "Подключи ретранслятор Oracle.",
             f"Цепочка: {routes}")


def _backups(c):
    from smweb import object_store
    if not object_store.configured():
        return c("backups", "Резервные копии базы", "warn", "R2 не подключён",
                 "Автоматические копии базы не сохраняются.", "Подключи R2 и сервис db-backup.")
    try:
        bucket = (os.environ.get("R2_PRIVATE_BUCKET") or "showcasemaker-private").strip()
        items = object_store.client().list_objects_v2(Bucket=bucket, Prefix="backups/db/").get("Contents") or []
    except Exception:
        return c("backups", "Резервные копии базы", "down", "Не удалось прочитать R2",
                 "Неизвестно, делаются ли копии.", "Проверь R2-переменные в .env.")
    if not items:
        return c("backups", "Резервные копии базы", "down", "Копий нет",
                 "Если сервер сломается, база пропадёт.", "Запусти сервис db-backup: docker compose up -d --build.")
    latest = max(items, key=lambda o: o["LastModified"])
    age_h = (time.time() - latest["LastModified"].timestamp()) / 3600
    ok = age_h <= 30
    return c("backups", "Резервные копии базы", "ok" if ok else "down",
             f"Последняя {age_h:.0f} ч назад" if age_h >= 1 else "Последняя меньше часа назад",
             f"Копий в R2: {len(items)}, база защищена." if ok else "Ночная копия не сделалась.",
             "" if ok else "Проверь docker compose logs db-backup.", f"{latest['Key'].rsplit('/', 1)[-1]} · {latest['Size'] / 1048576:.1f} МБ")


CHECKS = (_mirror, _relay, _steam_import, _modal, _bg_remove, _loop_ai, _telegram, _bot_api, _backups)


def components(make_component) -> list[dict]:
    if time.time() - _CACHE["at"] < TTL and _CACHE["items"]:
        return _CACHE["items"]

    def run(check):
        try:
            return check(make_component)
        except Exception as exc:  # one broken probe must not hide the others
            return make_component(check.__name__.strip("_"), check.__name__.strip("_"), "warn",
                                  "Проверка не выполнилась", "Состояние неизвестно.", "", type(exc).__name__)

    with ThreadPoolExecutor(max_workers=len(CHECKS)) as pool:
        items = list(pool.map(run, CHECKS))
    _CACHE.update(at=time.time(), items=items)
    return items
