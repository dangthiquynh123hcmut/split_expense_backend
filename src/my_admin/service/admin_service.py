from typing import Optional
from uuid import UUID

from authenticate.queries import Query as Auth_Query
from event.queries import Query as EventQuery
from expense.queries import Query as ExpenseQuery
from group.queries import Query as GroupQuery
from group.schemas.response import GroupName
from my_admin.schemas.request import OrderByBalanceSchema
from my_admin.schemas.response import (
    AdminGroupResponse,
    ExpenseCategoryResponse,
    GroupStatisticsResponse,
    RatingResponse,
    TodayOverviewResponse,
    UserInsightsResponse,
)
from utils.schemas.filter_and_order_by import (
    FilterDateSchema,
    FilterEventAdminSchema,
    FilterNameSchema,
)
from wallet.orm.deposit import DepositORM
from wallet.orm.transaction import TransactionORM
from wallet.orm.withdraw import WithdrawORM

from ..orm.admin_orm import Query
from ..schemas.request import UserFilter
from ..schemas.response import (
    EventManagementResponse,
    ListEventMemberResponse,
    ListEventResponse,
    UserCreator,
    UserEventSchema,
)


class AdminService:
    def __init__(self):
        self.query = Query()
        self.auth_query = Auth_Query()
        self.withdraw_query = WithdrawORM()
        self.deposit_query = DepositORM()
        self.transaction_query = TransactionORM()
        self.expense_query = ExpenseQuery()
        self.group_query = GroupQuery()
        self.events_query = EventQuery()

    def list_users(
        self,
        filter: Optional[UserFilter] = None,
        order_by: Optional[OrderByBalanceSchema] = None,
    ):
        return self.query.list_users(filter=filter, order_by=order_by)

    def today_overview(self):
        total_users_today, total_users_yesterday = self.auth_query.total_users_use_app()
        total_tranfer_today, total_tranfer_yesterday = (
            self.transaction_query.total_transactions_today()
        )
        total_deposit_today, total_deposit_yesterday = (
            self.deposit_query.total_deposit_today()
        )
        total_withdraw_today, total_withdraw_yesterday = (
            self.withdraw_query.total_withdraw_today()
        )
        total_transactions_today = (
            total_deposit_today + total_withdraw_today + total_tranfer_today
        )
        total_transactions_yesterday = (
            total_deposit_yesterday + total_withdraw_yesterday + total_tranfer_yesterday
        )
        total_withdraw_money_today, total_withdraw_money_yesterday = (
            self.withdraw_query.total_withdraw_money_today()
        )
        total_deposit_today, total_deposit_yesterday = (
            self.deposit_query.total_deposit_money_today()
        )
        total_money_today = total_deposit_today + total_withdraw_money_today
        total_money_yesterday = total_deposit_yesterday + total_withdraw_money_yesterday
        new_users_today, new_users_yesterday = self.auth_query.count_new_users()

        return TodayOverviewResponse(
            total_users=total_users_today,
            total_transactions=total_transactions_today,
            total_money=total_money_today,
            new_users=new_users_today,
            percent_increase_users=(
                (total_users_today - total_users_yesterday)
                / total_users_yesterday
                * 100
                if total_users_yesterday > 0
                else 100.0
            ),
            percent_increase_transactions=(
                (total_transactions_today - total_transactions_yesterday)
                / total_transactions_yesterday
                * 100
                if total_transactions_yesterday > 0
                else 100.0
            ),
            percent_increase_money=(
                (total_money_today - total_money_yesterday)
                / total_money_yesterday
                * 100
                if total_money_yesterday > 0
                else 100.0
            ),
            percent_increase_new_users=(
                (new_users_today - new_users_yesterday) / new_users_yesterday * 100
                if new_users_yesterday > 0
                else 100.0
            ),
        )

    def user_insights(self, year: int) -> list[UserInsightsResponse]:
        insights_data = self.query.user_insights(year)

        return [
            UserInsightsResponse(
                month_year=insight["month_year"],
                new_users=insight["new_users"],
                loyal_users=insight["loyal_users"],
                return_users=insight["return_users"],
            )
            for insight in insights_data
        ]

    def expense_categories(self) -> list[ExpenseCategoryResponse]:
        categories_data = self.expense_query.expense_categories()

        return [
            ExpenseCategoryResponse(
                category=category["category"],
                total_amount=category["total_amount"],
            )
            for category in categories_data
        ]

    def rating(self, filter: FilterDateSchema) -> list[RatingResponse]:
        rating_data = self.query.rating(filter=filter)

        return [
            RatingResponse(
                date=rating["date"],
                rate=rating["avg_rate"],
            )
            for rating in rating_data
        ]

    def group_statistics(self) -> GroupStatisticsResponse:
        total_groups, total_groups_yesterday = self.group_query.count_groups()
        total_members, total_members_yesterday = self.group_query.count_members()
        active_groups, active_groups_yesterday = self.group_query.count_active_groups()
        return GroupStatisticsResponse(
            total_groups=total_groups,
            total_members=total_members,
            active_groups=active_groups,
            percent_increase_groups=(
                (total_groups - total_groups_yesterday) / total_groups_yesterday * 100
                if total_groups_yesterday > 0
                else 100.0
            ),
            percent_increase_members=(
                (total_members - total_members_yesterday)
                / total_members_yesterday
                * 100
                if total_members_yesterday > 0
                else 100.0
            ),
            percent_increase_active_groups=(
                (active_groups - active_groups_yesterday)
                / active_groups_yesterday
                * 100
                if active_groups_yesterday > 0
                else 100.0
            ),
        )

    def deactivate_group(self, group_uid: UUID) -> bool:
        self.group_query.deactivate_inactive_groups(group_uid=group_uid)
        return True

    def list_groups(self, filter: FilterNameSchema) -> list[AdminGroupResponse]:
        return self.group_query.list_groups_admin(filter=filter)

    def events_management(self) -> EventManagementResponse:
        total_events, total_events_yesterday = self.events_query.count_events()
        total_members, total_members_yesterday = self.events_query.count_event_members()
        active_events, active_events_yesterday = self.events_query.count_active_events()
        total_finished_events, total_finished_events_yesterday = (
            self.events_query.count_finished_events()
        )
        return EventManagementResponse(
            total_events=total_events,
            total_members=total_members,
            active_events=active_events,
            total_finished_events=total_finished_events,
            percent_increase_events=(
                (total_events - total_events_yesterday) / total_events_yesterday * 100
                if total_events_yesterday > 0
                else 100.0
            ),
            percent_increase_members=(
                (total_members - total_members_yesterday)
                / total_members_yesterday
                * 100
                if total_members_yesterday > 0
                else 100.0
            ),
            percent_increase_active_events=(
                (active_events - active_events_yesterday)
                / active_events_yesterday
                * 100
                if active_events_yesterday > 0
                else 100.0
            ),
            percent_increase_finished_events=(
                (total_finished_events - total_finished_events_yesterday)
                / total_finished_events_yesterday
                * 100
                if total_finished_events_yesterday > 0
                else 100.0
            ),
        )

    def list_events(self, filter: FilterEventAdminSchema) -> list[ListEventResponse]:
        query = self.events_query.list_events_admin(filter=filter)
        return [
            ListEventResponse(
                event_uid=query.uid,
                event_name=query.name,
                event_description=query.description,
                event_start=query.event_start,
                event_end=query.event_end,
                status=query.status,
                creator=UserCreator.from_orm(query.creator),
                group=GroupName.from_orm(query.group),
            )
            for query in query
        ]

    def list_event_members(
        self, filter: FilterNameSchema
    ) -> list[ListEventMemberResponse]:
        query = self.events_query.list_event_members_admin(filter=filter)
        return [
            ListEventMemberResponse(
                event_member_uid=member.event_member_uid,
                user=UserEventSchema.from_orm(member.user),
                status=member.status,
            )
            for member in query
        ]
