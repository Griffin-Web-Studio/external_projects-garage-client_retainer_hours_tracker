# RetainerTracker

Internal tool for tracking client retainer hours, time entries, and overage
billing.

Clients are put on a support retainer with a monthly hour allocation. Employees
log time against the client's current term; the app tracks usage in real
time, flags clients running low or over their allocation, and handles term
renewal (converting unused hours to development time, or migrating them
forward) and overage billing.

Looking to work on the codebase itself rather than just run the app? See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Stack

- **Django 6**: server-rendered templates, class-based views
- **SQLite**: single-file database, no server needed
- **mozilla-django-oidc**: OIDC + PKCE authentication (IdP)
- **Tailwind CSS v4** via `pnpm`: one package, no framework
- **Whitenoise**: static file serving in production
- **uv** - Python dependency management

## Quick start

### Using the devcontainer (recommended)

Opening this repo in the provided devcontainer (VS Code / any
`devcontainers`-compatible tool) runs the full bootstrap automatically:
installs `uv`, syncs Python dependencies, installs `pnpm` packages, installs
the pre-commit hooks, and generates `.env` / `settings.ini` from their
`.example` templates.

The devcontainer bootstrap already runs `manage.py migrate`, which - on
first run - also generates a random `SECRET_KEY` and writes it into `.env`
for you (see `core/utils/env.py`). Nothing to do there manually.

After the container finishes building:

```bash
# Build the CSS (one-time; use `pnpm dev` in a separate terminal while developing)
pnpm build

# Seed core data (an admin account)
python manage.py seed

# Run
python manage.py runserver
```

### Manual setup

```bash
# 1. Python environment
pipx install uv
uv sync --all-extras
source .venv/bin/activate

# 2. Secrets and business config (both gitignored except the .example files)
./scripts/setup_settings.sh
# Copies settings.example.ini -> settings.ini and .env.example -> .env,
# installs the pre-commit hooks, and runs migrations - which, on first run,
# also generates a random SECRET_KEY and writes it into .env for you.

# 3. CSS (requires Node + pnpm)
corepack enable          # ships with Node 16.9+
pnpm install
pnpm build                # compiles static/build/css/final.css

# During development, watch mode in a separate terminal:
pnpm dev

# 4. Seed core data (an admin account) - add --full for fake demo data
python manage.py seed

# 5. Run
python manage.py runserver
```

Default admin login (Django admin only): `admin@example.com` / `changeme123`

- see [Authentication](#authentication--IdP-oidc--pkce) below for why
  this is admin-only.

## Configuration

### `.env` - secrets and environment (gitignored, never committed)

| Variable             | Required | Description                                                                                                        |
| -------------------- | :------: | ------------------------------------------------------------------------------------------------------------------ |
| `SECRET_KEY`         |   yes    | Django secret key - auto-generated into `.env` on first run if still set to the placeholder `your-secret-key-here` |
| `DEBUG`              |          | `True` in dev, `False` in prod (default: `False`)                                                                  |
| `ALLOWED_HOSTS`      |          | Comma-separated hostnames (default: `localhost,127.0.0.1`)                                                         |
| `STATIC_URL`         |          | Static file URL prefix (default: `static/`)                                                                        |
| `DEFAULT_FROM_EMAIL` |          | From-address for outgoing email (default: `local@localhost`)                                                       |

`DB_NAME` also ships in `.env.example` but isn't currently read anywhere -
the SQLite filename is fixed. Don't rely on it.

### `settings.ini` - business logic (committed, open-source friendly)

```ini
[branding]
APP_NAME = RetainerTracker        # shown in UI and browser title

[hours]
TERM_MONTHS = 12                  # contract term length
DEV_CONVERSION_RATIO = 2.0        # 1 dev hour costs this many support hours
MAX_MIGRATE_HOURS = 6             # max support hours migratable without conversion
LOW_HOURS_THRESHOLD = 75          # % used at which "low" warning appears

[auth]
OIDC_ALLOWED_DOMAINS =            # comma-separated; blank = any authenticated user
```

All `[hours]` values feed directly into `tracker/hours.py` via the
`HoursConfig` dataclass (resolved through `core.app_settings.AppConfig`) - no
other files need touching if you change these.

## Authentication - IdP OIDC + PKCE

1. In IdP, create a **Web** application:
   - Authentication method: **PKCE** (no client secret needed for a public
     client)
   - Allowed redirect URI: `https://yourdomain.com/oidc/callback/`
     (exact match required - scheme, host, port, and trailing slash all
     matter; this is the single most common setup mistake)

   "Sign out" in this app only ends the local Django session - it does not
   currently perform an RP-initiated logout at IdP, so a post-logout
   redirect URI isn't needed yet. (`mozilla-django-oidc` does expose its own
   `/oidc/logout/` view that would use one, but nothing in the app links to
   it today.)

2. Fill in the `OIDC_*` variables under `[auth]` in `settings.ini`:

   ```ini
   [auth]
   OIDC_ALLOWED_DOMAINS = yourcompany.io, contractor.com
   OIDC_CLIENT_ID = <from IdP>
   OIDC_CLIENT_SECRET =              ; leave blank for a PKCE-only public client
   OIDC_ISSUER = https://your-org.IdP.cloud
   OIDC_LABEL = IdP Name              ; shown on the "Sign in with ..." button
   ```

   OIDC is enabled automatically as soon as `OIDC_ISSUER` is non-blank - no
   separate feature flag.

3. Restart - the login page will show the "Sign in with `{OIDC_LABEL}`"
   button.

Users are auto-provisioned on first login if their email domain is listed in
`OIDC_ALLOWED_DOMAINS` (blank = any authenticated domain is accepted, not
recommended for production). The provisioned account has no Django password
and can only authenticate via OIDC.

### Local fallback

Django admin (`/admin/`) uses standard username/password, but only
**superusers** can log in this way - see
`core/backends/SuperuserOnlyModelBackend.py`. Everyone else must use OIDC.
The seeded `admin@example.com` account is intended for initial setup only -
change its password immediately or restrict access to the admin URL at the
web server level.

## Business logic

### `tracker/hours.py` - pure calculation, no Django dependency

`HoursConfig` is a plain dataclass. You can exercise the hours logic without
a Django process, given an explicit config:

```python
from tracker.hours import HoursConfig, calculate_term_hours

cfg = HoursConfig(term_months=12, dev_conversion_ratio=2.0)
summary = calculate_term_hours(term, entries, config=cfg)
```

### Active term

- Client accrues `monthly_hours` support hours per calendar month (current
  partial month included).
- Migrated support hours from a previous term are an opening balance on top.
- Development hours (from a previous term's conversion) are a separate pool.

### Term renewal - two options

| Option              | What happens                                                   |
| ------------------- | -------------------------------------------------------------- |
| **Convert to dev**  | remaining support ÷ `dev_conversion_ratio` = development hours |
| **Migrate support** | up to `max_migrate_hours` carry forward; excess is forfeited   |

### Overage billing

Overages are computed in real time on the client detail page. Use the
"Record Billing" form to mark hours as invoiced. Unbilled = computed overage

- total billed.

## Seeding data

```bash
python manage.py seed              # core data only - creates the admin account
python manage.py seed --full       # + a fake dataset for development/demos
python manage.py seed --full --employees 5 --clients 10 --entries 50
```

The `--full` seeder refuses to run when `DEBUG=False` - it's dev/demo only.

## Production

```bash
pnpm build                          # minify CSS
python manage.py collectstatic      # gather static files
```

Run with gunicorn behind nginx. Whitenoise serves static files from Django
directly for simplicity, but nginx is recommended for any meaningful
traffic.

```
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
SECRET_KEY=<strong-random-key>
```
