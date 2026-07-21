from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from tracker.models import Client, Retainer


class WorkOrderListView(LoginRequiredMixin, View):
    """View for listing a retainer's work orders."""

    def get(self, request, pk, retainer_pk):
        """Renders the retainer's work orders, most recent first.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to list work
                orders for.

        Returns:
            HttpResponse: Rendered work_order_list.html.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        work_orders = retainer.work_orders.all()

        return render(
            request,
            "work_order_list.html",
            {
                "client": client,
                "retainer": retainer,
                "work_orders": work_orders,
            },
        )
