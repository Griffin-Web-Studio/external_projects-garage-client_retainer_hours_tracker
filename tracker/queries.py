"""Cross-view query helpers shared by dashboard and retainer list views."""

from __future__ import annotations

from typing import Iterable

from tracker.hours import (
    HoursConfig,
    TermSummary,
    calculate_term_hours,
    get_hours_config,
)
from tracker.models import ClientTerm, Retainer


def urgent_retainers(
    retainers: Iterable[Retainer] | None = None,
    config: HoursConfig | None = None,
) -> list[tuple[Retainer, ClientTerm, TermSummary]]:
    """Ranks retainers by how urgently they need attention.

    Expired retainers awaiting renewal sort first (longest-overdue
    first), then active retainers by remaining support minutes ascending
    (deepest overage first) - i.e. "least hours left first".

    Args:
        retainers (Iterable[Retainer] | None, optional): Retainers to
            rank. Defaults to None, in which case every active retainer
            belonging to an active client is used.
        config (HoursConfig | None, optional): Hours config. Defaults to
            None, in which case `get_hours_config()` is used.

    Returns:
        list[tuple[Retainer, ClientTerm, TermSummary]]: `(retainer,
            term, summary)` triples, ranked most urgent first. Retainers
            with no term at all are excluded.
    """

    if retainers is None:
        retainers = Retainer.objects.filter(
            is_active=True, client__is_active=True
        ).select_related("client")

    if config is None:
        config = get_hours_config()

    ranked = []

    for retainer in retainers:
        term = retainer.current_term

        if not term:
            continue

        entries = list(term.time_entries.all())
        summary = calculate_term_hours(term, entries, config)
        is_expired = summary.status == "expired"

        if is_expired:
            sort_key = (0, term.end_date.toordinal())
        else:
            sort_key = (1, summary.remaining_support)

        ranked.append((sort_key, retainer, term, summary))

    ranked.sort(key=lambda row: row[0])

    return [(retainer, term, summary) for _, retainer, term, summary in ranked]
