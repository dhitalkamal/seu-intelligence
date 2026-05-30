#!/bin/sh
set -e

# wait for the database to accept connections
until uv run python manage.py check --database default > /dev/null 2>&1; do
  echo "waiting for database..."
  sleep 2
done

uv run python manage.py migrate --noinput
exec uv run gunicorn config.wsgi:application --bind 0.0.0.0:8007 --workers 2
