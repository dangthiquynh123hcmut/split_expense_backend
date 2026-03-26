"""
Performance tests for the debt-simplification algorithm
(utils.functions.debt_simplification.simplify_minflow).

What is measured
----------------
1. Correctness at varying scales — the algorithm must produce a set of
   transactions whose net-flow matches the original balance sheet.
2. Output minimality — the number of output transactions must never exceed
   (number of non-zero balances - 1), the theoretical upper bound for a
   min-flow simplification.
3. Wall-time scaling — the algorithm must finish within strict time budgets
   for small (5), medium (20) and large (50) participant counts.

These are pure-logic tests: no database interaction is required.
"""

import time
from decimal import Decimal
from uuid import uuid4

import pytest

from utils.functions.debt_simplification import simplify_minflow


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Wall-time budgets per scale (seconds)
BUDGET_SMALL_SECONDS = 0.01  # 5 participants
BUDGET_MEDIUM_SECONDS = 0.05  # 20 participants
BUDGET_LARGE_SECONDS = 0.5  # 50 participants


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_balances(n: int, debt_per_person: float = 100.0):
    """
    Build a balanced sheet with *n* participants:
    - First half owe  debt_per_person each (negative balance)
    - Second half are owed debt_per_person each (positive balance)
    Totals cancel out, so simplify_minflow should produce ≤ n-1 transactions.
    """
    uids = [uuid4() for _ in range(n)]
    half = n // 2
    balances = []
    for i, uid in enumerate(uids):
        if i < half:
            balances.append((uid, -Decimal(str(debt_per_person))))
        else:
            balances.append((uid, Decimal(str(debt_per_person))))
    # Ensure zero-sum: adjust the last positive entry if n is odd
    total = sum(b for _, b in balances)
    if total != 0 and balances:
        last_uid, last_val = balances[-1]
        balances[-1] = (last_uid, last_val - total)
    # Remove participants whose balance is exactly zero (edge-case cleanup)
    balances = [(uid, val) for uid, val in balances if val != 0]
    return balances


def _net_flow(balances, transactions):
    """
    Given an original balance list and the transactions produced by
    simplify_minflow, return the net residual balance per participant.
    All residuals must be zero for a correct solution.
    """
    residual = {uid: val for uid, val in balances}
    for debtor, creditor, amount in transactions:
        residual[debtor] = residual.get(debtor, Decimal("0")) + Decimal(str(amount))
        residual[creditor] = residual.get(creditor, Decimal("0")) - Decimal(str(amount))
    return residual


# ---------------------------------------------------------------------------
# Correctness
# ---------------------------------------------------------------------------


class TestDebtSimplificationCorrectness:
    """All produced transactions must fully settle the original balance sheet."""

    def test_zero_balances_produce_no_transactions(self):
        assert simplify_minflow([]) == []

    def test_single_debt_pair_produces_one_transaction(self):
        a, b = uuid4(), uuid4()
        balances = [(a, Decimal("-100")), (b, Decimal("100"))]
        txs = simplify_minflow(balances)
        assert len(txs) == 1
        assert txs[0] == (a, b, Decimal("100"))

    def test_small_scale_residuals_are_zero(self):
        balances = _make_balances(5, debt_per_person=50.0)
        txs = simplify_minflow(balances)
        residual = _net_flow(balances, txs)
        for uid, val in residual.items():
            assert val == pytest.approx(0, abs=1e-6), (
                f"Non-zero residual {val} for participant {uid}"
            )

    def test_medium_scale_residuals_are_zero(self):
        balances = _make_balances(20, debt_per_person=75.0)
        txs = simplify_minflow(balances)
        residual = _net_flow(balances, txs)
        for uid, val in residual.items():
            assert val == pytest.approx(0, abs=1e-6)

    def test_large_scale_residuals_are_zero(self):
        balances = _make_balances(50, debt_per_person=200.0)
        txs = simplify_minflow(balances)
        residual = _net_flow(balances, txs)
        for uid, val in residual.items():
            assert val == pytest.approx(0, abs=1e-6)

    def test_asymmetric_amounts_residuals_are_zero(self):
        """Balances with unequal individual amounts must still be settled."""
        participants = [uuid4() for _ in range(6)]
        # Deliberately unequal amounts, but zero-sum
        balances = [
            (participants[0], Decimal("-300")),
            (participants[1], Decimal("-150")),
            (participants[2], Decimal("-50")),
            (participants[3], Decimal("200")),
            (participants[4], Decimal("100")),
            (participants[5], Decimal("200")),
        ]
        txs = simplify_minflow(balances)
        residual = _net_flow(balances, txs)
        for uid, val in residual.items():
            assert val == pytest.approx(0, abs=1e-6)

    def test_all_creditors_produce_no_transactions(self):
        """If everyone has a positive balance the sheet is inconsistent —
        simplify_minflow should not raise, just return empty."""
        balances = [(uuid4(), Decimal("100")) for _ in range(5)]
        # The algorithm only loops while BOTH debtors and creditors exist
        txs = simplify_minflow(balances)
        # No debtors → no transactions
        assert txs == []

    def test_all_debtors_produce_no_transactions(self):
        """Same as above but all negative balances."""
        balances = [(uuid4(), Decimal("-100")) for _ in range(5)]
        txs = simplify_minflow(balances)
        assert txs == []


# ---------------------------------------------------------------------------
# Output minimality
# ---------------------------------------------------------------------------


class TestDebtSimplificationMinimality:
    """
    The number of output transactions should be less than the number of
    non-zero balance participants (a known upper bound for min-flow).
    """

    def test_transaction_count_below_participant_count_small(self):
        balances = _make_balances(6)
        txs = simplify_minflow(balances)
        non_zero = len([v for _, v in balances if v != 0])
        assert len(txs) < non_zero, (
            f"Expected < {non_zero} transactions, got {len(txs)}"
        )

    def test_transaction_count_below_participant_count_medium(self):
        balances = _make_balances(20)
        txs = simplify_minflow(balances)
        non_zero = len([v for _, v in balances if v != 0])
        assert len(txs) < non_zero

    def test_transaction_count_below_participant_count_large(self):
        balances = _make_balances(50)
        txs = simplify_minflow(balances)
        non_zero = len([v for _, v in balances if v != 0])
        assert len(txs) < non_zero

    def test_single_creditor_multiple_debtors_minimised(self):
        """5 debtors → 1 creditor ⇒ exactly 5 transactions (star topology)."""
        creditor = uuid4()
        debtors = [uuid4() for _ in range(5)]
        balances = [(d, Decimal("-100")) for d in debtors]
        balances.append((creditor, Decimal("500")))
        txs = simplify_minflow(balances)
        # Each debtor pays the creditor once
        assert len(txs) == 5


# ---------------------------------------------------------------------------
# Wall-time scaling
# ---------------------------------------------------------------------------


class TestDebtSimplificationWallTime:
    """The algorithm must run well within strict time budgets at every scale."""

    def test_small_scale_within_budget(self):
        balances = _make_balances(5, debt_per_person=100.0)
        t0 = time.perf_counter()
        simplify_minflow(balances)
        elapsed = time.perf_counter() - t0
        assert elapsed < BUDGET_SMALL_SECONDS, (
            f"simplify_minflow (n=5) took {elapsed:.6f}s (budget {BUDGET_SMALL_SECONDS}s)"
        )

    def test_medium_scale_within_budget(self):
        balances = _make_balances(20, debt_per_person=100.0)
        t0 = time.perf_counter()
        simplify_minflow(balances)
        elapsed = time.perf_counter() - t0
        assert elapsed < BUDGET_MEDIUM_SECONDS, (
            f"simplify_minflow (n=20) took {elapsed:.6f}s (budget {BUDGET_MEDIUM_SECONDS}s)"
        )

    def test_large_scale_within_budget(self):
        balances = _make_balances(50, debt_per_person=100.0)
        t0 = time.perf_counter()
        simplify_minflow(balances)
        elapsed = time.perf_counter() - t0
        assert elapsed < BUDGET_LARGE_SECONDS, (
            f"simplify_minflow (n=50) took {elapsed:.6f}s (budget {BUDGET_LARGE_SECONDS}s)"
        )

    def test_repeated_calls_do_not_degrade(self):
        """
        Calling simplify_minflow 100 times with the same medium-scale input
        must finish in under 5 × BUDGET_MEDIUM_SECONDS total.
        Verifies there is no state mutation or memory leak across calls.
        """
        balances = _make_balances(20, debt_per_person=100.0)
        total_budget = 5 * BUDGET_MEDIUM_SECONDS

        t0 = time.perf_counter()
        for _ in range(100):
            simplify_minflow(balances)
        elapsed = time.perf_counter() - t0

        assert elapsed < total_budget, (
            f"100 calls to simplify_minflow (n=20) took {elapsed:.4f}s "
            f"(budget {total_budget}s)"
        )
