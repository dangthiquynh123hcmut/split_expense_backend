from uuid import UUID

from authenticate.models import User
from exceptions.friends import FriendHasRelation
from exceptions.users import UserNotFound
from utils.types import TUser

from .queries import Query
from .schemas.request import (
    AddFriendRequest,
    FilterFriendSchema,
    OrderByUserSchema,
    RespondFriendRequest,
)


class FriendService:
    def __init__(self):
        self.query = Query()

    @staticmethod
    def get_friend_by_uid(uid: UUID) -> User:
        try:
            return User.objects.get(uid=uid)
        except User.DoesNotExist:
            raise UserNotFound

    def send_friend_request(self, user: TUser, data: AddFriendRequest):
        friend = self.get_friend_by_uid(uid=data.receiver_uid)
        if self.query.find_relationship(user=user, friend=friend):
            raise FriendHasRelation
        if user.uid == friend.uid:
            raise FriendHasRelation
        return self.query.send_friend_request(
            user=user, message=data.message, friend=friend
        )

    def list_friends(
        self, user: TUser, filter: FilterFriendSchema, order_by: OrderByUserSchema
    ):
        return self.query.list_friends(user=user, filter=filter, order_by=order_by)

    def respond_request_friend(self, user: TUser, data: RespondFriendRequest):
        friend = self.get_friend_by_uid(uid=data.requester_uid)
        if data.action == "ACCEPT":
            return self.query.accept_request(friend=friend, user=user)
        if data.action == "REJECT":
            return self.query.reject_request(friend=friend, user=user)

    def remove_friend(self, user: TUser, friend_uid: UUID):
        friend = self.get_friend_by_uid(uid=friend_uid)
        return self.query.remove_friend(user=user, friend=friend)
