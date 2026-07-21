"""Cross-view query helpers shared by dashboard and retainer list views."""

from __future__ import annotations

from typing import Iterable

from tracker.hours import (
    HoursConfig,
    TermSummary,
    calculate_term_hours,
    get_hours_config,
)
from tracker.models import ClientTerm, Retainer, WorkOrder, WorkOrderItem


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
        purchases = list(term.hours_purchases.all())
        summary = calculate_term_hours(term, entries, purchases, config)
        is_expired = summary.status == "expired"

        if is_expired:
            sort_key = (0, term.end_date.toordinal())
        else:
            sort_key = (1, summary.remaining_support)

        ranked.append((sort_key, retainer, term, summary))

    ranked.sort(key=lambda row: row[0])

    return [(retainer, term, summary) for _, retainer, term, summary in ranked]


_WORK_ORDER_STATUS_RANK = {
    WorkOrder.STATUS_IN_PROGRESS: 0,
    WorkOrder.STATUS_OPEN: 1,
    WorkOrder.STATUS_COMPLETED: 2,
}


def ranked_work_orders(
    work_orders: Iterable[WorkOrder] | None = None,
) -> list[WorkOrder]:
    """Ranks work orders for the company-wide list page.

    In Progress sorts first (most actionable), then Open, then
    Completed last - most-recently-updated first within each group.

    Args:
        work_orders (Iterable[WorkOrder] | None, optional): Work orders
            to rank. Defaults to None, in which case every work order
            across every client is used.

    Returns:
        list[WorkOrder]: Work orders ranked most-actionable first.
    """

    if work_orders is None:
        work_orders = WorkOrder.objects.select_related(
            "retainer", "retainer__client"
        ).prefetch_related("items")

    ranked = sorted(work_orders, key=lambda wo: wo.updated_at, reverse=True)
    ranked.sort(key=lambda wo: _WORK_ORDER_STATUS_RANK.get(wo.status, 3))

    return ranked


def work_order_item_progress(work_order: WorkOrder) -> tuple[int, int]:
    """Counts a work order's completed vs. total checklist items.

    Args:
        work_order (WorkOrder): Work order to count items for - `items`
            should already be prefetched to avoid an extra query.

    Returns:
        tuple[int, int]: `(completed_count, total_count)`.
    """

    items = list(work_order.items.all())
    completed = sum(
        1 for i in items if i.status == WorkOrderItem.STATUS_COMPLETED
    )

    return completed, len(items)
