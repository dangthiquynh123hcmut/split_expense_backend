from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ninja import Field, ModelSchema, Schema

from attachment.schemas.responses import AttachmentResponse
from expense.models import Expense
from user.schemas.response import UserResponse


class UserExpense(UserResponse):
    amount: Decimal


class ExpenseResponse(ModelSchema):
    receipt_url: List[AttachmentResponse] = Field(default_factory=list)
    list_user: List[UserExpense]
    paid_by: UserResponse

    class Meta:
        model = Expense
        exclude = [
            "name_no_accent",
            "creator",
            "receipt_url",
            "created_at",
            "split_type",
        ]


class CreateExpense(ModelSchema):
    class Meta:
        model = Expense
        exclude = [
            "name_no_accent",
            "status",
            "event",
            "creator",
            "paid_by",
            "receipt_url",
        ]


class ExpenseMemberResponse(Schema):
    user: UserResponse
    status: str
    amount: float


class ExpenseDetailResponse(ModelSchema):
    expense_members: List[ExpenseMemberResponse]

    class Meta:
        model = Expense
        exclude = [
            "name_no_accent",
            "status",
            "event",
            "creator",
            "created_at",
            "split_type",
        ]


class NameExpense(Schema):
    uid: UUID
    name: str
    currency: str
    amount: float
    created_at: datetime
    status: Optional[str] = None
    category: Optional[str] = None
    from_user: Optional[str] = None
    to_user: Optional[str] = None
    event: Optional[str] = None
