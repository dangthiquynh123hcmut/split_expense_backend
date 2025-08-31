from typing import List, Optional
from uuid import UUID

from ninja import Schema


class ExpenseRequest(Schema):
    name: str
    avatar_url: Optional[str]
    list_user_uid: List[UUID]


class ExpenseUpdateRequest(Schema):
    name: str
    avatar_url: Optional[str]
    list_user_uid: List[UUID]


class FilterExpenseSchema(Schema):
    name: Optional[str]
    avatar_url: Optional[str]
    list_user_uid: Optional[List[UUID]]


class OrderByExpenseSchema(Schema):
    name: Optional[str]
    avatar_url: Optional[str]
    list_user_uid: Optional[List[UUID]]
