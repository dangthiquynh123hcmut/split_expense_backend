from ninja import Schema


# class TransactionRequest(Schema):
#     amount: float
#     currency: str


class WithdrawRequest(Schema):
    account_number: str
    amount: float
    bank_name: str
