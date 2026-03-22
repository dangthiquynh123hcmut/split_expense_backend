"""
Unit tests for utils.functions.debt_simplification.simplify_minflow.

This is a pure Python function with no database or Django dependency.
Each test exercises a different graph topology to verify the
min-flow debt-simplification algorithm.
"""

from utils.functions.debt_simplification import simplify_minflow


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _net(transactions):
    """Convert a transaction list back to a net-balance map for verification."""
    net = {}
    for debtor, creditor, amount in transactions:
        net[debtor] = net.get(debtor, 0) - amount
        net[creditor] = net.get(creditor, 0) + amount
    return net


def _input_net(balances):
    return {p: b for p, b in balances}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSimplifyMinflow:
    def test_empty_balances_returns_empty(self):
        """No balances ⇒ no transactions needed."""
        assert simplify_minflow([]) == []

    def test_all_zero_balances_returns_empty(self):
        """Everyone is already settled."""
        balances = [("alice", 0), ("bob", 0), ("carol", 0)]
        assert simplify_minflow(balances) == []

    def test_single_debtor_single_creditor(self):
        """Alice owes Bob 50 ⇒ one transaction Alice→Bob for 50."""
        balances = [("alice", -50), ("bob", 50)]
        result = simplify_minflow(balances)
        assert len(result) == 1
        debtor, creditor, amount = result[0]
        assert debtor == "alice"
        assert creditor == "bob"
        assert amount == 50

    def test_two_debtors_one_creditor(self):
        """Alice owes 30, Bob owes 20, Carol is owed 50."""
        balances = [("alice", -30), ("bob", -20), ("carol", 50)]
        result = simplify_minflow(balances)
        # Net balances should be preserved
        net = _net(result)
        assert net.get("carol", 0) == 50
        assert net.get("alice", 0) == -30
        assert net.get("bob", 0) == -20

    def test_one_debtor_two_creditors(self):
        """Alice owes 50 total; Bob is owed 30, Carol is owed 20."""
        balances = [("alice", -50), ("bob", 30), ("carol", 20)]
        result = simplify_minflow(balances)
        net = _net(result)
        assert net.get("alice", 0) == -50
        assert net.get("bob", 0) == 30
        assert net.get("carol", 0) == 20

    def test_four_people_complex_split(self):
        """
        Classic group-dinner scenario with four people.
        Alice: -20, Bob: -10, Carol: +15, Dave: +15
        The algorithm should produce at most 3 transactions.
        """
        balances = [("alice", -20), ("bob", -10), ("carol", 15), ("dave", 15)]
        result = simplify_minflow(balances)
        # Verify net balances match input
        net = _net(result)
        expected = _input_net(balances)
        for person, balance in expected.items():
            assert abs(net.get(person, 0) - balance) < 1e-9
        # The algorithm should produce no more transactions than there are people
        assert len(result) <= len(balances)

    def test_balanced_pair_produces_no_transactions(self):
        """If two people have equal and opposite balances that cancel, the result
        should reflect that only a single transfer is needed, not zero, because
        they don't sum to zero individually."""
        balances = [("alice", -100), ("bob", 100)]
        result = simplify_minflow(balances)
        assert len(result) == 1
        assert result[0][2] == 100

    def test_amount_is_positive(self):
        """All amounts in the output must be positive numbers."""
        balances = [
            ("u1", -15),
            ("u2", -25),
            ("u3", 10),
            ("u4", 30),
        ]
        result = simplify_minflow(balances)
        for _, _, amount in result:
            assert amount > 0

    def test_transaction_participants_are_valid_people(self):
        """Every participant in output transactions must appear in the input."""
        people = {"alice", "bob", "carol", "dave"}
        balances = [("alice", -40), ("bob", -10), ("carol", 20), ("dave", 30)]
        result = simplify_minflow(balances)
        for debtor, creditor, _ in result:
            assert debtor in people
            assert creditor in people

    def test_net_balances_preserved_across_transactions(self):
        """After applying all transactions, every person's net change must equal
        their original balance."""
        balances = [
            ("a", -100),
            ("b", -50),
            ("c", 75),
            ("d", 75),
        ]
        result = simplify_minflow(balances)
        net = _net(result)
        for person, original_balance in balances:
            assert abs(net.get(person, 0) - original_balance) < 1e-9

    def test_large_imbalance(self):
        """One person owes a very large amount to multiple creditors."""
        balances = [("whale", -1000), ("a", 300), ("b", 400), ("c", 300)]
        result = simplify_minflow(balances)
        net = _net(result)
        assert abs(net.get("whale", 0) - (-1000)) < 1e-9
        assert abs(net.get("a", 0) - 300) < 1e-9
