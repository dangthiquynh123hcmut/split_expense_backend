from typing import List
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
            "status",
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
    expense_uid: UUID = Field(..., alias="uid")
    name: str
    currency: str


class ListExpenseResponse(Schema):
    name_expense: NameExpense
    status: str
    amount: float
