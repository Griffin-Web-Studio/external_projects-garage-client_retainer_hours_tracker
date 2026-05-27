import random
from datetime import date, timedelta

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from tracker.models import Client, ClientTerm, TimeEntry

_faker = Faker()


# ───────────────────────────────────────────────────────────| ClientFactory |──
class ClientFactory(DjangoModelFactory):
    """Generates a fake Client with no term attached.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    class Meta:
        model = Client

    name = factory.LazyFunction(_faker.company)
    notes = factory.LazyFunction(_faker.sentence)
    is_active = True


# ───────────────────────────────────────────────────────| ClientTermFactory |──
class ClientTermFactory(DjangoModelFactory):
    """Generates a ClientTerm for a given client. Defaults to an active first
    term starting ~6 months ago.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    class Meta:
        model = ClientTerm

    client = factory.SubFactory(ClientFactory)
    term_number = 1
    start_date = factory.LazyFunction(
        lambda: date.today().replace(day=1) - timedelta(days=180)
    )
    end_date = factory.LazyAttribute(
        lambda o: o.start_date.replace(year=o.start_date.year + 1)
    )
    monthly_hours = factory.LazyFunction(
        lambda: random.choice([5, 8, 10, 15, 20])
    )
    carry_over_type = ClientTerm.CARRY_NONE
    dev_hours_from_conversion = 0
    migrated_support_hours = 0


# ────────────────────────────────────────────────────────| TimeEntryFactory |──
class TimeEntryFactory(DjangoModelFactory):
    """Generates a TimeEntry against a given client and term. Requires `client`,
    `term`, and `employee` to be passed explicitly.

    Args:
        DjangoModelFactory (DjangoModelFactory): Model Factory
    """

    class Meta:
        model = TimeEntry

    client = factory.SubFactory(ClientFactory)
    term = factory.SubFactory(ClientTermFactory)
    employee = factory.LazyAttribute(lambda o: o.term.client)
    date = factory.LazyFunction(
        lambda: _faker.date_between(start_date="-6m", end_date="today")
    )
    hours = factory.LazyFunction(
        lambda: round(random.uniform(0.5, 4.0) * 2) / 2
    )
    description = factory.LazyFunction(_faker.sentence)
    type = factory.LazyFunction(
        lambda: random.choice(["SUPPORT", "SUPPORT", "DEVELOPMENT"])
    )
