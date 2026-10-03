#!/bin/sh
# Container entrypoint of the api service.
# Brings the tool database to the latest schema before the server starts, so a fresh
# `docker compose up` works without a manual migration step. A failing migration stops
# the container instead of starting an API on a half-migrated database.
# Set RUN_MIGRATIONS=false to skip (e.g. when migrations are run as a separate step).
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "entrypoint: alembic upgrade head"
    alembic upgrade head
else
    echo "entrypoint: RUN_MIGRATIONS=${RUN_MIGRATIONS}, skipping migrations"
fi

exec "$@"
