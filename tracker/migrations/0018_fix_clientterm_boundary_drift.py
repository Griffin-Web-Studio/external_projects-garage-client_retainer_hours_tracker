from datetime import timedelta

from django.db import migrations


def fix_clientterm_boundary_drift(apps, schema_editor):
    """Recomputes ClientTerm start_date/end_date to remove the
    accumulated one-day-per-renewal drift caused by end_date
    previously being computed as the exact calendar anniversary of
    start_date instead of one day before it (see the matching code
    fix - this migration only corrects data already written under the
    old, buggy convention).

    Walks each retainer's term chain in term_number order. The first
    term's start_date is left untouched (user-entered, authoritative);
    every date after that is recomputed from the corrected previous
    term's end_date. Uses today's configured term_months for every
    term, since term_months isn't stored per-term and there's no
    historical record of what it was when any given term was created -
    today's value is the only available source.

    Any TimeEntry whose date lands in a different term once boundaries
    shift (i.e. it was logged exactly on an old anniversary day) is
    reassigned to match, using the same date-range lookup
    0008_backfill_time_entry_terms.py used. HoursPurchase and
    OverageBilling are deliberately left untouched - both are set
    explicitly to whatever term was current at creation time (a
    business action, not a date-derived lookup), so they keep pointing
    at the same term row regardless of that row's date columns
    shifting.

    Args:
        apps: Historical app registry.
        schema_editor: Unused, required by the RunPython signature.
    """

    from tracker.hours import add_months, get_hours_config

    Retainer = apps.get_model("tracker", "Retainer")
    ClientTerm = apps.get_model("tracker", "ClientTerm")
    TimeEntry = apps.get_model("tracker", "TimeEntry")

    term_months = get_hours_config().term_months
    one_day = timedelta(days=1)

    for retainer in Retainer.objects.all():
        terms = list(
            ClientTerm.objects.filter(retainer_id=retainer.pk).order_by(
                "term_number"
            )
        )

        if not terms:
            continue

        if any(term.end_date < term.start_date for term in terms):
            print(
                f"Skipping retainer {retainer.pk} ({retainer.name}) - "
                "a term has end_date before start_date, needs manual "
                "review."
            )
            continue

        changed = False
        previous_end = None

        for term in terms:
            new_start = (
                term.start_date
                if previous_end is None
                else (previous_end + one_day)
            )
            new_end = add_months(new_start, term_months) - one_day

            if new_start != term.start_date or new_end != term.end_date:
                term.start_date = new_start
                term.end_date = new_end
                term.save(update_fields=["start_date", "end_date"])
                changed = True

            previous_end = new_end

        if not changed:
            continue

        for entry in TimeEntry.objects.filter(retainer_id=retainer.pk):
            matched_term = (
                ClientTerm.objects.filter(
                    retainer_id=retainer.pk,
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
        ("tracker", "0017_seed_default_report_template"),
    ]

    operations = [
        migrations.RunPython(
            fix_clientterm_boundary_drift, migrations.RunPython.noop
        ),
    ]
