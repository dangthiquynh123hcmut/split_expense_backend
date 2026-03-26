"""
Shared fixtures for performance tests.

All fixtures here create large datasets to expose O(N) query patterns and
verify that service-layer and ORM operations stay within bounded query counts
and wall-time budgets.

Database: in-memory SQLite (via test_settings.py).
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from authenticate.models import User
from event.models import Event, EventMember
from expense.models import Expense, UserSharesInExpense
from group.models import Group, GroupMember
from wallet.models import Transaction


# ---------------------------------------------------------------------------
# Dataset sizes – keep small enough for SQLite, large enough to expose N+1
# ---------------------------------------------------------------------------

MEMBER_COUNT = 10  # extra members (not counting the leader)
EXPENSE_COUNT = 20  # expenses inside the large event
TX_COUNT = 50  # peer-to-peer wallet transactions


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def make_user(
    email: str,
    phone_number: str,
    balance: float = 0.0,
    full_name: str | None = None,
) -> User:
    user = User.objects.create_user(
        email=email,
        password="PerfTestPass1!",
        full_name=full_name or f"Perf {email.split('@')[0]}",
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
def large_group(db):
    """
    A Group with MEMBER_COUNT regular members plus a leader.
    Returns (group, leader, [member_1, ..., member_N]).
    """
    leader = make_user(
        "perf_leader@example.com",
        phone_number="0900000000",
        balance=1_000_000.0,
        full_name="Perf Leader",
    )
    members = [
        make_user(
            f"perf_member_{i}@example.com",
            phone_number=f"091{i:07d}",
            full_name=f"Perf Member {i}",
        )
        for i in range(MEMBER_COUNT)
    ]
    group = Group.objects.create(name="Perf Group", leader=leader)
    GroupMember.objects.bulk_create(
        [GroupMember(group=group, user=leader)]
        + [GroupMember(group=group, user=m) for m in members]
    )
    return group, leader, members


@pytest.fixture
def large_event(db, large_group):
    """
    An Event inside large_group with all members enrolled.
    Returns (event, group, leader, [members]).
    """
    group, leader, members = large_group
    all_users = [leader] + members
    event = Event.objects.create(
        name="Perf Event",
        creator=leader,
        group=group,
        event_start=date.today(),
        event_end=date.today() + timedelta(days=7),
    )
    EventMember.objects.bulk_create(
        [EventMember(event=event, user=u) for u in all_users]
    )
    return event, group, leader, members


@pytest.fixture
def large_event_with_expenses(db, large_event):
    """
    large_event populated with EXPENSE_COUNT expenses.
    Each expense is split equally among all members; the leader is paid_by.
    Returns (event, group, leader, members, [expenses]).
    """
    event, group, leader, members = large_event
    all_users = [leader] + members
    n = len(all_users)
    per_person = Decimal("100.00") / n
    receiver_amount = Decimal("100.00") - per_person  # what leader gets back

    # Bulk-create all expense rows
    expense_objs = [
        Expense(
            name=f"Perf Expense {i}",
            event=event,
            paid_by=leader,
            creator=leader,
            total_amount=100.0,
            currency="VND",
            split_type="EQUAL",
            expense_date="2026-01-01T00:00:00+00:00",
        )
        for i in range(EXPENSE_COUNT)
    ]
    created = Expense.objects.bulk_create(expense_objs)

    # Bulk-create UserSharesInExpense for every (expense, user) pair
    shares = []
    for expense in created:
        for user in all_users:
            shares.append(
                UserSharesInExpense(
                    expense=expense,
                    user=user,
                    amount=per_person,
                    receiver_amount=receiver_amount
                    if user == leader
                    else Decimal("0.0"),
                )
            )
    UserSharesInExpense.objects.bulk_create(shares)

    return event, group, leader, members, created


@pytest.fixture
def bulk_transactions(db, large_group):
    """
    TX_COUNT peer-to-peer Transaction rows between leader and first member.
    Returns (transactions, leader, receiver).

    Each Transaction is created via .create() so that the model's save()
    method runs and the unique `code` field is auto-generated correctly.
    """
    group, leader, members = large_group
    receiver = members[0]
    txs = [
        Transaction.objects.create(
            from_user=leader,
            to_user=receiver,
            amount=Decimal("50.00"),
            currency="VND",
            description=f"Perf TX {i}",
        )
        for i in range(TX_COUNT)
    ]
    return txs, leader, receiver
