from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from tracker.models import Client, Retainer, WorkOrder


class WorkOrderDetailView(LoginRequiredMixin, View):
    """View for a work order's checklist and timer controls."""

    def get(self, request, pk, retainer_pk, wo_pk):
        """Renders the work order's checklist.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the work order to display.

        Returns:
            HttpResponse: Rendered work_order_detail.html.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        work_order = get_object_or_404(
            WorkOrder, pk=wo_pk, retainer_id=retainer_pk
        )
        items = work_order.items.select_related("owner").all()

        return render(
            request,
            "work_order_detail.html",
            {
                "client": client,
                "retainer": retainer,
                "work_order": work_order,
                "items": items,
            },
        )
