from uuid import UUID

from ninja import Query

from exceptions.friends import FriendHasRelation
from exceptions.users import UserNotFound
from friend.schemas.response import FriendResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

from .schemas.request import (
    AddFriendRequest,
    FilterFriendSchema,
    OrderByUserSchema,
    RespondFriendRequest,
)
from .schemas.response import AddFriendResponse
from .services import FriendService


@api(
    prefix_or_class="friends",
    tags=["Friends"],
    auth=AuthBear(),
    permissions=[IsAuthenticated],
)
class FriendAPI(Controller):
    def __init__(self, service: FriendService):
        self.service = service

    @post(
        "/request",
        response=AddFriendResponse,
        exceptions=(FriendHasRelation, UserNotFound),
    )
    def send_friend_request(
        self, request: AuthenticatedRequest, data: AddFriendRequest
    ):
        return self.service.send_friend_request(user=request.user, data=data)

    @get("", response=FriendResponse, paginate=True)
    @paginate
    def list_friends(
        self,
        request: AuthenticatedRequest,
        filter: FilterFriendSchema = Query(...),
        order_by: OrderByUserSchema = Query(...),
    ):
        return self.service.list_friends(
            user=request.user, filter=filter, order_by=order_by
        )

    @post("/respond", response=bool)
    def respond_request_friend(
        self, request: AuthenticatedRequest, data: RespondFriendRequest
    ):
        return self.service.respond_request_friend(user=request.user, data=data)

    @delete("/{friend_uid}", response=bool)
    def remove_friend(self, request: AuthenticatedRequest, friend_uid: UUID) -> bool:
        return self.service.remove_friend(user=request.user, friend_uid=friend_uid)
