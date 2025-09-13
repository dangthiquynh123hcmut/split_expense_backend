from uuid import UUID

from ninja import Field, ModelSchema, Schema

from attachment.schemas.responses import AttachmentResponse
from group.models import Group
from user.schemas.response import UserResponse


class GroupResponse(ModelSchema):
    avatar_url: AttachmentResponse | None = None

    class Meta:
        model = Group
        exclude = ["created_at", "updated_at", "status", "name_no_accent"]


class CreateGroup(ModelSchema):
    class Meta:
        model = Group
        exclude = ["created_at", "updated_at", "status", "name_no_accent", "avatar_url"]


class CreateGroupResponse(Schema):
    attachment_uid: UUID = Field(..., alias="uid")
    url: str
    group: CreateGroup


class UserInGroup(Schema):
    group_members_uid: UUID = Field(..., alias="uid")
    user: UserResponse
