from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.shortcuts import render
from django.views import View

from tracker.models import Client


class ClientListView(LoginRequiredMixin, View):
    """View listing every client, active or not, with their retainer
    count.
    """

    def get(self, request):
        """Renders the clients list page.

        Args:
            request (HttpRequest): Incoming GET request.

        Returns:
            HttpResponse: Rendered client_list.html with every client
                and its retainer count.
        """

        clients = Client.objects.annotate(retainer_count=Count("retainers"))

        return render(request, "client_list.html", {"clients": clients})
