from authenticate.models import User

from .schemas.request import UserFilterSchema


class Query:
    @staticmethod
    def search_user(search: UserFilterSchema):
        query = User.objects.filter(is_staff=False)
        return query.filter(search.get_filter_expression())
