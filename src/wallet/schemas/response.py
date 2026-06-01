from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from ninja import Field, ModelSchema, Schema

from bank_account.schemas.responses import BankAccountResponse
from user.schemas.response import UserResponse
from wallet.models import WalletDeposit, Withdraw


class WalletDepositResponse(ModelSchema):
    class Meta:
        model = WalletDeposit
        fields = "__all__"


class WalletWithdrawResponse(ModelSchema):
    user: UserResponse
    bank_account: BankAccountResponse

    class Meta:
        model = Withdraw
        fields = "__all__"


class TransactionHistoryResponse(Schema):
    uid: UUID
    type: Literal["deposit", "withdraw"]
    amount: Decimal
    currency: Optional[str] = None
    code: str
    date: datetime = Field(..., alias="created_at")


class TransactionResponse(Schema):
    from_user: UserResponse
    to_user: UserResponse
    amount: float
    description: Optional[str] = None
    group: Optional[str] = None
    code: str
    created_at: datetime
    event: Optional[str] = None


class ListTransactionResponse(Schema):
    from_user: str
    to_user: str
    amount: Decimal
    description: Optional[str] = None
    group: Optional[str] = None
    code: str
    created_at: datetime
