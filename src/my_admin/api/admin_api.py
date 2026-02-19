from uuid import UUID

from ninja import Query

from exceptions.users import UserNotFound
from message.schemas.request import MessageFilter
from my_admin.schemas.request import OrderByBalanceSchema
from my_admin.schemas.response import RatingResponse
from user.schemas.response import UserResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get, patch
from utils.router.paginate import paginate
from utils.router.permissions import IsAdminUser
from utils.schemas.filter_and_order_by import (
    FilterDateSchema,
    FilterEventAdminSchema,
    FilterExpenseAdminSchema,
    FilterFullNameSchema,
    FilterNameSchema,
)

from ..schemas.request import FilterTransactionSchema, UserFilter
from ..schemas.response import (
    AdminGroupResponse,
    EventManagementResponse,
    ExpenseAttachmentResponse,
    ExpenseCategoryResponse,
    ExpenseInEventResponse,
    ExpenseItemResponse,
    ExpenseManagementResponse,
    GroupStatisticsResponse,
    ListEventMemberResponse,
    ListEventResponse,
    ListExpenseResponse,
    ListTransactionWithdrawDepositResponse,
    MessageGroupResponse,
    MessageInGroupResponse,
    MessageManagementResponse,
    ParticipatingGroupsResponse,
    SplitExpenseResponse,
    TodayOverviewResponse,
    TransactionManagementResponse,
    UserInforResponse,
    UserInsightsResponse,
)
from ..service.admin_service import AdminService


@api(
    prefix_or_class="admin",
    tags=["Admin"],
    auth=AuthBear(),
    permissions=[IsAdminUser],
)
class AdminController(Controller):
    def __init__(self, service: AdminService):
        self.service = service

    @get("/users", response=UserResponse, paginate=True)
    @paginate
    def list_users(
        self,
        filter: UserFilter = Query(...),
        order_by: OrderByBalanceSchema = Query(...),
    ):
        return self.service.list_users(filter=filter, order_by=order_by)

    @get("/today-overview", response=TodayOverviewResponse)
    def today_overview(self):
        return self.service.today_overview()

    @get("/user-insights", response=list[UserInsightsResponse])
    def user_insights(self, year: int = Query(...)):
        return self.service.user_insights(year=year)

    @get("/expense-categories", response=list[ExpenseCategoryResponse])
    def expense_categories(self):
        return self.service.expense_categories()

    @get("/rating", response=list[RatingResponse])
    def rating(self, filter: FilterDateSchema = Query(...)):
        return self.service.rating(filter=filter)

    @get("/group", response=GroupStatisticsResponse)
    def group_statistics(self):
        return self.service.group_statistics()

    @patch("/group/{group_uid}", response=bool)
    def deactivate_group(self, group_uid: UUID):
        return self.service.deactivate_group(group_uid=group_uid)

    @patch("/group/active/{group_uid}", response=bool)
    def active_group(self, group_uid: UUID):
        return self.service.active_groups(group_uid=group_uid)

    @get("/groups", response=AdminGroupResponse, paginate=True)
    @paginate
    def list_groups(
        self,
        filter: FilterNameSchema = Query(...),
    ):
        return self.service.list_groups(filter=filter)

    @get("/event-management", response=EventManagementResponse)
    def event_management(self):
        return self.service.event_management()

    @get("/events", response=ListEventResponse, paginate=True)
    @paginate
    def list_events(
        self,
        filter: FilterEventAdminSchema = Query(...),
    ):
        return self.service.list_events(filter=filter)

    @get(
        "/event/{event_uid}/event-members",
        response=ListEventMemberResponse,
        paginate=True,
    )
    @paginate
    def list_event_members(
        self,
        event_uid: UUID,
        filter: FilterFullNameSchema = Query(...),
    ):
        return self.service.list_event_members(event_uid=event_uid, filter=filter)

    @get("/expense/{event_uid}", response=ExpenseInEventResponse)
    def get_expenses_in_event(self, event_uid: UUID):
        return self.service.get_expenses_in_event(event_uid=event_uid)

    @patch("/event/{event_uid}", response=bool)
    def deactivate_event(self, event_uid: UUID):
        return self.service.deactivate_event(event_uid=event_uid)

    @patch("/event/active/{event_uid}", response=bool)
    def active_event(self, event_uid: UUID):
        return self.service.active_event(event_uid=event_uid)

    @get("/expense-management", response=ExpenseManagementResponse)
    def expense_management(self):
        return self.service.expense_management()

    @get("/expenses", response=ExpenseItemResponse, paginate=True)
    @paginate
    def get_all_expenses(self, filter: FilterExpenseAdminSchema = Query(...)):
        return self.service.get_all_expenses(filter=filter)

    @patch("/expense/deactivate/{expense_uid}", response=bool)
    def deactivate_expense(self, expense_uid: UUID):
        return self.service.deactivate_expense(expense_uid=expense_uid)

    @patch("/expense/active/{expense_uid}", response=bool)
    def active_expense(self, expense_uid: UUID):
        return self.service.active_expense(expense_uid=expense_uid)

    @get("/expenses/{expense_uid}", response=SplitExpenseResponse)
    def get_split_expense(self, expense_uid: UUID):
        return self.service.get_split_expense(expense_uid=expense_uid)

    @get(
        "/expense/{expense_uid}/attachments",
        response=ExpenseAttachmentResponse,
        paginate=True,
    )
    @paginate
    def get_expense_attachments(self, expense_uid: UUID):
        expense = self.service.expense_query.get_expense_by_uid(expense_uid=expense_uid)
        return self.service.get_expense_attachments(expense=expense)

    @get("/message/group/{group_uid}", response=MessageInGroupResponse, paginate=True)
    @paginate
    def get_messages_in_group(
        self, group_uid: UUID, filter: MessageFilter = Query(...)
    ):
        return self.service.get_messages_in_group(group_uid=group_uid, filter=filter)

    @get("/message-management", response=MessageManagementResponse)
    def message_management(self):
        return self.service.message_management()

    @get("/messages/group", response=MessageGroupResponse, paginate=True)
    @paginate
    def list_messages_group(self):
        return self.service.list_messages_group()

    @get("/transactions-management", response=TransactionManagementResponse)
    def transactions_management(self):
        return self.service.transactions_management()

    @get(
        "/transactions", response=ListTransactionWithdrawDepositResponse, paginate=True
    )
    @paginate
    def list_transactions_withdraws_and_deposits(
        self, filter: FilterTransactionSchema = Query(...)
    ):
        return self.service.list_transactions_withdraws_and_deposits(filter=filter)


@api(
    prefix_or_class="admin/users",
    tags=["Users"],
    auth=AuthBear(),
    permissions=[IsAdminUser],
)
class AdminUsersController(Controller):
    def __init__(self, service: AdminService):
        self.service = service

    @get("/{user_uid}", response=UserInforResponse)
    def get_info_user(self, user_uid: UUID):
        return self.service.get_info_user(user_uid=user_uid)

    @patch("/{user_uid}/activate", response=bool, exceptions=(UserNotFound,))
    def activate_user(self, user_uid: UUID):
        return self.service.activate_user(user_uid=user_uid)

    @get("/{user_uid}/groups", response=ParticipatingGroupsResponse, paginate=True)
    @paginate
    def list_participating_groups(
        self,
        user_uid: UUID,
        filter: FilterNameSchema = Query(...),
    ):
        return self.service.list_participating_groups(user_uid=user_uid, filter=filter)

    @get("/{user_uid}/expenses", response=ListExpenseResponse, paginate=True)
    @paginate
    def list_user_expenses(
        self,
        user_uid: UUID,
        filter: FilterNameSchema = Query(...),
    ):
        return self.service.list_user_expenses(user_uid=user_uid, filter=filter)
