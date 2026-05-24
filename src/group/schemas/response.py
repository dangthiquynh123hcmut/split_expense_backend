from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from ninja import Field, ModelSchema, Schema

from attachment.schemas.responses import AttachmentResponse
from group.models import Group
from user.schemas.response import UserResponse


class GroupName(ModelSchema):
    avatar_url: Optional[AttachmentResponse] = None

    class Meta:
        model = Group
        exclude = ["created_at", "updated_at", "status", "name_no_accent", "leader"]


class GroupResponse(ModelSchema):
    avatar_url: Optional[AttachmentResponse] = None
    leader: UserResponse

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
    currency: str


class UserBalanceGroupResponse(Schema):
    full_name: str
    avatar_url: Optional[AttachmentResponse] = None
    uid: UUID


class BalanceMembersResponse(Schema):
    user: Optional[UserBalanceGroupResponse] = None
    balance: Optional[Decimal] = None


class BalanceGroupResponse(ModelSchema):
    group_members: Optional[List[BalanceMembersResponse]] = None
    avatar_url: Optional[AttachmentResponse] = None

    class Meta:
        model = Group
        exclude = ["created_at", "updated_at", "status", "name_no_accent", "leader"]


class DetailGroup(Schema):
    group: GroupResponse
    event_attended: str = "0/0"
    shared_expenses: str = "0/0"
    total_amount: float = 0.0
    user_spent: float = 0.0
    restructured_debt: Optional[List[DebtMember]] = None


class GroupMembersReport(Schema):
    full_name: str
    percent: Decimal


class GroupReport(Schema):
    group: GroupResponse
    events: int = 0
    shared_expenses: int = 0
    total_amount: float = 0.0
    members: int


class GroupChart(Schema):
    month: int = Field(..., alias="created_at__month")
    total_amount: float
