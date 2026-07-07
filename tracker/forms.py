"""Forms for client, time entry, term renewal, and overage billing input."""

from datetime import date

from django import forms

from tracker.hours import get_max_migrate_hours


class NewClientForm(forms.Form):
    """Form for creating a new client and their first term.

    Attributes:
        name (CharField): Client's display name.
        start_date (DateField): Start date of the client's first term.
        monthly_hours (FloatField): Support hours granted per calendar
            month.
        notes (CharField): Optional internal notes about the client.
    """

    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Acme Ltd"}),
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    monthly_hours = forms.FloatField(
        min_value=0.5,
        widget=forms.NumberInput(attrs={"placeholder": "10", "step": "0.5"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Optional internal notes..."}
        ),
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
        hours (FloatField): Number of hours worked.
        type (ChoiceField): Whether the entry is support or development
            time.
        description (CharField): Description of the work performed.
    """

    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date.today,
    )
    hours = forms.FloatField(
        min_value=0.25,
        widget=forms.NumberInput(attrs={"placeholder": "1.5", "step": "0.25"}),
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


class NewTermForm(forms.Form):
    """Form for renewing an expired term with a carryover choice.

    Attributes:
        carry_over_type (ChoiceField): How unused support hours carry
            over into the new term. Choices are populated in `__init__`
            so the migrate-hours label reflects the live config value.
        monthly_hours (FloatField): Support hours granted per calendar
            month under the new term.
    """

    carry_over_type = forms.ChoiceField(choices=[])  # populated in __init__
    monthly_hours = forms.FloatField(
        min_value=0.5,
        widget=forms.NumberInput(attrs={"step": "0.5"}),
        label="Monthly support hours (new term)",
    )

    def __init__(self, *args, **kwargs):
        """Populates `carry_over_type` choices from the live hours config.

        Args:
            *args: Positional arguments forwarded to `forms.Form.__init__`.
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


class BillOverageForm(forms.Form):
    """Form for recording an overage billing against a client's term.

    Attributes:
        type (ChoiceField): Whether the billed hours are support or
            development time.
        hours_charged (FloatField): Number of hours being billed.
        invoice_ref (CharField): Optional invoice reference.
        notes (CharField): Optional notes about the billing.
    """

    type = forms.ChoiceField(
        choices=[("SUPPORT", "Support"), ("DEVELOPMENT", "Development")],
    )
    hours_charged = forms.FloatField(
        min_value=0.25,
        widget=forms.NumberInput(attrs={"step": "0.25"}),
    )
    invoice_ref = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "INV-001 (optional)"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional"}),
    )
