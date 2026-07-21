"""Template filters for formatting and styling hours data in templates."""

from django import template

from tracker.hours import fmt_hm as _fmt_hm
from tracker.hours import hm_to_minutes

register = template.Library()


@register.filter
def fmt_hm(value):
    """Formats a total-minutes value as a compact "Xh Ym" string.

    Args:
        value: Total minutes to format, coerced to int.

    Returns:
        str: `value` formatted as e.g. "5h", "30m", or "5h 30m", or "—"
            if `value` cannot be converted to an int.
    """

    try:
        return _fmt_hm(int(value))

    except TypeError, ValueError:
        return "—"


@register.filter
def hm(hours, minutes):
    """Formats a raw hours + minutes field pair for template display.

    Args:
        hours: Whole hours, coerced to int.
        minutes: Minutes (0-59), coerced to int.

    Returns:
        str: `hours`/`minutes` formatted as e.g. "5h", "30m", or "5h 30m",
            or "—" if either value cannot be converted to an int.
    """

    try:
        return _fmt_hm(hm_to_minutes(int(hours), int(minutes)))

    except TypeError, ValueError:
        return "—"


@register.filter
def hours_bar_color(status):
    """Maps an hours status to a Tailwind background color class.

    Args:
        status: HoursStatus string ("healthy", "low", or "overage").

    Returns:
        str: Tailwind background color utility class for the progress bar.
    """

    return {
        "healthy": "bg-emerald-500",
        "low": "bg-amber-500",
        "overage": "bg-red-500",
    }.get(status, "bg-slate-500")


@register.filter
def status_badge_classes(status):
    """Maps an hours status to Tailwind badge utility classes.

    Args:
        status: HoursStatus string ("healthy", "low", or "overage").

    Returns:
        str: Tailwind utility classes for the status badge.
    """

    return {
        "healthy": (
            "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20"
        ),
        "low": "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20",
        "overage": "bg-red-500/10 text-red-400 ring-1 ring-red-500/20",
    }.get(status, "bg-slate-700/50 text-slate-400 ring-1 ring-white/10")


@register.filter
def status_label(status):
    """Maps an hours status to a human-readable label.

    Args:
        status: HoursStatus string ("healthy", "low", or "overage").

    Returns:
        str: Human-readable label for `status`, or `status` unchanged if
            not recognised.
    """

    return {
        "healthy": "On track",
        "low": "Low hours",
        "overage": "Overage",
    }.get(status, status)


@register.filter
def entry_type_classes(entry_type):
    """Maps a time entry type to Tailwind badge utility classes.

    Args:
        entry_type: TimeEntry type string ("SUPPORT" or "DEVELOPMENT").

    Returns:
        str: Tailwind utility classes for the entry type badge.
    """

    if entry_type == "SUPPORT":
        return "bg-indigo-500/10 text-indigo-400"

    return "bg-purple-500/10 text-purple-400"


@register.filter
def work_order_status_classes(status):
    """Maps a work order status to Tailwind badge utility classes.

    Args:
        status: WorkOrder.status string ("OPEN", "IN_PROGRESS", or
            "COMPLETED").

    Returns:
        str: Tailwind utility classes for the status badge.
    """

    return {
        "OPEN": "bg-slate-700/50 text-slate-400 ring-1 ring-white/10",
        "IN_PROGRESS": (
            "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20"
        ),
        "COMPLETED": (
            "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20"
        ),
    }.get(status, "bg-slate-700/50 text-slate-400 ring-1 ring-white/10")


@register.filter
def work_order_status_label(status):
    """Maps a work order status to a human-readable label.

    Args:
        status: WorkOrder.status string ("OPEN", "IN_PROGRESS", or
            "COMPLETED").

    Returns:
        str: Human-readable label for `status`, or `status` unchanged
            if not recognised.
    """

    return {
        "OPEN": "Open",
        "IN_PROGRESS": "In progress",
        "COMPLETED": "Completed",
    }.get(status, status)


@register.filter
def item_status_classes(status):
    """Maps a checklist item status to Tailwind badge utility classes.

    Args:
        status: WorkOrderItem.status string ("NOT_STARTED", "RUNNING",
            "PAUSED", or "COMPLETED").

    Returns:
        str: Tailwind utility classes for the status badge.
    """

    return {
        "NOT_STARTED": "bg-slate-700/50 text-slate-400 ring-1 ring-white/10",
        "RUNNING": (
            "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20"
        ),
        "PAUSED": "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20",
        "COMPLETED": (
            "bg-indigo-500/10 text-indigo-400 ring-1 ring-indigo-500/20"
        ),
    }.get(status, "bg-slate-700/50 text-slate-400 ring-1 ring-white/10")


@register.filter
def item_status_label(status):
    """Maps a checklist item status to a human-readable label.

    Args:
        status: WorkOrderItem.status string ("NOT_STARTED", "RUNNING",
            "PAUSED", or "COMPLETED").

    Returns:
        str: Human-readable label for `status`, or `status` unchanged
            if not recognised.
    """

    return {
        "NOT_STARTED": "Not started",
        "RUNNING": "Running",
        "PAUSED": "Paused",
        "COMPLETED": "Completed",
    }.get(status, status)


@register.filter
def item_type_classes(billing_type):
    """Maps a checklist item billing type to Tailwind badge utility classes.

    Args:
        billing_type: WorkOrderItem.billing_type string ("SUPPORT",
            "SUPPORT_DEV_OVERAGE", or "DEVELOPMENT").

    Returns:
        str: Tailwind utility classes for the billing type badge.
    """

    return {
        "SUPPORT": "bg-indigo-500/10 text-indigo-400",
        "SUPPORT_DEV_OVERAGE": "bg-amber-500/10 text-amber-400",
        "DEVELOPMENT": "bg-purple-500/10 text-purple-400",
    }.get(billing_type, "bg-slate-700/50 text-slate-400")


@register.filter
def clamp(value, min_val=0):
    """Clamps a value to a minimum floor.

    Args:
        value: Value to clamp, coerced to float.
        min_val: Floor to clamp to, coerced to float. Defaults to 0.

    Returns:
        float: The greater of `value` and `min_val`, or `min_val`
            unchanged if `value` cannot be converted to a float.
    """

    try:
        return max(float(value), float(min_val))

    except TypeError, ValueError:
        return min_val


@register.filter
def floatformat_pct(value):
    """Formats a value as a whole-number percentage string.

    Args:
        value: Value to format, coerced to float.

    Returns:
        str: `value` rounded to a whole number, or "0" if `value` cannot
            be converted to a float.
    """

    try:
        return f"{float(value):.0f}"

    except TypeError, ValueError:
        return "0"
