from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from django.db.models import Avg, Count, F
from django.db.models.functions import ExtractMonth, TruncDate
from django.utils.timezone import now

from authenticate.models import User
from my_admin.schemas.request import OrderByBalanceSchema
from utils.schemas.filter_and_order_by import FilterDateSchema

from ..models import LoginHistory, RatingMonthly, UserMonthlyActivity
from ..schemas.request import UserFilter


class Query:
    @staticmethod
    def list_users(
        filter: Optional[UserFilter] = None,
        order_by: Optional[OrderByBalanceSchema] = None,
    ):
        query = User.objects.filter(is_staff=False)

        if filter:
            query = query.filter(filter.get_filter_expression())
        if order_by:
            query = query.order_by(order_by.get_order_by_expression())
        return query

    @staticmethod
    def count_total_admins():
        return User.objects.filter(
            is_staff=True, role="ADMIN", is_active=True
        ).count(), User.objects.filter(
            is_staff=True,
            role="ADMIN",
            is_active=True,
            date_joined__date__lt=now().date(),
        ).count()

    @staticmethod
    def user_insights(year: int):
        new_users_by_month = defaultdict(int)
        new_users_qs = (
            User.objects.filter(role="USER", is_active=True, date_joined__year=year)
            .annotate(signup_month=ExtractMonth("date_joined"))
            .values("signup_month")
            .annotate(count=Count("uid"))
        )

        for item in new_users_qs:
            new_users_by_month[item["signup_month"]] = item["count"]

        activities = (
            UserMonthlyActivity.objects.filter(
                year=year, user__role="USER", user__is_active=True
            )
            .select_related("user")
            .values("month", "user__uid", "user__date_joined", "login_count")
        )

        activity_by_month: Dict[int, Dict[Any, Dict[str, Any]]] = defaultdict(dict)

        for activity in activities:
            month = activity["month"]
            user_uid = activity["user__uid"]
            signup_date = activity["user__date_joined"]
            login_count = activity["login_count"]

            activity_by_month[month][user_uid] = {
                "date_joined": signup_date,
                "login_count": login_count,
            }

        insights_data = []

        for month in range(1, 13):
            signup_month_start = datetime(year, month, 1)

            new_users = new_users_by_month.get(month, 0)

            loyal_users = len(
                [
                    uid
                    for uid, data in activity_by_month[month].items()
                    if data["login_count"] >= 5
                ]
            )

            return_users = len(
                [
                    uid
                    for uid, data in activity_by_month[month].items()
                    if data["date_joined"] < signup_month_start
                ]
            )

            month_year = datetime(year, month, 1).strftime("%m/%Y")

            insights_data.append(
                {
                    "month_year": month_year,
                    "new_users": new_users,
                    "loyal_users": loyal_users,
                    "return_users": return_users,
                }
            )

        return insights_data

    @staticmethod
    def rating(filter: FilterDateSchema):
        return (
            RatingMonthly.objects.filter(filter.get_filter_expression())
            .annotate(date=TruncDate(F("created_at")))  # type: ignore
            .values("date")
            .annotate(avg_rate=Avg("rate"))
            .order_by("date")
        )

    @staticmethod
    def update_rating_monthly(user: User, rate: int):
        RatingMonthly.objects.update_or_create(user=user, rate=rate)
        return

    @staticmethod
    def list_user_login_history(user_uid: UUID):
        return LoginHistory.objects.filter(user__uid=user_uid).order_by("-created_at")

    @staticmethod
    def create_user_login_history(user: User, **kwargs):
        LoginHistory.objects.create(user=user, **kwargs)
