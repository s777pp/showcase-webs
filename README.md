# Showcase Maker (SteamShowcase Maker Web)

Web app for preparing Steam profile showcases (Workshop, Featured, Artwork Split):
image/GIF/video processing, GPU upscaling, layered Builder, Steam profile import,
gallery, Pro access. Production: https://showcasemaker.com (8 UI languages).

**Coding agents: read [`AGENTS.md`](AGENTS.md) first.** It holds the architecture,
rules, current state and next steps.

## Stack

FastAPI + Uvicorn, PostgreSQL (SQLite for local dev), Redis, external worker
(FFmpeg / gifski / Pillow), Cloudflare R2, Modal GPU, static HTML/JS/CSS (no bundler).
Deployed with Docker Compose behind nginx and a Cloudflare Tunnel.

## Local development (Windows or Linux)

```powershell
py -3.14 -m pip install -r requirements-dev.txt
copy .env.example .env        # fill only what you need; SECRET_KEY must be >= 32 chars
py -3.14 main.py              # http://127.0.0.1:8080
```

Without `DATABASE_URL` / `REDIS_URL` the app uses SQLite under `./data` and
in-process job state, so a single process is enough. FFmpeg and gifski must be on
`PATH` for media processing.

## Checks

```powershell
py -3.14 -m pytest tests -q          # full suite (~35 s, 245 tests on 2026-09-25)
node scripts/check_i18n.js           # RU/EN/6-language dictionary completeness
```

Run the tests with a throw-away `DATA_DIR` and without `DATABASE_URL`/`REDIS_URL`
so nothing production-like is touched.

## Deployment

See [`DEPLOY.md`](DEPLOY.md). Threat model: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).
