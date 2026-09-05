#!/usr/bin/env bash
# API container entrypoint: wait for Postgres, run migrations, then start uvicorn.
set -euo pipefail

echo "[entrypoint] waiting for postgres at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
until python -c "
import os, socket
s = socket.socket()
s.settimeout(2)
s.connect((os.environ.get('POSTGRES_HOST', 'postgres'), int(os.environ.get('POSTGRES_PORT', '5432'))))
s.close()
" 2>/dev/null; do
  sleep 1
done

echo "[entrypoint] running alembic migrations..."
alembic upgrade head

echo "[entrypoint] starting: $*"
exec "$@"
