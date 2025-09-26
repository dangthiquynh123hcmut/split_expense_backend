from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ninja import Schema
from pydantic import Field

from utils.enums import SplitTypeEnum


class AmountExpenseMember(Schema):
    user_uid: UUID
    amount: Decimal


class ExpenseRequest(Schema):
    name: str
    total_amount: Decimal = Field(..., gt=0)
    currency: str
    category: str
    event_uid: UUID
    paid_by: Optional[UUID] = None
    note: Optional[str] = None
    expense_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    split_type: SplitTypeEnum
    list_expense_member: List[AmountExpenseMember]


class ExpenseUpdateRequest(Schema):
    name: str
    total_amount: Decimal = Field(..., gt=0)
    currency: str
    category: str
    paid_by: Optional[UUID] = None
    note: Optional[str] = None
    expense_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    split_type: SplitTypeEnum
    list_expense_member: List[AmountExpenseMember]
