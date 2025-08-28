from typing import Optional
from uuid import UUID

from ninja import ModelSchema, Schema
from pydantic import ConfigDict

from friend.models import Friend


class AddFriendResponse(Schema):
    receiver_uid: UUID
    requester_uid: UUID
    message: Optional[str]
    avatar_url: Optional[str] = None
    full_name: str


class UserResponse(Schema):
    uid: UUID
    full_name: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FriendResponse(ModelSchema):
    user: UserResponse
    friend: UserResponse

    class Meta:
        model = Friend
        exclude = ["created_at", "updated_at", "message_request"]
