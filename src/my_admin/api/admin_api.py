from ninja import Query

from my_admin.schemas.request import OrderByBalanceSchema
from my_admin.schemas.response import RatingResponse
from user.schemas.response import UserResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get
from utils.router.paginate import paginate
from utils.router.permissions import IsAdminUser
from utils.schemas.filter_and_order_by import FilterDateSchema

from ..schemas.request import UserFilter
from ..schemas.response import (
    ExpenseCategoryResponse,
    TodayOverviewResponse,
    UserInsightsResponse,
)
from ..service.admin_service import AdminService


@api(
    prefix_or_class="admin",
    tags=["Admin"],
    auth=AuthBear(),
    permissions=[IsAdminUser],
)
class AdminController(Controller):
    def __init__(self, service: AdminService):
        self.service = service

    @get("/users", response=UserResponse, paginate=True)
    @paginate
    def list_users(
        self,
        filter: UserFilter = Query(...),
        order_by: OrderByBalanceSchema = Query(...),
    ):
        return self.service.list_users(filter=filter, order_by=order_by)

    @get("/today-overview", response=TodayOverviewResponse)
    def today_overview(self):
        return self.service.today_overview()

    @get("/user-insights", response=list[UserInsightsResponse])
    def user_insights(self, year: int = Query(...)):
        return self.service.user_insights(year=year)

    @get("/expense-categories", response=list[ExpenseCategoryResponse])
    def expense_categories(self):
        return self.service.expense_categories()

    @get("/rating", response=list[RatingResponse])
    def rating(self, filter: FilterDateSchema = Query(...)):
        return self.service.rating(filter=filter)
