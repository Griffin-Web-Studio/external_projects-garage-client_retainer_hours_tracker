from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View

from tracker.hours import get_hours_config
from tracker.models import TimerSegment, WorkOrderItem
from tracker.timers import (
    daily_dev_minutes_used,
    enforce_caps,
    item_elapsed_minutes,
    status_payload,
)


class StartTimerView(LoginRequiredMixin, View):
    """JSON endpoint for starting (or resuming) a checklist item's timer."""

    def post(self, request, pk, retainer_pk, wo_pk, item_pk):
        """Starts or resumes the item's timer for the requesting employee.

        Args:
            request (HttpRequest): Incoming POST request. `billing_type`
                is read from POST data - only required (and used) the
                first time an item is started.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the owning work order.
            item_pk (int): Primary key of the checklist item to start.

        Returns:
            JsonResponse: The item's timer status on success (200), or
                an `{"error": ...}` body on failure - 400 for a missing/
                invalid billing type, 409 for a conflicting state (item
                completed, owned by someone else, at a cap, or the
                employee already has another timer running).
        """

        item = get_object_or_404(
            WorkOrderItem,
            pk=item_pk,
            work_order_id=wo_pk,
            work_order__retainer_id=retainer_pk,
            work_order__retainer__client_id=pk,
        )
        cfg = get_hours_config()

        if item.status == WorkOrderItem.STATUS_COMPLETED:
            return JsonResponse(
                {"error": "This item is already completed."}, status=409
            )

        if item.owner_id is not None and item.owner_id != request.user.pk:
            return JsonResponse(
                {
                    "error": (
                        f"This item is already in progress by "
                        f"{item.owner.name}."
                    )
                },
                status=409,
            )

        if TimerSegment.objects.filter(
            employee=request.user, ended_at__isnull=True
        ).exists():
            return JsonResponse(
                {
                    "error": (
                        "You already have another timer running. Stop it "
                        "before starting a new one."
                    )
                },
                status=409,
            )

        billing_type = item.billing_type or request.POST.get("billing_type")

        if billing_type not in dict(WorkOrderItem.TYPE_CHOICES):
            return JsonResponse(
                {"error": "Choose a billing type to start this item's timer."},
                status=400,
            )

        if billing_type == WorkOrderItem.TYPE_SUPPORT:
            elapsed = item_elapsed_minutes(item)

            if elapsed >= cfg.max_support_minutes_per_task:
                return JsonResponse(
                    {
                        "error": (
                            "This item hit the support cap - confirm "
                            "overage to continue."
                        )
                    },
                    status=409,
                )

        if billing_type == WorkOrderItem.TYPE_DEVELOPMENT:
            max_daily_minutes = round(cfg.max_dev_hours_per_day * 60)

            if daily_dev_minutes_used(request.user) >= max_daily_minutes:
                return JsonResponse(
                    {"error": "You've reached today's development hour limit."},
                    status=409,
                )

        item.billing_type = billing_type
        item.owner = request.user
        item.status = WorkOrderItem.STATUS_RUNNING
        item.save()

        TimerSegment.objects.create(
            item=item, employee=request.user, started_at=timezone.now()
        )

        status = enforce_caps(item, cfg)

        return JsonResponse(status_payload(item, status))
