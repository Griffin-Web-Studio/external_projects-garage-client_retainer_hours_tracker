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

    @property
    def current_term(self):
        return self.terms.order_by("-term_number").first()


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

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="terms"
    )
    term_number = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()  # set to start_date + 1 year on save
    monthly_hours = models.FloatField()

    # Carryover from the previous term
    carry_over_type = models.CharField(
        max_length=20, choices=CARRY_CHOICES, default=CARRY_NONE
    )
    dev_hours_from_conversion = models.FloatField(default=0)  # CONVERT_TO_DEV
    migrated_support_hours = models.FloatField(default=0)  # MIGRATE_SUPPORT

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["client", "term_number"]]
        ordering = ["term_number"]

    def __str__(self):
        return f"{self.client.name} — Term {self.term_number}"
