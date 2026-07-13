"""Forms for client, time entry, term renewal, and overage billing input."""

from datetime import date

from django import forms

from tracker.hours import (
    fmt_hm,
    get_max_migrate_hours,
    get_min_log_entry_minutes,
    get_min_overage_billing_minutes,
    hm_to_minutes,
)
from tracker.models import HoursPurchase


def _validate_min_duration(
    cleaned_data: dict,
    hours_field: str,
    minutes_field: str,
    min_minutes: int,
) -> None:
    """Raises a form error if `hours_field` + `minutes_field` is too short.

    Args:
        cleaned_data (dict): The form's `cleaned_data`, already containing
            valid values for `hours_field` and `minutes_field`.
        hours_field (str): Name of the whole-hours field.
        minutes_field (str): Name of the minutes (0-59) field.
        min_minutes (int): Minimum total minutes required.

    Raises:
        forms.ValidationError: Attached to `hours_field` if the combined
            duration is below `min_minutes`.
    """

    hours = cleaned_data.get(hours_field)
    minutes = cleaned_data.get(minutes_field)

    if hours is None or minutes is None:
        return

    if hm_to_minutes(hours, minutes) < min_minutes:
        unit = "minute" if min_minutes == 1 else "minutes"
        raise forms.ValidationError(
            {hours_field: f"Must be at least {min_minutes} {unit} in total."}
        )


class NewClientForm(forms.Form):
    """Form for creating a new client, their first retainer, and its
    first term.

    Attributes:
        name (CharField): Client's display name.
        retainer_name (CharField): Display name for the client's first
            retainer.
        start_date (DateField): Start date of the retainer's first term.
        monthly_hours (IntegerField): Whole support hours granted per
            calendar month.
        monthly_minutes (IntegerField): Additional support minutes (0-59)
            granted per calendar month.
        notes (CharField): Optional internal notes about the client.
    """

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Acme Ltd"}),
    )
    retainer_name = forms.CharField(
        max_length=200,
        label="Retainer name",
        initial="Support Retainer",
        widget=forms.TextInput(attrs={"placeholder": "Support Retainer"}),
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    monthly_hours = forms.IntegerField(
        min_value=0,
        label="Monthly support hours",
        widget=forms.NumberInput(attrs={"placeholder": "10"}),
    )
    monthly_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        label="Monthly support minutes",
        initial=0,
        widget=forms.NumberInput(attrs={"placeholder": "0"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Optional internal notes..."}
        ),
    )

    def clean(self):
        """Validates that the combined monthly hours/minutes is >= 30 min.

        Returns:
            dict: The form's cleaned data.
        """

        cleaned_data = super().clean()
        _validate_min_duration(
            cleaned_data, "monthly_hours", "monthly_minutes", 30
        )
        return cleaned_data


class NewRetainerForm(forms.Form):
    """Form for adding a new retainer contract to an existing client.

    Attributes:
        name (CharField): Retainer's display name.
        start_date (DateField): Start date of the retainer's first term.
        monthly_hours (IntegerField): Whole support hours granted per
            calendar month.
        monthly_minutes (IntegerField): Additional support minutes (0-59)
            granted per calendar month.
    """

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Design Retainer"}),
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    monthly_hours = forms.IntegerField(
        min_value=0,
        label="Monthly support hours",
        widget=forms.NumberInput(attrs={"placeholder": "10"}),
    )
    monthly_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        label="Monthly support minutes",
        initial=0,
        widget=forms.NumberInput(attrs={"placeholder": "0"}),
    )

    def clean(self):
        """Validates that the combined monthly hours/minutes is >= 30 min.

        Returns:
            dict: The form's cleaned data.
        """

        cleaned_data = super().clean()
        _validate_min_duration(
            cleaned_data, "monthly_hours", "monthly_minutes", 30
        )
        return cleaned_data


class EditRetainerForm(forms.Form):
    """Form for editing an existing retainer's name and status.

    Attributes:
        name (CharField): Retainer's display name.
        is_active (ChoiceField): Whether the retainer is active or
            inactive.
    """

    name = forms.CharField(max_length=200)
    is_active = forms.ChoiceField(
        choices=[("true", "Active"), ("false", "Inactive")],
    )


class EditClientForm(forms.Form):
    """Form for editing an existing client's name, notes, and status.

    Attributes:
        name (CharField): Client's display name.
        notes (CharField): Optional internal notes about the client.
        is_active (ChoiceField): Whether the client is active or inactive.
    """

    name = forms.CharField(max_length=200)
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    is_active = forms.ChoiceField(
        choices=[("true", "Active"), ("false", "Inactive")],
    )


class LogTimeForm(forms.Form):
    """Form for logging a time entry against a client's active term.

    Attributes:
        date (DateField): Date the work was performed.
        hours (IntegerField): Whole hours worked.
        minutes (IntegerField): Additional minutes worked (0-59).
        type (ChoiceField): Whether the entry is support or development
            time.
        description (CharField): Description of the work performed.
    """

    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    hours = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={"placeholder": "1"}),
    )
    minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        initial=0,
        widget=forms.NumberInput(attrs={"placeholder": "30"}),
    )
    type = forms.ChoiceField(
        choices=[("SUPPORT", "Support"), ("DEVELOPMENT", "Development")],
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "e.g. Fixed login issue, updated DNS records...",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        """Caps the date widget's picker at today.

        Args:
            *args: Positional arguments forwarded to `forms.Form.__init__`.
            **kwargs: Keyword arguments forwarded to `forms.Form.__init__`.
        """

        super().__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["max"] = date.today().isoformat()

    def clean_date(self):
        """Validates that the entry's date isn't in the future.

        Work that hasn't happened yet can't be logged - a future date
        that falls within the current term's range would otherwise be
        counted as used hours before the work is actually done.

        Returns:
            date: The cleaned date value.

        Raises:
            forms.ValidationError: If the date is after today.
        """

        entry_date = self.cleaned_data["date"]

        if entry_date > date.today():
            raise forms.ValidationError("Date can't be in the future.")

        return entry_date

    def clean(self):
        """Validates that the combined hours/minutes meets the
        configured minimum log entry duration.

        Returns:
            dict: The form's cleaned data.
        """

        cleaned_data = super().clean()
        _validate_min_duration(
            cleaned_data, "hours", "minutes", get_min_log_entry_minutes()
        )
        return cleaned_data


class NewTermForm(forms.Form):
    """Form for renewing an expired term with a carryover choice.

    Also gains one `purchase_resolution_<pk>` ChoiceField per unresolved
    `HoursPurchase` with unused hours left on the expiring term, so the
    renewer can choose refund-vs-carry-forward for each individually.

    Attributes:
        carry_over_type (ChoiceField): How unused support hours carry
            over into the new term. Choices are populated in `__init__`
            so the migrate-hours label reflects the live config value.
        monthly_hours (IntegerField): Whole support hours granted per
            calendar month under the new term.
        monthly_minutes (IntegerField): Additional support minutes (0-59)
            granted per calendar month under the new term.
    """

    carry_over_type = forms.ChoiceField(choices=[])  # populated in __init__
    monthly_hours = forms.IntegerField(
        min_value=0,
        label="Monthly support hours (new term)",
    )
    monthly_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        initial=0,
        label="Monthly support minutes (new term)",
    )

    def __init__(self, *args, unresolved_purchases=None, **kwargs):
        """Populates `carry_over_type` choices and per-purchase fields.

        Args:
            *args: Positional arguments forwarded to `forms.Form.__init__`.
            unresolved_purchases (list[tuple[HoursPurchase, int]] | None,
                optional): `(purchase, remaining_minutes)` pairs needing
                a refund-vs-carry-forward choice. Defaults to None (no
                unresolved purchases on this term).
            **kwargs: Keyword arguments forwarded to `forms.Form.__init__`.
        """

        super().__init__(*args, **kwargs)
        max_h = get_max_migrate_hours()
        self.fields["carry_over_type"].choices = [
            (
                "CONVERT_TO_DEV",
                "Convert remaining support hours to development hours "
                "(÷ conversion ratio)",
            ),
            (
                "MIGRATE_SUPPORT",
                f"Migrate support hours forward (max {max_h:g}h, excess "
                "forfeited)",
            ),
        ]

        self.unresolved_purchases = unresolved_purchases or []

        for purchase, remaining_minutes in self.unresolved_purchases:
            self.fields[f"purchase_resolution_{purchase.pk}"] = (
                forms.ChoiceField(
                    choices=[
                        (
                            HoursPurchase.CARRIED_FORWARD,
                            "Carry forward to new term",
                        ),
                        (HoursPurchase.REFUNDED, "Refund to client"),
                    ],
                    initial=HoursPurchase.CARRIED_FORWARD,
                    label=f"{fmt_hm(remaining_minutes)} unused "
                    f"({purchase.invoice_ref or 'no invoice ref'})",
                )
            )

    def clean(self):
        """Validates that the combined monthly hours/minutes is >= 30 min.

        Returns:
            dict: The form's cleaned data.
        """

        cleaned_data = super().clean()
        _validate_min_duration(
            cleaned_data, "monthly_hours", "monthly_minutes", 30
        )
        return cleaned_data


class BillOverageForm(forms.Form):
    """Form for recording an overage billing against a client's term.

    Attributes:
        type (ChoiceField): Whether the billed hours are support or
            development time.
        hours_charged (IntegerField): Whole hours being billed.
        minutes_charged (IntegerField): Additional minutes being billed
            (0-59).
        invoice_ref (CharField): Optional invoice reference.
        notes (CharField): Optional notes about the billing.
    """

    type = forms.ChoiceField(
        choices=[("SUPPORT", "Support"), ("DEVELOPMENT", "Development")],
    )
    hours_charged = forms.IntegerField(min_value=0)
    minutes_charged = forms.IntegerField(min_value=0, max_value=59, initial=0)
    invoice_ref = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "INV-001 (optional)"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional"}),
    )

    def clean(self):
        """Validates that the combined hours/minutes meets the
        configured minimum overage billing duration.

        Returns:
            dict: The form's cleaned data.
        """

        cleaned_data = super().clean()
        _validate_min_duration(
            cleaned_data,
            "hours_charged",
            "minutes_charged",
            get_min_overage_billing_minutes(),
        )
        return cleaned_data


class HoursPurchaseForm(forms.Form):
    """Form for recording a purchase of extra buffer support hours.

    Attributes:
        hours (IntegerField): Whole hours purchased.
        minutes (IntegerField): Additional minutes purchased (0-59).
        invoice_ref (CharField): Optional invoice reference.
        notes (CharField): Optional notes about the purchase.
    """

    hours = forms.IntegerField(min_value=0)
    minutes = forms.IntegerField(min_value=0, max_value=59, initial=0)
    invoice_ref = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "INV-001 (optional)"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional"}),
    )

    def clean(self):
        """Validates that the combined hours/minutes meets the
        configured minimum overage billing duration.

        Returns:
            dict: The form's cleaned data.
        """

        cleaned_data = super().clean()
        _validate_min_duration(
            cleaned_data, "hours", "minutes", get_min_overage_billing_minutes()
        )
        return cleaned_data
