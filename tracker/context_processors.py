from typing import TypedDict

from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse

from core.app_settings import AppConfig
from tracker.features.nav_links import DashboardMode, NAV_LINKS, NavLinkConfig


def app_settings(request: HttpRequest) -> dict[str, str | bool]:
    """Injects global application settings into every template context so views
    don't have to pass them manually.

    Available in all templates:
        {{ APP_NAME }}     - configurable via settings.ini [branding] app_name
        {{ OIDC_ENABLED }} - True when OIDC is configured in .env

    Args:
        request (HttpRequest): HTTP request object

    Returns:
        dict[str, str | bool]: context
    """

    settings = AppConfig.get()

    return {
        "APP_NAME": getattr(settings, "app_name", "UnnamedApp"),
        "OIDC_LABEL": getattr(settings, "oidc_label", "OIDC"),
        "OIDC_ENABLED": getattr(settings, "oidc_enabled", False),
    }


class ResolvedNavLink(TypedDict):
    """A fully resolved nav link ready for the sidebar template.

    Produced by `nav_links()` after permission filtering, URL
    resolution, and active-state detection have been applied.

    Attributes:
        label (str): Human-readable link label.
        url (str): Resolved URL for the link's target view.
        icon (str): Icon slug, matched against a small inline SVG map
            in the sidebar template.
        active (bool): Whether this link matches the current route.
        target (str): Anchor target, e.g. "_self".
    """

    label: str
    url: str
    icon: str
    active: bool
    target: str


def _resolve_link(
    link: NavLinkConfig,
    user_role: str,
    is_admin_mode: bool,
    current_url_name: str | None,
) -> ResolvedNavLink | None:
    """Resolves one `NavLinkConfig` entry to a template-ready dict.

    Args:
        link (NavLinkConfig): The static nav link definition to resolve.
        user_role (str): The current user's `Employee.role` value.
        is_admin_mode (bool): Whether the current route is under the
            admin dashboard.
        current_url_name (str | None): The URL name for the active
            route.

    Returns:
        ResolvedNavLink | None: Resolved link dict, or None to exclude
            it - permission denied, wrong dashboard mode, or an
            unresolvable URL name.
    """

    permission = link.get("permission")
    if permission and permission != "all" and permission != user_role:
        return None

    mode = link.get("mode", DashboardMode.NORMAL)
    if mode == DashboardMode.NORMAL and is_admin_mode:
        return None
    if mode == DashboardMode.ADMIN and not is_admin_mode:
        return None

    name = link["name"]
    try:
        url = reverse(name)
    except NoReverseMatch:
        return None

    return {
        "label": link["label"],
        "url": url,
        "icon": link.get("icon", ""),
        "active": current_url_name == name,
        "target": link.get("target", "_self"),
    }


def nav_links(request: HttpRequest) -> dict[str, list[ResolvedNavLink]]:
    """Builds the filtered, resolved sidebar nav link list for the request.

    Reads the static `NAV_LINKS` config and returns only the links the
    current user is permitted to see in the current dashboard mode.
    Unauthenticated requests get an empty list.

    Args:
        request (HttpRequest): HTTP request object.

    Returns:
        dict[str, list[ResolvedNavLink]]: Context dict with a single
            `nav_links` key.
    """

    if not request.user.is_authenticated:
        return {"nav_links": []}

    is_admin_mode = request.path.startswith("/dashboard/admin")
    current_url_name = (
        request.resolver_match.url_name if request.resolver_match else None
    )

    resolved: list[ResolvedNavLink] = [
        r
        for link in NAV_LINKS
        if (
            r := _resolve_link(
                link, request.user.role, is_admin_mode, current_url_name
            )
        )
        is not None
    ]

    return {"nav_links": resolved}
