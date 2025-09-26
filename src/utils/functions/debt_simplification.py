def simplify_minflow(balances):
    transactions = []
    debtors = {p: b for (p, b) in balances.items() if b < 0}
    creditors = {p: b for (p, b) in balances.items() if b > 0}
    while debtors:
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


def compute_balances(list_users, list_debts):
    balances = {user: 0 for user in list_users}
    for debtor, creditor, value in list_debts:
        balances[debtor] -= value
        balances[creditor] += value
    return balances


def debt_simplification(list_users, list_debts):
    balances = compute_balances(list_users, list_debts)
    return simplify_minflow(balances), balances
