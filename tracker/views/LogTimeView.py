from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tracker.forms import LogTimeForm
from tracker.models import Client, TimeEntry


class LogTimeView(LoginRequiredMixin, View):
    """View for logging a time entry against a client's active term."""

    def get(self, request, pk):
        """Renders a blank time-entry form for the client's current term.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the client to log time against.

        Returns:
            HttpResponse: Rendered log_time.html with a blank form.
        """

        client = get_object_or_404(Client, pk=pk)

        return render(
            request,
            "log_time.html",
            {
                "client": client,
                "term": client.terms.order_by("-term_number").first(),
                "form": LogTimeForm(
                    initial={"date": date.today(), "type": "SUPPORT"}
                ),
                "back_url": f"/clients/{client.pk}/",
            },
        )

    def post(self, request, pk):
        """Validates the submitted form and creates the time entry.

        The entry is attached to whichever term's date range actually
        covers the entered date - not necessarily the client's current
        term. Dates that predate every term (e.g. historical work logged
        for a client who existed before being tracked here) are saved
        with no term and excluded from every term's hour totals.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the client to log time against.

        Returns:
            HttpResponse: Redirect to the detail page of the term the
                entry landed in (or the client's current term page if it
                has no matching term) on success or if the client has no
                term at all, otherwise the form re-rendered with errors.
        """

        client = get_object_or_404(Client, pk=pk)
        current_term = client.terms.order_by("-term_number").first()
        form = LogTimeForm(request.POST)

        if not current_term:
            return redirect("client-detail", pk=pk)

        if form.is_valid():
            entry_date = form.cleaned_data["date"]
            matched_term = client.term_for_date(entry_date)

            TimeEntry.objects.create(
                client=client,
                term=matched_term,
                employee=request.user,
                date=entry_date,
                hours=form.cleaned_data["hours"],
                minutes=form.cleaned_data["minutes"],
                type=form.cleaned_data["type"],
                description=form.cleaned_data["description"],
            )

            if matched_term and matched_term.pk != current_term.pk:
                return redirect(
                    "client-detail-term",
                    pk=pk,
                    term_number=matched_term.term_number,
                )

            return redirect("client-detail", pk=pk)

        return render(
            request,
            "log_time.html",
            {
                "client": client,
                "term": current_term,
                "form": form,
                "back_url": f"/clients/{client.pk}/",
            },
        )
