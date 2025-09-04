from django.db.models import Case, CharField, Exists, OuterRef, Q, Value, When

from authenticate.models import User
from friend.models import Friend
from utils.types import TUser

from .schemas.request import UserFilterSchema


class Query:
    @staticmethod
    def search_user(user: TUser, search: UserFilterSchema):
        query = User.objects.filter(is_staff=False)
        list_user = query.filter(search.get_filter_expression())

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
