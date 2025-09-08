from typing import List
from uuid import UUID

from ninja import Schema


class GroupRequest(Schema):
    name: str
    list_user_uid: List[UUID]


class GroupUpdateRequest(Schema):
    name: str
    list_user_uid: List[UUID] = []
