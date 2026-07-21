"""
Work order checklist item timer logic.

Mirrors tracker/hours.py's shape: functions accept an optional HoursConfig
instance so cap/reminder/daily-limit values can be swapped out in tests
without touching settings.ini. Billing decisions (the Support/Dev split,
cap/daily-limit checks) live here, not in views or JS - JS only displays
what this module computes and reacts to it via polling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from tracker.hours import HoursConfig, get_hours_config, hm_to_minutes
from tracker.models import TimeEntry, WorkOrderItem


def item_elapsed_minutes(item: WorkOrderItem, now=None) -> int:
    """Sums an item's timer segments into a total elapsed minute count.

    Args:
        item (WorkOrderItem): Item whose segments to sum.
        now (datetime | None, optional): Reference time for the item's
            still-running segment, if any. Defaults to None, in which
            case `django.utils.timezone.now()` is used.

    Returns:
        int: Total elapsed minutes across all of the item's segments,
            rounded to the nearest minute.
    """

    if now is None:
        now = timezone.now()

    total_seconds = sum(
        ((segment.ended_at or now) - segment.started_at).total_seconds()
        for segment in item.segments.all()
    )

    return round(total_seconds / 60)


def support_dev_split(
    elapsed_minutes: int, cap_minutes: int
) -> tuple[int, int]:
    """Splits an elapsed-minute total into Support and Development portions.

    Args:
        elapsed_minutes (int): Total elapsed minutes on the item.
        cap_minutes (int): Support cap (`MAX_SUPPORT_MINUTES_PER_TASK`).

    Returns:
        tuple[int, int]: `(support_minutes, dev_minutes)` such that
            `support_minutes` never exceeds `cap_minutes` and the two
            sum to `elapsed_minutes`.
    """

    support_minutes = min(elapsed_minutes, cap_minutes)
    dev_minutes = max(0, elapsed_minutes - cap_minutes)

    return support_minutes, dev_minutes


def daily_dev_minutes_used(employee, today: date | None = None) -> int:
    """Sums an employee's already-finalised Development minutes for a day.

    Args:
        employee (Employee): Employee to sum for.
        today (date | None, optional): Day to sum. Defaults to None, in
            which case today's local date is used.

    Returns:
        int: Total minutes across the employee's `TimeEntry` rows of
            type DEVELOPMENT dated `today`. Does not include any
            live/not-yet-finalised timer segment - see
            `check_thresholds` for that.
    """

    if today is None:
        today = timezone.localdate()

    entries = TimeEntry.objects.filter(
        employee=employee, type=TimeEntry.TYPE_DEVELOPMENT, date=today
    )

    return sum(hm_to_minutes(e.hours, e.minutes) for e in entries)


@dataclass
class TimerStatus:
    """Computed live status for a work order item's timer.

    Attributes:
        elapsed_minutes (int): Total elapsed minutes across all segments.
        support_minutes (int): Portion of `elapsed_minutes` billed (or
            to be billed) as Support.
        dev_minutes (int): Portion of `elapsed_minutes` billed (or to
            be billed) as Development.
        should_pause_for_cap (bool): True if a SUPPORT-typed item has
            reached the support cap and needs employee confirmation to
            continue as Support + Dev Overage.
        should_hard_stop_for_daily_cap (bool): True if continuing to
            run would push the owning employee's Development-billed
            time today past the daily cap.
    """

    elapsed_minutes: int
    support_minutes: int
    dev_minutes: int
    should_pause_for_cap: bool
    should_hard_stop_for_daily_cap: bool


def check_thresholds(
    item: WorkOrderItem, config: HoursConfig | None = None
) -> TimerStatus:
    """Computes an item's live elapsed time and whether any cap has been hit.

    Args:
        item (WorkOrderItem): Item to check - `segments` and `owner`
            should be usable (i.e. it has been started at least once).
        config (HoursConfig | None, optional): Hours config. Defaults
            to None, in which case `get_hours_config()` is used.

    Returns:
        TimerStatus: The item's current elapsed time, Support/Dev
            split, and whether it needs to pause (support cap) or hard
            stop (daily development cap).
    """

    if config is None:
        config = get_hours_config()

    elapsed = item_elapsed_minutes(item)
    cap_minutes = config.max_support_minutes_per_task

    if item.billing_type == WorkOrderItem.TYPE_DEVELOPMENT:
        support_minutes, dev_minutes = 0, elapsed
    elif item.billing_type == WorkOrderItem.TYPE_SUPPORT_DEV_OVERAGE:
        support_minutes, dev_minutes = support_dev_split(elapsed, cap_minutes)
    else:  # SUPPORT, or blank (not yet started)
        support_minutes, dev_minutes = elapsed, 0

    should_pause_for_cap = (
        item.billing_type == WorkOrderItem.TYPE_SUPPORT
        and elapsed >= cap_minutes
    )

    should_hard_stop_for_daily_cap = False
    if dev_minutes > 0 and item.owner is not None:
        max_daily_minutes = round(config.max_dev_hours_per_day * 60)
        # `daily_dev_minutes_used` only sums *finalised* TimeEntry rows,
        # so adding this item's own live `dev_minutes` isn't double
        # counting - this item hasn't been finalised yet.
        already_used = daily_dev_minutes_used(item.owner)
        should_hard_stop_for_daily_cap = (
            already_used + dev_minutes >= max_daily_minutes
        )

    return TimerStatus(
        elapsed_minutes=elapsed,
        support_minutes=support_minutes,
        dev_minutes=dev_minutes,
        should_pause_for_cap=should_pause_for_cap,
        should_hard_stop_for_daily_cap=should_hard_stop_for_daily_cap,
    )
