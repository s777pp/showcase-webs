# SteamShowcase на Railway — настройка после деплоя

Railway собирает **`Dockerfile`** и запускает **один сервис**. Файл `docker-compose.yml`
здесь не используется вообще — он только для VPS (см. `DEPLOY.md`).

Отсюда главное правило: на Railway работает режим **`WORKER_MODE=embedded`** —
обработка идёт в пуле потоков внутри того же контейнера. Отдельный сервис-воркер
не подходит, потому что том Railway нельзя примонтировать к двум сервисам, а значит
воркер не сможет отдать готовый ZIP через API.

---

## 1. Убрать утёкшие ключи (сделать до пуша)

`data/access_codes.json` лежал в репозитории. Добавления в `.gitignore` **недостаточно** —
файл уже отслеживается git, его нужно снять с учёта явно:

```bash
git rm --cached data/access_codes.json data/used_codes.json
git add .gitignore
git commit -m "Remove access codes from repo"
```

Файл останется у тебя на диске, но перестанет уходить в GitHub и в Docker-образ.

> Старые ключи (`SM-WEB-519F7C-A083`, `SM-WEB-65B30E-E422`, `SM-WEB-E34C88-6EB3`,
> `SM-WEB-B05EA8-24B5`) и админский `SHOWCASE-WEB-PRO` **скомпрометированы**, если репозиторий
> публичный: они лежат в истории коммитов и достаются командой `git log -p`. Их нужно
> перевыпустить. Чистка истории (`git filter-repo` / BFG) имеет смысл только вместе с
> перевыпуском — сами по себе форки и кеши GitHub она не лечит.

Сгенерировать новые:

```bash
python scripts/gen_access_codes.py 10 --label Pro
```

Скрипт печатает готовые строки `ACCESS_CODES=...` и `ACCESS_CODES_JSON=...`.

---

## 2. Подключить Redis

1. В проекте Railway: **New → Database → Add Redis**.
2. Открой сервис **Redis → вкладка Variables**. Там будет `REDIS_URL`
   (приватный адрес вида `redis://default:***@redis.railway.internal:6379`)
   и `REDIS_PUBLIC_URL`.
3. Перейди в **сервис приложения → Variables** и добавь ссылку:

   ```
   REDIS_URL=${{Redis.REDIS_URL}}
   ```

   `Redis` — это **имя сервиса** в твоём проекте. Если ты переименовал его,
   подставь своё имя, иначе ссылка не разрешится и переменная приедет пустой.

**Три самые частые причины «Redis не работает»:**

| Симптом | Причина | Что делать |
|---|---|---|
| `redis_detail.configured: false` | Переменная `REDIS_URL` в сервисе приложения не задана или ссылка не разрешилась | Проверь точное имя сервиса в `${{Имя.REDIS_URL}}` |
| `Error 111 connecting` / `Name or service not known` | Взят приватный адрес, но Redis в **другом проекте или окружении** | Приватная сеть работает только внутри одного проекта+окружения. Либо перенеси сервисы, либо используй `REDIS_PUBLIC_URL` |
| `AuthenticationError` | Пароль скопирован руками и устарел | Всегда используй ссылку `${{Redis.REDIS_URL}}`, а не копипаст |

Redis **необязателен**. Без него приложение полностью работает: очередь, квоты
и лимиты просто живут в памяти процесса и сбрасываются при рестарте.

---

## 3. Переменные окружения сервиса приложения

Обязательные:

```
DATA_DIR=/data
UVICORN_WORKERS=1
WORKER_MODE=embedded
MAX_JOB_WORKERS=2
SECRET_KEY=<длинная случайная строка>
APP_URL=https://<твой-домен>
```

Ключи доступа (вместо удалённого файла):

```
ACCESS_CODES=SM-WEB-AAAAAA-BBBB,SM-WEB-CCCCCC-DDDD
ADMIN_ACCESS_CODE=<новый админский код>
```

либо с метками одной строкой:

```
ACCESS_CODES_JSON={"SM-WEB-AAAAAA-BBBB":{"type":"unlimited","label":"Pro"}}
```

Опционально: `REDIS_URL`, `FREE_LIMIT`, `MAX_UPLOAD_MB`, `MAX_JOBS_PER_USER`,
OAuth (`DISCORD_*`, `GOOGLE_*`, `TELEGRAM_*`), `STRIPE_*`.

> **`UVICORN_WORKERS` держи равным 1.** ZIP-результат лежит на диске того процесса,
> который его собрал. При двух и более воркерах часть запросов `/api/process/status`
> и `/api/process/download` попадает в процесс, который об этой задаче ничего не знает.
> `PORT` Railway подставляет сам — задавать его вручную не нужно.

---

## 4. Том для данных

**Сервис приложения → Settings → Volumes → Add Volume**, mount path `/data`.

Без тома при каждом редеплое теряются: база `users.db`, галерея, аватары и загруженные
файлы задач.

---

## 5. Проверка после деплоя

```bash
curl -s https://<домен>/api/health | python -m json.tool
```

Ожидаемый ответ при подключённом Redis:

```json
{
  "ok": true,
  "db": true,
  "redis": true,
  "redis_detail": { "configured": true, "ok": true,
                    "host": "redis.railway.internal:6379", "error": null },
  "worker": { "mode": "embedded", "external_alive": false,
              "max_concurrent": 2, "queue": 0 },
  "version": "prod-opt-2"
}
```

Если `redis: false` — смотри `redis_detail.error`, там будет конкретная причина
(раньше эндпоинт молча отдавал `false`).

Если `worker.mode` не `embedded` — переменная `WORKER_MODE` перебита где-то ещё
(или остался старый `USE_EXTERNAL_WORKER=1`; удали его).

Дальше — боевая проверка: открой `/app`, вкладку **Process**, загрузи картинку.
Прогресс должен дойти до 100% и скачать ZIP.

---

## 6. Если Process всё ещё не работает

Смотри логи сервиса (**Deployments → View Logs**):

| Строка в логе | Значение |
|---|---|
| `WORKER_MODE=external but no live worker — running embedded` | Где-то остался `USE_EXTERNAL_WORKER=1` или `WORKER_MODE=external`. Задача всё равно выполнится — но переменную лучше убрать |
| `ffmpeg`/`gifski` not found | Ломается сборка образа; проверь шаги установки в `Dockerfile` |
| 429 `Too many active jobs` | Достигнут `MAX_JOBS_PER_USER` (по умолчанию 2). Дождись завершения или подними лимит |
| 403 `Limit N files/day` | Исчерпана бесплатная квота — нужен код доступа или Pro |

Полезные проверки:

```bash
curl -s https://<домен>/api/health_legacy | python -m json.tool   # ffmpeg, шрифты, шаблоны
```

---

## 7. Обновление

`git push` в ветку, к которой привязан сервис — Railway пересоберёт образ
автоматически. Переменные и том при редеплое сохраняются.
