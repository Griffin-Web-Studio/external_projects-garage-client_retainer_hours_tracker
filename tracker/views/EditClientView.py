from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tracker.forms import EditClientForm
from tracker.models import Client


class EditClientView(LoginRequiredMixin, View):
    """View for editing an existing client's name, notes, and status."""

    def get(self, request, pk):
        """Renders the client form pre-filled with the client's values.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the client to edit.

        Returns:
            HttpResponse: Rendered client_form.html pre-filled for
                editing.
        """

        client = get_object_or_404(Client, pk=pk)
        form = EditClientForm(
            initial={
                "name": client.name,
                "notes": client.notes,
                "is_active": "true" if client.is_active else "false",
            }
        )

        return render(request, "client_form.html", self._context(client, form))

    def post(self, request, pk):
        """Validates and applies the submitted changes to the client.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the client to edit.

        Returns:
            HttpResponse: Redirect to the client's detail page on
                success, otherwise the form re-rendered with errors.
        """

        client = get_object_or_404(Client, pk=pk)
        form = EditClientForm(request.POST)

        if form.is_valid():
            client.name = form.cleaned_data["name"]
            client.notes = form.cleaned_data.get("notes") or ""
            client.is_active = form.cleaned_data["is_active"] == "true"
            client.save()

            return redirect("client-detail", pk=client.pk)

        return render(request, "client_form.html", self._context(client, form))

    def _context(self, client, form):
        """Builds the shared client_form.html context.

        Args:
            client (Client): Client being edited.
            form (EditClientForm): Bound or unbound form to render.

        Returns:
            dict: Context for rendering client_form.html.
        """

        return {
            "form": form,
            "title": f"Edit - {client.name}",
            "submit_label": "Save Changes",
            "back_url": f"/clients/{client.pk}/",
        }
