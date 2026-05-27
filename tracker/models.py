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
