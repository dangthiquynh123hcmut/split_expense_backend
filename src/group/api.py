from typing import List, Literal
from uuid import UUID

from ninja import Query

from event.schemas.response import EventResponse
from exceptions.group import GroupNotFound, LeaveIsDenied, UserNotInGroup
from exceptions.users import UserNotFound
from expense.schemas.response import NameExpense
from utils.exceptions import DeleteIsDenied, GetIsDenied, UpdatedIsDenied
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.schemas.filter_and_order_by import (
    FilterCurrencySchema,
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.types import AuthenticatedRequest

from .schemas.request import (
    DebtOptimizationRequest,
    ExternalTransferRequest,
    GroupRequest,
    GroupUpdateRequest,
    RemindRequest,
    UpdateGroupLeaderRequest,
)
from .schemas.response import (
    BalanceGroupResponse,
    CreateGroup,
    DetailGroup,
    GroupChart,
    GroupMembersReport,
    GroupReport,
    GroupResponse,
    UserInGroup,
)
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

    @get(
        "/balance-members",
        response=BalanceGroupResponse,
        paginate=True,
        exceptions=(GroupNotFound, GetIsDenied),
    )
    @paginate
    def get_balances_by_group_and_member(
        self,
        request: AuthenticatedRequest,
        currency: str = "VND",
        filter: FilterNameSchema = Query(...),
        order_by: OrderByNameAndUpdatedAtSchema = Query(...),
    ):
        return self.service.get_balances_by_group_and_member(
            user=request.user,
            currency=currency,
            filter=filter,
            order_by=order_by,
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

    @get("/{group_uid}", response=DetailGroup, exceptions=(GroupNotFound,))
    def get_group_detail(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        filter: FilterCurrencySchema = Query(...),
    ):
        return self.service.get_group_detail(
            user=request.user, group_uid=group_uid, filter=filter
        )

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

    @get(
        "/{group_uid}/expenses",
        response=NameExpense,
        paginate=True,
        exceptions=(GroupNotFound, GetIsDenied),
    )
    @paginate
    def list_expenses_in_a_group(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        status: Literal["DELETED", "ACTIVE"] = "ACTIVE",
    ):
        return self.service.list_expenses_in_a_group(
            user=request.user,
            group_uid=group_uid,
            status=status,
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

    @put(
        "/{group_uid}/debt-optimization",
        response=bool,
        exceptions=(GroupNotFound, UpdatedIsDenied),
    )
    def update_debt_optimization(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        payload: DebtOptimizationRequest,
    ):
        return self.service.update_debt_optimization(
            user=request.user,
            group_uid=group_uid,
            debt_optimization=payload.debt_optimization,
        )

    @get(
        "/{group_uid}/report",
        response=GroupReport,
        exceptions=(GroupNotFound, GetIsDenied),
    )
    def group_report(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
    ):
        return self.service.group_report(user=request.user, group_uid=group_uid)

    @get(
        "/{group_uid}/members-report",
        response=List[GroupMembersReport],
        exceptions=(GroupNotFound, GetIsDenied),
    )
    def get_member_spending(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        currency: str = "VND",
    ):
        return self.service.get_member_spending(
            user=request.user, group_uid=group_uid, currency=currency
        )

    @get(
        "/{group_uid}/chart",
        response=List[GroupChart],
        exceptions=(GroupNotFound, GetIsDenied),
    )
    def chart_expenses_in_group(
        self, request: AuthenticatedRequest, group_uid: UUID, year: int
    ):
        return self.service.chart_expenses_in_group(
            user=request.user, group_uid=group_uid, year=year
        )

    @post(
        "/{group_uid}/remind",
        response=bool,
        exceptions=(GroupNotFound, UserNotFound),
    )
    def remind_group_members(
        self, request: AuthenticatedRequest, group_uid: UUID, payload: RemindRequest
    ):
        self.service.remind_group_members(
            user=request.user, group_uid=group_uid, payload=payload
        )
        return True

    @post(
        "/{group_uid}/external-transfer",
        response=bool,
        exceptions=(GroupNotFound, UserNotFound),
    )
    def group_external_transfer(
        self,
        request: AuthenticatedRequest,
        group_uid: UUID,
        payload: ExternalTransferRequest,
    ):
        return self.service.group_external_transfer(
            user=request.user, group_uid=group_uid, payload=payload
        )


@api(prefix_or_class="", tags=["Group"], auth=None)
class GroupPublicAPI(Controller):
    def __init__(self, service: Service):
        self.service = service

    @get("/confirm-transfer", response=bool)
    def confirm_transfer(self, token: str):
        return self.service.confirm_transfer_token(uid=token)
