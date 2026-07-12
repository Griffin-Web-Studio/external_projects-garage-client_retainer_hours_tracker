from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tracker.forms import NewRetainerForm
from tracker.hours import add_months, get_term_months
from tracker.models import Client, ClientTerm, Retainer


class NewRetainerView(LoginRequiredMixin, View):
    """View for adding a new retainer contract to an existing client."""

    def get(self, request, pk):
        """Renders a blank retainer form.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the client to add a retainer to.

        Returns:
            HttpResponse: Rendered client_form.html with a blank form.
        """

        client = get_object_or_404(Client, pk=pk)

        return render(request, "client_form.html", self._context(client))

    def post(self, request, pk):
        """Validates the submitted form and creates the retainer and
        its first term.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the client to add a retainer to.

        Returns:
            HttpResponse: Redirect to the new retainer's detail page on
                success, otherwise the form re-rendered with errors.
        """

        client = get_object_or_404(Client, pk=pk)
        form = NewRetainerForm(request.POST)

        if form.is_valid():
            start = form.cleaned_data["start_date"]
            end = add_months(start, get_term_months())
            retainer = Retainer.objects.create(
                client=client, name=form.cleaned_data["name"]
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

        return render(request, "client_form.html", self._context(client, form))

    def _context(self, client, form=None):
        """Builds the shared client_form.html context.

        Args:
            client (Client): Client the new retainer belongs to.
            form (NewRetainerForm | None, optional): Bound form to
                re-render with validation errors. Defaults to None, in
                which case a fresh unbound form is built.

        Returns:
            dict: Context for rendering client_form.html.
        """

        return {
            "form": form or NewRetainerForm(),
            "title": f"New Retainer - {client.name}",
            "intro_text": (
                "Creates the retainer and its first "
                f"{get_term_months()}-month term."
            ),
            "submit_label": "Create Retainer",
            "back_url": f"/clients/{client.pk}/",
        }
