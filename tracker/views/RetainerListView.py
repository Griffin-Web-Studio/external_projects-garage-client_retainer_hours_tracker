from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from tracker.queries import urgent_retainers


class RetainerListView(LoginRequiredMixin, View):
    """View listing every active retainer, most urgent first."""

    def get(self, request):
        """Renders the retainers list page.

        Args:
            request (HttpRequest): Incoming GET request.

        Returns:
            HttpResponse: Rendered retainer_list.html with every active
                retainer, ranked most urgent first.
        """

        return render(
            request,
            "retainer_list.html",
            {"retainer_data": urgent_retainers()},
        )
