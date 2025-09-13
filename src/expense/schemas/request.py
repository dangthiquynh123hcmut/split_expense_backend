from datetime import date
from typing import List, Optional
from uuid import UUID

from ninja import Schema
from pydantic import Field

from attachment.schemas.requests import GeneratePresignedUrlSchema
from utils.enums import SplitTypeEnum


class AmountExpenseMember(Schema):
    user_uid: UUID
    amount: float


class ExpenseRequest(Schema):
    name: str
    total_amount: float = Field(..., gt=0)
    currency: str
    category: str
    event_uid: UUID
    paid_by: Optional[UUID] = None
    note: Optional[str] = None
    expense_date: Optional[date] = None
    remaind_at: Optional[date] = None
    split_type: SplitTypeEnum
    list_expense_member: List[AmountExpenseMember]
    list_attachment: List[GeneratePresignedUrlSchema]


class ExpenseUpdateRequest(Schema):
    name: str
    total_amount: float = Field(..., gt=0)
    currency: str
    category: str
    paid_by: Optional[UUID] = None
    note: Optional[str] = None
    expense_date: Optional[date] = None
    remaind_at: Optional[date] = None
    split_type: SplitTypeEnum
    list_expense_member: List[AmountExpenseMember]
