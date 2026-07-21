from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from tracker.forms import CompleteWorkOrderItemForm
from tracker.hours import get_hours_config, hm_to_minutes, minutes_to_hm
from tracker.models import Client, Retainer, TimeEntry, WorkOrder, WorkOrderItem
from tracker.timers import item_elapsed_minutes, support_dev_split


class CompleteWorkOrderItemView(LoginRequiredMixin, View):
    """View for reviewing and finalising a checklist item's tracked time.

    Not a one-click action - completing an item is a review-and-adjust
    step, since a timer accidentally left running can inflate the
    recorded time well past what was actually worked. The computed
    elapsed time (split into Support/Development buckets where
    relevant) is shown pre-filled but editable before anything is
    saved as a `TimeEntry`.
    """

    def get(self, request, pk, retainer_pk, wo_pk, item_pk):
        """Stops the item's active segment (if any) and renders the
        review form pre-filled with its computed elapsed time.

        Args:
            request (HttpRequest): Incoming GET request.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the owning work order.
            item_pk (int): Primary key of the checklist item to complete.

        Returns:
            HttpResponse: Rendered client_form.html with the review
                form, or a redirect back to the work order if the item
                can't be completed right now.
        """

        client, retainer, work_order, item = self._lookup(
            pk, retainer_pk, wo_pk, item_pk
        )
        guard_response = self._guard(
            request, client, retainer, work_order, item
        )

        if guard_response:
            return guard_response

        self._stop_active_segment(item)
        form = CompleteWorkOrderItemForm(
            billing_type=item.billing_type, initial=self._initial(item)
        )

        return render(
            request,
            "client_form.html",
            self._context(client, retainer, work_order, item, form),
        )

    def post(self, request, pk, retainer_pk, wo_pk, item_pk):
        """Validates the reviewed durations and creates the resulting
        `TimeEntry` row(s).

        Args:
            request (HttpRequest): Incoming POST request with form data.
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the owning work order.
            item_pk (int): Primary key of the checklist item to complete.

        Returns:
            HttpResponse: Redirect to the work order's detail page on
                success, otherwise the form re-rendered with errors.
        """

        client, retainer, work_order, item = self._lookup(
            pk, retainer_pk, wo_pk, item_pk
        )
        guard_response = self._guard(
            request, client, retainer, work_order, item
        )

        if guard_response:
            return guard_response

        self._stop_active_segment(item)
        form = CompleteWorkOrderItemForm(
            request.POST, billing_type=item.billing_type
        )

        if form.is_valid():
            today = date.today()
            term = retainer.term_for_date(today)
            description = form.cleaned_data["description"]

            if "support_hours" in form.cleaned_data:
                self._create_entry(
                    client,
                    retainer,
                    term,
                    item,
                    TimeEntry.TYPE_SUPPORT,
                    form.cleaned_data["support_hours"],
                    form.cleaned_data["support_minutes"],
                    description,
                )

            if "dev_hours" in form.cleaned_data:
                self._create_entry(
                    client,
                    retainer,
                    term,
                    item,
                    TimeEntry.TYPE_DEVELOPMENT,
                    form.cleaned_data["dev_hours"],
                    form.cleaned_data["dev_minutes"],
                    description,
                )

            item.status = WorkOrderItem.STATUS_COMPLETED
            item.save()

            return redirect(
                "work-order-detail", pk=pk, retainer_pk=retainer_pk, wo_pk=wo_pk
            )

        return render(
            request,
            "client_form.html",
            self._context(client, retainer, work_order, item, form),
        )

    def _lookup(self, pk, retainer_pk, wo_pk, item_pk):
        """Fetches the full client/retainer/work order/item chain.

        Args:
            pk (int): Primary key of the owning client.
            retainer_pk (int): Primary key of the owning retainer.
            wo_pk (int): Primary key of the owning work order.
            item_pk (int): Primary key of the checklist item.

        Returns:
            tuple[Client, Retainer, WorkOrder, WorkOrderItem]: The
                looked-up objects.
        """

        client = get_object_or_404(Client, pk=pk)
        retainer = get_object_or_404(Retainer, pk=retainer_pk, client_id=pk)
        work_order = get_object_or_404(
            WorkOrder, pk=wo_pk, retainer_id=retainer_pk
        )
        item = get_object_or_404(WorkOrderItem, pk=item_pk, work_order_id=wo_pk)

        return client, retainer, work_order, item

    def _guard(self, request, client, retainer, work_order, item):
        """Blocks completing an item that hasn't started, is already
        done, or is owned by someone else.

        Args:
            request (HttpRequest): Incoming request.
            client (Client): Item's owning client.
            retainer (Retainer): Item's owning retainer.
            work_order (WorkOrder): Item's owning work order.
            item (WorkOrderItem): Item being completed.

        Returns:
            HttpResponse | None: A redirect back to the work order if
                completion isn't allowed right now, otherwise None.
        """

        if item.status == WorkOrderItem.STATUS_NOT_STARTED:
            messages.error(
                request, "Start this item's timer before completing it."
            )
            return redirect(
                "work-order-detail",
                pk=client.pk,
                retainer_pk=retainer.pk,
                wo_pk=work_order.pk,
            )

        if item.status == WorkOrderItem.STATUS_COMPLETED:
            return redirect(
                "work-order-detail",
                pk=client.pk,
                retainer_pk=retainer.pk,
                wo_pk=work_order.pk,
            )

        if item.owner_id is not None and item.owner_id != request.user.pk:
            messages.error(
                request, f"This item is being tracked by {item.owner.name}."
            )
            return redirect(
                "work-order-detail",
                pk=client.pk,
                retainer_pk=retainer.pk,
                wo_pk=work_order.pk,
            )

        return None

    def _stop_active_segment(self, item):
        """Ends the item's active timer segment, if any.

        Args:
            item (WorkOrderItem): Item whose active segment (if any)
                should be stopped.
        """

        segment = item.segments.filter(ended_at__isnull=True).first()

        if segment is not None:
            segment.ended_at = timezone.now()
            segment.save()

            if item.status == WorkOrderItem.STATUS_RUNNING:
                item.status = WorkOrderItem.STATUS_PAUSED
                item.save()

    def _initial(self, item):
        """Builds the review form's initial values from computed elapsed time.

        Args:
            item (WorkOrderItem): Item to compute initial values for.

        Returns:
            dict: Initial values for `CompleteWorkOrderItemForm`.
        """

        elapsed = item_elapsed_minutes(item)
        cap = get_hours_config().max_support_minutes_per_task
        initial = {"description": item.description}

        if item.billing_type == WorkOrderItem.TYPE_DEVELOPMENT:
            hours, minutes = minutes_to_hm(elapsed)
            initial.update({"dev_hours": hours, "dev_minutes": minutes})

        elif item.billing_type == WorkOrderItem.TYPE_SUPPORT_DEV_OVERAGE:
            support_minutes, dev_minutes = support_dev_split(elapsed, cap)
            s_hours, s_minutes = minutes_to_hm(support_minutes)
            d_hours, d_minutes = minutes_to_hm(dev_minutes)
            initial.update(
                {
                    "support_hours": s_hours,
                    "support_minutes": s_minutes,
                    "dev_hours": d_hours,
                    "dev_minutes": d_minutes,
                }
            )

        else:  # SUPPORT
            hours, minutes = minutes_to_hm(elapsed)
            initial.update({"support_hours": hours, "support_minutes": minutes})

        return initial

    def _create_entry(
        self,
        client,
        retainer,
        term,
        item,
        entry_type,
        hours,
        minutes,
        description,
    ):
        """Creates one `TimeEntry` row, skipping a zero-duration bucket.

        Args:
            client (Client): Item's owning client.
            retainer (Retainer): Item's owning retainer.
            term (ClientTerm | None): Term the entry falls in, or None
                for a historical entry.
            item (WorkOrderItem): Item the entry is being finalised for.
            entry_type (str): `TimeEntry.TYPE_SUPPORT` or
                `TimeEntry.TYPE_DEVELOPMENT`.
            hours (int): Whole hours for this bucket.
            minutes (int): Minutes (0-59) for this bucket.
            description (str): Description to save on the entry.
        """

        if hm_to_minutes(hours, minutes) == 0:
            return

        TimeEntry.objects.create(
            client=client,
            retainer=retainer,
            term=term,
            employee=item.owner,
            date=date.today(),
            hours=hours,
            minutes=minutes,
            type=entry_type,
            description=description,
            timer_item=item,
        )

    def _context(self, client, retainer, work_order, item, form):
        """Builds the shared client_form.html context.

        Args:
            client (Client): Item's owning client.
            retainer (Retainer): Item's owning retainer.
            work_order (WorkOrder): Item's owning work order.
            item (WorkOrderItem): Item being completed.
            form (CompleteWorkOrderItemForm): Bound or unbound form to
                render.

        Returns:
            dict: Context for rendering client_form.html.
        """

        return {
            "form": form,
            "title": f"Complete - {item.description}",
            "intro_text": (
                "Review the tracked time before it's saved. Adjust if the "
                "timer ran longer than the actual work done."
            ),
            "submit_label": "Save & Complete",
            "back_url": (
                f"/clients/{client.pk}/retainers/{retainer.pk}/"
                f"work-orders/{work_order.pk}/"
            ),
        }
