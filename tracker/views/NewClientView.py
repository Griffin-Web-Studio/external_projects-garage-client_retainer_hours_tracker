from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from tracker.forms import NewClientForm
from tracker.hours import add_months, get_term_months
from tracker.models import Client, ClientTerm


class NewClientView(LoginRequiredMixin, View):
    """View for creating a new client and their first contract term."""

    def get(self, request):
        """Renders a blank client form.

        Args:
            request (HttpRequest): Incoming GET request.

        Returns:
            HttpResponse: Rendered client_form.html with a blank form.
        """

        return render(
            request,
            "client_form.html",
            {
                "form": NewClientForm(),
                "title": "New Client",
                "back_url": "/dashboard/",
                "term_months": get_term_months(),
            },
        )

    def post(self, request):
        """Validates the submitted form and creates the client and term.

        Args:
            request (HttpRequest): Incoming POST request with form data.

        Returns:
            HttpResponse: Redirect to the new client's detail page on
                success, otherwise the form re-rendered with errors.
        """

        form = NewClientForm(request.POST)

        if form.is_valid():
            start = form.cleaned_data["start_date"]
            end = add_months(start, get_term_months())
            client = Client.objects.create(
                name=form.cleaned_data["name"],
                notes=form.cleaned_data.get("notes") or "",
            )
            ClientTerm.objects.create(
                client=client,
                term_number=1,
                start_date=start,
                end_date=end,
                monthly_hours=form.cleaned_data["monthly_hours"],
                monthly_minutes=form.cleaned_data["monthly_minutes"],
                carry_over_type=ClientTerm.CARRY_NONE,
            )

            return redirect("client-detail", pk=client.pk)

        return render(
            request,
            "client_form.html",
            {
                "form": form,
                "title": "New Client",
                "back_url": "/dashboard/",
                "term_months": get_term_months(),
            },
        )
