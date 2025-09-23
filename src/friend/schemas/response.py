from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Schema

from attachment.schemas.responses import AttachmentResponse


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
