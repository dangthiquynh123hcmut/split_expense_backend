from uuid import UUID

from exceptions.event import EventNotFound
from utils.exceptions import DeleteIsDenied
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
)
from utils.types import TUser

from .queries import Query
from .schemas.request import EventRequest, EventUpdateRequest


class Service:
    def __init__(self):
        self.query = Query()

    def create_event(self, user: TUser, data: EventRequest):
        event = self.query.create_event(user=user, data=data)
        self.query.create_event_members(event=event, member_uids=data.list_user_uid)
        return event

    def get_event(self, event_uid: UUID):
        return self.query.get_event(event_uid=event_uid)

    def update_event(self, event_uid: UUID, data: EventUpdateRequest):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        return self.query.update_event(event=event, data=data)

    def leave_event(self, user: TUser, event_uid: UUID):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        return self.query.leave_event(user=user, event=event)

    def delete_event(self, user: TUser, event_uid: UUID):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        if user != event.creator:
            raise DeleteIsDenied
        return self.query.delete_event(event_uid=event_uid)

    def list_event_members(
        self,
        event_uid: UUID,
        filter: FilterFullNameSchema,
        order_by: OrderByFullNameAndUpdatedAtSchema,
    ):
        event = self.query.get_event(event_uid=event_uid)
        return self.query.list_event_members(
            event=event, filter=filter, order_by=order_by
        )

    def join_event(self, user: TUser, event_uid: UUID):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        return self.query.join_event(user=user, event=event)

    def list_events_groups(
        self,
        user: TUser,
        filter: FilterNameSchema,
    ):
        return self.query.list_events_groups(user=user, filter=filter)
