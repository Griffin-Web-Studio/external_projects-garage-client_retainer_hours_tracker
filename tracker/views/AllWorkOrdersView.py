from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from tracker.queries import ranked_work_orders, work_order_item_progress


class AllWorkOrdersView(LoginRequiredMixin, View):
    """View listing every work order across every client, most
    actionable first (In Progress, then Open, then Completed)."""

    def get(self, request):
        """Renders the company-wide work orders list page.

        Args:
            request (HttpRequest): Incoming GET request.

        Returns:
            HttpResponse: Rendered work_order_list_all.html with every
                work order, ranked most actionable first.
        """

        rows = []

        for wo in ranked_work_orders():
            completed, total = work_order_item_progress(wo)
            rows.append(
                {
                    "work_order": wo,
                    "completed_items": completed,
                    "total_items": total,
                }
            )

        return render(request, "work_order_list_all.html", {"rows": rows})
