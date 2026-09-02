# ShowcaseMaker production deployment

Production runs on the OVH Ubuntu VPS with Docker Compose. Cloudflare Tunnel is
the only public ingress, PostgreSQL is the source of truth, Redis backs queues,
and R2 stores persistent media. `/data` remains a working/cache volume.

## First deployment

```bash
cd /opt/showcasemaker
git pull --ff-only
cp -n .env.example .env
nano .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose exec -T app curl -fsS http://127.0.0.1:8080/api/health
```

The production `.env` must contain `APP_URL`, `DATABASE_URL`, all three R2
credentials, both bucket names, `R2_PUBLIC_BASE_URL`, the Tunnel token,
`SECRET_KEY`, OAuth secrets and `TRUSTED_PROXY_HOPS=2`.

## Upgrading an existing install: required `.env` edits

`HTTP_PORT` used to carry the bind address (`HTTP_PORT=127.0.0.1:8080`). The
publish spec is now `${HTTP_BIND}:${HTTP_PORT}:80`, so that old value expands to
an invalid spec and `docker compose up` refuses to start. Split it in two:

```bash
sed -i 's/^HTTP_PORT=.*/HTTP_PORT=8080/' .env
grep -q '^HTTP_BIND=' .env || echo 'HTTP_BIND=127.0.0.1' >> .env
docker compose config --quiet   # must print nothing
```

`GALLERY_ADMIN_EMAILS` no longer has a built-in fallback address, so gallery
moderation is disabled until it is set. The app logs a warning at startup when
it is empty.

## One-time Railway/SQLite migration

Copy `railway-backup` to `/opt/showcasemaker/railway-backup` on the VPS, then:

```bash
cd /opt/showcasemaker
docker compose run --rm -v "$PWD/railway-backup:/import:ro" app \
  python scripts/migrate_sqlite_to_postgres.py /import/users_backup.db
docker compose run --rm -v "$PWD/railway-backup:/import:ro" app \
  python scripts/migrate_sqlite_to_postgres.py /import/users_backup.db --apply
docker compose run --rm -v "$PWD/railway-backup:/import:ro" app \
  python scripts/migrate_media_to_r2.py /import
docker compose run --rm -v "$PWD/railway-backup:/import:ro" app \
  python scripts/migrate_media_to_r2.py /import --apply
```

The first command in each pair is a dry run. Do not run the `--apply` command
unless its counts and paths are correct.

Activation codes are private production data. Copy the old list into the app
volume instead of committing it:

```bash
docker compose cp data/access_codes.json app:/data/access_codes.json
docker compose restart app
```

After the migration, verify the backend and object store:

```bash
docker compose exec -T app curl -fsS http://127.0.0.1:8080/api/health | python -m json.tool
docker compose logs --tail=100 app worker cloudflared
```

Expected values: `database_backend=postgresql`, `r2.ok=true`, `redis=true`,
`worker.external_alive=true`, `ffmpeg=true`, `gifski=true`.

Then confirm the proxy chain resolves to the real visitor address, because the
rate limiter and the daily quota are both keyed on it:

```bash
curl -fsS -H "X-Admin-Secret: $ADMIN_SECRET" https://showcasemaker.com/api/admin/whoami
```

`resolved_ip` must equal `cf_connecting_ip`. If it does not, set
`TRUSTED_PROXY_HOPS` to `xff_entries` minus the index of the real client counted
from the right, and restart `app`.

## Updates

```bash
cd /opt/showcasemaker
git pull --ff-only
docker compose build --pull app worker
docker compose up -d
docker compose ps
python scripts/smoke_test.py https://showcasemaker.com
```

## Rollback

Before an update, record the current commit with `git rev-parse HEAD` and create
a PostgreSQL dump plus an R2 backup/versioning policy. Rolling application code
back must never delete the PostgreSQL or R2 data.
