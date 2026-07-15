from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tracker.forms import NewTermForm
from tracker.hours import (
    add_months,
    allocate_purchased_hours_usage,
    calculate_term_hours,
    compute_converted_dev_minutes,
    compute_migrated_support_minutes,
    fmt_hm,
    get_hours_config,
    minutes_to_hm,
)
from tracker.models import Client, ClientTerm, HoursPurchase, Retainer


class NewTermView(LoginRequiredMixin, View):
    """View for renewing a retainer's expired term with a carryover
    choice.
    """

    def _get_context(
        self,
        client,
        retainer,
        term,
        summary,
        cfg,
        unresolved_purchases,
        form=None,
    ):
        """Builds the template context shared by GET and POST.

        Args:
            client (Client): Client the retainer belongs to.
            retainer (Retainer): Retainer whose term is being renewed.
            term (ClientTerm): The expired term being renewed.
            summary (ExpiredTermSummary): Hours summary for `term`.
            cfg (HoursConfig): Business config for hours calculations.
            unresolved_purchases (list[tuple[HoursPurchase, int]]):
                `(purchase, remaining_minutes)` pairs needing a
                refund-vs-carry-forward choice.
            form (NewTermForm | None, optional): Bound form to
                re-render with validation errors. Defaults to None, in
                which case a fresh unbound form is built.

        Returns:
            dict: Context for rendering new_term.html.
        """

        remaining = summary.remaining_support_for_carryover

        form = form or NewTermForm(
            initial={
                "monthly_hours": term.monthly_hours,
                "monthly_minutes": term.monthly_minutes,
            },
            unresolved_purchases=unresolved_purchases,
        )

        # Django templates can't build a dynamic `form.purchase_resolution_5`
        # lookup, so pair each purchase with its already-bound field here.
        purchase_resolution_rows = [
            (
                purchase,
                remaining_minutes,
                form[f"purchase_resolution_{purchase.pk}"],
            )
            for purchase, remaining_minutes in unresolved_purchases
        ]

        return {
            "client": client,
            "retainer": retainer,
            "term": term,
            "summary": summary,
            "remaining": remaining,
            "conv_dev_hours": compute_converted_dev_minutes(remaining, cfg),
            "mig_sup_hours": compute_migrated_support_minutes(remaining, cfg),
            "max_migrate": cfg.max_migrate_hours,
            "purchase_resolution_rows": purchase_resolution_rows,
            "form": form,
            "fmt_hm": fmt_hm,
        }

    def _get_expired(self, pk, retainer_pk, cfg):
        """Loads a retainer's latest term, its summary, and any
        unresolved purchases, if expired.

        Args:
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer.
            cfg (HoursConfig): Business config for hours calculations.

        Returns:
            tuple: `(client, retainer, term, summary,
                unresolved_purchases)`. `term` and `summary` are None
                if the retainer has no term yet, in which case
                `unresolved_purchases` is an empty list.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        term = retainer.current_term

        if not term:
            return client, retainer, None, None, []

        entries = list(term.time_entries.all())
        purchases = list(term.hours_purchases.all())
        summary = calculate_term_hours(term, entries, purchases, cfg)

        allocation = allocate_purchased_hours_usage(
            purchases, summary.purchased_support_used
        )
        unresolved_purchases = [
            (purchase, remaining)
            for purchase, remaining in allocation
            if remaining > 0
        ]

        return client, retainer, term, summary, unresolved_purchases

    def get(self, request, pk, retainer_pk):
        """Renders the renewal form for a retainer's expired term.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to renew.

        Returns:
            HttpResponse: Rendered new_term.html, or a redirect to the
                retainer's detail page if there's no term or the
                current term hasn't expired yet.
        """

        cfg = get_hours_config()
        client, retainer, term, summary, unresolved_purchases = (
            self._get_expired(pk, retainer_pk, cfg)
        )

        if not term or summary.status != "expired":
            return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

        return render(
            request,
            "new_term.html",
            self._get_context(
                client, retainer, term, summary, cfg, unresolved_purchases
            ),
        )

    def post(self, request, pk, retainer_pk):
        """Validates the renewal form and creates the new term.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to renew.

        Returns:
            HttpResponse: Redirect to the retainer's detail page on
                success or if renewal isn't applicable, otherwise the
                form re-rendered with errors.
        """

        cfg = get_hours_config()
        client, retainer, term, summary, unresolved_purchases = (
            self._get_expired(pk, retainer_pk, cfg)
        )

        if not term or summary.status != "expired":
            return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

        form = NewTermForm(
            request.POST, unresolved_purchases=unresolved_purchases
        )

        if not form.is_valid():
            return render(
                request,
                "new_term.html",
                self._get_context(
                    client,
                    retainer,
                    term,
                    summary,
                    cfg,
                    unresolved_purchases,
                    form,
                ),
            )

        carry_type = form.cleaned_data["carry_over_type"]
        monthly_hours = form.cleaned_data["monthly_hours"]
        monthly_minutes = form.cleaned_data["monthly_minutes"]
        remaining = summary.remaining_support_for_carryover

        dev_hours_from_conversion, dev_minutes_from_conversion = 0, 0
        migrated_support_hours, migrated_support_minutes = 0, 0

        if carry_type == ClientTerm.CARRY_CONVERT_DEV:
            dev_hours_from_conversion, dev_minutes_from_conversion = (
                minutes_to_hm(compute_converted_dev_minutes(remaining, cfg))
            )
        elif carry_type == ClientTerm.CARRY_MIGRATE:
            migrated_support_hours, migrated_support_minutes = minutes_to_hm(
                compute_migrated_support_minutes(remaining, cfg)
            )

        new_start = term.end_date + timedelta(days=1)
        new_end = add_months(new_start, cfg.term_months) - timedelta(days=1)

        new_term = ClientTerm.objects.create(
            retainer=retainer,
            term_number=term.term_number + 1,
            start_date=new_start,
            end_date=new_end,
            monthly_hours=monthly_hours,
            monthly_minutes=monthly_minutes,
            carry_over_type=carry_type,
            dev_hours_from_conversion=dev_hours_from_conversion,
            dev_minutes_from_conversion=dev_minutes_from_conversion,
            migrated_support_hours=migrated_support_hours,
            migrated_support_minutes=migrated_support_minutes,
        )

        self._resolve_purchases(
            unresolved_purchases, form, new_term, term.term_number
        )

        return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

    def _resolve_purchases(
        self, unresolved_purchases, form, new_term, old_term_number
    ):
        """Applies each unresolved purchase's chosen disposition.

        Args:
            unresolved_purchases (list[tuple[HoursPurchase, int]]):
                `(purchase, remaining_minutes)` pairs from the expiring
                term.
            form (NewTermForm): Validated form holding each purchase's
                `purchase_resolution_<pk>` choice.
            new_term (ClientTerm): The newly-created term to carry
                unused hours forward onto, if chosen.
            old_term_number (int): Term number of the expiring term,
                for the carry-forward note.
        """

        for purchase, remaining_minutes in unresolved_purchases:
            resolution = form.cleaned_data[f"purchase_resolution_{purchase.pk}"]
            purchase.resolution = resolution
            purchase.save(update_fields=["resolution"])

            if resolution == HoursPurchase.CARRIED_FORWARD:
                carry_hours, carry_minutes = minutes_to_hm(remaining_minutes)
                HoursPurchase.objects.create(
                    term=new_term,
                    hours=carry_hours,
                    minutes=carry_minutes,
                    invoice_ref=purchase.invoice_ref,
                    notes=f"Carried forward from term {old_term_number}",
                )
