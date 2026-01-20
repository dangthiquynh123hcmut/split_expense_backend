from typing import Optional

from friend.schemas.request import OrderByUserSchema

from ..orm.admin_orm import Query
from ..schemas.request import UserFilter


class AdminService:
    def __init__(self):
        self.query = Query()

    def list_users(
        self,
        filter: Optional[UserFilter] = None,
        order_by: Optional[OrderByUserSchema] = None,
    ):
        return self.query.list_users(filter=filter, order_by=order_by)
