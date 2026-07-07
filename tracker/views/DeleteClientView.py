from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tracker.models import Client


class DeleteClientView(LoginRequiredMixin, View):
    """View for permanently deleting a client and all their data."""

    def post(self, request, pk):
        """Deletes the client and redirects to the dashboard.

        Args:
            request (HttpRequest): Incoming POST request.
            pk (int): Primary key of the client to delete.

        Returns:
            HttpResponse: Redirect to the dashboard.
        """

        get_object_or_404(Client, pk=pk).delete()

        return redirect("dashboard")
