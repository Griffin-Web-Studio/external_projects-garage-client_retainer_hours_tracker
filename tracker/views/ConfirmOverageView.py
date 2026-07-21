from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View

from tracker.hours import get_hours_config
from tracker.models import TimerSegment, WorkOrderItem
from tracker.timers import enforce_caps, item_elapsed_minutes, status_payload


class ConfirmOverageView(LoginRequiredMixin, View):
    """JSON endpoint for confirming a Support item's escalation to
    Support + Dev Overage billing once it's hit the support cap."""

    def post(self, request, pk, retainer_pk, wo_pk, item_pk):
        """Flips a capped Support item to Support + Dev Overage and
        resumes its timer.

        Only valid once the item has actually reached the configured
        support cap and is paused there - this is the one case where
        `billing_type` changes after being set on first Start.

        Args:
            request (HttpRequest): Incoming POST request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the owning work order.
            item_pk (int): Primary key of the checklist item to escalate.

        Returns:
            JsonResponse: The item's timer status on success (200), or
                an `{"error": ...}` body on failure - 403 if the
                requesting employee isn't the item's owner, 409 if the
                item isn't a Support item awaiting confirmation or the
                employee already has another timer running.
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
                    "error": (
                        "Only the employee who started this item can "
                        "confirm overage."
                    )
                },
                status=403,
            )

        if item.billing_type != WorkOrderItem.TYPE_SUPPORT:
            return JsonResponse(
                {"error": "This item isn't awaiting overage confirmation."},
                status=409,
            )

        cfg = get_hours_config()
        elapsed = item_elapsed_minutes(item)

        if elapsed < cfg.max_support_minutes_per_task:
            return JsonResponse(
                {"error": "This item hasn't reached the support cap yet."},
                status=409,
            )

        if TimerSegment.objects.filter(
            employee=request.user, ended_at__isnull=True
        ).exists():
            return JsonResponse(
                {
                    "error": (
                        "You already have another timer running. Stop it "
                        "before continuing this one."
                    )
                },
                status=409,
            )

        item.billing_type = WorkOrderItem.TYPE_SUPPORT_DEV_OVERAGE
        item.status = WorkOrderItem.STATUS_RUNNING
        item.save()

        TimerSegment.objects.create(
            item=item, employee=request.user, started_at=timezone.now()
        )

        status = enforce_caps(item, cfg)

        return JsonResponse(status_payload(item, status))
