from typing import List, Optional
from uuid import UUID

from ninja import Schema


class GroupRequest(Schema):
    name: str
    avatar_url: Optional[str] = None
    list_user_uid: List[UUID]


class GroupUpdateRequest(Schema):
    name: str
    avatar_url: Optional[str] = None
    list_user_uid: List[UUID] = []
