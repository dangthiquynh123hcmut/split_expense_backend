from typing import Optional
from uuid import UUID

from ninja import Schema


class TransferRequest(Schema):
    amount: float
    currency: str
    user_uid: UUID
    description: Optional[str] = ""
    group_uid: Optional[UUID] = None
    transfer_token: str


class VerifyPinRequest(Schema):
    pin: str
    amount: float


class WithdrawRequest(Schema):
    account_number: str
    amount: float
    bank_name: str
