# SteamShowcase (showcase-webs)

Web tool for Steam profile showcases: Workshop / Featured / Split, GIF/video, gallery, profiles, Pro billing.

## Quick local (single process)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# system ffmpeg + optional gifski
export DATA_DIR=./data
uvicorn main:app --host 127.0.0.1 --port 8080
```

Open http://127.0.0.1:8080

## Production

See **[DEPLOY.md](DEPLOY.md)** for Docker Compose (Nginx + App + Worker + Redis + Postgres).

```bash
cp .env.example .env
docker compose up -d --build
```

## Architecture (production)

- **FastAPI** — HTTP API, auth, gallery, profile (2 Uvicorn workers)
- **Worker** — FFmpeg / gifski / Pillow jobs from Redis queue
- **Redis** — job queue, rate limits, quota
- **PostgreSQL** — provisioned; SQLite remains default until migration
- **Nginx** — reverse proxy, static, body size limits

## Health

`GET /api/health` → `{ ok, db, redis, version }`

## Docs

- `docs/ARCHITECTURE_AUDIT.md` — audit before optimization
- `DEPLOY.md` — VPS + Cloudflare deploy
- `TELEGRAM_SETUP.md` — Telegram Login Widget

## License

Private / as designated by repository owner.
