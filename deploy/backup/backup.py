"""Nightly PostgreSQL backup to the private R2 bucket.

Runs in its own small container (deploy/backup) built on postgres:16-alpine,
so pg_dump always matches the server version.  Every day at BACKUP_HOUR
(UTC) it writes ``pg_dump -Fc`` to ``backups/db/<timestamp>.dump`` in the
private bucket and keeps the newest BACKUP_KEEP dumps.

    python3 backup.py          # scheduler loop (container default)
    python3 backup.py --once   # one backup now, e.g. to test the setup
"""
import datetime as dt
import os
import subprocess
import sys
import tempfile
import time

import boto3

PREFIX = "backups/db/"
KEEP = int(os.environ.get("BACKUP_KEEP") or 14)
HOUR = int(os.environ.get("BACKUP_HOUR") or 3)


def _client():
    endpoint = (os.environ.get("R2_ENDPOINT") or "").strip() or \
        f"https://{os.environ['R2_ACCOUNT_ID'].strip()}.r2.cloudflarestorage.com"
    return boto3.client("s3", endpoint_url=endpoint, region_name=(os.environ.get("R2_REGION") or "auto"),
                        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"].strip(),
                        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"].strip())


def backup_once() -> str:
    bucket = (os.environ.get("R2_PRIVATE_BUCKET") or "showcasemaker-private").strip()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    env = dict(os.environ, PGPASSWORD=os.environ["POSTGRES_PASSWORD"])
    with tempfile.NamedTemporaryFile(suffix=".dump") as tmp:
        subprocess.run(["pg_dump", "-h", os.environ.get("POSTGRES_HOST", "postgres"),
                        "-U", os.environ["POSTGRES_USER"], "-d", os.environ["POSTGRES_DB"],
                        "-Fc", "-Z", "6", "-f", tmp.name], check=True, env=env)
        size = os.path.getsize(tmp.name)
        if size < 1024:
            raise RuntimeError(f"dump is suspiciously small ({size} bytes)")
        key = f"{PREFIX}{stamp}.dump"
        client = _client()
        client.upload_file(tmp.name, bucket, key)
    listing = client.list_objects_v2(Bucket=bucket, Prefix=PREFIX).get("Contents") or []
    old = sorted(listing, key=lambda o: o["Key"])[:-KEEP] if len(listing) > KEEP else []
    for obj in old:
        client.delete_object(Bucket=bucket, Key=obj["Key"])
    print(f"[backup] {key} {size / 1048576:.1f} MB uploaded, {len(listing) - len(old)} kept", flush=True)
    return key


def _seconds_until_next_run() -> float:
    now = dt.datetime.now(dt.timezone.utc)
    run = now.replace(hour=HOUR, minute=30, second=0, microsecond=0)
    if run <= now:
        run += dt.timedelta(days=1)
    return (run - now).total_seconds()


def main():
    if "--once" in sys.argv:
        backup_once()
        return
    print(f"[backup] scheduler started: daily at {HOUR:02d}:30 UTC, keeping {KEEP} dumps", flush=True)
    while True:
        time.sleep(_seconds_until_next_run())
        for attempt in range(3):
            try:
                backup_once()
                break
            except Exception as exc:  # retry, then wait for tomorrow
                print(f"[backup] attempt {attempt + 1} failed: {type(exc).__name__}: {exc}", flush=True)
                time.sleep(300)


if __name__ == "__main__":
    main()
