import random

from django.conf import settings
from django.core.management.base import OutputWrapper
from factory.django import DjangoModelFactory

from database.factories.client_factory import (
    ClientFactory,
    ClientTermFactory,
    RetainerFactory,
    TimeEntryFactory,
)
from database.factories.employee_factory import (
    AdminFactory,
    EmployeeFactory,
)


# ───────────────────────────────────────────────────────────────| DevSeeder |──
class DevSeeder:
    """Seeds a rich fake dataset for development and demo purposes. Hard-errors
    if DEBUG is False - must never run in production. Non-destructive: appends
    to existing data.
    """

    def run(
        self: DevSeeder,
        stdout: OutputWrapper = None,
        num_employees: int = 3,
        num_clients: int = 5,
        num_entries: int = 20,
    ) -> None:
        self._guard_production()
        employees = self._seed_employees(stdout, num_employees)
        self._seed_clients(stdout, employees, num_clients, num_entries)

    # ── Private ───────────────────────────────────────────────────────────────

    def _guard_production(self: DevSeeder) -> None:
        if not settings.DEBUG:
            raise RuntimeError(
                "DevSeeder refused to run: DEBUG is False.\n"
                "This seeder is for development only."
            )

    def _log(self: DevSeeder, stdout: OutputWrapper, message: str) -> None:
        if stdout:
            stdout.write(message)

    def _seed_employees(self: DevSeeder, stdout: str, count: int) -> list:
        created: list[DjangoModelFactory] = []

        # At least one extra admin in the dev dataset
        admin = AdminFactory(password="password")
        created.append(admin)
        self._log(
            stdout,
            f"  ✔️ Admin employee: {admin.email} / password",
        )

        for _ in range(count):
            employee = EmployeeFactory(password="password")
            created.append(employee)
            self._log(
                stdout,
                f"  ✔️ Employee: {employee.email} / password",
            )

        return created

    def _seed_clients(
        self: DevSeeder,
        stdout: OutputWrapper,
        employees: list,
        num_clients: int,
        num_entries: int,
    ) -> None:
        entries_per_client = max(1, num_entries // num_clients)
        retainer_names = [
            "Support Retainer",
            "Design Retainer",
            "Development Retainer",
        ]

        for i in range(num_clients):
            client = ClientFactory()
            names = random.sample(retainer_names, random.choice([1, 1, 2]))
            entries_per_retainer = max(1, entries_per_client // len(names))

            self._log(stdout, f"  ✔️ Client: {client.name}")

            for name in names:
                retainer = RetainerFactory(client=client, name=name)
                term = ClientTermFactory(retainer=retainer)

                self._log(
                    stdout,
                    f"    └─ Retainer: {retainer.name}"
                    f" ({term.monthly_hours}h/mo)",
                )

                for _ in range(entries_per_retainer):
                    TimeEntryFactory(
                        retainer=retainer,
                        client=client,
                        term=term,
                        employee=employees[i % len(employees)],
                    )

                self._log(
                    stdout,
                    f"        {entries_per_retainer} time"
                    f" {'entry' if entries_per_retainer == 1 else 'entries'}"
                    f" logged",
                )
