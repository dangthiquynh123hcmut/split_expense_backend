from typing import List
from uuid import UUID

from ninja import Query

from event.schemas.response import ListEventGroup
from exceptions.event import EventNotFound
from exceptions.group import GroupNotFound
from exceptions.users import UserNotFound
from utils.exceptions import (
    CreateIsDenied,
    DeleteIsDenied,
    GetIsDenied,
    UpdatedIsDenied,
)
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
)
from utils.types import AuthenticatedRequest

from .schemas.request import AddMember, EventRequest, EventUpdateRequest
from .schemas.response import EventMemberResponse, EventResponse
from .services import Service


@api(
    prefix_or_class="events",
    tags=["Event"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class EventAPI(Controller):
    def __init__(self, service: Service):
        self.service = service

    @post(
        "",
        response=EventResponse,
        exceptions=(GroupNotFound, UserNotFound, CreateIsDenied),
    )
    def create_event(self, request: AuthenticatedRequest, data: EventRequest):
        return self.service.create_event(user=request.user, data=data)

    @get("/{event_uid}", response=EventResponse, exceptions=(EventNotFound,))
    def get_event(self, event_uid: UUID):
        return self.service.get_event(event_uid=event_uid)

    @put(
        "/{event_uid}",
        response=EventResponse,
        exceptions=(EventNotFound, UpdatedIsDenied),
    )
    def update_event(
        self, request: AuthenticatedRequest, event_uid: UUID, data: EventUpdateRequest
    ):
        return self.service.update_event(
            user=request.user, event_uid=event_uid, data=data
        )

    @delete("/{event_uid}", response=bool, exceptions=(EventNotFound, DeleteIsDenied))
    def delete_event(self, request: AuthenticatedRequest, event_uid: UUID):
        return self.service.delete_event(user=request.user, event_uid=event_uid)

    @post("/{event_uid}/join", response=bool, exceptions=(EventNotFound,))
    def join_event(self, request: AuthenticatedRequest, event_uid: UUID):
        self.service.join_event(user=request.user, event_uid=event_uid)
        return True

    @post("/{event_uid}/add", response=bool, exceptions=(EventNotFound, UserNotFound))
    def add_member_to_event(self, event_uid: UUID, data: AddMember):
        self.service.add_member_to_event(event_uid=event_uid, data=data)
        return True

    # @post("/{event_uid}/leave", response=bool, exceptions=(EventNotFound,))
    # def leave_event(self, request: AuthenticatedRequest, event_uid: UUID):
    #     return self.service.leave_event(user = request.user, event_uid=event_uid)

    @get(
        "/{event_uid}/members",
        response=EventMemberResponse,
        paginate=True,
        exceptions=(EventNotFound, GetIsDenied),
    )
    @paginate
    def list_event_members(
        self,
        request: AuthenticatedRequest,
        event_uid: UUID,
        filter: FilterFullNameSchema = Query(...),
        order_by: OrderByFullNameAndUpdatedAtSchema = Query(...),
    ):
        return self.service.list_event_members(
            user=request.user, event_uid=event_uid, filter=filter, order_by=order_by
        )

    # @post("/{event_uid}/members/{user_uid}", response=bool, exceptions=(EventNotFound,))
    # def remove_event_member(
    #     self, request: AuthenticatedRequest, event_uid: UUID, user_uid: UUID
    # ):
    #     self.service.remove_event_member(user=request.user, event_uid=event_uid)
    #     return True


@api(
    prefix_or_class="events-groups",
    tags=["Event"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class EventGroupAPI(Controller):
    def __init__(self, service: Service):
        self.service = service

    @get("", response=List[ListEventGroup])
    def list_events_groups(
        self,
        request: AuthenticatedRequest,
        filter: FilterNameSchema = Query(...),
    ):
        return self.service.list_events_groups(user=request.user, filter=filter)
