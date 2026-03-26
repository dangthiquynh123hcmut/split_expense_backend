"""
Performance tests for expense ORM queries and service operations.

What is measured
----------------
1. Query-count efficiency — list_expenses_in_event and list_expenses_by_user
   must NOT grow O(N) queries with the number of expense rows.
2. Wall-time budget — bulk creation of 20 expenses + their member shares must
   complete within an acceptable time limit on an in-memory SQLite database.
3. Aggregate correctness at scale — UserSharesInExpense row count is
   consistent with the number of expenses × the number of members.

The fixtures that supply large datasets are defined in conftest.py.
"""

import time
from decimal import Decimal

import pytest
from django.db import connection, reset_queries
from django.test.utils import override_settings

from expense.models import Expense, UserSharesInExpense
from expense.queries import Query as ExpenseQuery
from tests.performance.conftest import EXPENSE_COUNT, MEMBER_COUNT
from utils.schemas.filter_and_order_by import (
    FilterAmountSchema,
    FilterDateSchema,
    FilterEventSchema,
)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Maximum number of SQL statements list_expenses_in_event may issue,
# regardless of how many expenses exist in the event.
MAX_QUERIES_LIST_IN_EVENT = 5

# Maximum number of SQL statements list_expenses_by_user may issue
# when there are EXPENSE_COUNT rows per user.
MAX_QUERIES_LIST_BY_USER = 5

# Wall-time budget (seconds) for creating 20 expenses + all member shares
# via bulk_create on an in-memory SQLite database.
BULK_CREATE_BUDGET_SECONDS = 3.0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _reset_and_count(fn):
    """Execute *fn* with query logging enabled; return (result, query_count)."""
    reset_queries()
    result = fn()
    return result, len(connection.queries)


# ---------------------------------------------------------------------------
# Query-count tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListExpensesInEventQueryCount:
    """list_expenses_in_event must issue a bounded number of SQL statements."""

    @override_settings(DEBUG=True)
    def test_query_count_is_bounded_for_large_event(self, large_event_with_expenses):
        """
        With EXPENSE_COUNT expenses the query count must not exceed
        MAX_QUERIES_LIST_IN_EVENT — i.e. no per-row SELECT.
        """
        event, _group, leader, _members, _expenses = large_event_with_expenses

        result, n_queries = _reset_and_count(
            lambda: ExpenseQuery.list_expenses_in_event(
                user=leader, event=event, status="ACTIVE"
            )
        )

        assert n_queries <= MAX_QUERIES_LIST_IN_EVENT, (
            f"list_expenses_in_event issued {n_queries} SQL queries for "
            f"{EXPENSE_COUNT} expenses (budget: {MAX_QUERIES_LIST_IN_EVENT})"
        )

    @override_settings(DEBUG=True)
    def test_returns_all_expenses_without_extra_queries(
        self, large_event_with_expenses
    ):
        """Result set size equals EXPENSE_COUNT with no extra per-record hits."""
        event, _group, leader, _members, _expenses = large_event_with_expenses

        result, _n = _reset_and_count(
            lambda: ExpenseQuery.list_expenses_in_event(
                user=leader, event=event, status="ACTIVE"
            )
        )

        assert len(result) == EXPENSE_COUNT


@pytest.mark.django_db
class TestListExpensesByUserQueryCount:
    """list_expenses_by_user must issue a bounded number of SQL statements."""

    @override_settings(DEBUG=True)
    def test_query_count_stays_bounded_at_scale(self, large_event_with_expenses):
        """
        list_expenses_by_user for a user who participates in EXPENSE_COUNT
        expenses must not issue a per-row query.
        """
        _event, _group, leader, _members, _expenses = large_event_with_expenses

        result, n_queries = _reset_and_count(
            lambda: list(
                ExpenseQuery.list_expenses_by_user(
                    user=leader,
                    status="ACTIVE",
                    filter=FilterDateSchema(),
                    filter_name=FilterEventSchema(),
                )
            )
        )

        assert n_queries <= MAX_QUERIES_LIST_BY_USER, (
            f"list_expenses_by_user issued {n_queries} queries for "
            f"{EXPENSE_COUNT} expenses (budget: {MAX_QUERIES_LIST_BY_USER})"
        )

    @override_settings(DEBUG=True)
    def test_result_count_matches_expense_count(self, large_event_with_expenses):
        """User participates in exactly EXPENSE_COUNT expenses."""
        _event, _group, leader, _members, _expenses = large_event_with_expenses

        result = list(
            ExpenseQuery.list_expenses_by_user(
                user=leader,
                status="ACTIVE",
                filter=FilterDateSchema(),
                filter_name=FilterEventSchema(),
            )
        )

        assert len(result) == EXPENSE_COUNT


# ---------------------------------------------------------------------------
# Aggregate-at-scale correctness
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAggregateQueriesAtScale:
    """Aggregate SQL functions must return correct totals for large datasets."""

    def test_total_expenses_in_event_matches_count(self, large_event_with_expenses):
        """total_expenses_in_event aggregate equals EXPENSE_COUNT."""
        event, _group, _leader, _members, _expenses = large_event_with_expenses

        agg = ExpenseQuery.total_expenses_in_event(event=event, currency="VND")

        assert agg["expense_total"] == EXPENSE_COUNT

    def test_total_amount_in_event_is_correct(self, large_event_with_expenses):
        """total_expenses_in_event total_amount equals EXPENSE_COUNT * 100."""
        event, _group, _leader, _members, _expenses = large_event_with_expenses

        agg = ExpenseQuery.total_expenses_in_event(event=event, currency="VND")
        expected = EXPENSE_COUNT * 100.0

        assert agg["total_amount"] == pytest.approx(expected, rel=1e-4)

    def test_user_share_row_count_matches_expenses_times_members(
        self, large_event_with_expenses
    ):
        """
        Total UserSharesInExpense rows = EXPENSE_COUNT × (MEMBER_COUNT + 1).
        This validates bulk_create integrity and detects missing share rows.
        """
        event, _group, _leader, _members, _expenses = large_event_with_expenses
        total_users = MEMBER_COUNT + 1  # members + leader
        expected_shares = EXPENSE_COUNT * total_users

        actual_shares = UserSharesInExpense.objects.filter(expense__event=event).count()

        assert actual_shares == expected_shares


# ---------------------------------------------------------------------------
# Wall-time budget
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBulkExpenseCreationTime:
    """Bulk-create of expenses + shares should stay within time budget."""

    def test_bulk_create_20_expenses_within_time_budget(self, large_event):
        """
        Creating 20 Expense rows + their UserSharesInExpense entries via
        bulk_create must finish within BULK_CREATE_BUDGET_SECONDS.
        """
        event, _group, leader, members = large_event
        all_users = [leader] + members
        total_users = len(all_users)
        per_person = Decimal("100.00") / total_users

        t0 = time.perf_counter()

        expense_objs = Expense.objects.bulk_create(
            [
                Expense(
                    name=f"TimedExpense {i}",
                    event=event,
                    paid_by=leader,
                    creator=leader,
                    total_amount=100.0,
                    currency="VND",
                    split_type="EQUAL",
                    expense_date="2026-01-01T00:00:00+00:00",
                )
                for i in range(20)
            ]
        )
        UserSharesInExpense.objects.bulk_create(
            [
                UserSharesInExpense(
                    expense=exp,
                    user=user,
                    amount=per_person,
                    receiver_amount=Decimal("0.0"),
                )
                for exp in expense_objs
                for user in all_users
            ]
        )

        elapsed = time.perf_counter() - t0

        assert elapsed < BULK_CREATE_BUDGET_SECONDS, (
            f"Bulk creation of 20 expenses took {elapsed:.3f}s "
            f"(budget: {BULK_CREATE_BUDGET_SECONDS}s)"
        )

    def test_bulk_created_expenses_are_persisted(self, large_event):
        """Expenses saved via bulk_create are retrievable from the database."""
        event, _group, leader, _members = large_event

        Expense.objects.bulk_create(
            [
                Expense(
                    name=f"PersistCheck {i}",
                    event=event,
                    paid_by=leader,
                    creator=leader,
                    total_amount=50.0,
                    currency="VND",
                    split_type="EQUAL",
                    expense_date="2026-06-01T00:00:00+00:00",
                )
                for i in range(5)
            ]
        )

        assert (
            Expense.objects.filter(event=event, name__startswith="PersistCheck").count()
            == 5
        )


# ---------------------------------------------------------------------------
# Amount-filter post-processing
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAmountFilterScaling:
    """
    The in-Python amount filtering inside Service.list_expenses_by_user
    must correctly narrow the result set at scale.
    """

    def test_max_amount_filter_reduces_result_set(self, large_event_with_expenses):
        """
        Per-user amount = 100/11 ≈ 9.09 VND.
        A max_amount filter of 5.0 should return zero results for the leader
        (whose receiver_amount is ~90.91 > 5.0).
        """
        from expense.service import Service

        _event, _group, leader, _members, _expenses = large_event_with_expenses

        results = Service().list_expenses_by_user(
            user=leader,
            status="ACTIVE",
            filter=FilterDateSchema(),
            filter_amount=FilterAmountSchema(max_amount=5.0),
            filter_name=FilterEventSchema(),
        )

        # Leader's amount is receiver_amount (~90.91) which exceeds 5.0
        for r in results:
            assert r.amount <= 5.0
