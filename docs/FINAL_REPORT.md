# Production optimization — report

## Architecture before

- Single Uvicorn process on Railway
- SQLite (`users.db`) with per-call connections
- FFmpeg/gifski/Pillow often in API process
- In-memory `_sessions`, `_usage`, `_process_jobs`
- Static + media via FastAPI
- No Redis, no dedicated worker, no Nginx in stack

## Problems found

See `docs/ARCHITECTURE_AUDIT.md` (P0–P3).

## Changes made

| Area | Change |
|------|--------|
| Queue | `redis_store.py` — jobs, quota, rate limit, access sessions |
| Worker | `worker.py` — up to `MAX_JOB_WORKERS` concurrent heavy jobs |
| API | Enqueue to Redis when `USE_EXTERNAL_WORKER=1`; per-user job cap |
| Middleware | Request ID + rate limits on auth/process/gallery/download-url |
| Health | `/api/health` (db/redis), `/api/ready` |
| Docker | Multi-service: nginx, app, worker, redis, postgres |
| Nginx | Proxy, `client_max_body_size 50m`, static cache headers, security headers |
| Postgres | `sql/schema_pg.sql` + `scripts/migrate_sqlite_to_pg.py` |
| Docs | `DEPLOY.md`, `.env.example`, README |

## Database

- **Runtime default:** still SQLite on `DATA_DIR/users.db` (safe for existing Railway).
- **Provisioned:** PostgreSQL in compose with full schema.
- **Migration script:** offline SQLite → PG; switch `DATABASE_URL` only after validating counts.
- **Not done in this pass:** full rewrite of `auth_db.py` queries to Postgres drivers (requires dual-dialect or SQLAlchemy follow-up).

## Worker

- Redis list queue `sm:jobs:queue`
- App writes uploads under `/data/jobs/{id}` and enqueues
- Worker runs same pipeline as `_run_process_job`
- Fallback: in-process thread if Redis down / `USE_EXTERNAL_WORKER=0`

## Storage

- Still local volume `/data` for gallery and results
- Object storage (R2/S3) **not** wired yet — next phase
- Nginx serves `/static` from bind mount

## Security

- Rate limits on login/register/process
- Security headers via Nginx
- Secrets via `.env` only
- Non-root user in Dockerfile

## Performance

- API workers configurable (`UVICORN_WORKERS=2`)
- Heavy work isolated when Redis+worker up
- Gallery still app-served originals (thumb pipeline next)

## Tests

| Check | Result |
|-------|--------|
| `ast.parse(main.py)` | OK |
| Live 20-user load test | **Not verified** (needs VPS) |
| SQLite→PG migration on prod data | **Not verified** |
| Telegram/Discord OAuth on new domain | **Not verified** |

## Deployment

Follow `DEPLOY.md` on Hetzner (or any Docker VPS), put Cloudflare in front.

## Remaining risks

1. `auth_db` still SQLite-first until PG driver work lands  
2. No object storage — large GIF traffic still hits VPS  
3. Worker imports `main` (heavy); extract pure processor entry later  
4. Gallery full-image responses without mandatory thumbs  
5. localStorage session token XSS surface remains  

## Honesty

This deliverable is a **production foundation** that matches the ROLE order (queue, workers, nginx, redis, postgres provisioned, rate limits, health). It is **not** a claim that every ROLE checkbox is fully verified under real 20-user load.
