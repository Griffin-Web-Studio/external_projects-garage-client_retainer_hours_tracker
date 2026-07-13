from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tracker.forms import BillOverageForm
from tracker.hours import get_hours_config, term_unbilled_overage
from tracker.models import Client, OverageBilling, Retainer
from tracker.views.RetainerDetailView import RetainerDetailView


class BillOverageView(LoginRequiredMixin, View):
    """View for recording an overage billing against a retainer's term."""

    def post(self, request, pk, retainer_pk, term_number=None):
        """Validates the submitted form and records the overage billing.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer being billed.
            term_number (int | None, optional): Term to bill against.
                Defaults to None, in which case the retainer's current
                (latest) term is billed.

        Returns:
            HttpResponse: Redirect to the billed term's detail page on
                success or if the retainer has no term, otherwise the
                retainer detail page re-rendered with the bill form
                errors.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)

        if term_number is not None:
            term = get_object_or_404(retainer.terms, term_number=term_number)
        else:
            term = retainer.current_term

        if not term:
            return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

        max_unbilled = term_unbilled_overage(term, get_hours_config())
        form = BillOverageForm(request.POST, max_unbilled=max_unbilled)

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
                    "retainer-detail-term",
                    pk=pk,
                    retainer_pk=retainer_pk,
                    term_number=term_number,
                )

            return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

        return RetainerDetailView()._render(
            request, pk, retainer_pk, bill_form=form, term_number=term_number
        )
