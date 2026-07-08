# Deploying RetainerTracker

Docker Compose deployment guide: `Dockerfile` (3-stage build), `docker-compose.yml`
(app + nginx reverse proxy), `nginx.conf`. See [README.md](../README.md) for
everything else (features, business logic, OIDC setup).

> **Not yet build-verified.** These files were written and reviewed
> carefully, but never actually run through `docker build`/`docker compose up`
> in a real Docker environment. Treat the first deploy as a dry run - watch
> the logs, don't point it at anything you can't afford to have go wrong.

## Prerequisites

- Docker and Docker Compose (`docker compose`, the plugin form - not the
  standalone `docker-compose` v1 binary).
- A real `.env` and `settings.ini` at the project root (see below) -
  neither is baked into the image; both are supplied at deploy time.

## Configuration split

Two different files, two different mechanisms, matching the two config
sources described in the main README:

| File           | Format      | How it reaches the container                                                                                    | Contains                                                                                                                     |
| -------------- | ----------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `.env`         | `KEY=VALUE` | `env_file:` in `docker-compose.yml` - injected as real environment variables, no file copied into the container | Secrets + deployment config: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_NAME`, `DB_DIR`, `STATIC_URL`, `DEFAULT_FROM_EMAIL` |
| `settings.ini` | INI         | Bind-mounted read-only at `/app/settings.ini`                                                                   | Business config: branding, hours, OIDC                                                                                       |

`.env` isn't INI-shaped, so `settings.ini` can't go through `env_file:` -
that's the only reason it's a bind mount instead.

Create both from their `.example` templates before first run:

```bash
cp .env.example .env
cp settings.example.ini settings.ini
```

Then edit `.env` at minimum:

```bash
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(50))">
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
```

Leave `DB_NAME`/`DB_DIR` alone - `docker-compose.yml` already sets
`DB_DIR=/app/data` to match the `app-data` volume. Don't override it unless
you've also changed the volume mount.

Edit `settings.ini`'s `[auth]` section for OIDC per the README's
[Authentication](../README.md#authentication---idp-oidc--pkce) section -
same steps, just editing the file directly instead of through the app's
auto-copy-on-first-run behavior.

## Build and run

```bash
docker compose build
docker compose up -d
docker compose logs -f web    # entrypoint.sh runs migrations, then gunicorn
```

The app is reachable through nginx on port 80. `web` itself isn't published
to the host at all - only nginx is - so nginx is the sole ingress point.

Create the initial admin account (same seeder as local dev):

```bash
docker compose exec web python manage.py seed
```

## TLS

`nginx.conf` as shipped is plain HTTP. It doesn't provision certificates
itself - pick one:

- Put this whole stack behind an external load balancer/ingress that
  terminates TLS and forwards plain HTTP to nginx's port 80. This is what
  `core/settings.py`'s `SECURE_PROXY_SSL_HEADER`/`USE_X_FORWARDED_HOST`
  are already set up to trust (see the comment there) - just make sure
  whatever's in front of nginx sets `X-Forwarded-Proto` correctly.
- Add a certbot sidecar/cron and extend `nginx.conf` with a `listen 443 ssl`
  block yourself - not included here since certificate provisioning is
  environment-specific (DNS provider, ACME challenge type, renewal
  scheduling).

Either way, OIDC's `redirect_uri` must be `https://` in production - see the
README's OIDC setup section. If you get Zitadel's
`redirect_uri missing in client configuration` error, check that the
Redirect URI registered in Zitadel exactly matches (scheme, host, trailing
slash) what the app is actually configured to serve behind - this bit us
once already in local dev.

## Backing up the database

SQLite is a single file in the `app-data` volume, at `/app/data/db.sqlite3`
inside the container. Use SQLite's own online backup, not a raw file copy,
so you don't grab it mid-write:

```bash
docker compose exec web sqlite3 /app/data/db.sqlite3 \
  ".backup '/app/data/backup-$(date +%Y%m%d).db'"
docker compose cp web:/app/data/backup-$(date +%Y%m%d).db ./
```

## Updating

```bash
git pull
docker compose build
docker compose up -d    # entrypoint.sh re-runs migrations on start
```

## Tuning

`entrypoint.sh` reads two optional env vars (set via `.env` or
`docker-compose.yml`'s `environment:`):

| Variable           | Default | Notes                                                                                                                                          |
| ------------------ | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `WEB_CONCURRENCY`  | `2`     | Gunicorn worker count. Kept modest by default - SQLite serializes writes across processes, so more workers doesn't mean more write throughput. |
| `GUNICORN_TIMEOUT` | `30`    | Worker timeout in seconds.                                                                                                                     |
