from typing import List

from ninja import Query

from friend.schemas.response import UserResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, get
from utils.router.permissions import IsAuthenticated

from .schemas.request import UserFilterSchema
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

    @get("", response=List[UserResponse])
    def search_user(self, search: UserFilterSchema = Query(...)):
        return self.service.search_user(search=search)
