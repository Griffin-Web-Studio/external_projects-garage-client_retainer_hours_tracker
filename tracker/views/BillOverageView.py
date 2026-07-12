from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tracker.forms import BillOverageForm
from tracker.models import Client, OverageBilling
from tracker.views.ClientDetailView import ClientDetailView


class BillOverageView(LoginRequiredMixin, View):
    """View for recording an overage billing against a client's term."""

    def post(self, request, pk, term_number=None):
        """Validates the submitted form and records the overage billing.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the client being billed.
            term_number (int | None, optional): Term to bill against.
                Defaults to None, in which case the client's current
                (latest) term is billed.

        Returns:
            HttpResponse: Redirect to the billed term's detail page on
                success or if the client has no term, otherwise the
                client detail page re-rendered with the bill form
                errors.
        """

        client = get_object_or_404(Client, pk=pk)

        if term_number is not None:
            term = get_object_or_404(client.terms, term_number=term_number)
        else:
            term = client.terms.order_by("-term_number").first()

        if not term:
            return redirect("client-detail", pk=pk)

        form = BillOverageForm(request.POST)

        if form.is_valid():
            OverageBilling.objects.create(
                client=client,
                term=term,
                type=form.cleaned_data["type"],
                hours_charged=form.cleaned_data["hours_charged"],
                minutes_charged=form.cleaned_data["minutes_charged"],
                invoice_ref=form.cleaned_data.get("invoice_ref") or "",
                notes=form.cleaned_data.get("notes") or "",
            )

            if term_number is not None:
                return redirect(
                    "client-detail-term", pk=pk, term_number=term_number
                )

            return redirect("client-detail", pk=pk)

        return ClientDetailView()._render(
            request, pk, bill_form=form, term_number=term_number
        )
