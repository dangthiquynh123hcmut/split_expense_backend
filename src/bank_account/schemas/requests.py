from ninja import Schema


class BankAccountRequest(Schema):
    bank_name: str
    account_number: str
    currency: str


class BankAccountUpdateRequest(Schema):
    bank_name: str
    account_number: str
    currency: str
