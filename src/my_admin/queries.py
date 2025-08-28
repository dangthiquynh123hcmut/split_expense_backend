from typing import Optional

from authenticate.models import User
from friend.schemas.request import OrderByUserSchema

from .schemas.request import UserFilter


class Query:
    @staticmethod
    def list_users(
        filter: Optional[UserFilter] = None,
        order_by: Optional[OrderByUserSchema] = None,
    ):
        query = User.objects.filter(is_staff=False)

        if filter:
            query = query.filter(filter.get_filter_expression())
        if order_by:
            query = query.order_by(order_by.get_order_by_expression())
        return query
