# Резервные копии базы

Контейнер `db-backup` каждый день в 03:30 UTC делает `pg_dump` базы и кладёт его
в приватный бакет R2: `backups/db/<дата-время>.dump`. Хранятся 14 последних копий.

Настройки (необязательно, в `.env`): `BACKUP_HOUR` (час UTC, по умолчанию 3),
`BACKUP_KEEP` (сколько копий хранить, по умолчанию 14).

## Проверить

```bash
cd /opt/showcasemaker
sudo docker compose logs --tail=5 db-backup              # "scheduler started" / "... uploaded"
sudo docker compose run --rm db-backup python3 /backup.py --once   # копия прямо сейчас
```

## Восстановить

1. Скачать нужный `.dump` из R2 (панель Cloudflare → R2 → приватный бакет → `backups/db/`)
   и положить на VPS, например в `/tmp/restore.dump`.
2. Остановить сайт, чтобы никто не писал в базу, и восстановить:

```bash
cd /opt/showcasemaker
sudo docker compose stop app worker
sudo docker compose cp /tmp/restore.dump postgres:/tmp/restore.dump
sudo docker compose exec postgres sh -c 'pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/restore.dump'
sudo docker compose start app worker
```

`--clean` заменяет текущие таблицы содержимым копии.
