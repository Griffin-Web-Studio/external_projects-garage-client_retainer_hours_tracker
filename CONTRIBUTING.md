# Contributing to RetainerTracker

This guide is for anyone working on the codebase itself. For product
features, configuration, and how to run the app, see
[README.md](README.md) first.

## Development environment

### Devcontainer (recommended)

Open the repo in the provided devcontainer - it installs `uv`, syncs Python
dependencies (including dev extras), installs `pnpm` packages, installs the
pre-commit hooks, and generates `.env` / `settings.ini` automatically via
`.devcontainer/post_create.sh`.

### Manual setup

```bash
pipx install uv
uv sync --all-extras          # installs the [dev] optional-dependencies group too
source .venv/bin/activate

corepack enable
pnpm install

./scripts/setup_settings.sh   # settings.ini, .env, pre-commit hooks, migrate
```

Then set `SECRET_KEY` in `.env` (see README) and run `pnpm build` at least
once before starting the server.

## Project structure

```
core/               Django project config: settings, urls, wsgi/asgi,
                     app_settings.py (settings.ini/.env loader), auth backends
tracker/             The one Django app. Models, views (one class per file
                     under tracker/views/), forms, business logic
                     (hours.py), OIDC backend, templates, template tags
database/
  factories/          factory_boy factories, used by seeders and (eventually) tests
  seeders/            CoreSeeder (required data) / DevSeeder (fake demo data),
                     orchestrated by Seeder
static/
  src/                Tailwind v4 source (global.css) - not served directly
  build/              compiled output (`pnpm build`) - gitignored
```

`tracker/views/__init__.py` re-exports every view class so
`tracker/urls.py` can do `views.SomeView.as_view()` without per-view import
lines.

## Coding conventions

- **Formatting**: [Black](https://black.readthedocs.io/), enforced by
  pre-commit. Line length 80 (see `[tool.black]` in `pyproject.toml`).
  Migrations are excluded from formatting.
- **Docstrings**: every class, function, and method gets a Google-style
  docstring - a one-line summary, then `Args:`/`Returns:` (or `Attributes:`
  for dataclasses/plain data containers), with real type-annotated
  descriptions. No exceptions for "obvious" one-liners or private helpers.
- **Python version**: this project targets Python 3.14+. Notably, Black will
  reformat parenthesized multi-exception `except` clauses into PEP 758's
  bare form - `except (TypeError, ValueError):` becomes
  `except TypeError, ValueError:`. This is _not_ the old Python 2
  `except Type, var:` binding syntax; it's real, intentional tuple-of-types
  matching on this toolchain. Don't "fix" it back to parentheses.
- **Imports**: the devcontainer ships the isort VS Code extension for
  stdlib/third-party/local grouping, but it's editor-assisted only - there's
  no isort pre-commit hook or CI check, so import order isn't gated.

## Database changes

```bash
python manage.py makemigrations tracker
python manage.py migrate
```

Review generated migrations before committing - squash or rename them if
the auto-generated name doesn't clearly describe the change.

Seeders live in `database/seeders/`. `CoreSeeder` must stay idempotent and
safe to run in any environment (it's what `manage.py seed` runs by default).
`DevSeeder` is fake-data-only and must keep its `DEBUG=False` guard.

## Frontend / CSS

Tailwind v4 source lives in `static/src/global.css`; compiled output goes to
`static/build/css/final.css` (gitignored, regenerated via `pnpm build`).
Brand colors and custom utilities (blob animation, dynamic-class safelist
for template-filter-generated classes) are defined there under `@theme` /
`@layer utilities`.

```bash
pnpm dev      # watch mode while developing templates
pnpm build    # one-off build, also required before collectstatic in prod
```

There's no JS bundler wired up yet (`ts:build`/`ts:watch` in `package.json`
are placeholders) - this is a server-rendered app with no client-side
framework.

## Testing

The working way to run tests today is Django's built-in runner:

```bash
python manage.py test
python manage.py test tracker.tests_some_module   # a single module
```

`pytest-django` and `pytest-cov` are listed as dev dependencies for future
use, but there's no `pytest.ini` / `DJANGO_SETTINGS_MODULE` wiring yet, so
`pytest` won't discover Django tests out of the box until that's set up -
stick to `manage.py test` in the meantime.

`tracker/tests.py` is currently a stub. When adding tests, prefer the
`factory_boy` factories in `database/factories/` over constructing model
instances by hand - they already encode sensible defaults (e.g.
`ClientTermFactory` defaults to an active term starting ~6 months ago).

## Pre-commit hooks

Installed automatically by `scripts/setup_settings.sh` (or manually via
`pre-commit install && pre-commit install --hook-type commit-msg`). They run:

- `check-yaml`, `end-of-file-fixer`, `trailing-whitespace`
- `black`
- `commitlint` - enforces the commit message convention below

## Commit messages

Commits must follow
[Conventional Commits](https://www.conventionalcommits.org/), enforced by
the `commitlint` pre-commit hook:

```
<type>(<scope>): <short summary>
```

`type` is one of `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`,
`perf`, `ci`, `build`. `scope` is typically a file or feature area. Examples
from this repo's history:

```
feat(tracker/hours): add retainer hours calculation engine
fix(tracker/templates): associate form labels with their controls
refactor(urls): add login required to dashboard
```

Prefer small, focused commits - one logical change per commit - over large
mixed-concern ones. It makes review and `git bisect` far easier.

## Submitting changes

This project is hosted on GitLab (`gitlab.griffin-studio.dev`). Push a
branch and open a merge request; `.gitlab-ci.yml` runs `test` and a
validate-only Docker `build` (Kaniko, `--no-push`) on every MR and push to
`main`. Nothing gets published from a regular push - see "Releasing" below
for that.

## Releasing (maintainers)

Versioning is handled by [Commitizen](https://commitizen-tools.github.io/commitizen/)
(`[tool.commitizen]` in `pyproject.toml`), driven entirely by the
Conventional Commits history since the last tag - nobody manually decides
the next version number.

```bash
cz bump --dry-run   # preview: computed version + generated changelog entry
cz bump             # bumps pyproject.toml's version, updates CHANGELOG.md,
                     # commits, and tags (tag_format = "v$version")
git push && git push --tags
```

Pushing the tag is what actually ships anything - `.gitlab-ci.yml`'s
`publish`/`release` stages only trigger on a `vX.Y.Z` tag: Kaniko builds and
pushes `:<tag>` + `:latest` to the Container Registry, then a GitLab Release
is created.

The bump level itself is Commitizen's built-in convention, not something
`pyproject.toml` configures: any `feat:` since the last tag → MINOR,
`fix:`/`perf:`/`refactor:` only → PATCH, a `BREAKING CHANGE:` footer (or
`!` after the type) → MAJOR. `docs:`/`chore:`/`style:`/`test:`/`ci:`/
`build:` commits don't trigger a bump on their own. `change_type_map` in
`pyproject.toml` is unrelated to bump level - it only relabels changelog
section headings (e.g. `fix` → "Bug Fixes").

On a repo with no tags yet at all, `cz bump` will interactively ask "Is
this the first tag created?" - answer yes, or pass `--yes` to skip the
prompt entirely (non-interactive, e.g. from a script).
