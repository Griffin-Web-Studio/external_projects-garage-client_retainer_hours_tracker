"""Jinja2 sandboxed rendering engine for overage report templates.

Report templates are stored in the database (`ReportTemplate.content`)
and editable via the admin, so they're rendered inside a Jinja2
`SandboxedEnvironment` rather than Django's own template language -
the sandbox blocks access to unsafe attributes/methods (e.g. reaching
`__class__`/`__globals__` to escape into arbitrary Python), so a
template can't be used to run code beyond what the rendering context
exposes.
"""

from django.utils import timezone
from jinja2.sandbox import SandboxedEnvironment

from tracker.hours import (
    calculate_term_hours,
    fmt_hm,
    get_hours_config,
    hm_to_minutes,
)
from tracker.models import ClientTerm, CompanyProfile


def _hm(hours, minutes) -> str:
    """Formats an hours/minutes field pair for Jinja2 templates.

    Args:
        hours: Whole hours.
        minutes: Minutes (0-59).

    Returns:
        str: `hours`/`minutes` formatted as e.g. "5h", "30m", or
            "5h 30m".
    """

    return fmt_hm(hm_to_minutes(hours, minutes))


def get_sandboxed_environment() -> SandboxedEnvironment:
    """Builds the sandboxed Jinja2 environment used to render report
    templates.

    Autoescaping is on, since rendered output feeds directly into PDF
    generation as HTML. Registers `fmt_hm`/`hm` as filters so templates
    can format minute counts and hour/minute field pairs the same way
    the app's own pages do, e.g. `{{ minutes|fmt_hm }}` or
    `{{ entry.hours|hm(entry.minutes) }}`.

    Returns:
        SandboxedEnvironment: A fresh sandboxed Jinja2 environment.
    """

    env = SandboxedEnvironment(autoescape=True)
    env.filters["fmt_hm"] = fmt_hm
    env.filters["hm"] = _hm
    return env


def render_template_string(source: str, context: dict) -> str:
    """Renders a raw Jinja2 template string inside the sandbox.

    Args:
        source (str): Jinja2 template source.
        context (dict): Variables available to the template.

    Returns:
        str: The rendered HTML.
    """

    template = get_sandboxed_environment().from_string(source)
    return template.render(**context)


def render_report_template(template, context: dict) -> str:
    """Renders a `ReportTemplate`'s content inside the sandbox.

    Args:
        template (ReportTemplate): Template whose `content` to render.
        context (dict): Variables available to the template.

    Returns:
        str: The rendered HTML.
    """

    return render_template_string(template.content, context)


def build_term_report_context(term: ClientTerm, config=None) -> dict:
    """Assembles the Jinja2 rendering context for a term's overage
    report.

    Self-contained - fetches the term's entries, purchases, and
    billings itself, along with the client's own CompanyProfile,
    rather than requiring the caller to have them pre-fetched.

    Args:
        term (ClientTerm): Term to build a report for.
        config (HoursConfig | None, optional): Hours config. Defaults
            to None, in which case `get_hours_config()` is used.

    Returns:
        dict: Context for rendering a `ReportTemplate` - `company`,
            `client`, `retainer`, `term`, `summary`, `entries`,
            `purchases`, `billings`, and `generated_at`.
    """

    if config is None:
        config = get_hours_config()

    retainer = term.retainer
    client = retainer.client

    entries = list(
        term.time_entries.select_related("employee").order_by("date")
    )
    purchases = list(term.hours_purchases.all())
    billings = list(term.overage_billings.order_by("billed_at"))
    summary = calculate_term_hours(term, entries, purchases, config)

    return {
        "company": CompanyProfile.get_solo(),
        "client": client,
        "retainer": retainer,
        "term": term,
        "summary": summary,
        "entries": entries,
        "purchases": purchases,
        "billings": billings,
        "generated_at": timezone.now(),
    }
