#!/bin/sh
set -e

# Only the web (gunicorn) container runs migrate/collectstatic on startup --
# the worker shares this image/entrypoint but would otherwise race the web
# container to apply the same migrations on every restart.
if [ "$1" = "gunicorn" ]; then
  echo "Waiting for database..."
  until uv run python manage.py check --database default >/dev/null 2>&1; do
    sleep 1
  done

  echo "Running migrations..."
  uv run python manage.py migrate --noinput

  echo "Collecting static files..."
  uv run python manage.py collectstatic --noinput
fi

echo "Starting: $*"
exec "$@"
