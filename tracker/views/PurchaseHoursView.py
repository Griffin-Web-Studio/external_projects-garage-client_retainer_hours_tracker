from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tracker.forms import HoursPurchaseForm
from tracker.models import HoursPurchase, Retainer
from tracker.views.RetainerDetailView import RetainerDetailView


class PurchaseHoursView(LoginRequiredMixin, View):
    """View for recording a purchase of extra buffer support hours
    against a retainer's current term.
    """

    def post(self, request, pk, retainer_pk):
        """Validates the submitted form and records the purchase.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer being
                purchased for.

        Returns:
            HttpResponse: Redirect to the retainer's detail page on
                success or if the retainer has no term, otherwise the
                retainer detail page re-rendered with the form errors.
        """

        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        term = retainer.current_term

        if not term:
            return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

        form = HoursPurchaseForm(request.POST)

        if form.is_valid():
            HoursPurchase.objects.create(
                term=term,
                hours=form.cleaned_data["hours"],
                minutes=form.cleaned_data["minutes"],
                invoice_ref=form.cleaned_data.get("invoice_ref") or "",
                notes=form.cleaned_data.get("notes") or "",
            )

            return redirect("retainer-detail", pk=pk, retainer_pk=retainer_pk)

        return RetainerDetailView()._render(
            request, pk, retainer_pk, purchase_form=form
        )
