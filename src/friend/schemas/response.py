from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import ModelSchema, Schema

from attachment.schemas.responses import AttachmentResponse
from group.models import RestructureDebt
from group.schemas.response import GroupName
from user.schemas.response import UserResponse


class AddFriendResponse(Schema):
    receiver_uid: UUID
    requester_uid: UUID
    message: Optional[str]
    avatar_url: Optional[AttachmentResponse] = None
    full_name: str


class FriendResponse(Schema):
    friend_uid: UUID
    full_name: str
    avatar_url: Optional[AttachmentResponse] = None
    friendship_uid: UUID
    start: Optional[datetime] = None


class RequestAddFriend(FriendResponse):
    message_request: Optional[str]


class FriendOverview(Schema):
    friend: UserResponse
    message: Optional[str] = None
    status: str
    friendship_uid: Optional[UUID] = None
    mutual_groups: int = 0
    shared_events: int = 0
    shared_expenses: int = 0
    total_debt: float = 0.0


class FriendDebt(ModelSchema):
    group: GroupName
    creditor: UserResponse
    debtor: UserResponse

    class Meta:
        model = RestructureDebt
        exclude = ["uid", "created_at", "updated_at"]
