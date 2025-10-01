from datetime import datetime
from typing import List, Optional
from uuid import UUID

from ninja import Field, ModelSchema, Schema

from attachment.schemas.responses import AttachmentResponse
from group.models import Group
from user.schemas.response import UserResponse
from utils.router.paginate import InnerPaginatedResponse


class GroupName(ModelSchema):
    avatar_url: Optional[AttachmentResponse] = None

    class Meta:
        model = Group
        exclude = ["created_at", "updated_at", "status", "name_no_accent", "leader"]


class GroupResponse(ModelSchema):
    avatar_url: Optional[AttachmentResponse] = None

    class Meta:
        model = Group
        exclude = ["created_at", "updated_at", "status", "name_no_accent"]


class CreateGroup(ModelSchema):
    class Meta:
        model = Group
        exclude = ["created_at", "updated_at", "status", "name_no_accent", "avatar_url"]


class UserInGroup(Schema):
    group_members_uid: UUID = Field(..., alias="uid")
    user: UserResponse
    joined_at: datetime


class DebtMember(Schema):
    debtor: UserResponse
    creditor: UserResponse
    value: float


class DebtSimplification(Schema):
    user: UserResponse
    total_amount: float
    transactions: List[DebtMember]


class BalanceMembersResponse(Schema):
    user: Optional[UserResponse] = None
    total_amount: Optional[float] = None


class BalanceGroupResponse(Schema):
    group: GroupName
    items: InnerPaginatedResponse[BalanceMembersResponse]
    # items: List[BalanceMembersResponse]
