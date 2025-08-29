from uuid import UUID

from authenticate.models import User
from exceptions.friends import FriendHasRelation
from exceptions.users import UserNotFound
from friend.schemas.response import FriendResponse, RequestAddFriend
from utils.types import TUser

from .queries import Query
from .schemas.request import AddFriendRequest, FilterFriendSchema, OrderByUserSchema


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
        list_friends = self.query.list_friends(
            user=user, filter=filter, order_by=order_by, status="ACCEPTED"
        )
        friends = []
        for f in list_friends:
            if f.user == user:
                other = f.friend
            else:
                other = f.user

            friends.append(
                FriendResponse(
                    friendship_uid=f.uid,
                    friend_uid=other.uid,
                    full_name=other.full_name,
                    avatar_url=other.avatar_url,
                )
            )

        return friends

    def list_friend_request(
        self,
        user: TUser,
        filter: FilterFriendSchema,
        order_by: OrderByUserSchema,
        request_type: str,
    ):
        queryset = self.query.list_friends(
            user=user, filter=filter, order_by=order_by, status="PENDING"
        )
        if not queryset.exists():
            return []

        list_received = []
        list_sent = []

        for f in queryset:
            if f.user == user:
                fri = f.friend
                list_sent.append(
                    RequestAddFriend(
                        friendship_uid=f.uid,
                        friend_uid=fri.uid,
                        full_name=fri.full_name,
                        avatar_url=fri.avatar_url,
                        message_request=f.message_request,
                    )
                )
            else:
                other = f.user
                list_received.append(
                    RequestAddFriend(
                        friendship_uid=f.uid,
                        friend_uid=other.uid,
                        full_name=other.full_name,
                        avatar_url=other.avatar_url,
                        message_request=f.message_request,
                    )
                )

        if request_type == "Received":
            return list_received
        if request_type == "Sent":
            return list_sent

    def accept_request_friend(self, friendship_uid: UUID):
        return self.query.accept_request_friend(friendship_uid=friendship_uid)

    def remove_or_reject_friend(self, friendship_uid: UUID):
        return self.query.remove_or_reject_friend(friendship_uid=friendship_uid)
