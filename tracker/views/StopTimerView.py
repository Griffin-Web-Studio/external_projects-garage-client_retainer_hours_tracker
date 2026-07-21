from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View

from tracker.models import WorkOrderItem
from tracker.timers import enforce_caps, status_payload


class StopTimerView(LoginRequiredMixin, View):
    """JSON endpoint for pausing a checklist item's timer."""

    def post(self, request, pk, retainer_pk, wo_pk, item_pk):
        """Ends the item's active timer segment, leaving it paused (not
        completed) - it can be resumed later.

        Args:
            request (HttpRequest): Incoming POST request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the owning work order.
            item_pk (int): Primary key of the checklist item to stop.

        Returns:
            JsonResponse: The item's timer status on success (200), or
                a 403 `{"error": ...}` body if the requesting employee
                isn't the item's owner.
        """

        item = get_object_or_404(
            WorkOrderItem,
            pk=item_pk,
            work_order_id=wo_pk,
            work_order__retainer_id=retainer_pk,
            work_order__retainer__client_id=pk,
        )

        if item.owner_id != request.user.pk:
            return JsonResponse(
                {
                    "error": "Only the employee who started this item can stop it."
                },
                status=403,
            )

        segment = item.segments.filter(ended_at__isnull=True).first()

        if segment is not None:
            segment.ended_at = timezone.now()
            segment.save()

        if item.status == WorkOrderItem.STATUS_RUNNING:
            item.status = WorkOrderItem.STATUS_PAUSED
            item.save()

        status = enforce_caps(item)

        return JsonResponse(status_payload(item, status))
