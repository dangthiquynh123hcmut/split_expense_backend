from typing import Optional
from uuid import UUID

from ninja import Schema


class AddFriendResponse(Schema):
    receiver_uid: UUID
    requester_uid: UUID
    message: Optional[str]
    avatar_url: Optional[str] = None
    full_name: str


class FriendResponse(Schema):
    friend_uid: UUID
    full_name: str
    avatar_url: Optional[str] = None
    friendship_uid: UUID


class RequestAddFriend(FriendResponse):
    message_request: Optional[str]
