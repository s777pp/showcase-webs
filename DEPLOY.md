# SteamShowcase — Production Deploy

Target: ~15–20 concurrent users on a single VPS (e.g. Hetzner CX33, 4 vCPU / 8 GB).

## Architecture

```text
Internet → Cloudflare → Nginx → FastAPI (2 workers)
                              → Redis ← Worker (FFmpeg/gifski)
                              → PostgreSQL (optional)
                              → /data volume
```

## 1. Server prep

```bash
# Ubuntu 22.04/24.04
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git curl
sudo usermod -aG docker $USER   # re-login
```

Firewall: allow 22, 80, 443 only.

## 2. Clone & configure

```bash
git clone https://github.com/s777pp/showcase-webs.git
cd showcase-webs
cp .env.example .env
nano .env   # set SECRET_KEY, OAuth, APP_URL, passwords
```

## 3. Start stack

```bash
docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1/api/health
```

Expect: `{"ok":true,"db":true,"redis":true,...}`

## 4. SQLite → PostgreSQL (optional but recommended)

1. Backup:

```bash
docker compose exec app python -c "print('ok')"
# copy volume DB
docker compose cp app:/data/users.db ./users_backup.db
```

2. Schema is auto-applied on first Postgres start via `sql/schema_pg.sql`.

3. Migrate:

```bash
docker compose run --rm -e DATABASE_URL=postgresql://showcase:PASSWORD@postgres:5432/showcase \
  -e SQLITE_PATH=/data/users.db app \
  python scripts/migrate_sqlite_to_pg.py
```

4. Set `DATABASE_URL` in `.env` and restart **only after** auth_db supports PG fully.  
   **Current default:** app still uses SQLite on `/data/users.db` for zero-risk cutover.  
   Postgres is provisioned so you can migrate when ready.

## 5. Cloudflare

- DNS A/AAAA → VPS  
- SSL Full (strict) once origin has cert, or Flexible during setup  
- Cache rules: cache `/static/*`, **bypass** `/api/*`  
- Bot fight / rate limiting at edge optional  

## 6. TLS (recommended)

Put Caddy or certbot in front, or Cloudflare origin cert. Nginx in this compose listens on :80; terminate TLS at Cloudflare or add a cert service.

## 7. Updates

```bash
git pull
docker compose build app worker
docker compose up -d app worker
```

## 8. Logs

```bash
docker compose logs -f app worker nginx
```

## 9. Rollback

```bash
docker compose down
# restore users_backup.db into volume
docker compose up -d
```

## 10. Load check (after deploy)

```bash
# install k6 or use ab
ab -n 200 -c 20 http://127.0.0.1/api/health
```

Heavy GIF jobs should not block `/api/health` or gallery when worker is separate.

## Environment reference

See `.env.example`.
