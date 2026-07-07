"""Template filters for formatting and styling hours data in templates."""

from django import template

from tracker.hours import fmt_hours as _fmt_hours

register = template.Library()


@register.filter
def fmt_hours(value):
    """Formats a float as a compact hours string for template display.

    Args:
        value: Value to format, coerced to float.

    Returns:
        str: `value` formatted as e.g. "5h" or "5.5h", or "—" if `value`
            cannot be converted to a float.
    """

    try:
        return _fmt_hours(float(value))

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
