"""
Shared fixtures for integration tests.

All fixtures here touch the database and must be used inside tests decorated
with @pytest.mark.django_db (or inside a class that has it at the class level).
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.test import RequestFactory as DjangoRequestFactory

from authenticate.models import User
from bank_account.models import BankAccount
from event.models import Event, EventMember
from group.models import Group, GroupMember
from utils.enums import BankEnum


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def make_user(
    email: str,
    password: str = "TestPass1!",
    full_name: str = "Test User",
    phone_number: str = "0900000000",
    balance: float = 0.0,
) -> User:
    """Create and persist a User via the custom manager."""
    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        phone_number=phone_number,
    )
    if balance:
        user.balance = balance
        user.save(update_fields=["balance"])
    return user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rf():
    """Django RequestFactory for building fake HTTP requests."""
    return DjangoRequestFactory()


@pytest.fixture
def user_a(db):
    return make_user(
        "alice@example.com", full_name="Alice Smith", phone_number="0911111111"
    )


@pytest.fixture
def user_b(db):
    return make_user(
        "bob@example.com", full_name="Bob Jones", phone_number="0922222222"
    )


@pytest.fixture
def user_c(db):
    return make_user(
        "carol@example.com", full_name="Carol White", phone_number="0933333333"
    )


@pytest.fixture
def rich_user(db):
    """A user with a pre-loaded wallet balance."""
    return make_user(
        "rich@example.com",
        full_name="Rich Person",
        phone_number="0944444444",
        balance=10_000.0,
    )


@pytest.fixture
def group_with_members(db, user_a, user_b, user_c):
    """
    A Group led by user_a, with user_b and user_c as members.
    Returns (group, [user_a, user_b, user_c]).
    """
    group = Group.objects.create(name="Test Group", leader=user_a)
    GroupMember.objects.bulk_create(
        [
            GroupMember(group=group, user=user_a),
            GroupMember(group=group, user=user_b),
            GroupMember(group=group, user=user_c),
        ]
    )
    return group, [user_a, user_b, user_c]


@pytest.fixture
def event_with_members(db, group_with_members):
    """
    An Event inside group_with_members, with all three members enrolled.
    Returns (event, group, [user_a, user_b, user_c]).
    """
    group, users = group_with_members
    event = Event.objects.create(
        name="Test Event",
        creator=users[0],
        group=group,
        event_start=date.today(),
        event_end=date.today() + timedelta(days=1),
    )
    EventMember.objects.bulk_create([EventMember(event=event, user=u) for u in users])
    return event, group, users


@pytest.fixture
def bank_account(db, user_a):
    """A BankAccount belonging to user_a."""
    return BankAccount.objects.create(
        user=user_a,
        bank_name=BankEnum.VIETCOMBANK,
        account_number="1234567890",
    )


@pytest.fixture
def mock_fcm():
    """Suppress all Firebase Cloud Messaging calls."""
    with (
        patch("utils.services.firebase_cm.fcm_service.FCMService.send_notification"),
        patch(
            "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
        ),
    ):
        yield


@pytest.fixture
def mock_email():
    """Suppress email delivery."""
    with patch("utils.services.email.client.EmailClient.send"):
        yield


@pytest.fixture
def mock_notification():
    """Suppress notification ORM writes."""
    with patch("message.orm.notification_queries.NotificationORM.create_notification"):
        yield
