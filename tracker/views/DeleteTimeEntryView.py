from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tracker.models import TimeEntry


class DeleteTimeEntryView(LoginRequiredMixin, View):
    """View for deleting a single time entry."""

    def post(self, request, pk):
        """Deletes the time entry and redirects to its retainer's
        detail page.

        Args:
            request (HttpRequest): Incoming POST request.
            pk (int): Primary key of the time entry to delete.

        Returns:
            HttpResponse: Redirect to the owning retainer's detail page.
        """

        entry = get_object_or_404(TimeEntry, pk=pk)
        client_pk = entry.client_id
        retainer_pk = entry.retainer_id
        entry.delete()

        return redirect(
            "retainer-detail", pk=client_pk, retainer_pk=retainer_pk
        )
