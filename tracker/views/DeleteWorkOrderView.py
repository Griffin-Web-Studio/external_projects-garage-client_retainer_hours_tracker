from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tracker.models import WorkOrder, WorkOrderItem


class DeleteWorkOrderView(LoginRequiredMixin, View):
    """View for permanently deleting a work order and its checklist."""

    def post(self, request, pk, retainer_pk, wo_pk):
        """Deletes the work order, unless a checklist item's timer has
        already been started.

        Args:
            request (HttpRequest): Incoming POST request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the work order to delete.

        Returns:
            HttpResponse: Redirect to the retainer's work order list on
                success, otherwise back to the work order's detail page
                with an error message.
        """

        work_order = get_object_or_404(
            WorkOrder, pk=wo_pk, retainer_id=retainer_pk
        )

        if work_order.items.exclude(
            status=WorkOrderItem.STATUS_NOT_STARTED
        ).exists():
            messages.error(
                request,
                "Can't delete a work order once any of its checklist "
                "items have been started.",
            )
            return redirect(
                "work-order-detail", pk=pk, retainer_pk=retainer_pk, wo_pk=wo_pk
            )

        work_order.delete()

        return redirect("work-order-list", pk=pk, retainer_pk=retainer_pk)
