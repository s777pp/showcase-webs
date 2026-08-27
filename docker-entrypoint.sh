#!/bin/sh
set -e

# Railway (and plain `docker run -v`) mount volumes owned by root:root. The image
# chowns /data at BUILD time, but the mount replaces that directory at RUNTIME, so
# a non-root process ends up unable to write to it. SQLite then fails every write
# with "attempt to write a readonly database" while SELECT still works — which is
# exactly the failure this entrypoint exists to prevent.
#
# So: start as root, fix ownership of the mounted volume, then drop privileges.

DATA_PATH="${DATA_DIR:-/data}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_PATH" 2>/dev/null || true
    if ! chown -R appuser:appuser "$DATA_PATH" 2>/dev/null; then
        echo "[entrypoint] WARNING: could not chown $DATA_PATH — writes may fail" >&2
    fi
    exec gosu appuser "$@"
fi

# Already unprivileged (e.g. platform forces a UID): run as-is and let the
# storage probe in /api/health report whether the volume is writable.
echo "[entrypoint] running as uid $(id -u), skipping volume chown" >&2
exec "$@"
