from datetime import datetime
from typing import List, Optional
from uuid import UUID

from ninja import Field, ModelSchema, Schema

from attachment.schemas.responses import AttachmentResponse
from expense.models import Expense
from user.schemas.response import UserResponse


class UserExpense(UserResponse):
    amount: float


class ExpenseResponse(ModelSchema):
    receipt_url: List[AttachmentResponse] = Field(default_factory=list)
    list_user: List[UserExpense]

    class Meta:
        model = Expense
        exclude = [
            "name_no_accent",
            "event",
            "creator",
            "paid_by",
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
    status: str
    created_at: datetime
    deleted: Optional[str] = None


class ExpenseEvent(Schema):
    expense: List[NameExpense]
    event: str
