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

- **Railway** (single service) → **[RAILWAY.md](RAILWAY.md)**
- **VPS / Docker Compose** (Nginx + App + Worker + Redis + Postgres) → **[DEPLOY.md](DEPLOY.md)**

```bash
cp .env.example .env
docker compose up -d --build
```

## Job processing

Heavy work (FFmpeg / gifski / Pillow) runs in one of two modes, chosen by `WORKER_MODE`:

| Mode | Where jobs run | Use when |
|------|----------------|----------|
| `embedded` (default) | Bounded thread pool inside the API container (`MAX_JOB_WORKERS`) | Single-service platforms — Railway, one VPS container |
| `external` | Separate `python worker.py` draining the Redis queue | API and worker share a volume (docker compose) |

In `external` mode the API checks a worker heartbeat in Redis and silently falls back
to embedded processing if no worker is alive, so jobs never stall in the queue.

**Redis is optional.** Without `REDIS_URL` the job store, quota and rate limits fall
back to process memory; everything works, but state is lost on restart.

**Keep `UVICORN_WORKERS=1`** unless you run `external` mode with shared storage —
result ZIPs live on the disk of the process that produced them.

## Access codes

The master list is `data/access_codes.json`, committed and shipped in the image —
trial codes carry a `hours` field that a flat env var cannot express. Env vars
(`ADMIN_ACCESS_CODE`, `ACCESS_CODES`, `ACCESS_CODES_JSON`) add to it, and
`DATA_DIR/access_codes.json` on the volume overrides everything.

Anyone with repo or image access can read the codes — keep the repo private if
that matters.

```bash
python scripts/gen_access_codes.py 10 --label Pro
```

## Security notes

- **Behind a proxy set `TRUSTED_PROXY_HOPS`** to the number of proxies that
  append to `X-Forwarded-For` (1 on Railway, 1 with the compose Nginx, 2 with
  Cloudflare in front). Quota and rate limits read the header from the right
  using this count, so the client cannot forge its own address. Run uvicorn
  with `--proxy-headers` (the Dockerfile does).
- **`ADMIN_SECRET`** guards `/api/admin/*` and gallery moderation, compared in
  constant time. Unset means denied, never allowed.
- **Gallery uploads require login and land as `pending`.** Only a moderator
  (`ADMIN_SECRET` header or `GALLERY_ADMIN_EMAILS`) can approve them or list
  anything other than the approved feed.
- **Stripe webhooks need `STRIPE_WEBHOOK_SECRET`** — without it the endpoint
  answers 503 instead of trusting an unsigned event.
- **Avatars and profile backgrounds resolve inside `DATA_DIR` only**, and the
  client cannot set those columns; they are written by the server on upload.
- **`/api/download-url` rejects private, loopback and link-local addresses**
  so it cannot be used to reach the platform's internal network.
- Session cookies are `HttpOnly`; unhandled errors log in full and return only
  a request id.

## Architecture (production)

- **FastAPI** — HTTP API, auth, gallery, profile
- **Worker** — FFmpeg / gifski / Pillow jobs (embedded pool or separate process)
- **Redis** — optional: job state, rate limits, quota
- **PostgreSQL** — provisioned in compose; SQLite remains the runtime default
- **Nginx** — reverse proxy, static, body size limits (compose only)

## Health

`GET /api/health` → `{ ok, db, redis, redis_detail, worker, version }`

`redis_detail.error` carries the reason Redis is unavailable; `worker` reports the
mode, concurrency and queue depth.

## Docs

- `RAILWAY.md` — Railway setup + troubleshooting
- `docs/ARCHITECTURE_AUDIT.md` — audit before optimization
- `DEPLOY.md` — VPS + Cloudflare deploy
- `TELEGRAM_SETUP.md` — Telegram Login Widget

## License

Private / as designated by repository owner.
