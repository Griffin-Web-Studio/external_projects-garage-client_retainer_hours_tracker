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

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the client to log time against.

        Returns:
            HttpResponse: Redirect to the client's detail page on
                success or if the client has no term, otherwise the
                form re-rendered with errors.
        """

        client = get_object_or_404(Client, pk=pk)
        term = client.terms.order_by("-term_number").first()
        form = LogTimeForm(request.POST)

        if not term:
            return redirect("client-detail", pk=pk)

        if form.is_valid():
            TimeEntry.objects.create(
                client=client,
                term=term,
                employee=request.user,
                date=form.cleaned_data["date"],
                hours=form.cleaned_data["hours"],
                type=form.cleaned_data["type"],
                description=form.cleaned_data["description"],
            )

            return redirect("client-detail", pk=pk)

        return render(
            request,
            "log_time.html",
            {
                "client": client,
                "term": term,
                "form": form,
                "back_url": f"/clients/{client.pk}/",
            },
        )
