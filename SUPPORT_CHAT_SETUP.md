# Помощник Showcase Maker — Groq Free

Прежний дизайн сохранён. Чат использует публичную RU/EN-справку сайта через Groq.
По умолчанию модель `openai/gpt-oss-20b`, Responses API, low reasoning.
Это название модели, а не подключение к платному API OpenAI.
Ключи `OPENAI_API_KEY` и прежняя настройка `SUPPORT_CHAT_MODEL` чат не использует.

## 1. Ключ и бесплатный тариф

Зарегистрируйся на https://console.groq.com/ и создай ключ в
https://console.groq.com/keys . Оставайся на Free: код не управляет тарифом
провайдера и не может гарантировать бесплатность, если ты сам включишь платный план.
API ограничивает и запросы, и токены; квота Groq может закончиться раньше лимита
нашего сайта. При HTTP 429 показывается уведомление, FAQ остаётся доступным.
Нет повторов запросов, автоматического переключения модели или другого провайдера.

Официальные источники:
- https://console.groq.com/docs/quickstart
- https://console.groq.com/docs/responses-api
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/your-data

Ключ не присылай в чат, не добавляй в HTML/JS и не коммить .env.
База знаний остаётся в репозитории; загружать её вручную в Groq не нужно.

## 2. GitHub

Изменения пока в рабочей копии, не опубликованы. В PowerShell из
`C:\Users\n1t1337\Documents\Codex\showcasemaker-current`:

```powershell
git status -sb
git switch main
git add -- .env.example AGENTS.md SUPPORT_CHAT_SETUP.md main.py redis_store.py smweb/support_chat.py smweb/support_knowledge.json smweb/routers/support.py static/css/support-chat.css static/js/support-chat.js static/index.html static/app.html static/gallery.html static/profile.html static/profile-view.html tests/test_support_chat.py
git diff --cached --stat
git commit -m "Add Groq support assistant with bilingual knowledge base"
git push origin main
```

На момент подготовки branch HEAD и origin/main совпадали. Если switch/commit/push
завершается ошибкой, остановись и пришли вывод без секретов: не применяй force push.
Не используй `git add .`: `data/steam_cache.json` — существующий рабочий кэш,
не относящийся к чату. Статический редизайн отменён и в этот commit не попадает.

## 3. VPS

Только после успешного push:

```bash
cd /opt/showcasemaker
git status --short
git pull --ff-only origin main
git log -1 --oneline
nano .env
```

При ошибке pull не продолжай развёртывание. Исторические untracked backups и
docker-compose.override.yml не удаляй.

Добавь/обнови только эти строки, не заменяя весь .env:

```dotenv
GROQ_API_KEY=ВСТАВЬ_СВОЙ_КЛЮЧ_GROQ
GROQ_CHAT_MODEL=openai/gpt-oss-20b
SUPPORT_CHAT_DAILY=20
SUPPORT_CHAT_GLOBAL_DAILY=300
```

Сохранить nano: Ctrl+O, Enter; выйти: Ctrl+X.
Ключ Groq нельзя вставлять в OPENAI_API_KEY. Остальные настройки сайта не трогай.
APP_URL должен соответствовать публичному домену. Доверенные прокси должны
соответствовать существующей цепочке Cloudflare/nginx.

Compose уже передаёт .env и общий Redis сервису app:

```bash
sudo docker compose config --quiet
sudo docker compose up -d --build --no-deps app
sudo docker compose ps app
sudo docker compose exec -T app curl -fsS http://127.0.0.1:8080/api/ready
sudo docker compose exec -T app python -c "from smweb.support_chat import configured, settings; print('Groq configured:', configured()); print('Model:', settings()['model'])"
```

Ожидаются `Groq configured: True` и `Model: openai/gpt-oss-20b`.
Это проверка наличия настройки, не валидности ключа/квоты. Открой сайт, обнови
страницу и спроси помощника: «Как сделать цикл для Steam?» Это проверит живой API.

Никаких миграций и новых зависимостей для чата нет. Worker не выполняет чат-запросы,
перезапуск worker из-за ключа не нужен. Не выполняй down -v и не удаляй данные.
Если код уже установлен и меняется только .env, вместо сборки:

```bash
sudo docker compose up -d --no-deps --force-recreate app
```

Простой restart не обновляет окружение контейнера.

## 4. Необязательный локальный запуск

```powershell
cd "C:\Users\n1t1337\Documents\Codex\showcasemaker-current"
notepad .env
py -m uvicorn main:app --env-file .env --host 127.0.0.1 --port 8092
```

Добавь те же четыре настройки. Открой http://127.0.0.1:8092/ .
Без --env-file Uvicorn не загружает .env автоматически.
Зависимости: `py -m pip install -r requirements.txt`, если окружение не готово.
Не меняй production-защиту ради локальной проверки. При несовместимом локальном
APP_URL/БД используй отдельный локальный env-файл по .env.example.

## Лимиты, данные и диагностика

- По умолчанию: 4 попытки/мин/IP, 20/сутки/IP, 300/сутки на весь сайт.
  Общий IP делит лимит. Production Redis использует фиксированные временные окна;
  локальный fallback — окно от начала счётчика. Смена IP не является способом
  обходить квоты провайдера.
- Неудачные попытки могут расходовать счётчики. Groq имеет отдельные ограничения,
  зависящие от аккаунта/модели. При необходимости уменьши лимиты сайта.
- Production Redis делит счётчики между процессами; при его сбое вызовы блокируются.
- До 1500 символов вопроса; до 6 сообщений истории от клиента, из них не более
  3000 символов последних сообщений отправляется провайдеру. Максимум1600 выходных
  токенов, включая рассуждение. Внутреннее рассуждение не показывается пользователю.
- Сайт не хранит переписку, история только в памяти страницы. Groq получает вопрос,
  ограниченную историю и публичную справку `smweb/support_knowledge.json`.
  Нет отправки AGENTS.md/.env, приватных аккаунтов и файлов. `store:false` не
  отменяет политики данных провайдера; проверь Groq Data Controls.
- Бот не выполняет действия, не видит статусы личных оплат/задач. При изменении
  функций обновляй обе языковые версии справки.
- «ИИ ещё не подключён»: нет GROQ_API_KEY или контейнер не пересоздан.
- `available:true` в /api/support/info означает лишь наличие ключа.
- Ответ недоступен: проверь действительность Groq-ключа, модель, квоту, Redis и
  исходящий HTTPS к api.groq.com. Сайт не раскрывает сырые ошибки провайдера.
- HTTP403: проверь Origin/APP_URL; HTTP429: лимит сайта либо Groq.
- Чтобы выключить ИИ: очисти GROQ_API_KEY и пересоздай app. FAQ останется.

## Проверки разработки

```powershell
py -m unittest discover -s tests -p "test_*.py"
node --check static/js/support-chat.js
node scripts/check_i18n.js
git diff --check
```

Живой Groq-запрос без пользовательского ключа не выполнялся; транспорт, ошибки,
неразглашение рассуждений и отсутствие платного fallback проверяются mock-тестами.
