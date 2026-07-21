from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tracker.forms import EditWorkOrderForm
from tracker.models import Client, Retainer, WorkOrder


class EditWorkOrderView(LoginRequiredMixin, View):
    """View for editing an existing work order's title and description."""

    def get(self, request, pk, retainer_pk, wo_pk):
        """Renders the work order form pre-filled with its current values.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the work order to edit.

        Returns:
            HttpResponse: Rendered client_form.html pre-filled for
                editing.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        work_order = get_object_or_404(
            WorkOrder, pk=wo_pk, retainer_id=retainer_pk
        )
        form = EditWorkOrderForm(
            initial={
                "title": work_order.title,
                "description": work_order.description,
            }
        )

        return render(
            request,
            "client_form.html",
            self._context(client, retainer, work_order, form),
        )

    def post(self, request, pk, retainer_pk, wo_pk):
        """Validates and applies the submitted changes to the work order.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the work order to edit.

        Returns:
            HttpResponse: Redirect to the work order's detail page on
                success, otherwise the form re-rendered with errors.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        work_order = get_object_or_404(
            WorkOrder, pk=wo_pk, retainer_id=retainer_pk
        )
        form = EditWorkOrderForm(request.POST)

        if form.is_valid():
            work_order.title = form.cleaned_data["title"]
            work_order.description = form.cleaned_data["description"]
            work_order.save()

            return redirect(
                "work-order-detail",
                pk=pk,
                retainer_pk=retainer_pk,
                wo_pk=work_order.pk,
            )

        return render(
            request,
            "client_form.html",
            self._context(client, retainer, work_order, form),
        )

    def _context(self, client, retainer, work_order, form):
        """Builds the shared client_form.html context.

        Args:
            client (Client): Retainer's owning client.
            retainer (Retainer): Work order's owning retainer.
            work_order (WorkOrder): Work order being edited.
            form (EditWorkOrderForm): Bound or unbound form to render.

        Returns:
            dict: Context for rendering client_form.html.
        """

        return {
            "form": form,
            "title": f"Edit - {work_order.title}",
            "submit_label": "Save Changes",
            "back_url": (
                f"/clients/{client.pk}/retainers/{retainer.pk}/"
                f"work-orders/{work_order.pk}/"
            ),
        }
