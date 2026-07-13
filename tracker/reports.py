"""Jinja2 sandboxed rendering engine for overage report templates.

Report templates are stored in the database (`ReportTemplate.content`)
and editable via the admin, so they're rendered inside a Jinja2
`SandboxedEnvironment` rather than Django's own template language -
the sandbox blocks access to unsafe attributes/methods (e.g. reaching
`__class__`/`__globals__` to escape into arbitrary Python), so a
template can't be used to run code beyond what the rendering context
exposes.
"""

from jinja2.sandbox import SandboxedEnvironment


def get_sandboxed_environment() -> SandboxedEnvironment:
    """Builds the sandboxed Jinja2 environment used to render report
    templates.

    Autoescaping is on, since rendered output feeds directly into PDF
    generation as HTML.

    Returns:
        SandboxedEnvironment: A fresh sandboxed Jinja2 environment.
    """

    return SandboxedEnvironment(autoescape=True)


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
