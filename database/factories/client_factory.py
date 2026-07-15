import random
from datetime import date, timedelta

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from database.factories.employee_factory import EmployeeFactory
from tracker.hours import add_months, get_term_months
from tracker.models import Client, ClientTerm, Retainer, TimeEntry

_faker = Faker()


# ───────────────────────────────────────────────────────────| ClientFactory |──
class ClientFactory(DjangoModelFactory):
    """Generates a fake Client with no retainer attached.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    class Meta:
        model = Client

    name = factory.LazyFunction(_faker.company)
    notes = factory.LazyFunction(_faker.sentence)
    is_active = True


# ─────────────────────────────────────────────────────────| RetainerFactory |──
class RetainerFactory(DjangoModelFactory):
    """Generates a fake Retainer for a given client, with no term attached.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    class Meta:
        model = Retainer

    client = factory.SubFactory(ClientFactory)
    name = factory.LazyFunction(
        lambda: random.choice(
            ["Support Retainer", "Design Retainer", "Development Retainer"]
        )
    )
    is_active = True


# ───────────────────────────────────────────────────────| ClientTermFactory |──
class ClientTermFactory(DjangoModelFactory):
    """Generates a ClientTerm for a given retainer. Defaults to an active
    first term starting ~6 months ago.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    class Meta:
        model = ClientTerm

    retainer = factory.SubFactory(RetainerFactory)
    term_number = 1
    start_date = factory.LazyFunction(
        lambda: date.today().replace(day=1) - timedelta(days=180)
    )
    end_date = factory.LazyAttribute(
        lambda o: add_months(o.start_date, get_term_months())
        - timedelta(days=1)
    )
    monthly_hours = factory.LazyFunction(
        lambda: random.choice([5, 8, 10, 15, 20])
    )
    monthly_minutes = factory.LazyFunction(
        lambda: random.choice([0, 15, 30, 45])
    )
    carry_over_type = ClientTerm.CARRY_NONE
    dev_hours_from_conversion = 0
    dev_minutes_from_conversion = 0
    migrated_support_hours = 0
    migrated_support_minutes = 0


# ────────────────────────────────────────────────────────| TimeEntryFactory |──
class TimeEntryFactory(DjangoModelFactory):
    """Generates a TimeEntry against a given retainer and term. Requires
    `retainer`, `term`, and `employee` to be passed explicitly.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    class Meta:
        model = TimeEntry

    retainer = factory.SubFactory(RetainerFactory)
    client = factory.LazyAttribute(lambda o: o.retainer.client)
    term = factory.SubFactory(
        ClientTermFactory, retainer=factory.SelfAttribute("..retainer")
    )
    employee = factory.SubFactory(EmployeeFactory)
    date = factory.LazyFunction(
        lambda: _faker.date_between(start_date="-6m", end_date="today")
    )
    hours = factory.LazyFunction(lambda: random.randint(0, 4))
    minutes = factory.LazyAttribute(
        lambda o: random.choice(
            [15, 30, 45] if o.hours == 0 else [0, 15, 30, 45]
        )
    )
    description = factory.LazyFunction(_faker.sentence)
    type = factory.LazyFunction(
        lambda: random.choice(["SUPPORT", "SUPPORT", "DEVELOPMENT"])
    )
