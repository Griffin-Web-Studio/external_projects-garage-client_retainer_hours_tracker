## v0.1.0-alpha.14 (2026-07-22)

### Bug Fixes

- **admin**: register WorkOrder, WorkOrderItem, and TimerSegment

### Features

- **admin**: add auto-promote the first-ever user
- **admin**: add elevate_admin command

## v0.1.0-alpha.13 (2026-07-21)

### Bug Fixes

- **dockerfile**: build the TS bundle too,, before collectstatic

## v0.1.0-alpha.12 (2026-07-21)

### Bug Fixes

- **timers**: recompute isMine live instead of caching it at page load

### Features

- **timers**: add browser notifications and fix silent audio dings
- **timers**: add browser notifications and fix silent audio dings
- **work-orders**: add company-wide Work Orders list + sidebar nav link
- **work-orders**: add Work Orders link to the retainer detail page
- **timers**: add live timer UI (timer controls, dings, cap prompts)
- **static/ts**: add typescript support
- **timers**: add start/stop/confirm-overage/status JSON endpoints
- **work-orders**: add Work Order CRUD (list/create/detail/edit/delete)
- **timers**: add work order item timer business logic
- **models**: add WorkOrder, WorkOrderItem, and TimerSegment models
- **hours**: add configurable timer thresholds to settings.ini

## v0.1.0-alpha.11 (2026-07-15)

### Bug Fixes

- **terms**: retroactively correct existing ClientTerm boundary drift
- **terms**: correct end_date off-by-one causing renewal drift

## v0.1.0-alpha.10 (2026-07-13)

### Features

- **nav**: add Company Profile link for admins

## v0.1.0-alpha.9 (2026-07-13)

### Bug Fixes

- **reports**: install WeasyPrint system libs, lazy-import weasyprint
- **reports**: seed a default report template

### Features

- **reports**: add report generation views and UI
- **reports**: add OverageReport model
- **reports**: add term report rendering context builder
- **reports**: add pluggable PDF renderer backend
- **reports**: add ReportTemplate model and sandboxed Jinja2 engine
- **clients**: add billing address fields
- **reports**: add CompanyProfile singleton model

## v0.1.0-alpha.8 (2026-07-13)

### Bug Fixes

- **hours**: surface leftover historical billing credit in buffer stat
- **hours**: base overage badge/stats on net unbilled overage

### Features

- **tracker**: resolve leftover purchased hours at term renewal
- **tracker**: surface purchased buffer hours on stat cards
- **tracker**: add "Purchase Extra Hours" action for buffer support hours
- **hours**: factor purchased buffer hours into term allocation
- **tracker**: add HoursPurchase model for prepaid overage buffer hours

## v0.1.0-alpha.7 (2026-07-13)

### Features

- **hours**: make log entry and overage billing minimums configurable

## v0.1.0-alpha.6 (2026-07-12)

### Features

- **templates/dashboard/base**: add sidebar logo
- **static/images/ico**: include static images and meta ico
- **static/images/ico**: add ico generator from svg
- **static/images**: add icons
- **tracker**: support multiple retainers per client

### Refactoring

- **static/images**: update icons

## v0.1.0-alpha.5 (2026-07-12)

### Bug Fixes

- **tracker**: reject future dates when logging time
- **tracker**: attribute time entries to the term matching their date

## v0.1.0-alpha.4 (2026-07-12)

### Bug Fixes

- **static**: guard STATICFILES_DIRS behind static/build existing

### Refactoring

- split hours field into hours and minutes
- **docker:compose:coolify**: correct template bug

## v0.1.0-alpha.3 (2026-07-10)

### Features

- **docker:compose:coolify**: add coolify template

### Refactoring

- **docker:entrypoint**: add env file generation

## v0.1.0-alpha.2 (2026-07-09)

### Bug Fixes

- **dockerfile**: pin app user to a fixed uid/gid

### Features

- **docker:local**: create docker for local tests

### Refactoring

- **docker**: use image instead of building local

## v0.1.0-alpha.1 (2026-07-09)

This is just a CI fix release.

## v0.1.0-alpha.0 (2026-07-09)

### Bug Fixes

- **dockerfile**: fix runtime permissions and missing Tailwind content
- **core/settings**: scope STATICFILES_DIRS to static/build only
- **core/app_settings**: wire up DB_NAME and add DB_DIR
- **tracker/templates**: associate form labels with their controls
- **styles**: import fonts
- **styles**: correct tw relative source
- ensure config parser ignores inline comments
- config file generation from example

### Features

- add docker-compose with nginx reverse proxy for deployment
- add Dockerfile for containerised deployment
- **tracker**: wire up dynamic sidebar nav links
- **tracker**: populate dashboard with client summaries
- **tracker**: add overage billing view
- **tracker**: add term renewal view
- **tracker**: add time-entry deletion view
- **tracker**: add client detail view
- **tracker**: add time-entry logging view
- **tracker**: add client delete view
- **tracker**: add client edit view
- **tracker**: add client creation view
- **tracker**: add client, time-entry, term, and billing forms
- **tracker**: add OIDC authentication backend
- **tracker/templatetags**: add hours_tags template filters
- **tracker/hours**: add retainer hours calculation engine
- **features/nav_link**: register nav links
- **urls**: add dashboard view
- **views**: add dashboard shell
- **templates**: prep for dashboard
- add attributions page
- **styles**: add utility for animated blob
- add login page
- **styles**: add brand colours
- **commands**: add seeder command
- **seeder**: add orchestrator
- **seeder**: add dev
- **seeder**: add core
- **factories**: add Employee
- **factories**: add Client
- **models**: add Overage Billing
- **models**: add Time Entry
- **models**: add Client Term
- **models**: add client
- **backend**: add custom superuser backend for basic auth
- **models**: add Employee (user) Model
- add base tailwind styles
- implement the tracker app
- add back logging system
- implement development email handling
- implement auth system and auth redirects
- update default DB config
- allow template processor debugging in dev
- integrate 3rd party apps and middleware
- implement white nose package to allow static file serving
- implement app settings ini config reader
- load some environment variables from .env using environ

### Refactoring

- **urls**: add login required to dashboard
- **templates/attributions**: update styles
- **templates/dashboard/base**: update styles
- **templates/dashboard/base**: add base dashboard layout and style
- **app**: set default auto field to BigAutoField
- move env processing logic into a separate AppEnv class
- load OIDC configs from ini file and remove env param
- populate secure secret to exclude hash and load file directly
- add package init files
- update url patterns in core and tracker app
- set default language code
