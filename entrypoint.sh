#!/bin/sh
set -e

# .env is never bind-mounted in any compose file - only injected as real env
# vars (env_file:/environment:) - so it never exists on disk in a container.
# Left alone, AppEnv.initialise() would auto-copy .env.example (placeholder
# values) instead, and only "work" because django-environ's read_env() skips
# keys already set in the environment. That's fragile and leaves a
# misleading file on disk (e.g. DEBUG=True even when actually running with
# DEBUG=False). Write the real thing from the actual environment instead, so
# AppEnv.initialise() never has to fall back at all.
cat > /app/.env <<EOF
SECRET_KEY=${SECRET_KEY:-your-secret-key-here}
DEBUG=${DEBUG:-False}
ALLOWED_HOSTS=${ALLOWED_HOSTS:-localhost,127.0.0.1}
STATIC_URL=${STATIC_URL:-static/}
DEFAULT_FROM_EMAIL=${DEFAULT_FROM_EMAIL:-local@localhost}
DB_NAME=${DB_NAME:-db.sqlite3}
DB_DIR=${DB_DIR:-}
EOF

python manage.py migrate --noinput

# SQLite serializes writes across processes, so keep worker count modest by
# default - override via WEB_CONCURRENCY if you know your traffic pattern.
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-30}" \
    --access-logfile - \
    --error-logfile -
