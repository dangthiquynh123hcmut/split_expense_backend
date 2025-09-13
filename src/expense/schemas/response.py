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


class List_attachment(Schema):
    uid: UUID
    url: str


class CreateExpenseResponse(Schema):
    list_attachment: List[List_attachment]
    expense: CreateExpense


class ExpenseMemberResponse(Schema):
    uid: UUID
    user_uid: UUID
    expense_uid: UUID
    status: str


class ExpenseDetailResponse(Schema):
    uid: UUID
    name: str
    list_user_uid: List[UUID]
    list_expense_member_uid: List[UUID]


class NameExpense(Schema):
    expense_uid: UUID = Field(..., alias="uid")
    name: str
    currency: str


class ListExpenseResponse(Schema):
    name_expense: NameExpense
    status: str
    amount: float
