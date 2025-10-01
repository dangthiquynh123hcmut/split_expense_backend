from uuid import UUID

from ninja import Query

from event.schemas.response import EventResponse
from exceptions.group import GroupNotFound, LeaveIsDenied, UserNotInGroup
from exceptions.users import UserNotFound
from expense.schemas.response import ExpenseEvent
from utils.exceptions import DeleteIsDenied, GetIsDenied, UpdatedIsDenied
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.types import AuthenticatedRequest

from .schemas.request import GroupRequest, GroupUpdateRequest, UpdateGroupLeaderRequest
from .schemas.response import CreateGroup, GroupResponse, UserInGroup
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
        response=CreateGroup,
        exceptions=(UserNotFound,),
    )
    def create_group(self, request: AuthenticatedRequest, data: GroupRequest):
        return self.service.create_group(
            leader=request.user, name=data.name, list_user_uids=data.list_user_uids
        )

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

    # @get(
    #     "/balance-members",
    #     response=BalanceGroupResponse,
    #     nested_paginate=True,
    #     exceptions=(GroupNotFound, GetIsDenied),
    # )
    # @nested_paginate
    # def get_balances_by_group_and_member(self, request: AuthenticatedRequest):
    #     return self.service.get_balances_by_group_and_member(user=request.user)

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
        exceptions=(
            GroupNotFound,
            UserNotFound,
            UpdatedIsDenied,
            UserNotInGroup,
            DeleteIsDenied,
        ),
    )
    def update_group(
        self, request: AuthenticatedRequest, group_uid: UUID, data: GroupUpdateRequest
    ):
        return self.service.update_group(
            user=request.user, group_uid=group_uid, data=data
        )

    # @get("/{group_uid}", response=GroupResponse, exceptions=(GroupNotFound,))
    # def get_group_detail(self, group_uid: UUID):
    #     return self.service.get_group_detail(group_uid=group_uid)

    @put(
        "/{group_uid}/leave",
        response=bool,
        exceptions=(GroupNotFound, LeaveIsDenied, UserNotInGroup),
    )
    def leave_group(self, request: AuthenticatedRequest, group_uid: UUID):
        self.service.leave_group(user=request.user, group_uid=group_uid)
        return True

    @delete("/{group_uid}", response=bool, exceptions=(GroupNotFound, DeleteIsDenied))
    def delete_group(self, request: AuthenticatedRequest, group_uid: UUID):
        return self.service.delete_group(user=request.user, group_uid=group_uid)

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

    # @get(
    #     "/{group_uid}/debt-simplification",
    #     response=DebtSimplification,
    #     exceptions=(GroupNotFound, GetIsDenied),
    # )
    # def debt_simplification(self, request: AuthenticatedRequest, group_uid: UUID):
    #     return self.service.debt_simplification(
    #         user=request.user, group_uid=group_uid
    #     )
    @get(
        "/{group_uid}/expenses",
        response=ExpenseEvent,
        paginate=True,
        exceptions=(GroupNotFound, GetIsDenied),
    )
    @paginate
    def list_expenses_in_a_group(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
    ):
        return self.service.list_expenses_in_a_group(
            user=request.user,
            group_uid=group_uid,
        )

    @put(
        "/{group_uid}/leader",
        response=bool,
        exceptions=(GroupNotFound, UpdatedIsDenied),
    )
    def update_group_leader(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        payload: UpdateGroupLeaderRequest,
    ):
        self.service.update_group_leader(
            user=request.user, group_uid=group_uid, new_leader=payload.new_leader
        )
        return True
