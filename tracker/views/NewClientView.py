from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from tracker.forms import NewClientForm
from tracker.hours import add_months, get_term_months
from tracker.models import Client, ClientTerm, Retainer


class NewClientView(LoginRequiredMixin, View):
    """View for creating a new client, their first retainer, and its
    first contract term.
    """

    def get(self, request):
        """Renders a blank client form.

        Args:
            request (HttpRequest): Incoming GET request.

        Returns:
            HttpResponse: Rendered client_form.html with a blank form.
        """

        return render(request, "client_form.html", self._context())

    def post(self, request):
        """Validates the submitted form and creates the client, its
        first retainer, and that retainer's first term.

        Args:
            request (HttpRequest): Incoming POST request with form data.

        Returns:
            HttpResponse: Redirect to the new retainer's detail page on
                success, otherwise the form re-rendered with errors.
        """

        form = NewClientForm(request.POST)

        if form.is_valid():
            start = form.cleaned_data["start_date"]
            end = add_months(start, get_term_months()) - timedelta(days=1)
            client = Client.objects.create(
                name=form.cleaned_data["name"],
                notes=form.cleaned_data.get("notes") or "",
            )
            retainer = Retainer.objects.create(
                client=client, name=form.cleaned_data["retainer_name"]
            )
            ClientTerm.objects.create(
                retainer=retainer,
                term_number=1,
                start_date=start,
                end_date=end,
                monthly_hours=form.cleaned_data["monthly_hours"],
                monthly_minutes=form.cleaned_data["monthly_minutes"],
                carry_over_type=ClientTerm.CARRY_NONE,
            )

            return redirect(
                "retainer-detail", pk=client.pk, retainer_pk=retainer.pk
            )

        return render(request, "client_form.html", self._context(form))

    def _context(self, form=None):
        """Builds the shared client_form.html context.

        Args:
            form (NewClientForm | None, optional): Bound form to
                re-render with validation errors. Defaults to None, in
                which case a fresh unbound form is built.

        Returns:
            dict: Context for rendering client_form.html.
        """

        return {
            "form": form or NewClientForm(),
            "title": "New Client",
            "intro_text": (
                "Creates the client, their first retainer, and its "
                f"first {get_term_months()}-month term."
            ),
            "submit_label": "Create Client",
            "back_url": "/clients/",
        }
