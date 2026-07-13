from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from tracker.hours import calculate_term_hours, get_hours_config
from tracker.models import Client


class ClientDetailView(LoginRequiredMixin, View):
    """View for a client's overview - info, edit/delete, and a status
    card per retainer.
    """

    def get(self, request, pk):
        """Renders the client overview page.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the client to display.

        Returns:
            HttpResponse: Rendered client_detail.html with the client's
                info and one status card per retainer.
        """

        client = get_object_or_404(Client, pk=pk)
        cfg = get_hours_config()
        retainer_data = []

        for retainer in client.retainers.order_by("name"):
            retainer.client = client  # avoid a re-fetch in _retainer_card.html
            term = retainer.current_term
            summary = None

            if term:
                entries = list(term.time_entries.all())
                purchases = list(term.hours_purchases.all())
                summary = calculate_term_hours(term, entries, purchases, cfg)

            retainer_data.append((retainer, term, summary))

        return render(
            request,
            "client_detail.html",
            {"client": client, "retainer_data": retainer_data},
        )
