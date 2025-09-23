from typing import List
from uuid import UUID

from ninja import Field, ModelSchema, Schema

from attachment.schemas.responses import AttachmentResponse
from expense.models import Expense


class ExpenseResponse(ModelSchema):
    receipt_url: List[AttachmentResponse] = Field(default_factory=list)

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
    user_uid: UUID
    full_name: str
    avatar_url: str
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
