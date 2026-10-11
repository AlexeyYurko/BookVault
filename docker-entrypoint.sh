#!/bin/sh
set -e

# Running as root: fix ownership of the mounted volumes, then drop privileges
# and re-run this script as the unprivileged appuser.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /tmp/bookvault
    chown -R appuser:appuser /data /app/static/cover_images /tmp/bookvault \
        || echo "warning: could not chown volumes" >&2
    exec gosu appuser "$0" "$@"
fi

# Ensure the schema is up to date before serving traffic.
alembic upgrade head

# Allow overriding the command, e.g. `docker compose run bookvault bash`.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
