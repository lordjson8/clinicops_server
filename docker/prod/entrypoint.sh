#!/bin/bash
set -e

echo "[Entrypoint] Waiting for PostgreSQL to be ready..."
while ! nc -z ${POSTGRES_HOST:-db} ${POSTGRES_PORT:-5432}; do
    sleep 0.5
done
echo "[Entrypoint] PostgreSQL is ready."

echo "[Entrypoint] Waiting for Redis to be ready..."
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
    sleep 0.5
done
echo "[Entrypoint] Redis is ready."

# Only backend (gunicorn) runs migrations and collectstatic
if [ "$1" = "gunicorn" ]; then
    echo "[Entrypoint] Applying database migrations..."
    python manage.py migrate --noinput

    echo "[Entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput
fi

echo "[Entrypoint] Setup complete. Starting..."
exec "$@"