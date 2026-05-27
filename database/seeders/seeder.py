from database.seeders.core_seeder import CoreSeeder
from database.seeders.dev_seeder import DevSeeder
from django.core.management.base import OutputWrapper


# ──────────────────────────────────────────────────────────────────| Seeder |──
class Seeder:
    """Orchestrates all seeders. The management command delegates entirely to
    this class.
    """

    def __init__(self, stdout: OutputWrapper = None) -> None:
        self._stdout = stdout
        self._core_seeder = CoreSeeder()
        self._dev_seeder = DevSeeder()

    def run_core(self) -> None:
        """Runner for the core seeder"""

        self._log("Running core seeder…")
        self._core_seeder.run(stdout=self._stdout)

    def run_dev(
        self,
        num_employees: int = 3,
        num_clients: int = 5,
        num_entries: int = 20,
    ) -> None:
        """Runner for the dev seeder

        Args:
            num_employees (int, optional): number of employees. Defaults to 3.
            num_clients (int, optional): number of clients. Defaults to 5.
            num_entries (int, optional): number of entries. Defaults to 20.
        """

        self._log("Running dev seeder…")
        self._dev_seeder.run(
            stdout=self._stdout,
            num_employees=num_employees,
            num_clients=num_clients,
            num_entries=num_entries,
        )

    # ── Private ───────────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        """Private logging function

        Args:
            message (str): Log Message
        """
        if self._stdout:
            self._stdout.write(message)
