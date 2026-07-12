from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tracker.models import Retainer


class DeleteRetainerView(LoginRequiredMixin, View):
    """View for permanently deleting a retainer and all its data."""

    def post(self, request, pk, retainer_pk):
        """Deletes the retainer and redirects to its client's overview.

        Args:
            request (HttpRequest): Incoming POST request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to delete.

        Returns:
            HttpResponse: Redirect to the owning client's detail page.
        """

        get_object_or_404(Retainer, pk=retainer_pk, client_id=pk).delete()

        return redirect("client-detail", pk=pk)
