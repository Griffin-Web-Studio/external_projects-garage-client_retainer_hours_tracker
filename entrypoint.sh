#!/bin/sh
set -e

python manage.py migrate --noinput

# SQLite serializes writes across processes, so keep worker count modest by
# default - override via WEB_CONCURRENCY if you know your traffic pattern.
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-30}" \
    --access-logfile - \
    --error-logfile -
