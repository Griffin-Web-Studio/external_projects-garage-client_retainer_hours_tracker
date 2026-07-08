# syntax=docker/dockerfile:1

# ───────────────────────────────────────────────────────────| CSS build stage |──
# Compiles Tailwind v4 (static/src/global.css -> static/build/css/final.css).
# static/build/ is gitignored, so this has to happen at image-build time.
FROM node:22-slim AS css-builder

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY static/src ./static/src
RUN pnpm css:build

# ───────────────────────────────────────────────────| Python dependencies stage |──
FROM python:3.14-slim AS python-builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

# Install dependencies first (better layer caching - only re-runs when
# pyproject.toml/uv.lock actually change).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Now the app itself, plus the compiled CSS from the previous stage.
COPY . .
COPY --from=css-builder /app/static/build ./static/build
RUN uv sync --frozen --no-dev

# collectstatic needs Django settings to load, but not real secrets - these
# build-time-only values are never copied into the runtime stage and are
# unrelated to whatever SECRET_KEY/ALLOWED_HOSTS the container is actually
# run with later.
ENV SECRET_KEY=build-time-only-unused-at-runtime \
    DEBUG=False \
    ALLOWED_HOSTS=localhost
RUN /app/.venv/bin/python manage.py collectstatic --noinput

# ────────────────────────────────────────────────────────────────| Runtime |──
FROM python:3.14-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=python-builder --chown=app:app /app/.venv /app/.venv
COPY --from=python-builder --chown=app:app /app/staticfiles /app/staticfiles
COPY --chown=app:app . .

# /app/data holds the SQLite file (see core/app_settings.py DB_DIR) - the
# only thing that needs to persist across container recreation. Bind a
# volume here in production.
RUN mkdir -p /app/data && chown app:app /app/data

COPY --chown=app:app entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/login/', timeout=3).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
