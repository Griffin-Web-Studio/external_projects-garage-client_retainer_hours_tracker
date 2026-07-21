from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tracker.forms import NewWorkOrderForm
from tracker.models import Client, Retainer, WorkOrder, WorkOrderItem


class NewWorkOrderView(LoginRequiredMixin, View):
    """View for creating a new work order and its checklist items."""

    def get(self, request, pk, retainer_pk):
        """Renders a blank work order form.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to create
                the work order under.

        Returns:
            HttpResponse: Rendered client_form.html with a blank form.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)

        return render(
            request, "client_form.html", self._context(client, retainer)
        )

    def post(self, request, pk, retainer_pk):
        """Validates the submitted form and creates the work order and
        its checklist items.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to create
                the work order under.

        Returns:
            HttpResponse: Redirect to the new work order's detail page
                on success, otherwise the form re-rendered with errors.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        form = NewWorkOrderForm(request.POST)

        if form.is_valid():
            work_order = WorkOrder.objects.create(
                retainer=retainer,
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                created_by=request.user,
            )
            WorkOrderItem.objects.bulk_create(
                WorkOrderItem(work_order=work_order, description=text, order=i)
                for i, text in enumerate(form.cleaned_data["items_text"])
            )

            return redirect(
                "work-order-detail",
                pk=pk,
                retainer_pk=retainer_pk,
                wo_pk=work_order.pk,
            )

        return render(
            request, "client_form.html", self._context(client, retainer, form)
        )

    def _context(self, client, retainer, form=None):
        """Builds the shared client_form.html context.

        Args:
            client (Client): Retainer's owning client.
            retainer (Retainer): Retainer the new work order belongs to.
            form (NewWorkOrderForm | None, optional): Bound form to
                re-render with validation errors. Defaults to None, in
                which case a fresh unbound form is built.

        Returns:
            dict: Context for rendering client_form.html.
        """

        return {
            "form": form or NewWorkOrderForm(),
            "title": f"New Work Order - {retainer.name}",
            "intro_text": "Creates a checklist of tasks the client requested.",
            "submit_label": "Create Work Order",
            "back_url": f"/clients/{client.pk}/retainers/{retainer.pk}/work-orders/",
        }
