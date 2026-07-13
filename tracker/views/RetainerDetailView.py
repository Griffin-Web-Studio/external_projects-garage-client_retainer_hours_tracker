from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from tracker.forms import BillOverageForm, HoursPurchaseForm
from tracker.hours import (
    ExpiredTermSummary,
    billed_overage,
    calculate_term_hours,
    compute_converted_dev_minutes,
    compute_migrated_support_minutes,
    display_hours_status,
    fmt_hm,
    get_hours_config,
    minutes_to_hm,
    unbilled_overage,
)
from tracker.models import Client, Retainer


class RetainerDetailView(LoginRequiredMixin, View):
    """View for a retainer's term status, entries, and billing.

    Shows the retainer's current term by default, or a specific past
    term when `term_number` is given - past terms are read-only (no
    renewal or "current term" actions), since they've already been
    superseded.
    """

    def get(self, request, pk, retainer_pk, term_number=None):
        """Renders the retainer detail page.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to display.
            term_number (int | None, optional): Specific term to
                display. Defaults to None, in which case the retainer's
                current (latest) term is shown.

        Returns:
            HttpResponse: Rendered retainer_detail.html.
        """

        return self._render(request, pk, retainer_pk, term_number=term_number)

    def _render(
        self,
        request,
        pk,
        retainer_pk,
        bill_form=None,
        purchase_form=None,
        term_number=None,
    ):
        """Builds the full context and renders retainer_detail.html.

        Args:
            request (HttpRequest): Incoming request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to display.
            bill_form (BillOverageForm | None, optional): Bound form to
                re-render with validation errors after a failed overage
                billing submission. Defaults to None, in which case a
                fresh unbound form is built.
            purchase_form (HoursPurchaseForm | None, optional): Bound
                form to re-render with validation errors after a failed
                hours purchase submission. Defaults to None, in which
                case a fresh unbound form is built.
            term_number (int | None, optional): Specific term to
                display. Defaults to None, in which case the retainer's
                current (latest) term is shown.

        Returns:
            HttpResponse: Rendered retainer_detail.html with the given
                term's summary, time entries, and billing history, or a
                bare "no term" page if the retainer has no term yet.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        current_term = retainer.current_term

        if term_number is not None:
            term = get_object_or_404(retainer.terms, term_number=term_number)
        else:
            term = current_term

        if not term:
            return render(
                request,
                "retainer_detail.html",
                {"client": client, "retainer": retainer, "term": None},
            )

        is_latest_term = term.pk == current_term.pk
        all_terms = list(retainer.terms.order_by("-term_number"))
        historical_entries = list(
            retainer.time_entries.filter(term__isnull=True)
            .select_related("employee")
            .order_by("-date")
        )

        cfg = get_hours_config()
        entries = list(
            term.time_entries.select_related("employee").order_by("-date")
        )
        billings = list(term.overage_billings.order_by("-billed_at"))
        purchases = list(term.hours_purchases.all())
        summary = calculate_term_hours(term, entries, purchases, cfg)

        is_active_term = summary.status == "active"
        s_overage = getattr(summary, "support_overage", 0)
        d_overage = getattr(summary, "dev_overage", 0)

        billed_s = billed_overage(billings, "SUPPORT")
        billed_d = billed_overage(billings, "DEVELOPMENT")
        unbilled_s = unbilled_overage(s_overage, billings, "SUPPORT")
        unbilled_d = unbilled_overage(d_overage, billings, "DEVELOPMENT")

        display_status = (
            display_hours_status(summary, unbilled_s, unbilled_d, cfg)
            if is_active_term
            else None
        )

        if bill_form is None:
            unbilled_hours, unbilled_minutes = minutes_to_hm(
                unbilled_s if unbilled_s > 0 else unbilled_d
            )
            bill_form = BillOverageForm(
                initial={
                    "type": "SUPPORT" if unbilled_s > 0 else "DEVELOPMENT",
                    "hours_charged": unbilled_hours,
                    "minutes_charged": unbilled_minutes,
                },
                max_unbilled={"SUPPORT": unbilled_s, "DEVELOPMENT": unbilled_d},
            )

        if purchase_form is None:
            purchase_form = HoursPurchaseForm()

        conv_dev_hours = 0
        mig_sup_hours = 0

        # Carryover-into-renewal preview only makes sense for the term
        # that's actually next in line for renewal - a past, non-latest
        # expired term has already been renewed (a newer term exists).
        if (
            is_latest_term
            and not is_active_term
            and isinstance(summary, ExpiredTermSummary)
        ):
            conv_dev_hours = compute_converted_dev_minutes(
                summary.remaining_support_for_carryover, cfg
            )
            mig_sup_hours = compute_migrated_support_minutes(
                summary.remaining_support_for_carryover, cfg
            )

        return render(
            request,
            "retainer_detail.html",
            {
                "client": client,
                "retainer": retainer,
                "term": term,
                "is_latest_term": is_latest_term,
                "all_terms": all_terms,
                "historical_entries": historical_entries,
                "entries": entries,
                "billings": billings,
                "purchases": purchases,
                "summary": summary,
                "is_active_term": is_active_term,
                "unbilled_s": unbilled_s,
                "unbilled_d": unbilled_d,
                "display_status": display_status,
                "billed_s": billed_s,
                "billed_d": billed_d,
                "has_overage": unbilled_s > 0 or unbilled_d > 0,
                "bill_form": bill_form,
                "purchase_form": purchase_form,
                "conv_dev_hours": conv_dev_hours,
                "mig_sup_hours": mig_sup_hours,
                "max_migrate": cfg.max_migrate_hours,
                "fmt_hm": fmt_hm,
            },
        )
