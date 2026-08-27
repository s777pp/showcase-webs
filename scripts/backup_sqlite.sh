#!/bin/sh
# Backup SQLite before migration
set -e
SRC="${SQLITE_PATH:-/data/users.db}"
DEST="${1:-./backup_users_$(date +%Y%m%d_%H%M%S).db}"
cp -a "$SRC" "$DEST"
echo "Backup written to $DEST"
ls -la "$DEST"
