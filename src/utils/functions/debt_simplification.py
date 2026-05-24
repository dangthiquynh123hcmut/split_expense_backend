def simplify_minflow(balances):
    transactions = []
    debtors = {p: b for (p, b) in balances if b < 0}
    creditors = {p: b for (p, b) in balances if b > 0}

    matched_debtors = []
    matched_creditors = []

    for debtor, debt_amount in debtors.items():
        for creditor, credit_amount in creditors.items():
            # debt_amount là số âm
            if -debt_amount == credit_amount:
                transactions.append((debtor, creditor, credit_amount))

                matched_debtors.append(debtor)
                matched_creditors.append(creditor)

                break

    for debtor in matched_debtors:
        del debtors[debtor]

    for creditor in matched_creditors:
        del creditors[creditor]

    while debtors and creditors:
        max_creditor = max(creditors, key=creditors.get)
        min_debtor = min(debtors, key=debtors.get)

        amount = min(-debtors[min_debtor], creditors[max_creditor])

        transactions.append((min_debtor, max_creditor, amount))

        debtors[min_debtor] += amount
        creditors[max_creditor] -= amount

        if debtors.get(min_debtor, 0) == 0:
            del debtors[min_debtor]
        if creditors.get(max_creditor, 0) == 0:
            del creditors[max_creditor]
    return transactions


def _collect_atomic_groups(mask, parent, result):
    """Recursively collect atomic (unsplittable) subgroups from the DP parent table."""
    if mask == 0:
        return
    if parent[mask] == -1:
        result.append(mask)
        return
    left = parent[mask]
    right = mask ^ left
    _collect_atomic_groups(left, parent, result)
    _collect_atomic_groups(right, parent, result)


def simplify_minflow_optimal(balances):
    n = len(balances)
    uids = [p[0] for p in balances]
    vals = [p[1] for p in balances]

    # dp[mask] = minimum transactions to settle the subset represented by mask
    dp = [float("inf")] * (1 << n)
    # parent[mask] = the submask used to split mask for the optimal cost
    parent = [-1] * (1 << n)
    dp[0] = 0

    for mask in range(1, 1 << n):
        balance_sum = sum(vals[i] for i in range(n) if mask >> i & 1)

        if balance_sum == 0:
            # Base cost: settle n people in a zero-sum group needs n-1 transactions
            dp[mask] = bin(mask).count("1") - 1

            # Try splitting into two independent zero-sum subgroups
            submask = (mask - 1) & mask
            while submask > 0:
                if dp[submask] != float("inf") and dp[mask ^ submask] != float("inf"):
                    cost = dp[submask] + dp[mask ^ submask]
                    if cost < dp[mask]:
                        dp[mask] = cost
                        parent[mask] = submask
                submask = (submask - 1) & mask

    # Collect atomic groups (subgroups that cannot be split further optimally)
    atomic_groups = []
    full_mask = (1 << n) - 1
    _collect_atomic_groups(full_mask, parent, atomic_groups)

    # Greedily settle each atomic group
    transactions = []
    for group_mask in atomic_groups:
        persons = [(uids[i], vals[i]) for i in range(n) if group_mask >> i & 1]
        debtors = {uid: -bal for uid, bal in persons if bal < 0}
        creditors = {uid: bal for uid, bal in persons if bal > 0}

        while debtors and creditors:
            max_creditor = max(creditors, key=creditors.get)
            max_debtor = max(debtors, key=debtors.get)
            amount = min(debtors[max_debtor], creditors[max_creditor])
            transactions.append((max_debtor, max_creditor, amount))
            debtors[max_debtor] -= amount
            creditors[max_creditor] -= amount
            if debtors[max_debtor] == 0:
                del debtors[max_debtor]
            if creditors[max_creditor] == 0:
                del creditors[max_creditor]

    return transactions
