from ninja import Query

from user.schemas.response import SearchUserResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get, post
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

from .schemas.request import ReviewUserRequest, UserFilterSchema
from .services import UserService


@api(
    prefix_or_class="users",
    tags=["Users"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class UserAPI(Controller):
    def __init__(self, service: UserService):
        self.service = service

    @get("", response=SearchUserResponse, paginate=True)
    @paginate
    def search_user(
        self, request: AuthenticatedRequest, search: UserFilterSchema = Query(...)
    ):
        return self.service.search_user(user=request.user, search=search)

    @post("/review", response=bool)
    def review_users(self, request: AuthenticatedRequest, data: ReviewUserRequest):
        self.service.review_users(user=request.user, rate=data.rate)
        return True
