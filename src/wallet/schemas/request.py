from typing import Optional
from uuid import UUID

from ninja import Schema


class TransferRequest(Schema):
    original_amount: float
    convert_amount: float
    currency: str
    user_uid: UUID
    description: Optional[str] = ""
    group_uid: Optional[UUID] = None
    transfer_token: str
    event_uid: Optional[UUID] = None


class VerifyPinRequest(Schema):
    pin: str
    amount: float


class WithdrawRequest(Schema):
    account_number: str
    amount: float
    bank_name: str
    description: Optional[str] = None
