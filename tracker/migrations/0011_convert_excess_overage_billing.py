from django.db import migrations


def convert_excess_overage_billing_to_purchases(apps, schema_editor):
    """Converts historical over-billed SUPPORT overage into HoursPurchase
    buffer records.

    Before this release, BillOverageForm didn't cap `hours_charged`
    against the actual outstanding overage, so a term could have more
    SUPPORT overage billed than it ever actually owed - money the
    client already paid for hours they hadn't used yet. That excess is
    exactly what HoursPurchase represents, so this backfills one
    HoursPurchase per affected term for the excess amount.

    Development overage has no buffer equivalent (HoursPurchase is
    support-only by design - dev overage is billed directly), so
    DEVELOPMENT-type billings are left untouched.

    Args:
        apps: Historical app registry.
        schema_editor: Unused, required by the RunPython signature.
    """

    from tracker.hours import (
        calculate_term_hours,
        get_hours_config,
        hm_to_minutes,
        minutes_to_hm,
    )

    ClientTerm = apps.get_model("tracker", "ClientTerm")
    HoursPurchase = apps.get_model("tracker", "HoursPurchase")

    cfg = get_hours_config()

    for term in ClientTerm.objects.all():
        entries = list(term.time_entries.all())
        purchases = list(term.hours_purchases.all())
        summary = calculate_term_hours(term, entries, purchases, cfg)

        billed_minutes = sum(
            hm_to_minutes(b.hours_charged, b.minutes_charged)
            for b in term.overage_billings.filter(type="SUPPORT")
        )
        excess = billed_minutes - summary.support_overage

        if excess > 0:
            hours, minutes = minutes_to_hm(excess)
            HoursPurchase.objects.create(
                term=term,
                hours=hours,
                minutes=minutes,
                notes=(
                    "Auto-migrated: SUPPORT overage previously billed "
                    "beyond what was actually owed at the time"
                ),
            )


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0010_hourspurchase"),
    ]

    operations = [
        migrations.RunPython(
            convert_excess_overage_billing_to_purchases,
            migrations.RunPython.noop,
        ),
    ]
