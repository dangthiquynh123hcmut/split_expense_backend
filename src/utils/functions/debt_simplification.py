import itertools

import networkx as nx


def edge_inverter(edge):
    if edge[0] < edge[1]:
        return (1, (edge[0], edge[1]))
    else:
        return (-1, (edge[1], edge[0]))


def simplify_transactions(G):
    G = G.copy()
    while True:
        try:
            cycle = nx.algorithms.cycles.find_cycle(G.to_undirected())
        except nx.exception.NetworkXNoCycle:
            break

        inverted, edge_to_remove = edge_inverter(cycle[0])
        amount_to_remove = G[edge_to_remove[0]][edge_to_remove[1]]["weight"] * inverted

        for edge in cycle:
            inverter, edge = edge_inverter(edge)
            G[edge[0]][edge[1]]["weight"] -= amount_to_remove * inverter
            if G[edge[0]][edge[1]]["weight"] == 0:
                G.remove_edge(edge[0], edge[1])
    return G


def to_transactions(graph):
    transactions = []
    for edge in graph.edges:
        inverter, (node1, node2) = edge_inverter(edge)
        owed = graph[node1][node2]["weight"] * inverter
        debtor, creditor, value = (
            (node1, node2, owed) if owed > 0 else (node2, node1, -owed)
        )

        transactions.append({"debtor": debtor, "creditor": creditor, "value": value})

    return transactions


def order_debt(debt):
    debtor, creditor, value = debt
    if debtor < creditor:
        return debt
    else:
        return (creditor, debtor, -value)


def filter_debt(debt):
    debtor, creditor, value = debt
    return value != 0 and debtor != creditor


def tidy_debts(debt_list):
    ordered = sorted([order_debt(d) for d in debt_list if order_debt(d) is not None])
    grouped = itertools.groupby(ordered, lambda debt: (debt[0], debt[1]))
    summed = [(key[0], key[1], sum([d[2] for d in debts])) for (key, debts) in grouped]
    return [d for d in summed if filter_debt(d)]


def compute_balances(list_users, list_debts):
    balances = {user: 0 for user in list_users}
    for debtor, creditor, value in list_debts:
        balances[debtor] -= value
        balances[creditor] += value
    return balances


def debt_simplification(list_users, list_debts):
    G = nx.DiGraph()
    G.add_nodes_from(list_users)
    G.add_weighted_edges_from(tidy_debts(list_debts))
    simplified = simplify_transactions(G)
    balances = compute_balances(list_users, list_debts)
    return to_transactions(simplified), balances
