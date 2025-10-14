from typing import Literal
from uuid import UUID

from ninja import Query

from exceptions.friends import FriendHasRelation, FriendshipNotFound
from exceptions.users import UserNotFound
from friend.schemas.response import FriendResponse, RequestAddFriend
from user.schemas.response import UserResponse
from utils.router.authenticate import AuthBear
from utils.router.controller import Controller, api, delete, get, post, put
from utils.router.paginate import paginate
from utils.router.permissions import IsAuthenticated
from utils.types import AuthenticatedRequest

from .schemas.request import AddFriendRequest, FilterFriendSchema, OrderByUserSchema
from .schemas.response import AddFriendResponse, FriendDebt, FriendOverview
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

    @get("/request", response=RequestAddFriend, paginate=True)
    @paginate
    def list_friend_request(
        self,
        request: AuthenticatedRequest,
        request_type: Literal["Received", "Sent"],
        filter: FilterFriendSchema = Query(...),
        order_by: OrderByUserSchema = Query(...),
    ):
        return self.service.list_friend_request(
            user=request.user,
            filter=filter,
            order_by=order_by,
            request_type=request_type,
        )

    @get("/{friend_uid}/mutual", response=UserResponse, paginate=True)
    @paginate
    def list_mutual_friends(self, request: AuthenticatedRequest, friend_uid: UUID):
        return self.service.list_mutual_friends(
            user=request.user, friend_uid=friend_uid
        )

    @get("/{friend_uid}", response=FriendOverview)
    def friends_overview(self, request: AuthenticatedRequest, friend_uid: UUID):
        return self.service.friends_overview(user=request.user, friend_uid=friend_uid)

    @put("/{friendship_uid}/accept", response=bool, exceptions=(FriendshipNotFound,))
    def accept_request_friend(self, friendship_uid: UUID):
        self.service.accept_request_friend(friendship_uid=friendship_uid)
        return True

    @delete("/{friendship_uid}/remove", response=bool, exceptions=(FriendshipNotFound,))
    def remove_or_reject_friend(self, friendship_uid: UUID):
        return self.service.remove_or_reject_friend(friendship_uid=friendship_uid)

    @get("/{friend_uid}/debt", response=FriendDebt, paginate=True)
    @paginate
    def friend_debt(self, request: AuthenticatedRequest, friend_uid: UUID):
        return self.service.friend_debt(user=request.user, friend_uid=friend_uid)
