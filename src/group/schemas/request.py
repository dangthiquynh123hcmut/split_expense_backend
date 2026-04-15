from typing import List, Optional
from uuid import UUID

from ninja import Schema


class GroupRequest(Schema):
    name: str
    list_user_uids: List[UUID]


class GroupUpdateRequest(Schema):
    name: str
    list_add_uids: Optional[List[UUID]] = []
    list_delete_uids: Optional[List[UUID]] = []


class UpdateGroupLeaderRequest(Schema):
    new_leader: UUID


class RemindRequest(Schema):
    user_uid: Optional[UUID] = None


class ExternalTransferRequest(Schema):
    amount: float
    user_uid: UUID
