from ninja import Query

from friend.schemas.request import OrderByUserSchema
from friend.schemas.response import UserResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get
from utils.router.paginate import paginate
from utils.router.permissions import IsAdminUser

from .schemas.request import UserFilter
from .services import AdminService


@api(
    prefix_or_class="admin", tags=["Admin"], auth=AuthBear(), permissions=[IsAdminUser]
)
class AdminAPI(Controller):
    def __init__(self, service: AdminService):
        self.service = service

    @get("/users", response=UserResponse, paginate=True)
    @paginate
    def list_users(
        self,
        filter: UserFilter = Query(...),
        order_by: OrderByUserSchema = Query(...),
    ):
        return self.service.list_users(filter=filter, order_by=order_by)
