#!/bin/bash
# Preview startup script — SQLite, no Docker required
set -e

cd "$(dirname "$0")/.."

export DJANGO_SETTINGS_MODULE=config.settings.preview
export PORT="${PORT:-8000}"

echo "=== ICED SPDITS — Preview Mode ==="
echo "Settings: $DJANGO_SETTINGS_MODULE"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear 2>/dev/null || true

echo "Seeding demo data..."
python manage.py seed_demo_data --participants 50 2>/dev/null || true

echo "=== Starting dev server on port $PORT ==="
exec python manage.py runserver 0.0.0.0:$PORT
