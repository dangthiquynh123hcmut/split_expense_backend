from typing import List
from uuid import UUID

from ninja import Schema


class GroupRequest(Schema):
    name: str
    avatar_url: str
    list_user_uid: List[UUID]
