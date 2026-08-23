# Showcase Maker Web

Веб-сервис для создания Steam-витрин (Workshop, Featured, Artwork Split), watermark, GIF из видео и hex21-трюка для загрузки.

## Возможности

- Workshop (5 частей), Featured 630px, Artwork Split
- Watermark с превью, шрифтами и позицией
- Конвертация видео/GIF
- Аккаунты, Pro-ключи (FunPay / коды), лимиты
- Публичная галерея (с модерацией)
- Rate-limit, строгая валидация загрузок

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Опционально: системный ffmpeg
# apt install ffmpeg   или положите бинарники в bin/

python main.py
# → http://127.0.0.1:8080
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `HOST` | Хост | `127.0.0.1` |
| `PORT` | Порт | `8080` |
| `DATA_DIR` | Папка данных (БД, jobs, usage) | `./data` |
| `FREE_LIMIT` | Бесплатных файлов в день | `5` |
| `MAX_UPLOAD_MB` | Макс. размер файла | `40` |
| `ADMIN_SECRET` | Секрет для админ-эндпоинтов | — |
| `STRIPE_SECRET_KEY` | Stripe (опционально) | — |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook | — |
| `STRIPE_PRICE_ID` | Stripe price | — |
| `APP_URL` | Публичный URL | `http://HOST:PORT` |
| `DA_CLIENT_ID` / `DA_CLIENT_SECRET` / `DA_REDIRECT_URI` | Discord OAuth (опц.) | — |
| `ACCESS_CODES` | Коды через запятую | — |
| `PRO_PRICE_LABEL` | Текст Pro | `Pro · безлимит` |

Создайте `.env` или задайте в панели хостинга (Railway / Render).

## Структура

```
main.py              — точка входа, app + middleware
routers/
  auth.py            — регистрация, логин, профиль
  billing.py         — checkout / webhook / unlock
  process.py         — обработка файлов + preview watermark
  meta.py            — health, quota, socials, gallery
  gallery.py         — публичная галерея + модерация
models.py            — Pydantic-модели
auth_db.py           — SQLite пользователи + usage + sessions
processor.py         — логика нарезки / watermark / GIF
static/              — фронтенд
```

## Docker

```bash
docker build -t showcase-maker .
docker run -p 8080:8080 -e DATA_DIR=/data -v $(pwd)/data:/data showcase-maker
```

## Безопасность

- Валидация MIME + magic bytes
- Rate-limit (slowapi)
- Одноразовые Pro-коды, привязка к аккаунту
- Автоочистка временных job-папок

## Лицензия

Личный проект. Используйте на свой страх и риск.
