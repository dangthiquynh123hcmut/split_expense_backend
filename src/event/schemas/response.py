from datetime import date
from typing import List, Optional
from uuid import UUID

from ninja import ModelSchema, Schema
from pydantic import ConfigDict

from attachment.schemas.responses import AttachmentResponse
from event.models import Event
from user.schemas.response import UserResponse


class EventResponse(ModelSchema):
    class Meta:
        model = Event
        exclude = ["created_at", "updated_at", "status", "name_no_accent"]


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
