from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tracker.forms import EditRetainerForm
from tracker.models import Client, Retainer


class EditRetainerView(LoginRequiredMixin, View):
    """View for editing an existing retainer's name and status."""

    def get(self, request, pk, retainer_pk):
        """Renders the retainer form pre-filled with its current values.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to edit.

        Returns:
            HttpResponse: Rendered client_form.html pre-filled for
                editing.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        form = EditRetainerForm(
            initial={
                "name": retainer.name,
                "is_active": "true" if retainer.is_active else "false",
            }
        )

        return render(
            request, "client_form.html", self._context(client, retainer, form)
        )

    def post(self, request, pk, retainer_pk):
        """Validates and applies the submitted changes to the retainer.

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the retainer to edit.

        Returns:
            HttpResponse: Redirect to the retainer's detail page on
                success, otherwise the form re-rendered with errors.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        form = EditRetainerForm(request.POST)

        if form.is_valid():
            retainer.name = form.cleaned_data["name"]
            retainer.is_active = form.cleaned_data["is_active"] == "true"
            retainer.save()

            return redirect(
                "retainer-detail", pk=client.pk, retainer_pk=retainer.pk
            )

        return render(
            request, "client_form.html", self._context(client, retainer, form)
        )

    def _context(self, client, retainer, form):
        """Builds the shared client_form.html context.

        Args:
            client (Client): Retainer's owning client.
            retainer (Retainer): Retainer being edited.
            form (EditRetainerForm): Bound or unbound form to render.

        Returns:
            dict: Context for rendering client_form.html.
        """

        return {
            "form": form,
            "title": f"Edit - {retainer.name}",
            "submit_label": "Save Changes",
            "back_url": f"/clients/{client.pk}/retainers/{retainer.pk}/",
        }
