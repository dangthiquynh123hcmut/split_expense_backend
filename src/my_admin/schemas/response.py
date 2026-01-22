from uuid import UUID

from ninja import Schema


class AdminResponse(Schema):
    email: str
    uid: UUID
    status: str


class TodayOverviewResponse(Schema):
    total_users: int
    percent_increase_users: float
    percent_increase_transactions: float
    percent_increase_money: float
    percent_increase_new_users: float
    total_transactions: int
    new_users: int
    total_money: int


class UserInsightsResponse(Schema):
    month_year: str
    new_users: int
    loyal_users: int
    return_users: int


class ExpenseCategoryResponse(Schema):
    category: str
    total_amount: float
