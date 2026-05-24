from datetime import date
from typing import List, Optional
from uuid import UUID

from ninja import ModelSchema, Schema
from pydantic import ConfigDict

from attachment.schemas.responses import AttachmentResponse
from event.models import Event
from group.schemas.response import UserBalanceGroupResponse
from user.schemas.response import UserResponse


class EventResponse(ModelSchema):
    class Meta:
        model = Event
        exclude = ["created_at", "updated_at", "status", "name_no_accent"]


class EventDetailResponse(Schema):
    uid: UUID
    name: str
    creator_id: UUID
    group_id: UUID
    description: Optional[str] = None
    event_start: date
    event_end: date
    total_expenses: Optional[int] = 0
    total: Optional[float] = 0.0
    members: Optional[int] = None


class EventGroup(Schema):
    event_uid: UUID
    event_name: str
    event_description: Optional[str] = None
    event_start: date
    event_end: date


class ListEventGroup(Schema):
    group_name: str
    group_avatar_url: Optional[AttachmentResponse] = None
    list_event: List[EventGroup]


class EventMemberResponse(Schema):
    event_member_uid: UUID
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)


class EventBalanceResponse(Schema):
    debtor: UserBalanceGroupResponse
    creditor: UserBalanceGroupResponse
    value: float
    currency: str
