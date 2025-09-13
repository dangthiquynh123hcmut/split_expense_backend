from uuid import UUID

from ninja import Query

from attachment.services import AttachmentService
from event.schemas.response import EventResponse
from exceptions.group import GroupNotFound
from exceptions.users import UserNotFound
from utils.exceptions import GetIsDenied, UpdatedIsDenied
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
from .schemas.response import CreateGroupResponse, GroupResponse, UserInGroup
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
        self.attachment_service = AttachmentService()

    @post(
        "",
        response=CreateGroupResponse,
        exceptions=(UserNotFound,),
    )
    def create_group(self, request: AuthenticatedRequest, data: GroupRequest):
        attachment, presigned_url = self.attachment_service.get_presigned_url(
            user=request.user,
            payload=data.image_file,
        )
        group = self.service.create_group(
            leader=request.user, name=data.name, list_user_uids=data.list_user_uids
        )
        return {"attachment_uid": attachment.uid, "url": presigned_url, "group": group}

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

    @get(
        "/{group_uid}/members",
        response=UserInGroup,
        paginate=True,
        exceptions=(GroupNotFound, GetIsDenied),
    )
    @paginate
    def list_group_members(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        filter: FilterFullNameSchema = Query(...),
        order_by: OrderByFullNameAndUpdatedAtSchema = Query(...),
    ):
        return self.service.list_group_members(
            user=request.user, group_uid=group_uid, filter=filter, order_by=order_by
        )

    @put(
        "/{group_uid}",
        response=GroupResponse,
        exceptions=(GroupNotFound, UserNotFound, UpdatedIsDenied),
    )
    def update_group(
        self, request: AuthenticatedRequest, group_uid: UUID, data: GroupUpdateRequest
    ):
        return self.service.update_group(
            user=request.user, group_uid=group_uid, data=data
        )

        # @get("/{group_uid}", response=GroupResponse, exceptions=(GroupNotFound,))
        # def get_group(self, group_uid: UUID):
        #     return  self.service.get_group(group_uid=group_uid)

        # @put("/{group_uid}/leave", response=bool)
        # def leave_group(self, request: AuthenticatedRequest, group_uid: UUID):
        #     group = self.service.get_group(group_uid=group_uid)
        #     return self.service.leave_group(user=request.user, group=group)

        # @delete("/{group_uid}", response=bool, exceptions=(GroupNotFound, DeleteIsDenied))
        # def delete_group(self,request:AuthenticatedRequest, group_uid: UUID):
        # return self.service.delete_group(user=request.user, group_uid=group_uid)

    @get(
        "/{group_uid}/events",
        response=EventResponse,
        paginate=True,
        exceptions=(GroupNotFound, GetIsDenied),
    )
    @paginate
    def list_events_in_a_group(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        filter: FilterNameSchema = Query(...),
        order_by: OrderByNameAndUpdatedAtSchema = Query(...),
    ):
        return self.service.list_events_in_a_group(
            user=request.user, group_uid=group_uid, filter=filter, order_by=order_by
        )
