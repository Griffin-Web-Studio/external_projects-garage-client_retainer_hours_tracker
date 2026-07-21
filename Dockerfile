# syntax=docker/dockerfile:1

# ───────────────────────────────────────────────────────| Static build stage |──
# Compiles Tailwind v4 (static/src/global.css -> static/build/css/final.css)
# and the TypeScript bundle (static/src/index.ts -> static/build/js/index.js
# via esbuild). static/build/ is gitignored, so this has to happen at
# image-build time - collectstatic below needs both to already exist, or it
# raises "Missing staticfiles manifest entry" at runtime for whichever one
# is missing.
FROM node:22-slim AS static-builder

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

# global.css's `@import "tailwindcss" source("../../")` and
# `@source "**/*.html"` mean Tailwind's JIT scanner needs to see the actual
# Django templates (project root, two levels up from static/src/global.css)
# to know which utility classes are used - copying only static/src left the
# scanner with nothing to scan, so it only emitted the base layer and the
# explicitly-inlined safelist classes, not what the templates actually use.
COPY static/src ./static/src
COPY tracker/templates ./tracker/templates
COPY esbuild.config.mjs tsconfig.json ./
RUN pnpm build

# ───────────────────────────────────────────────| Python dependencies stage |──
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

# Now the app itself, plus the compiled CSS/JS from the previous stage.
COPY . .
COPY --from=static-builder /app/static/build ./static/build
RUN uv sync --frozen --no-dev

# collectstatic needs Django settings to load, but not real secrets - these
# build-time-only values are never copied into the runtime stage and are
# unrelated to whatever SECRET_KEY/ALLOWED_HOSTS the container is actually
# run with later.
ENV SECRET_KEY=build-time-only-unused-at-runtime \
    DEBUG=False \
    ALLOWED_HOSTS=localhost
RUN /app/.venv/bin/python manage.py collectstatic --noinput

# ─────────────────────────────────────────────────────────────────| Runtime |──
FROM python:3.14-slim AS runtime

# WeasyPrint (PDF report generation) needs these system libraries, not
# part of the base image - only required here (not python-builder):
# tracker/pdf.py imports weasyprint lazily inside the render call, so
# nothing at build time (collectstatic, etc.) ever touches it.
#
# Fixed UID/GID (not auto-assigned) so docker-compose.yml's init-permissions
# service - a minimal image, not this one, so it doesn't have `app` defined
# by name - can `chown 1000:1000` bind-mounted config to match.
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends -qq \
       libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --home /app app

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=python-builder --chown=app:app /app/.venv /app/.venv
COPY --from=python-builder --chown=app:app /app/staticfiles /app/staticfiles
COPY --chown=app:app . .

# /app itself needs to be writable by `app`, not just the files in it:
# .env is never bind-mounted (only injected via compose's env_file: as real
# env vars), so AppEnv.initialise() always tries to auto-copy .env.example
# -> .env on startup - WORKDIR created /app as root, and --chown above only
# covers the files COPY brought in, not the pre-existing directory itself.
#
# /app/data holds the SQLite file (see core/app_settings.py DB_DIR) - the
# only thing that needs to persist across container recreation. Bind a
# volume here in production.
RUN chown app:app /app && mkdir -p /app/data && chown app:app /app/data

COPY --chown=app:app entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/login/', timeout=3).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
