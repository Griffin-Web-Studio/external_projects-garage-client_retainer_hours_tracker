from tracker.models import Employee


# ──────────────────────────────────────────────────────────────| CoreSeeder |──
class CoreSeeder:
    """Seeds the minimum data required for the app to function. Safe to run in
    any environment. Non-destructive - skips silently if core data already
    exists.
    """

    DEFAULT_EMAIL = "admin@example.com"
    DEFAULT_PASSWORD = "changeme123"

    def run(self, stdout=None) -> None:
        self._seed_admin(stdout)

    # ── Private ───────────────────────────────────────────────────────────────

    def _log(self, stdout, message: str) -> None:
        if stdout:
            stdout.write(message)

    def _seed_admin(self, stdout) -> None:
        if Employee.objects.filter(email=self.DEFAULT_EMAIL).exists():
            self._log(
                stdout,
                f"  Admin {self.DEFAULT_EMAIL} already exists," " skipping.",
            )
            return

        Employee.objects.create_superuser(
            email=self.DEFAULT_EMAIL,
            name="Admin",
            password=self.DEFAULT_PASSWORD,
        )
        self._log(
            stdout,
            f"  ✔️ Created admin: {self.DEFAULT_EMAIL}"
            f" / {self.DEFAULT_PASSWORD}",
        )
