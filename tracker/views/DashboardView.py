from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import render
from django.views import View

from tracker.models import Client
from tracker.queries import urgent_retainers

DASHBOARD_RETAINER_LIMIT = 6


class DashboardView(LoginRequiredMixin, View):
    """View listing active clients and the most urgent active retainers."""

    def get(self, request):
        """Renders the dashboard.

        Args:
            request (HttpRequest): Incoming GET request.

        Returns:
            HttpResponse: Rendered dashboard/dashboard.html with a
                client card grid (active clients + their retainer
                count) and the top `DASHBOARD_RETAINER_LIMIT` most
                urgent active retainers.
        """

        clients = Client.objects.filter(is_active=True).annotate(
            retainer_count=Count("retainers")
        )
        retainer_data = urgent_retainers()
        overage_count = 0
        low_count = 0

        for _, _, summary in retainer_data:
            if summary.status != "active":
                continue

            if summary.hours_status == "overage":
                overage_count += 1
            elif summary.hours_status == "low":
                low_count += 1

        return render(
            request,
            "dashboard/dashboard.html",
            {
                "clients": clients,
                "retainer_data": retainer_data[:DASHBOARD_RETAINER_LIMIT],
                "retainer_total": len(retainer_data),
                "overage_count": overage_count,
                "low_count": low_count,
            },
        )
