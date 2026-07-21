import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from tracker.hours import get_hours_config
from tracker.models import Client, Retainer, WorkOrder
from tracker.timers import enforce_caps, status_payload


class WorkOrderDetailView(LoginRequiredMixin, View):
    """View for a work order's checklist and timer controls."""

    def get(self, request, pk, retainer_pk, wo_pk):
        """Renders the work order's checklist.

        Each item's timer status is computed (and, if a cap has been
        crossed since it was last checked, enforced) at render time via
        `tracker.timers.enforce_caps`, so the initial server-rendered
        page is always accurate - the timer JS then keeps it live via
        polling from there.

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
        cfg = get_hours_config()
        rows = []

        for item in items:
            payload = status_payload(item, enforce_caps(item, cfg))
            rows.append(
                {
                    "item": item,
                    "status_json": json.dumps(payload),
                    "elapsed_minutes": payload["elapsed_minutes"],
                }
            )

        return render(
            request,
            "work_order_detail.html",
            {
                "client": client,
                "retainer": retainer,
                "work_order": work_order,
                "rows": rows,
                "reminder_minutes": ",".join(
                    str(m) for m in cfg.timer_reminder_minutes
                ),
                "current_employee_id": request.user.pk,
            },
        )
