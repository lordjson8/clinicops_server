#!/bin/bash

# ==============================================================================
# PRODUCTION ENTRYPOINT SCRIPT
#
# This script is executed when the production container starts.
# It prepares the environment by:
# 1. Waiting for the database and Redis to be available.
# 2. Running Django database migrations.
# 3. Collecting all static files to a shared volume for Nginx to serve.
# 4. Starting the Gunicorn web server (by executing the CMD).
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# --- 1. Wait for Services ---
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

# --- 2. Run Database Migrations ---
echo "[Entrypoint] Applying database migrations..."
python manage.py migrate --noinput

# --- 3. Collect Static Files ---
# This command collects all static files from the Django apps into the
# STATIC_ROOT directory, which is a volume shared with the Nginx container.
echo "[Entrypoint] Collecting static files..."
python manage.py collectstatic --noinput

echo "[Entrypoint] Setup complete. Starting the application server..."

# --- 4. Execute the Container's Main Command ---
# This will execute the CMD from the Dockerfile, which is "gunicorn...".
exec "$@"
