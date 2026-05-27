import factory
from factory.django import DjangoModelFactory
from faker import Faker

from tracker.models import Employee

_faker = Faker()


# ─────────────────────────────────────────────────────────| EmployeeFactory |──
class EmployeeFactory(DjangoModelFactory):
    """Generates fake Employee instances. Password is set to 'password' by
    default for dev convenience. OIDC users in production will have unusable
    passwords - this factory is strictly for development seeding and test
    fixtures.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    class Meta:
        model = Employee
        django_get_or_create = ("email",)

    name = factory.LazyFunction(_faker.name)
    email = factory.LazyAttribute(
        lambda o: f"{o.name.lower().replace(' ', '.')}@example.com"
    )
    role = Employee.ROLE_EMPLOYEE
    is_active = True
    is_staff = False

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if not create:
            return
        raw = extracted or "password"
        obj.set_password(raw)
        obj.save()


# ────────────────────────────────────────────────────────────| AdminFactory |──
class AdminFactory(EmployeeFactory):
    """Convenience sub-factory for admin/staff employees.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    role = Employee.ROLE_ADMIN
    is_staff = True
    is_superuser = True
