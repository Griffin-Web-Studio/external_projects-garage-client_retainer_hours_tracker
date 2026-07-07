"""
Core retainer hours calculation logic.

All functions accept an optional HoursConfig instance. When running inside
Django the config is populated from AppConfig (which reads settings.ini).
Outside Django (e.g. unit tests) you can pass an explicit HoursConfig with
whatever values you need - no Django dependency required.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, Union

from tracker.models import ClientTerm, TimeEntry

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
    """

    term_months: int = 12
    dev_conversion_ratio: float = (
        2.0  # 1 dev hour costs this many support hours
    )
    max_migrate_hours: float = 6.0  # cap on hours migrated without conversion
    low_hours_threshold: float = 75.0  # % used before "low" warning triggers


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


# ─────────────────────────────────────────────────────────────────| Helpers |──


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


def fmt_hours(value: float) -> str:
    """Formats a float as a compact hours string.

    Args:
        value (float): Number of hours.

    Returns:
        str: `value` formatted as e.g. "5h" for whole numbers or "5.5h"
            for fractional ones.
    """

    if value == int(value):
        return f"{int(value)}h"

    return f"{value:.1f}h"


# ─────────────────────────────────────────────────────| Summary dataclasses |──

HoursStatus = Literal["healthy", "low", "overage"]


@dataclass
class ActiveTermSummary:
    """Computed hours summary for a term that is still in progress.

    Attributes:
        status (Literal["active"]): Always "active" for this summary type.
        monthly_allocation (float): Support hours granted per calendar
            month under the term.
        months_elapsed (int): Number of months counted towards allocation
            so far, capped at the term length.
        total_support_allocated (float): Total support hours allocated to
            date (monthly allocation x months elapsed, plus any migrated
            hours).
        total_support_used (float): Total support hours logged so far.
        remaining_support (float): Support hours left to use; negative
            values are clamped to 0 via `support_overage`.
        support_used_pct (float): Percentage of allocated support hours
            used, capped at 100.
        support_overage (float): Support hours used beyond the allocation.
        total_dev_available (float): Development hours available from a
            previous term's conversion.
        total_dev_used (float): Development hours logged so far.
        remaining_dev (float): Development hours left to use.
        dev_overage (float): Development hours used beyond what's
            available.
        hours_status (HoursStatus): Overall health of the term - "healthy",
            "low", or "overage".
    """

    status: Literal["active"]
    monthly_allocation: float
    months_elapsed: int
    total_support_allocated: float
    total_support_used: float
    remaining_support: float
    support_used_pct: float
    support_overage: float
    total_dev_available: float
    total_dev_used: float
    remaining_dev: float
    dev_overage: float
    hours_status: HoursStatus


@dataclass
class ExpiredTermSummary:
    """Computed hours summary for a term that has ended.

    Attributes:
        status (Literal["expired"]): Always "expired" for this summary
            type.
        total_support_allocated (float): Total support hours allocated
            over the full term.
        total_support_used (float): Total support hours logged over the
            full term.
        support_overage (float): Support hours used beyond the allocation.
        total_dev_available (float): Development hours available from a
            previous term's conversion.
        total_dev_used (float): Development hours logged over the full
            term.
        remaining_dev (float): Development hours never used.
        dev_overage (float): Development hours used beyond what's
            available.
        remaining_support_for_carryover (float): Unused support hours
            eligible for conversion or migration into the next term.
    """

    status: Literal["expired"]
    total_support_allocated: float
    total_support_used: float
    support_overage: float
    total_dev_available: float
    total_dev_used: float
    remaining_dev: float
    dev_overage: float
    remaining_support_for_carryover: float


TermSummary = Union[ActiveTermSummary, ExpiredTermSummary]


# ─────────────────────────────────────────────────────────| Main calculator |──


def calculate_term_hours(
    term: ClientTerm,
    time_entries: TimeEntry,
    config: HoursConfig | None = None,
) -> TermSummary:
    """Calculates the hours summary for a client term.

    Args:
        term (ClientTerm): ClientTerm instance to summarise.
        time_entries (TimeEntry): Pre-filtered TimeEntry instances
            belonging to `term`.
        config (HoursConfig | None, optional): Hours config. Defaults to
            None, in which case `get_hours_config()` is used.

    Returns:
        TermSummary: An `ActiveTermSummary` if `term` has not yet ended,
            otherwise an `ExpiredTermSummary`.
    """

    if config is None:
        config = get_hours_config()

    today = date.today()
    is_active = today < term.end_date

    support_entries = [e for e in time_entries if e.type == "SUPPORT"]
    dev_entries = [e for e in time_entries if e.type == "DEVELOPMENT"]

    total_support_used = sum(e.hours for e in support_entries)
    total_dev_used = sum(e.hours for e in dev_entries)
    total_dev_available = term.dev_hours_from_conversion

    if is_active:
        elapsed = _months_between(term.start_date, today)
        months_elapsed = min(elapsed + 1, config.term_months)

        total_support_allocated = (
            months_elapsed * term.monthly_hours + term.migrated_support_hours
        )

        remaining_support = total_support_allocated - total_support_used
        support_overage = max(-remaining_support, 0)
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
            monthly_allocation=term.monthly_hours,
            months_elapsed=months_elapsed,
            total_support_allocated=total_support_allocated,
            total_support_used=total_support_used,
            remaining_support=remaining_support,
            support_used_pct=support_used_pct,
            support_overage=support_overage,
            total_dev_available=total_dev_available,
            total_dev_used=total_dev_used,
            remaining_dev=remaining_dev,
            dev_overage=dev_overage,
            hours_status=hours_status,
        )

    # ── Expired ───────────────────────────────────────────────────────────────
    total_support_allocated = (
        config.term_months * term.monthly_hours + term.migrated_support_hours
    )
    remaining_support = total_support_allocated - total_support_used
    support_overage = max(-remaining_support, 0)

    remaining_dev = total_dev_available - total_dev_used
    dev_overage = max(-remaining_dev, 0)

    return ExpiredTermSummary(
        status="expired",
        total_support_allocated=total_support_allocated,
        total_support_used=total_support_used,
        support_overage=support_overage,
        total_dev_available=total_dev_available,
        total_dev_used=total_dev_used,
        remaining_dev=remaining_dev,
        dev_overage=dev_overage,
        remaining_support_for_carryover=max(remaining_support, 0),
    )


# ─────────────────────────────────────────────────────────| Renewal helpers |──


def compute_converted_dev_hours(
    remaining_support: float,
    config: HoursConfig | None = None,
) -> float:
    """Converts unused support hours into development hours.

    Args:
        remaining_support (float): Unused support hours carried over from
            the previous term. Negative values are treated as 0.
        config (HoursConfig | None, optional): Hours config. Defaults to
            None, in which case `get_hours_config()` is used.

    Returns:
        float: Development hours granted for the new term.
    """

    if config is None:
        config = get_hours_config()

    return max(remaining_support, 0) / config.dev_conversion_ratio


def compute_migrated_support_hours(
    remaining_support: float,
    config: HoursConfig | None = None,
) -> float:
    """Caps unused support hours eligible for migration to the next term.

    Args:
        remaining_support (float): Unused support hours carried over from
            the previous term. Negative values are treated as 0.
        config (HoursConfig | None, optional): Hours config. Defaults to
            None, in which case `get_hours_config()` is used.

    Returns:
        float: Support hours migrated forward, capped at
            `config.max_migrate_hours`.
    """

    if config is None:
        config = get_hours_config()

    return min(max(remaining_support, 0), config.max_migrate_hours)


# ─────────────────────────────────────────────────| Overage billing helpers |──


def billed_overage(billings, entry_type: str) -> float:
    """Sums hours already billed for a given entry type.

    Args:
        billings: Iterable of OverageBilling instances.
        entry_type (str): TimeEntry type to filter by, "SUPPORT" or
            "DEVELOPMENT".

    Returns:
        float: Total hours charged across `billings` matching
            `entry_type`.
    """

    return sum(b.hours_charged for b in billings if b.type == entry_type)


def unbilled_overage(
    computed_overage: float, billings, entry_type: str
) -> float:
    """Computes overage hours not yet billed.

    Args:
        computed_overage (float): Overage hours computed for the term.
        billings: Iterable of OverageBilling instances.
        entry_type (str): TimeEntry type to filter by, "SUPPORT" or
            "DEVELOPMENT".

    Returns:
        float: `computed_overage` minus hours already billed, floored
            at 0.
    """

    return max(0, computed_overage - billed_overage(billings, entry_type))
