from django.core.management.base import BaseCommand, CommandParser

from tracker.models import Employee


# ─────────────────────────────────────────────────────────────────| Command |──
class Command(BaseCommand):
    """Elevate Admin Command

    Args:
        BaseCommand (BaseCommand): Base command
    """

    help = (
        "Elevate an employee to admin (role=ADMIN, is_staff=True, "
        "is_superuser=True). Lists employees and prompts for a choice "
        "unless --email is given."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        """Arguments handler

        Args:
            parser (CommandParser): Command parser
        """

        parser.add_argument(
            "--email",
            type=str,
            default=None,
            help=(
                "Email of the employee to elevate - skips the "
                "interactive prompt."
            ),
        )

    def handle(self, *args, **options) -> None:
        """Command run handler"""

        employees = list(Employee.objects.order_by("email"))

        if not employees:
            self.stdout.write(self.style.ERROR("No employees exist yet."))
            return

        email = options["email"]

        if email:
            try:
                employee = Employee.objects.get(email__iexact=email.strip())
            except Employee.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"No employee found with email '{email}'.")
                )
                return
        else:
            employee = self._prompt_for_employee(employees)

            if employee is None:
                return

        if employee.role == Employee.ROLE_ADMIN and employee.is_superuser:
            self.stdout.write(
                self.style.WARNING(f"{employee.email} is already an admin.")
            )
            return

        employee.role = Employee.ROLE_ADMIN
        employee.is_staff = True
        employee.is_superuser = True
        employee.save(update_fields=["role", "is_staff", "is_superuser"])

        self.stdout.write(
            self.style.SUCCESS(f"{employee.email} is now an admin.")
        )

    def _prompt_for_employee(
        self, employees: list[Employee]
    ) -> Employee | None:
        """Lists employees and prompts for which one to elevate.

        Args:
            employees (list[Employee]): Employees to choose from,
                already ordered for stable numbering.

        Returns:
            Employee | None: The chosen employee, or None if the input
                wasn't a valid choice.
        """

        self.stdout.write("Employees:")

        for i, employee in enumerate(employees, start=1):
            flags = []

            if employee.is_superuser:
                flags.append("superuser")
            elif employee.is_staff:
                flags.append("staff")

            if employee.role == Employee.ROLE_ADMIN:
                flags.append("role=ADMIN")

            suffix = f" ({', '.join(flags)})" if flags else ""
            self.stdout.write(
                f"  {i}. {employee.email} - {employee.name}{suffix}"
            )

        choice = input("Elevate which employee? [number]: ").strip()

        if not choice.isdigit() or not (1 <= int(choice) <= len(employees)):
            self.stdout.write(self.style.ERROR("Invalid selection."))
            return None

        return employees[int(choice) - 1]
