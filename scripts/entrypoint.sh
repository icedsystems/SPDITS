#!/bin/bash
# Docker entrypoint script for the Django app
set -e

echo "=== ICED SPDITS — Starting (command: $1) ==="

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until python -c "import psycopg2; psycopg2.connect('${DATABASE_URL}')" 2>/dev/null; do
  sleep 1
done
echo "✓ PostgreSQL ready"

# Wait for Redis
echo "Waiting for Redis..."
until python -c "import redis; redis.from_url('${REDIS_URL}').ping()" 2>/dev/null; do
  sleep 1
done
echo "✓ Redis ready"

# Only the main app container (gunicorn) runs migrations and setup.
# Celery workers and beat skip this to avoid race conditions.
if [ "${1}" = "gunicorn" ]; then
  echo "Running database migrations..."
  python manage.py migrate --noinput

  echo "Collecting static files..."
  python manage.py collectstatic --noinput --clear

  echo "Ensuring superuser exists..."
  python manage.py ensure_superuser || true
fi

echo "=== Launching: $@ ==="
exec "$@"
