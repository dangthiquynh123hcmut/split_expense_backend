from typing import Optional

from authenticate.queries import Query as Auth_Query
from my_admin.schemas.request import OrderByBalanceSchema
from my_admin.schemas.response import TodayOverviewResponse, UserInsightsResponse
from wallet.orm.deposit import DepositORM
from wallet.orm.transaction import TransactionORM
from wallet.orm.withdraw import WithdrawORM

from ..orm.admin_orm import Query
from ..schemas.request import UserFilter


class AdminService:
    def __init__(self):
        self.query = Query()
        self.auth_query = Auth_Query()
        self.withdraw_query = WithdrawORM()
        self.deposit_query = DepositORM()
        self.transaction_query = TransactionORM()

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
        total_withdrawals_today, total_withdrawals_yesterday = (
            self.withdraw_query.total_withdrawals_today()
        )
        total_transactions_today = (
            total_deposit_today + total_withdrawals_today + total_tranfer_today
        )
        total_transactions_yesterday = (
            total_deposit_yesterday
            + total_withdrawals_yesterday
            + total_tranfer_yesterday
        )
        total_admins_today, total_admins_yesterday = self.query.count_total_admins()
        new_users_today, new_users_yesterday = self.auth_query.count_new_users()

        return TodayOverviewResponse(
            total_users=total_users_today,
            total_transactions=total_transactions_today,
            total_admins=total_admins_today,
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
            percent_increase_admins=(
                (total_admins_today - total_admins_yesterday)
                / total_admins_yesterday
                * 100
                if total_admins_yesterday > 0
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
