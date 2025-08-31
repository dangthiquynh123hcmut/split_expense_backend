from typing import List, Optional
from uuid import UUID

from ninja import ModelSchema, Schema
from pydantic import ConfigDict

from event.models import Event


class EventResponse(ModelSchema):
    class Meta:
        model = Event
        exclude = ["created_at", "updated_at", "status", "name_no_accent"]


class ListEvent(EventResponse):
    group_id: UUID
    group_name: str
    group_avatar_url: Optional[str]
    group_uid: UUID


class EventGroup(Schema):
    event_uid: UUID
    event_name: str


class ListEventGroup(Schema):
    group_name: str
    group_avatar_url: Optional[str]
    list_event: List[EventGroup]


class EventMemberResponse(Schema):
    event_member_uid: UUID
    user_uid: UUID
    full_name: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
