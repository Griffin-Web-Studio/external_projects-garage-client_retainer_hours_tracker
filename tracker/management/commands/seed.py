from django.core.management.base import BaseCommand, CommandParser

from database.seeders.seeder import Seeder


# ─────────────────────────────────────────────────────────────────| Command |──
class Command(BaseCommand):
    """Seeder Command

    Args:
        BaseCommand (BaseCommand): Base command
    """

    help = (
        "Seed the database.\n"
        "  Default: core data only (admin user).\n"
        "  --full:  core + full fake dataset (dev only)."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        """Arguments handler

        Args:
            parser (CommandParser): Command parser
        """

        parser.add_argument(
            "--full",
            action="store_true",
            help="Seed full fake dataset (development only).",
        )
        parser.add_argument(
            "--employees",
            type=int,
            default=3,
            metavar="N",
            help="Number of fake employees to create (default: 3).",
        )
        parser.add_argument(
            "--clients",
            type=int,
            default=5,
            metavar="N",
            help="Number of fake clients to create (default: 5).",
        )
        parser.add_argument(
            "--entries",
            type=int,
            default=20,
            metavar="N",
            help=(
                "Total time entries to distribute across"
                " clients (default: 20)."
            ),
        )

    def handle(self, *args, **options) -> None:
        """Command run handler"""
        seeder = Seeder(stdout=self.stdout)
        seeder.run_core()

        if options["full"]:
            seeder.run_dev(
                num_employees=options["employees"],
                num_clients=options["clients"],
                num_entries=options["entries"],
            )

        self.stdout.write(self.style.SUCCESS("\nDone."))
