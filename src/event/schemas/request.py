from datetime import date
from typing import List, Optional
from uuid import UUID

from ninja import Schema


class EventRequest(Schema):
    name: str
    list_user_uid: List[UUID] | None = None
    description: Optional[str] = None
    event_start: date
    event_end: Optional[date] = None
    group_id: UUID


class EventUpdateRequest(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    event_start: Optional[date] = None
    event_end: Optional[date] = None


class AddMember(Schema):
    user_uids: List[UUID]
