#!/bin/sh
# Wait for the database, apply migrations, load demo data on first start, then run the server.
set -e

python -m app.core.wait_db
alembic upgrade head

if [ "${DEMO_MODE:-true}" = "true" ]; then
  python -m app.seed --if-empty
fi

exec "$@"
