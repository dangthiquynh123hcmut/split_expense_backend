"""
Performance tests for wallet ORM queries.

What is measured
----------------
1. Query-count efficiency — list_transactions and
   get_external_transaction_history must issue a bounded number of SQL
   statements even when there are many rows in the database.
2. Bulk transaction creation wall-time — TX_COUNT wallet transactions
   must be bulk-created within an acceptable time budget.
3. Aggregate correctness — count helpers must return accurate totals for
   large datasets.
4. Balance update atomicity at scale — update_balance_in_wallet must
   correctly adjust the user's balance using F() expressions, verifying
   no race condition artefacts in a single-threaded SQLite context.

Fixtures are supplied by tests/performance/conftest.py.
"""

import time
from decimal import Decimal

import pytest
from django.db import connection, reset_queries
from django.test.utils import override_settings

from tests.performance.conftest import TX_COUNT, make_user
from utils.schemas.filter_and_order_by import (
    FilterCodeSchema,
    FilterDateAndAmountSchema,
    FilterGroupSchema,
)
from wallet.models import Transaction, WalletDeposit
from wallet.orm.transaction import TransactionORM


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

MAX_QUERIES_LIST_TXS = 5  # list_transactions max SQL statements
MAX_QUERIES_EXTERNAL_HISTORY = 5  # get_external_transaction_history max
BULK_TX_BUDGET_SECONDS = 3.0  # wall-time for creating TX_COUNT transactions


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _reset_and_count(fn):
    reset_queries()
    result = fn()
    return result, len(connection.queries)


# ---------------------------------------------------------------------------
# list_transactions query count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListTransactionsQueryCount:
    """list_transactions must issue a bounded number of SQL queries."""

    @override_settings(DEBUG=True)
    def test_query_count_bounded_for_many_transactions(self, bulk_transactions):
        """
        With TX_COUNT rows, list_transactions must not issue per-row queries.
        """
        _txs, leader, _receiver = bulk_transactions

        result, n_queries = _reset_and_count(
            lambda: list(
                TransactionORM.list_transactions(
                    user=leader,
                    filter=FilterGroupSchema(),
                    filter_date_and_amount=FilterDateAndAmountSchema(),
                )
            )
        )

        assert n_queries <= MAX_QUERIES_LIST_TXS, (
            f"list_transactions issued {n_queries} queries for {TX_COUNT} rows "
            f"(budget: {MAX_QUERIES_LIST_TXS})"
        )

    def test_returned_count_equals_tx_count(self, bulk_transactions):
        """
        All TX_COUNT transactions are visible to the sender.
        """
        _txs, leader, _receiver = bulk_transactions

        results = list(
            TransactionORM.list_transactions(
                user=leader,
                filter=FilterGroupSchema(),
                filter_date_and_amount=FilterDateAndAmountSchema(),
            )
        )

        assert len(results) == TX_COUNT

    def test_all_transactions_visible_to_receiver(self, bulk_transactions):
        """Receiver also sees all TX_COUNT transactions in their history."""
        _txs, _leader, receiver = bulk_transactions

        results = list(
            TransactionORM.list_transactions(
                user=receiver,
                filter=FilterGroupSchema(),
                filter_date_and_amount=FilterDateAndAmountSchema(),
            )
        )

        assert len(results) == TX_COUNT


# ---------------------------------------------------------------------------
# get_external_transaction_history query count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestExternalTransactionHistoryQueryCount:
    """
    get_external_transaction_history performs a UNION of deposits and
    withdrawals; it must issue a bounded number of statements.
    """

    def _create_deposits(self, user, count: int = 25):
        # Use .create() so the model's save() sets the unique `code` field.
        for _ in range(count):
            WalletDeposit.objects.create(
                user=user, amount=Decimal("100.00"), currency="VND"
            )

    @override_settings(DEBUG=True)
    def test_query_count_bounded_with_many_deposits(self, large_group, db):
        _group, leader, _members = large_group
        self._create_deposits(leader, count=25)

        result, n_queries = _reset_and_count(
            lambda: list(
                TransactionORM.get_external_transaction_history(
                    user=leader,
                    filter_code=FilterCodeSchema(),
                    filter=FilterDateAndAmountSchema(),
                )
            )
        )

        assert n_queries <= MAX_QUERIES_EXTERNAL_HISTORY, (
            f"get_external_transaction_history issued {n_queries} queries "
            f"for 25 deposits (budget: {MAX_QUERIES_EXTERNAL_HISTORY})"
        )

    def test_deposit_rows_appear_in_history(self, large_group, db):
        """All created WalletDeposit rows must surface in the history."""
        _group, leader, _members = large_group
        self._create_deposits(leader, count=10)

        results = list(
            TransactionORM.get_external_transaction_history(
                user=leader,
                filter_code=FilterCodeSchema(),
                filter=FilterDateAndAmountSchema(),
            )
        )

        deposit_rows = [r for r in results if r["type"] == "deposit"]
        assert len(deposit_rows) == 10


# ---------------------------------------------------------------------------
# Bulk transaction creation wall-time
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBulkTransactionCreationTime:
    """bulk_create of TX_COUNT transactions must be within time budget."""

    def test_bulk_create_transactions_within_budget(self, large_group):
        _group, leader, members = large_group
        receiver = members[0]

        # Pre-generate unique codes because bulk_create bypasses save().
        # Format: 5-char prefix + 25-digit zero-padded index = 30 chars (max_length).
        t0 = time.perf_counter()
        Transaction.objects.bulk_create(
            [
                Transaction(
                    from_user=leader,
                    to_user=receiver,
                    amount=Decimal("25.00"),
                    currency="VND",
                    description=f"Perf Timed TX {i}",
                    code=f"BULK-{i:025d}",
                )
                for i in range(TX_COUNT)
            ]
        )
        elapsed = time.perf_counter() - t0

        assert elapsed < BULK_TX_BUDGET_SECONDS, (
            f"Bulk-creating {TX_COUNT} transactions took {elapsed:.3f}s "
            f"(budget: {BULK_TX_BUDGET_SECONDS}s)"
        )

    def test_bulk_created_transactions_are_persisted(self, large_group):
        _group, leader, members = large_group
        receiver = members[1]

        Transaction.objects.bulk_create(
            [
                Transaction(
                    from_user=leader,
                    to_user=receiver,
                    amount=Decimal("10.00"),
                    currency="VND",
                    description=f"PersistTX {i}",
                    code=f"PRSV-{i:025d}",
                )
                for i in range(10)
            ]
        )

        count = Transaction.objects.filter(
            from_user=leader, to_user=receiver, description__startswith="PersistTX"
        ).count()
        assert count == 10


# ---------------------------------------------------------------------------
# Balance update via F() expressions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBalanceUpdateCorrectness:
    """
    update_balance_in_wallet must accurately update balances using F()
    expressions — no Python-side arithmetic, no stale reads.
    """

    def test_single_credit_updates_balance(self, db):
        user = make_user("wallet_perf_credit@example.com", "0899000001", balance=0.0)

        TransactionORM.update_balance_in_wallet(uid=user.uid, amount=Decimal("500.00"))

        user.refresh_from_db()
        assert user.balance == pytest.approx(500.0)

    def test_single_debit_updates_balance(self, db):
        user = make_user("wallet_perf_debit@example.com", "0899000002", balance=1000.0)

        TransactionORM.update_balance_in_wallet(uid=user.uid, amount=Decimal("-300.00"))

        user.refresh_from_db()
        assert user.balance == pytest.approx(700.0)

    def test_repeated_updates_accumulate_correctly(self, db):
        """
        Applying 10 increments of 100 to a zero-balance user must yield 1000.
        This validates F() expression chaining (no stale-read drift).
        """
        user = make_user("wallet_perf_accum@example.com", "0899000003", balance=0.0)

        for _ in range(10):
            TransactionORM.update_balance_in_wallet(
                uid=user.uid, amount=Decimal("100.00")
            )

        user.refresh_from_db()
        assert user.balance == pytest.approx(1000.0)

    def test_balance_update_for_many_users_within_budget(self, large_group):
        """
        Updating balances for MEMBER_COUNT users sequentially (as happens
        during settlement) must complete within a reasonable time.
        """
        _group, leader, members = large_group
        all_users = [leader] + members
        budget = 2.0  # seconds

        t0 = time.perf_counter()
        for user in all_users:
            TransactionORM.update_balance_in_wallet(
                uid=user.uid, amount=Decimal("50.00")
            )
        elapsed = time.perf_counter() - t0

        assert elapsed < budget, (
            f"Sequential balance updates for {len(all_users)} users took "
            f"{elapsed:.3f}s (budget: {budget}s)"
        )

        # Spot-check one user
        leader.refresh_from_db()
        assert leader.balance == pytest.approx(1_000_050.0)


# ---------------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTransactionAggregates:
    """Count and total helpers must be accurate for large datasets."""

    def test_get_total_transactions_matches_tx_count(self, bulk_transactions):
        _txs, leader, _receiver = bulk_transactions

        total = TransactionORM.get_total_transactions(user=leader)

        assert total == TX_COUNT

    @override_settings(DEBUG=True)
    def test_get_total_transactions_single_query(self, bulk_transactions):
        _txs, leader, _receiver = bulk_transactions

        reset_queries()
        TransactionORM.get_total_transactions(user=leader)
        n_queries = len(connection.queries)

        assert n_queries == 1, (
            f"get_total_transactions issued {n_queries} queries (expected 1)"
        )
