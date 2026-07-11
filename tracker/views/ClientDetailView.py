from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from tracker.forms import BillOverageForm
from tracker.hours import (
    ExpiredTermSummary,
    billed_overage,
    calculate_term_hours,
    compute_converted_dev_minutes,
    compute_migrated_support_minutes,
    fmt_hm,
    get_hours_config,
    minutes_to_hm,
    unbilled_overage,
)
from tracker.models import Client


class ClientDetailView(LoginRequiredMixin, View):
    """View for a client's current term status, entries, and billing."""

    def get(self, request, pk):
        """Renders the client detail page.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the client to display.

        Returns:
            HttpResponse: Rendered client_detail.html.
        """

        return self._render(request, pk)

    def _render(self, request, pk, bill_form=None):
        """Builds the full context and renders client_detail.html.

        Args:
            request (HttpRequest): Incoming request.
            pk (int): Primary key of the client to display.
            bill_form (BillOverageForm | None, optional): Bound form to
                re-render with validation errors after a failed overage
                billing submission. Defaults to None, in which case a
                fresh unbound form is built.

        Returns:
            HttpResponse: Rendered client_detail.html with the client's
                current term summary, time entries, and billing history,
                or a bare "no term" page if the client has no term yet.
        """

        client = get_object_or_404(Client, pk=pk)
        term = client.terms.order_by("-term_number").first()

        if not term:
            return render(
                request,
                "client_detail.html",
                {"client": client, "term": None},
            )

        cfg = get_hours_config()
        entries = list(
            term.time_entries.select_related("employee").order_by("-date")
        )
        billings = list(term.overage_billings.order_by("-billed_at"))
        summary = calculate_term_hours(term, entries, cfg)

        is_active_term = summary.status == "active"
        s_overage = getattr(summary, "support_overage", 0)
        d_overage = getattr(summary, "dev_overage", 0)

        billed_s = billed_overage(billings, "SUPPORT")
        billed_d = billed_overage(billings, "DEVELOPMENT")
        unbilled_s = unbilled_overage(s_overage, billings, "SUPPORT")
        unbilled_d = unbilled_overage(d_overage, billings, "DEVELOPMENT")

        if bill_form is None:
            unbilled_hours, unbilled_minutes = minutes_to_hm(
                unbilled_s if unbilled_s > 0 else unbilled_d
            )
            bill_form = BillOverageForm(
                initial={
                    "type": "SUPPORT" if unbilled_s > 0 else "DEVELOPMENT",
                    "hours_charged": unbilled_hours,
                    "minutes_charged": unbilled_minutes,
                }
            )

        conv_dev_hours = 0
        mig_sup_hours = 0

        if not is_active_term and isinstance(summary, ExpiredTermSummary):
            conv_dev_hours = compute_converted_dev_minutes(
                summary.remaining_support_for_carryover, cfg
            )
            mig_sup_hours = compute_migrated_support_minutes(
                summary.remaining_support_for_carryover, cfg
            )

        return render(
            request,
            "client_detail.html",
            {
                "client": client,
                "term": term,
                "entries": entries,
                "billings": billings,
                "summary": summary,
                "is_active_term": is_active_term,
                "unbilled_s": unbilled_s,
                "unbilled_d": unbilled_d,
                "billed_s": billed_s,
                "billed_d": billed_d,
                "has_overage": unbilled_s > 0 or unbilled_d > 0,
                "bill_form": bill_form,
                "conv_dev_hours": conv_dev_hours,
                "mig_sup_hours": mig_sup_hours,
                "max_migrate": cfg.max_migrate_hours,
                "fmt_hm": fmt_hm,
            },
        )
