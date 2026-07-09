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
