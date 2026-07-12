"""Static nav link definitions for the dashboard sidebar.

Each entry is resolved at request time by the `nav_links` context processor,
which handles permission filtering, URL resolution, and active-state detection.

Shape of each entry
-------------------
name        Django URL name - used for `reverse()` and active-state matching.
label       Human-readable link label shown in the sidebar.
icon        Solar Icons class string (`icon_si_*`).
permission  `PermissionSlug` string that gates visibility. Omit the key, set to
              `None`, or use `"all"` to show to every authenticated user
              regardless of role.
mode        `DashboardMode` controlling which dashboard context shows the link.
              Defaults to `DashboardMode.NORMAL` when omitted.
target      Optional anchor target. Defaults to `"_self"` when omitted.
"""

from enum import StrEnum
from typing import NotRequired, TypedDict


class DashboardMode(StrEnum):
    """Controls which dashboard context a nav link is visible in.

    Args:
        StrEnum (type): Base class - members compare and behave as plain
        strings.
    """

    NORMAL = "normal"
    ADMIN = "admin"
    BOTH = "both"


class NavLinkConfig(TypedDict):
    """Shape of a single entry in `NAV_LINKS`.

    Required keys (`name`, `label`, `icon`) must always be present. Optional
    keys use `NotRequired` so static analysers treat them as absent rather than
    typed as `str | None`.

    Args:
        TypedDict (type): Base class that turns the class body into a typed
            `dict` schema understood by static type checkers.
    """

    name: str
    label: str
    icon: str
    permission: NotRequired[str]
    mode: NotRequired[DashboardMode]
    target: NotRequired[str]


NAV_LINKS: list[NavLinkConfig] = [
    {
        "name": "dashboard",
        "label": "Dashboard",
        "icon": "icon_si_widget",
        "mode": DashboardMode.NORMAL,
        # No permission - every authenticated user sees the dashboard.
    },
    {
        "name": "client-list",
        "label": "Clients",
        "icon": "icon_si_users_group",
        "mode": DashboardMode.NORMAL,
        # No permission - every authenticated user can view clients.
    },
    {
        "name": "retainer-list",
        "label": "Retainers",
        "icon": "icon_si_clipboard",
        "mode": DashboardMode.NORMAL,
        # No permission - every authenticated user can view retainers.
    },
]
