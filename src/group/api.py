from uuid import UUID

from ninja import Query

from event.schemas.response import EventResponse
from exceptions.group import GroupNotFound
from user.schemas.response import UserResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.types import AuthenticatedRequest

from .schemas.request import GroupRequest, GroupUpdateRequest
from .schemas.response import GroupResponse
from .services import Service


@api(
    prefix_or_class="groups",
    tags=["Group"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class GroupAPI(Controller):
    def __init__(self, service: Service):
        self.service = service

    @post(
        "",
        response=GroupResponse,
    )
    def create_group(self, request: AuthenticatedRequest, data: GroupRequest):
        return self.service.create_group(leader=request.user, data=data)

    @get("", response=GroupResponse, paginate=True)
    @paginate
    def list_groups(
        self,
        request: AuthenticatedRequest,
        filter: FilterNameSchema = Query(...),
        order_by: OrderByNameAndUpdatedAtSchema = Query(...),
    ):
        return self.service.list_groups(
            user=request.user, filter=filter, order_by=order_by
        )

    @get("/{group_uid}/members", response=UserResponse, paginate=True)
    @paginate
    def list_group_members(
        self,
        group_uid: UUID,
        filter: FilterFullNameSchema = Query(...),
        order_by: OrderByFullNameAndUpdatedAtSchema = Query(...),
    ):
        return self.service.list_group_members(
            group_uid=group_uid, filter=filter, order_by=order_by
        )

    @put("/{group_uid}", response=GroupResponse, exceptions=(GroupNotFound,))
    def update_group(self, group_uid: UUID, data: GroupUpdateRequest):
        return self.service.update_group(group_uid=group_uid, data=data)

        # @get("/{group_uid}", response=GroupResponse, exceptions=(GroupNotFound,))
        # def get_group(self, group_uid: UUID):
        #     return  self.service.get_group(group_uid=group_uid)

        # @get("/{group_uid}", response=GroupDetailResponse, exceptions=(GroupNotFound,))
        # def get_group(self, group_uid: UUID):
        #     return  self.service.get_detail_group(group_uid=group_uid)

        # @put("/{group_uid}/leave", response=bool)
        # def leave_group(self, request: AuthenticatedRequest, group_uid: UUID):
        #     group = self.service.get_group(group_uid=group_uid)
        #     return self.service.leave_group(user=request.user, group=group)

        # @delete("/{group_uid}", response=bool, exceptions=(GroupNotFound, DeleteIsDenied))
        # def delete_group(self,request:AuthenticatedRequest, group_uid: UUID):
        # return self.service.delete_group(user=request.user, group_uid=group_uid)

    @get("/{group_uid}/events", response=EventResponse, paginate=True)
    @paginate
    def list_events_in_a_group(
        self,
        group_uid: UUID,
        filter: FilterNameSchema = Query(...),
        order_by: OrderByNameAndUpdatedAtSchema = Query(...),
    ):
        return self.service.list_events_in_a_group(
            group_uid=group_uid, filter=filter, order_by=order_by
        )
