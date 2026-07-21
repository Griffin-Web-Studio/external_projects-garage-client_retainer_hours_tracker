from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from tracker.models import WorkOrderItem
from tracker.timers import enforce_caps, status_payload


class TimerStatusView(LoginRequiredMixin, View):
    """JSON endpoint for polling a checklist item's live timer status."""

    def get(self, request, pk, retainer_pk, wo_pk, item_pk):
        """Returns the item's current elapsed time and cap status.

        Enforces caps as a side effect (see `tracker.timers.enforce_caps`)
        so a cap can't be exceeded just because the client hasn't
        polled recently - any employee can poll, not just the item's
        owner, since this is read-only.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the owning work order.
            item_pk (int): Primary key of the checklist item to check.

        Returns:
            JsonResponse: The item's current timer status.
        """

        item = get_object_or_404(
            WorkOrderItem,
            pk=item_pk,
            work_order_id=wo_pk,
            work_order__retainer_id=retainer_pk,
            work_order__retainer__client_id=pk,
        )
        status = enforce_caps(item)

        return JsonResponse(status_payload(item, status))
