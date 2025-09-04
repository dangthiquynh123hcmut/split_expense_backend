from django.db.models import OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from authenticate.models import User
from friend.models import Friend
from utils.types import TUser

from .schemas.request import UserFilterSchema


class Query:
    @staticmethod
    def search_user(user: TUser, search: UserFilterSchema):
        query = User.objects.filter(is_staff=False)
        list_user = query.filter(search.get_filter_expression())

        friend_status_qs = Friend.objects.filter(
            Q(user=user, friend=OuterRef("pk")) | Q(user=OuterRef("pk"), friend=user)
        ).values("status")[:1]

        list_user = list_user.annotate(
            status=Coalesce(Subquery(friend_status_qs), Value("NONE"))
        )

        return list_user
