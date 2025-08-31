from typing import List, Optional
from uuid import UUID

from ninja import Schema


class ExpenseResponse(Schema):
    uid: UUID
    name: str
    avatar_url: Optional[str]
    list_user_uid: List[UUID]


class ExpenseMemberResponse(Schema):
    uid: UUID
    user_uid: UUID
    expense_uid: UUID
    status: str


class ExpenseDetailResponse(Schema):
    uid: UUID
    name: str
    avatar_url: Optional[str]
    list_user_uid: List[UUID]
    list_expense_member_uid: List[UUID]
