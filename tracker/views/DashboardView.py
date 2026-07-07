from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from tracker.hours import calculate_term_hours, get_hours_config
from tracker.models import Client


class DashboardView(LoginRequiredMixin, View):
    """View listing active clients with their current term status."""

    def get(self, request):
        """Renders the dashboard with per-client hours summaries.

        Args:
            request (HttpRequest): Incoming GET request.

        Returns:
            HttpResponse: Rendered dashboard/dashboard.html with one
                entry per active client (its current term and hours
                summary, if any), plus counts of clients in overage or
                running low on hours.
        """

        cfg = get_hours_config()
        client_data = []
        overage_count = 0
        low_count = 0

        for client in Client.objects.filter(is_active=True):
            term = client.terms.order_by("-term_number").first()
            summary = None

            if term:
                entries = list(term.time_entries.all())
                summary = calculate_term_hours(term, entries, cfg)

                if summary.status == "active":
                    if summary.hours_status == "overage":
                        overage_count += 1
                    elif summary.hours_status == "low":
                        low_count += 1

            client_data.append(
                {"client": client, "term": term, "summary": summary}
            )

        return render(
            request,
            "dashboard/dashboard.html",
            {
                "client_data": client_data,
                "overage_count": overage_count,
                "low_count": low_count,
            },
        )
