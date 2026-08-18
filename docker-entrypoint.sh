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

  # Best-effort: only if a license key is configured and the volume doesn't
  # already have it (see docker-compose.prod.yml's advergo_geoip_prod mount --
  # without a persistent volume this would re-download ~66MB on every deploy
  # instead of once). Never blocks startup -- login-history location is a
  # nice-to-have display field, not worth failing the whole app over if
  # MaxMind is unreachable or the key is bad.
  if [ -n "$MAXMIND_LICENSE_KEY" ] && [ ! -f /app/geoip/GeoLite2-City.mmdb ]; then
    echo "Downloading GeoLite2 database..."
    uv run python manage.py download_geoip_db || echo "GeoLite2 download failed, continuing without it."
  fi
fi

echo "Starting: $*"
exec "$@"
