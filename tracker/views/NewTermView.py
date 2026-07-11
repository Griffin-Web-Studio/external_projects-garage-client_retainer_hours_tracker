from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tracker.forms import NewTermForm
from tracker.hours import (
    add_months,
    calculate_term_hours,
    compute_converted_dev_minutes,
    compute_migrated_support_minutes,
    fmt_hm,
    get_hours_config,
    minutes_to_hm,
)
from tracker.models import Client, ClientTerm


class NewTermView(LoginRequiredMixin, View):
    """View for renewing a client's expired term with a carryover choice."""

    def _get_context(self, client, term, summary, cfg, form=None):
        """Builds the template context shared by GET and POST.

        Args:
            client (Client): Client whose term is being renewed.
            term (ClientTerm): The expired term being renewed.
            summary (ExpiredTermSummary): Hours summary for `term`.
            cfg (HoursConfig): Business config for hours calculations.
            form (NewTermForm | None, optional): Bound form to
                re-render with validation errors. Defaults to None, in
                which case a fresh unbound form is built.

        Returns:
            dict: Context for rendering new_term.html.
        """

        remaining = summary.remaining_support_for_carryover

        return {
            "client": client,
            "term": term,
            "summary": summary,
            "remaining": remaining,
            "conv_dev_hours": compute_converted_dev_minutes(remaining, cfg),
            "mig_sup_hours": compute_migrated_support_minutes(remaining, cfg),
            "max_migrate": cfg.max_migrate_hours,
            "form": form
            or NewTermForm(
                initial={
                    "monthly_hours": term.monthly_hours,
                    "monthly_minutes": term.monthly_minutes,
                }
            ),
            "fmt_hm": fmt_hm,
        }

    def _get_expired(self, pk, cfg):
        """Loads a client's latest term and its summary, if expired.

        Args:
            pk (int): Primary key of the client.
            cfg (HoursConfig): Business config for hours calculations.

        Returns:
            tuple: `(client, term, summary)`. `term` and `summary` are
                None if the client has no term yet.
        """

        client = get_object_or_404(Client, pk=pk)
        term = client.terms.order_by("-term_number").first()

        if not term:
            return client, None, None

        entries = list(term.time_entries.all())
        summary = calculate_term_hours(term, entries, cfg)

        return client, term, summary

    def get(self, request, pk):
        """Renders the renewal form for a client's expired term.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the client to renew.

        Returns:
            HttpResponse: Rendered new_term.html, or a redirect to the
                client's detail page if there's no term or the current
                term hasn't expired yet.
        """

        cfg = get_hours_config()
        client, term, summary = self._get_expired(pk, cfg)

        if not term or summary.status != "expired":
            return redirect("client-detail", pk=pk)

        return render(
            request,
            "new_term.html",
            self._get_context(client, term, summary, cfg),
        )

    def post(self, request, pk):
        """Validates the renewal form and creates the new term.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the client to renew.

        Returns:
            HttpResponse: Redirect to the client's detail page on
                success or if renewal isn't applicable, otherwise the
                form re-rendered with errors.
        """

        cfg = get_hours_config()
        client, term, summary = self._get_expired(pk, cfg)

        if not term or summary.status != "expired":
            return redirect("client-detail", pk=pk)

        form = NewTermForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "new_term.html",
                self._get_context(client, term, summary, cfg, form),
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
        new_end = add_months(new_start, cfg.term_months)

        ClientTerm.objects.create(
            client=client,
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

        return redirect("client-detail", pk=pk)
