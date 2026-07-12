import django.db.models.deletion
from django.db import migrations, models


def backfill_retainers(apps, schema_editor):
    """Creates one default retainer per existing client and reattaches
    their terms and time entries to it.

    Every client currently has exactly one implicit retainer (its
    ClientTerm timeline) - this makes that explicit as a named Retainer
    row so existing data keeps working once retainers become first-class.

    Args:
        apps: Historical app registry.
        schema_editor: Unused, required by the RunPython signature.
    """

    Client = apps.get_model("tracker", "Client")
    Retainer = apps.get_model("tracker", "Retainer")
    ClientTerm = apps.get_model("tracker", "ClientTerm")
    TimeEntry = apps.get_model("tracker", "TimeEntry")

    for client in Client.objects.all():
        retainer = Retainer.objects.create(
            client=client, name="Support Retainer"
        )
        ClientTerm.objects.filter(client_id=client.pk).update(
            retainer_id=retainer.pk
        )
        TimeEntry.objects.filter(client_id=client.pk).update(
            retainer_id=retainer.pk
        )


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0008_backfill_time_entry_terms"),
    ]

    operations = [
        migrations.CreateModel(
            name="Retainer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retainers",
                        to="tracker.client",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="clientterm",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="clientterm",
            name="retainer",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="terms",
                to="tracker.retainer",
            ),
        ),
        migrations.AddField(
            model_name="timeentry",
            name="retainer",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="time_entries",
                to="tracker.retainer",
            ),
        ),
        migrations.RunPython(backfill_retainers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="clientterm",
            name="retainer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="terms",
                to="tracker.retainer",
            ),
        ),
        migrations.AlterField(
            model_name="timeentry",
            name="retainer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="time_entries",
                to="tracker.retainer",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="clientterm",
            unique_together={("retainer", "term_number")},
        ),
        migrations.RemoveField(
            model_name="clientterm",
            name="client",
        ),
    ]
