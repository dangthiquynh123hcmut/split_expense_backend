from ninja import Schema


class TransactionRequest(Schema):
    amount: float
    currency: str
