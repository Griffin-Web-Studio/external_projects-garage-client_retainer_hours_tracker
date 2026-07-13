from django.db import migrations, models


def mark_historical_billing_purchases(apps, schema_editor):
    """Flags the buffer purchases 0011 backfilled from pre-existing
    OverageBilling totals.

    Those rows represent money already counted in an OverageBilling
    total, not new money - display code needs to know which purchases
    they are so it can avoid counting that portion of the billing as
    buffer credit a second time.

    Args:
        apps: Historical app registry.
        schema_editor: Unused, required by the RunPython signature.
    """

    HoursPurchase = apps.get_model("tracker", "HoursPurchase")
    HoursPurchase.objects.filter(notes__startswith="Auto-migrated:").update(
        from_historical_billing=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0011_convert_excess_overage_billing"),
    ]

    operations = [
        migrations.AddField(
            model_name="hourspurchase",
            name="from_historical_billing",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            mark_historical_billing_purchases, migrations.RunPython.noop
        ),
    ]
