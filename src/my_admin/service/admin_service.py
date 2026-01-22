from typing import Optional

from authenticate.queries import Query as Auth_Query
from expense.queries import Query as ExpenseQuery
from my_admin.schemas.request import OrderByBalanceSchema
from my_admin.schemas.response import (
    ExpenseCategoryResponse,
    TodayOverviewResponse,
    UserInsightsResponse,
)
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
        self.expense_query = ExpenseQuery()

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
