"""
Core retainer hours calculation logic.

All functions accept an optional HoursConfig instance. When running inside
Django the config is populated from AppConfig (which reads settings.ini).
Outside Django (e.g. unit tests) you can pass an explicit HoursConfig with
whatever values you need - no Django dependency required.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Literal, Union

from tracker.models import ClientTerm, HoursPurchase, TimeEntry

# ───────────────────────────────────────────────────────────| Configuration |──


@dataclass
class HoursConfig:
    """All tuneable business constants in one place.

    Defaults match the shipped settings.ini values.

    Attributes:
        term_months (int): Number of months in a single contract term.
        dev_conversion_ratio (float): Support hours one converted
            development hour costs.
        max_migrate_hours (float): Cap on support hours migrated forward
            to a new term without conversion.
        low_hours_threshold (float): Percentage of allocated hours used
            at which the "low" warning triggers.
        min_log_entry_minutes (int): Minimum total minutes a single
            time entry can be logged for.
        min_overage_billing_minutes (int): Minimum total minutes a
            single overage billing can be recorded for.
        max_support_minutes_per_task (int): Hard cap on a Support-typed
            work order checklist item's timer before it must be
            escalated to Support + Dev Overage billing.
        timer_reminder_minutes (tuple[int, ...]): Minutes into a running
            checklist item timer at which an audible reminder plays.
        max_dev_hours_per_day (float): Daily cap on Development-billed
            timer time per employee.
    """

    term_months: int = 12
    dev_conversion_ratio: float = (
        2.0  # 1 dev hour costs this many support hours
    )
    max_migrate_hours: float = 6.0  # cap on hours migrated without conversion
    low_hours_threshold: float = 75.0  # % used before "low" warning triggers
    min_log_entry_minutes: int = 5
    min_overage_billing_minutes: int = 1
    max_support_minutes_per_task: int = 30
    timer_reminder_minutes: tuple[int, ...] = (10, 15, 20)
    max_dev_hours_per_day: float = 8.0


def get_hours_config() -> HoursConfig:
    """Builds an HoursConfig from AppConfig (settings.ini).

    Falls back to dataclass defaults if AppConfig has not been initialised
    (e.g. in standalone unit tests run outside Django).

    Returns:
        HoursConfig: Business config resolved from settings.ini, or the
            dataclass defaults if AppConfig is unavailable.
    """
    try:
        from core.app_settings import AppConfig

        cfg = AppConfig.get()

        return HoursConfig(
            term_months=cfg.term_months,
            dev_conversion_ratio=cfg.dev_conversion_ratio,
            max_migrate_hours=cfg.max_migrate_hours,
            low_hours_threshold=cfg.low_hours_threshold,
            min_log_entry_minutes=cfg.min_log_entry_minutes,
            min_overage_billing_minutes=cfg.min_overage_billing_minutes,
            max_support_minutes_per_task=cfg.max_support_minutes_per_task,
            timer_reminder_minutes=cfg.timer_reminder_minutes,
            max_dev_hours_per_day=cfg.max_dev_hours_per_day,
        )

    except Exception:
        return HoursConfig()


# Convenience accessors used by views and forms
def get_term_months() -> int:
    """Gets the configured contract term length.

    Returns:
        int: Number of months in a single contract term.
    """

    return get_hours_config().term_months


def get_max_migrate_hours() -> float:
    """Gets the configured cap on migrated support hours.

    Returns:
        float: Maximum support hours that can be migrated forward to a
            new term without conversion.
    """

    return get_hours_config().max_migrate_hours


def get_dev_conversion_ratio() -> float:
    """Gets the configured support-to-dev hour conversion ratio.

    Returns:
        float: Support hours one converted development hour costs.
    """

    return get_hours_config().dev_conversion_ratio


def get_min_log_entry_minutes() -> int:
    """Gets the configured minimum duration for a single time entry.

    Returns:
        int: Minimum total minutes a single time entry can be logged
            for.
    """

    return get_hours_config().min_log_entry_minutes


def get_min_overage_billing_minutes() -> int:
    """Gets the configured minimum duration for a single overage billing.

    Returns:
        int: Minimum total minutes a single overage billing can be
            recorded for.
    """

    return get_hours_config().min_overage_billing_minutes


def get_max_support_minutes_per_task() -> int:
    """Gets the configured cap on a Support-typed checklist item's timer.

    Returns:
        int: Minutes a Support-typed work order checklist item's timer
            may run before it must be escalated to Support + Dev
            Overage billing.
    """

    return get_hours_config().max_support_minutes_per_task


def get_timer_reminder_minutes() -> tuple[int, ...]:
    """Gets the configured audible-reminder thresholds for a running timer.

    Returns:
        tuple[int, ...]: Minutes into a running checklist item timer at
            which an audible reminder plays.
    """

    return get_hours_config().timer_reminder_minutes


def get_max_dev_hours_per_day() -> float:
    """Gets the configured daily cap on Development-billed timer time.

    Returns:
        float: Maximum hours of Development-billed timer time a single
            employee may accrue in one day.
    """

    return get_hours_config().max_dev_hours_per_day


# ─────────────────────────────────────────────────────────────────| Helpers |──


def add_months(d: date, months: int) -> date:
    """Adds calendar months to a date, clamping to the target month's length.

    Args:
        d (date): Starting date.
        months (int): Number of calendar months to add.

    Returns:
        date: `d` shifted forward by `months` months. If `d.day` doesn't
            exist in the target month (e.g. 31 Jan + 1 month), it's
            clamped to that month's last day.
    """

    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])

    return d.replace(year=year, month=month, day=day)


def _months_between(start: date, end: date) -> int:
    """Counts whole calendar months between two dates.

    Args:
        start (date): Earlier date.
        end (date): Later date.

    Returns:
        int: Number of calendar months between `start` and `end`, based
            on year/month only (day-of-month is ignored).
    """

    return (end.year - start.year) * 12 + (end.month - start.month)


def hm_to_minutes(hours: int, minutes: int) -> int:
    """Combines an hours + minutes pair into a total minute count.

    Args:
        hours (int): Whole hours.
        minutes (int): Minutes, 0-59.

    Returns:
        int: Total minutes represented by `hours` and `minutes`.
    """

    return hours * 60 + minutes


def minutes_to_hm(total_minutes: int) -> tuple[int, int]:
    """Splits a total minute count back into an hours + minutes pair.

    Args:
        total_minutes (int): Total minutes, expected to be >= 0.

    Returns:
        tuple[int, int]: `(hours, minutes)` such that
            `hours * 60 + minutes == total_minutes`.
    """

    return divmod(int(round(total_minutes)), 60)


def fmt_hm(total_minutes: int) -> str:
    """Formats a total minute count as a compact "Xh Ym" string.

    Args:
        total_minutes (int): Total minutes to format.

    Returns:
        str: e.g. "5h" when there's no remainder, "30m" when under an
            hour, or "5h 30m" for a mix of both.
    """

    hours, minutes = minutes_to_hm(total_minutes)

    if minutes == 0:
        return f"{hours}h"

    if hours == 0:
        return f"{minutes}m"

    return f"{hours}h {minutes}m"


# ─────────────────────────────────────────────────────| Summary dataclasses |──

HoursStatus = Literal["healthy", "low", "overage"]


@dataclass
class ActiveTermSummary:
    """Computed hours summary for a term that is still in progress.

    All hour quantities below are expressed in total minutes (not decimal
    hours) - format them for display with `fmt_hm`.

    Attributes:
        status (Literal["active"]): Always "active" for this summary type.
        monthly_allocation (int): Support minutes granted per calendar
            month under the term.
        months_elapsed (int): Number of months counted towards allocation
            so far, capped at the term length.
        total_support_allocated (int): Total support minutes allocated to
            date (monthly allocation x months elapsed, plus any migrated
            minutes, plus any purchased buffer minutes).
        total_support_used (int): Total support minutes logged so far.
        remaining_support (int): Support minutes left to use (allocation
            and purchased buffer combined); negative values are clamped
            to 0 via `support_overage`.
        support_used_pct (float): Percentage of allocated support minutes
            used, capped at 100.
        support_overage (int): Support minutes used beyond the allocation
            and purchased buffer combined - what still needs billing.
        purchased_support (int): Total buffer minutes bought this term
            via `HoursPurchase`, on top of the monthly allocation.
        purchased_support_used (int): Buffer minutes actually drawn on
            so far - only nonzero once the ordinary allocation (monthly
            + migrated) is exhausted.
        purchased_support_remaining (int): Buffer minutes still unused.
        total_dev_available (int): Development minutes available from a
            previous term's conversion.
        total_dev_used (int): Development minutes logged so far.
        remaining_dev (int): Development minutes left to use.
        dev_overage (int): Development minutes used beyond what's
            available.
        hours_status (HoursStatus): Overall health of the term - "healthy",
            "low", or "overage".
    """

    status: Literal["active"]
    monthly_allocation: int
    months_elapsed: int
    total_support_allocated: int
    total_support_used: int
    remaining_support: int
    support_used_pct: float
    support_overage: int
    purchased_support: int
    purchased_support_used: int
    purchased_support_remaining: int
    total_dev_available: int
    total_dev_used: int
    remaining_dev: int
    dev_overage: int
    hours_status: HoursStatus


@dataclass
class ExpiredTermSummary:
    """Computed hours summary for a term that has ended.

    All hour quantities below are expressed in total minutes (not decimal
    hours) - format them for display with `fmt_hm`.

    Attributes:
        status (Literal["expired"]): Always "expired" for this summary
            type.
        total_support_allocated (int): Total support minutes allocated
            over the full term (monthly allocation, migrated carryover,
            and any purchased buffer combined).
        total_support_used (int): Total support minutes logged over the
            full term.
        support_overage (int): Support minutes used beyond the allocation
            and purchased buffer combined - what still needs billing.
        purchased_support (int): Total buffer minutes bought this term
            via `HoursPurchase`, on top of the monthly allocation.
        purchased_support_used (int): Buffer minutes actually drawn on.
        purchased_support_remaining (int): Buffer minutes left unused at
            term end - to be refunded or carried forward at renewal, at
            full value (not subject to the conversion ratio or
            migration cap applied to `remaining_support_for_carryover`).
        total_dev_available (int): Development minutes available from a
            previous term's conversion.
        total_dev_used (int): Development minutes logged over the full
            term.
        remaining_dev (int): Development minutes never used.
        dev_overage (int): Development minutes used beyond what's
            available.
        remaining_support_for_carryover (int): Unused *ordinary*
            (monthly allocation + migrated) support minutes eligible
            for conversion or migration into the next term - excludes
            the purchased buffer, which has its own carryover path.
    """

    status: Literal["expired"]
    total_support_allocated: int
    total_support_used: int
    support_overage: int
    purchased_support: int
    purchased_support_used: int
    purchased_support_remaining: int
    total_dev_available: int
    total_dev_used: int
    remaining_dev: int
    dev_overage: int
    remaining_support_for_carryover: int


TermSummary = Union[ActiveTermSummary, ExpiredTermSummary]


# ─────────────────────────────────────────────────────────| Main calculator |──


def calculate_term_hours(
    term: ClientTerm,
    time_entries: TimeEntry,
    hours_purchases: HoursPurchase,
    config: HoursConfig | None = None,
) -> TermSummary:
    """Calculates the hours summary for a client term.

    Args:
        term (ClientTerm): ClientTerm instance to summarise.
        time_entries (TimeEntry): Pre-filtered TimeEntry instances
            belonging to `term`.
        hours_purchases (HoursPurchase): Pre-filtered HoursPurchase
            instances belonging to `term`.
        config (HoursConfig | None, optional): Hours config. Defaults to
            None, in which case `get_hours_config()` is used.

    Returns:
        TermSummary: An `ActiveTermSummary` if `term` has not yet ended,
            otherwise an `ExpiredTermSummary`.
    """

    if config is None:
        config = get_hours_config()

    today = date.today()
    is_active = today <= term.end_date

    support_entries = [e for e in time_entries if e.type == "SUPPORT"]
    dev_entries = [e for e in time_entries if e.type == "DEVELOPMENT"]

    total_support_used = sum(
        hm_to_minutes(e.hours, e.minutes) for e in support_entries
    )
    total_dev_used = sum(hm_to_minutes(e.hours, e.minutes) for e in dev_entries)
    total_dev_available = hm_to_minutes(
        term.dev_hours_from_conversion, term.dev_minutes_from_conversion
    )
    monthly_allocation = hm_to_minutes(term.monthly_hours, term.monthly_minutes)
    migrated_support = hm_to_minutes(
        term.migrated_support_hours, term.migrated_support_minutes
    )
    purchased_support = sum(
        hm_to_minutes(p.hours, p.minutes) for p in hours_purchases
    )

    if is_active:
        elapsed = _months_between(term.start_date, today)
        months_elapsed = min(elapsed + 1, config.term_months)

        # "Ordinary" allocation - monthly hours plus migrated carryover,
        # excluding the purchased buffer. Used to work out how much of
        # the buffer (if any) has actually been drawn on, and feeds
        # `remaining_support_for_carryover` on expiry - the buffer has
        # its own separate carryover path (see HoursPurchase).
        base_allocated = months_elapsed * monthly_allocation + migrated_support
        total_support_allocated = base_allocated + purchased_support

        remaining_support = total_support_allocated - total_support_used
        support_overage = max(-remaining_support, 0)
        purchased_support_used = min(
            purchased_support, max(0, total_support_used - base_allocated)
        )
        purchased_support_remaining = purchased_support - purchased_support_used
        support_used_pct = (
            min(total_support_used / total_support_allocated * 100, 100)
            if total_support_allocated > 0
            else 0
        )

        remaining_dev = total_dev_available - total_dev_used
        dev_overage = max(-remaining_dev, 0)

        if support_overage > 0 or dev_overage > 0:
            hours_status: HoursStatus = "overage"

        elif support_used_pct > config.low_hours_threshold:
            hours_status = "low"

        else:
            hours_status = "healthy"

        return ActiveTermSummary(
            status="active",
            monthly_allocation=monthly_allocation,
            months_elapsed=months_elapsed,
            total_support_allocated=total_support_allocated,
            total_support_used=total_support_used,
            remaining_support=remaining_support,
            support_used_pct=support_used_pct,
            support_overage=support_overage,
            purchased_support=purchased_support,
            purchased_support_used=purchased_support_used,
            purchased_support_remaining=purchased_support_remaining,
            total_dev_available=total_dev_available,
            total_dev_used=total_dev_used,
            remaining_dev=remaining_dev,
            dev_overage=dev_overage,
            hours_status=hours_status,
        )

    # ── Expired ───────────────────────────────────────────────────────────────
    base_allocated = config.term_months * monthly_allocation + migrated_support
    total_support_allocated = base_allocated + purchased_support

    remaining_support = total_support_allocated - total_support_used
    support_overage = max(-remaining_support, 0)
    purchased_support_used = min(
        purchased_support, max(0, total_support_used - base_allocated)
    )
    purchased_support_remaining = purchased_support - purchased_support_used

    remaining_dev = total_dev_available - total_dev_used
    dev_overage = max(-remaining_dev, 0)

    return ExpiredTermSummary(
        status="expired",
        total_support_allocated=total_support_allocated,
        total_support_used=total_support_used,
        support_overage=support_overage,
        purchased_support=purchased_support,
        purchased_support_used=purchased_support_used,
        purchased_support_remaining=purchased_support_remaining,
        total_dev_available=total_dev_available,
        total_dev_used=total_dev_used,
        remaining_dev=remaining_dev,
        dev_overage=dev_overage,
        remaining_support_for_carryover=max(
            base_allocated - total_support_used, 0
        ),
    )


# ─────────────────────────────────────────────────────────| Renewal helpers |──


def compute_converted_dev_minutes(
    remaining_support: int,
    config: HoursConfig | None = None,
) -> int:
    """Converts unused support minutes into development minutes.

    Args:
        remaining_support (int): Unused support minutes carried over from
            the previous term. Negative values are treated as 0.
        config (HoursConfig | None, optional): Hours config. Defaults to
            None, in which case `get_hours_config()` is used.

    Returns:
        int: Development minutes granted for the new term, rounded to
            the nearest minute.
    """

    if config is None:
        config = get_hours_config()

    return round(max(remaining_support, 0) / config.dev_conversion_ratio)


def compute_migrated_support_minutes(
    remaining_support: int,
    config: HoursConfig | None = None,
) -> int:
    """Caps unused support minutes eligible for migration to the next term.

    Args:
        remaining_support (int): Unused support minutes carried over from
            the previous term. Negative values are treated as 0.
        config (HoursConfig | None, optional): Hours config. Defaults to
            None, in which case `get_hours_config()` is used.

    Returns:
        int: Support minutes migrated forward, capped at
            `config.max_migrate_hours` (converted to minutes).
    """

    if config is None:
        config = get_hours_config()

    max_migrate_minutes = round(config.max_migrate_hours * 60)

    return min(max(remaining_support, 0), max_migrate_minutes)


def allocate_purchased_hours_usage(
    hours_purchases: HoursPurchase, purchased_support_used: int
) -> list[tuple[HoursPurchase, int]]:
    """Attributes purchased-buffer consumption to individual purchases.

    Draws down `purchased_support_used` minutes FIFO - oldest purchase
    first, matching `HoursPurchase`'s default ordering - so each
    purchase's own leftover can be resolved (refunded or carried
    forward) individually at term renewal.

    Args:
        hours_purchases (HoursPurchase): HoursPurchase instances
            belonging to a term, oldest first.
        purchased_support_used (int): Total minutes drawn from the
            combined purchased pool this term (a term summary's
            `purchased_support_used`).

    Returns:
        list[tuple[HoursPurchase, int]]: `(purchase, remaining_minutes)`
            pairs in the same order as `hours_purchases`.
    """

    remaining_to_consume = purchased_support_used
    allocation = []

    for purchase in hours_purchases:
        total = hm_to_minutes(purchase.hours, purchase.minutes)
        consumed = min(total, remaining_to_consume)
        allocation.append((purchase, total - consumed))
        remaining_to_consume -= consumed

    return allocation


# ─────────────────────────────────────────────────| Overage billing helpers |──


def billed_overage(billings, entry_type: str) -> int:
    """Sums minutes already billed for a given entry type.

    Args:
        billings: Iterable of OverageBilling instances.
        entry_type (str): TimeEntry type to filter by, "SUPPORT" or
            "DEVELOPMENT".

    Returns:
        int: Total minutes charged across `billings` matching
            `entry_type`.
    """

    return sum(
        hm_to_minutes(b.hours_charged, b.minutes_charged)
        for b in billings
        if b.type == entry_type
    )


def unbilled_overage(computed_overage: int, billings, entry_type: str) -> int:
    """Computes overage minutes not yet billed.

    Args:
        computed_overage (int): Overage minutes computed for the term.
        billings: Iterable of OverageBilling instances.
        entry_type (str): TimeEntry type to filter by, "SUPPORT" or
            "DEVELOPMENT".

    Returns:
        int: `computed_overage` minus minutes already billed, floored
            at 0.
    """

    return max(0, computed_overage - billed_overage(billings, entry_type))


def term_unbilled_overage(
    term: ClientTerm, config: HoursConfig | None = None
) -> dict:
    """Computes unbilled overage minutes for both entry types on a term.

    Self-contained convenience wrapper for callers that don't already
    have the term's entries/purchases/billings pre-fetched - unlike
    `calculate_term_hours`, which expects them passed in.

    Args:
        term (ClientTerm): Term to compute unbilled overage for.
        config (HoursConfig | None, optional): Hours config. Defaults
            to None, in which case `get_hours_config()` is used.

    Returns:
        dict[str, int]: `{"SUPPORT": ..., "DEVELOPMENT": ...}` unbilled
            overage minutes, each floored at 0.
    """

    if config is None:
        config = get_hours_config()

    entries = list(term.time_entries.all())
    purchases = list(term.hours_purchases.all())
    billings = list(term.overage_billings.all())
    summary = calculate_term_hours(term, entries, purchases, config)

    support_overage = getattr(summary, "support_overage", 0)
    dev_overage = getattr(summary, "dev_overage", 0)

    return {
        "SUPPORT": unbilled_overage(support_overage, billings, "SUPPORT"),
        "DEVELOPMENT": unbilled_overage(dev_overage, billings, "DEVELOPMENT"),
    }


def display_hours_status(
    summary: ActiveTermSummary,
    unbilled_support: int,
    unbilled_dev: int,
    config: HoursConfig | None = None,
) -> HoursStatus:
    """Computes the term's health status for display, netted against
    what's actually still owed.

    `summary.hours_status` is "overage" whenever raw usage exceeds the
    allocation and purchased buffer, even if that excess has already
    been paid off (e.g. leftover credit from historical over-billing
    that predates `BillOverageForm` capping `hours_charged` at the
    outstanding amount). Badges and stat cards should reflect what's
    actually unbilled, not the raw figure, so a term never reads as
    "in overage" when nothing is owed.

    Args:
        summary (ActiveTermSummary): The term's computed hours summary.
        unbilled_support (int): Unbilled SUPPORT overage minutes.
        unbilled_dev (int): Unbilled DEVELOPMENT overage minutes.
        config (HoursConfig | None, optional): Hours config. Defaults
            to None, in which case `get_hours_config()` is used.

    Returns:
        HoursStatus: "overage" if there's a net unbilled amount,
            otherwise the same "low"/"healthy" classification
            `calculate_term_hours` would produce without any overage.
    """

    if config is None:
        config = get_hours_config()

    if unbilled_support > 0 or unbilled_dev > 0:
        return "overage"

    if summary.support_used_pct > config.low_hours_threshold:
        return "low"

    return "healthy"


def display_purchased_remaining(
    summary: TermSummary, hours_purchases, billings
) -> int:
    """Computes the "purchased buffer remaining" figure for display,
    folding in leftover historical billing credit.

    `summary.purchased_support_remaining` only reflects explicit
    `HoursPurchase` rows. Some of those rows (created by the one-time
    migration that converted pre-cap over-billing into buffer records,
    flagged via `from_historical_billing`) were carved out of an
    existing `OverageBilling` total rather than being new money - the
    rest of that same billing can still be sitting unspent as implicit
    credit, netted only inside `unbilled_overage`'s subtraction and
    otherwise invisible on the term's stat cards. This adds that
    leftover credit to the buffer figure so it isn't hidden, without
    double-counting the portion already represented by a
    `from_historical_billing` purchase.

    Args:
        summary (TermSummary): The term's computed hours summary.
        hours_purchases: Iterable of HoursPurchase instances for the
            term.
        billings: Iterable of OverageBilling instances for the term.

    Returns:
        int: `summary.purchased_support_remaining` plus any leftover
            SUPPORT billing credit not already represented by a
            `from_historical_billing` purchase.
    """

    carved = sum(
        hm_to_minutes(p.hours, p.minutes)
        for p in hours_purchases
        if p.from_historical_billing
    )
    billed = billed_overage(billings, "SUPPORT")
    credit = max(0, billed - summary.support_overage - carved)

    return summary.purchased_support_remaining + credit
