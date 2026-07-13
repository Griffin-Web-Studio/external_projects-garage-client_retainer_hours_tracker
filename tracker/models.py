from django.core.validators import MaxValueValidator
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


# ────────────────────────────────────────────| Employee (custom user model) |──
class EmployeeManager(BaseUserManager):
    """An extended user manager class for custom user model

    Args:
        BaseUserManager (BaseUserManager): Base user manager class
    """

    def create_user(
        self: EmployeeManager,
        email: str,
        name: str = "",
        password: str | None = None,
        **extra,
    ) -> AbstractBaseUser:
        """Create standard user

        Args:
            self (EmployeeManager): ref to class self
            email (str): Users email
            name (str, optional): User name. Defaults to "".
            password (str | None, optional): User password. Defaults to None.

        Raises:
            ValueError: Email Required

        Returns:
            AbstractBaseUser: Returns abstract base user model
        """

        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)
        user: AbstractBaseUser = self.model(email=email, name=name, **extra)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)

        return user

    def create_superuser(
        self: EmployeeManager,
        email: str,
        password: str | None = None,
        **extra,
    ) -> AbstractBaseUser:
        """Create super user

        Args:
            self (EmployeeManager): ref to class self
            email (str): Users email
            password (str | None, optional): User password. Defaults to None.

        Returns:
            AbstractBaseUser: Returns abstract base user model
        """

        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", "ADMIN")

        return self.create_user(email, password=password, **extra)


class Employee(AbstractBaseUser, PermissionsMixin):
    """Employee Model

    Args:
        AbstractBaseUser (AbstractBaseUser): Abstract base user
        PermissionsMixin (PermissionsMixin): Permissions mixins

    Returns:
        Employee: Employee model
    """

    ROLE_EMPLOYEE = "EMPLOYEE"
    ROLE_ADMIN = "ADMIN"
    ROLE_CHOICES: list[tuple[str, str]] = [
        (ROLE_EMPLOYEE, "Employee"),
        (ROLE_ADMIN, "Admin"),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200)
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []
    objects = EmployeeManager()

    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.name} <{self.email}>"


# ──────────────────────────────────────────────────────────────────| Client |──
class Client(models.Model):
    """Client model

    Args:
        models (Model): base model

    Returns:
        Client: Client model
    """

    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ────────────────────────────────────────────────────────────────| Retainer |──
class Retainer(models.Model):
    """Retainer model - one independent retainer contract for a client.

    A client can have multiple retainers running in parallel (e.g. a
    "Support Retainer" and a "Design Retainer"), each with its own term
    timeline, monthly hour allocation, and carryover rules.

    Args:
        models (Model): base model

    Returns:
        Retainer: Retainer model
    """

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="retainers"
    )
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.client.name} — {self.name}"

    @property
    def current_term(self):
        return self.terms.order_by("-term_number").first()

    def term_for_date(self, entry_date):
        """Finds the term whose date range covers a given date.

        Args:
            entry_date (date): Date to look up.

        Returns:
            ClientTerm | None: The term with `start_date <= entry_date <=
                end_date`, or None if no term covers that date (e.g. a
                historical date from before this retainer's first term).
        """

        return self.terms.filter(
            start_date__lte=entry_date, end_date__gte=entry_date
        ).first()


# ──────────────────────────────────────────────────────────────| ClientTerm |──
class ClientTerm(models.Model):
    """Client Term model

    Args:
        models (Model): base model

    Returns:
        ClientTerm: Client Term model
    """

    CARRY_NONE = "NONE"
    CARRY_CONVERT_DEV = "CONVERT_TO_DEV"
    CARRY_MIGRATE = "MIGRATE_SUPPORT"
    CARRY_CHOICES: list[tuple[str, str]] = [
        (CARRY_NONE, "First term (no carryover)"),
        (
            CARRY_CONVERT_DEV,
            "Convert remaining support > development hours (/2)",
        ),
        (CARRY_MIGRATE, "Migrate support hours forward (max 6h)"),
    ]

    retainer = models.ForeignKey(
        Retainer, on_delete=models.CASCADE, related_name="terms"
    )
    term_number = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()  # set to start_date + 1 year on save
    monthly_hours = models.PositiveIntegerField()
    monthly_minutes = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(59)]
    )

    # Carryover from the previous term
    carry_over_type = models.CharField(
        max_length=20, choices=CARRY_CHOICES, default=CARRY_NONE
    )
    # CONVERT_TO_DEV
    dev_hours_from_conversion = models.PositiveIntegerField(default=0)
    dev_minutes_from_conversion = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(59)]
    )
    # MIGRATE_SUPPORT
    migrated_support_hours = models.PositiveIntegerField(default=0)
    migrated_support_minutes = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(59)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["retainer", "term_number"]]
        ordering = ["term_number"]

    def __str__(self):
        return f"{self.retainer} — Term {self.term_number}"


# ───────────────────────────────────────────────────────────────| TimeEntry |──
class TimeEntry(models.Model):
    """Time Entry model

    Args:
        models (Model): base model

    Returns:
        TimeEntry: Time Entry model
    """

    TYPE_SUPPORT = "SUPPORT"
    TYPE_DEVELOPMENT = "DEVELOPMENT"
    TYPE_CHOICES: list[tuple[str, str]] = [
        (TYPE_SUPPORT, "Support"),
        (TYPE_DEVELOPMENT, "Development"),
    ]

    # Denormalized - must always equal `retainer.client`. Kept alongside
    # `retainer` for convenient client-scoped queries (e.g. historical
    # entries across all of a client's retainers).
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="time_entries"
    )
    retainer = models.ForeignKey(
        Retainer, on_delete=models.CASCADE, related_name="time_entries"
    )
    # Null when the entry's date falls outside every term this retainer
    # has ever had (e.g. historical work logged from before the retainer
    # was set up) - such entries don't count toward any term's hours.
    term = models.ForeignKey(
        ClientTerm,
        on_delete=models.CASCADE,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="time_entries"
    )
    date = models.DateField()
    hours = models.PositiveIntegerField()
    minutes = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(59)]
    )
    description = models.TextField()
    type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_SUPPORT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        suffix = f" {self.minutes}m" if self.minutes else ""
        return (
            f"{self.client.name} — {self.hours}h{suffix} {self.type} on "
            f"{self.date}"
        )


# ──────────────────────────────────────────────────────────| OverageBilling |──
class OverageBilling(models.Model):
    """Overage Billing model

    Args:
        models (Model): base model

    Returns:
        OverageBilling: Overage Billing model
    """

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="overage_billings"
    )
    term = models.ForeignKey(
        ClientTerm, on_delete=models.CASCADE, related_name="overage_billings"
    )
    type = models.CharField(max_length=20)  # SUPPORT | DEVELOPMENT
    hours_charged = models.PositiveIntegerField()
    minutes_charged = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(59)]
    )
    invoice_ref = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    billed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-billed_at"]

    def __str__(self):
        suffix = f" {self.minutes_charged}m" if self.minutes_charged else ""
        return (
            f"{self.client.name} — {self.hours_charged}h{suffix} "
            f"{self.type} billed"
        )


# ──────────────────────────────────────────────────────────| HoursPurchase |──
class HoursPurchase(models.Model):
    """HoursPurchase model - extra support hours a client has paid for as
    a buffer against overage, on top of a term's monthly allocation.

    Support hours only - development overage is billed directly via
    OverageBilling, not buffered. Consumed only once the term's ordinary
    allocation (monthly hours + migrated carryover) is exhausted, so a
    purchase sits untouched as a safety net until it's actually needed.
    Kept separate from the term's normal end-of-term carryover
    (`ClientTerm.carry_over_type`) since purchased hours are refunded or
    carried forward at full value, not subject to the conversion ratio
    or migration cap that applies to unused monthly allocation.

    Args:
        models (Model): base model

    Returns:
        HoursPurchase: HoursPurchase model
    """

    REFUNDED = "REFUNDED"
    CARRIED_FORWARD = "CARRIED_FORWARD"
    RESOLUTION_CHOICES: list[tuple[str, str]] = [
        (REFUNDED, "Refunded"),
        (CARRIED_FORWARD, "Carried forward"),
    ]

    term = models.ForeignKey(
        ClientTerm, on_delete=models.CASCADE, related_name="hours_purchases"
    )
    hours = models.PositiveIntegerField()
    minutes = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(59)]
    )
    invoice_ref = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)

    # Blank while the purchase's term is still active (or its leftover
    # hasn't been resolved yet at renewal). Set once resolved.
    resolution = models.CharField(
        max_length=20, choices=RESOLUTION_CHOICES, blank=True
    )

    # True for purchases backfilled from a pre-existing OverageBilling
    # total rather than new money - lets display code net that portion
    # out of the billing so it isn't counted as buffer credit twice.
    from_historical_billing = models.BooleanField(default=False)

    class Meta:
        ordering = ["purchased_at"]  # oldest first - buffer is consumed FIFO

    def __str__(self):
        return f"{self.term} — {self.hours}h{self.minutes:02d}m purchased"
