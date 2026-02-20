from django.db.models import Case, CharField, Exists, OuterRef, Q, Value, When
from django.utils.timezone import now

from authenticate.models import User
from friend.models import Friend
from utils.functions.get_last_month import get_last_month
from utils.types import TUser

from .schemas.request import UserFilterSchema


class Query:
    @staticmethod
    def search_user(user: TUser, search: UserFilterSchema):
        list_user = User.objects.filter(
            Q(is_staff=False) & search.get_filter_expression()
        ).exclude(uid=user.uid)

        accepted_qs = Friend.objects.filter(
            Q(user=user, friend=OuterRef("pk"), status="ACCEPTED")
            | Q(user=OuterRef("pk"), friend=user, status="ACCEPTED")
        )

        pending_qs = Friend.objects.filter(
            user=user, friend=OuterRef("pk"), status="PENDING"
        )

        response_qs = Friend.objects.filter(
            user=OuterRef("pk"), friend=user, status="PENDING"
        )

        list_user = list_user.annotate(
            status=Case(
                When(Exists(accepted_qs), then=Value("ACCEPTED")),
                When(Exists(pending_qs), then=Value("PENDING")),
                When(Exists(response_qs), then=Value("RESPONSE")),
                default=Value("NONE"),
                output_field=CharField(),
            )
        )

        return list_user

    @staticmethod
    def update_balance(user: TUser, amount: float):
        user.balance += amount
        user.save()
        return

    @staticmethod
    def total_users_in_app():
        start_last_month, end_last_month = get_last_month(now())
        start_this_month = now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return User.objects.filter(
            date_joined__gte=start_this_month
        ).count(), User.objects.filter(
            date_joined__gte=start_last_month, date_joined__lte=end_last_month
        ).count()
