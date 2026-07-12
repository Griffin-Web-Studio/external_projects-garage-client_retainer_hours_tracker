from django.db import migrations


def backfill_time_entry_terms(apps, schema_editor):
    """Reassigns every TimeEntry's term to whichever term's date range
    actually covers the entry's date.

    Entries were previously always attached to "whatever the client's
    current term was" at the time they were logged, regardless of the
    entered date - this corrects any entry that landed in the wrong term
    (or should have no term at all, e.g. historical work logged for a
    client who existed before being tracked here) as a result.

    Args:
        apps: Historical app registry.
        schema_editor: Unused, required by the RunPython signature.
    """

    TimeEntry = apps.get_model("tracker", "TimeEntry")
    ClientTerm = apps.get_model("tracker", "ClientTerm")

    for entry in TimeEntry.objects.all():
        matched_term = (
            ClientTerm.objects.filter(
                client_id=entry.client_id,
                start_date__lte=entry.date,
                end_date__gte=entry.date,
            )
            .order_by("term_number")
            .first()
        )
        matched_term_id = matched_term.pk if matched_term else None

        if matched_term_id != entry.term_id:
            entry.term_id = matched_term_id
            entry.save(update_fields=["term"])


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0007_alter_timeentry_term"),
    ]

    operations = [
        migrations.RunPython(
            backfill_time_entry_terms, migrations.RunPython.noop
        ),
    ]
