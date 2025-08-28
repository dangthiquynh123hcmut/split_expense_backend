from typing import Optional

from django.db.models import Q

from authenticate.models import User
from utils.enums import FriendStatusEnum
from utils.types import TUser

from .models import Friend
from .schemas.request import FilterFriendSchema, OrderByUserSchema
from .schemas.response import AddFriendResponse


class Query:
    @staticmethod
    def send_friend_request(
        user: TUser, message: str, friend: User
    ) -> AddFriendResponse:
        Friend.objects.create(
            user=user,
            friend=friend,
            status=FriendStatusEnum.PENDING,
            message_request=message,
        )
        return AddFriendResponse(
            requester_uid=user.uid,
            receiver_uid=friend.uid,
            message=message,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
        )

    @staticmethod
    def list_friends(
        user: User,
        filter: Optional[FilterFriendSchema] = None,
        order_by: Optional[OrderByUserSchema] = None,
    ):
        query = Friend.objects.filter(Q(user=user) | Q(friend=user))

        if filter:
            query = query.filter(filter.get_filter_expression())

        if order_by:
            query = query.order_by(order_by.get_order_by_expression())

        return query

    @staticmethod
    def find_relationship(user: User, friend: User) -> Optional[Friend]:
        return Friend.objects.filter(
            Q(user=user, friend=friend) | Q(user=friend, friend=user)
        ).first()

    @staticmethod
    def accept_request(friend: User, user: User) -> bool:
        rel = Query.find_relationship(user=user, friend=friend)
        if rel and rel.status == FriendStatusEnum.PENDING:
            rel.status = FriendStatusEnum.ACCEPTED
            rel.save(update_fields=["status", "updated_at"])
            return True
        return False

    @staticmethod
    def reject_request(friend: User, user: User) -> bool:
        rel = Query.find_relationship(user=user, friend=friend)
        if rel and rel.status == FriendStatusEnum.PENDING:
            rel.delete()
            return True
        return False

    @staticmethod
    def remove_friend(user: User, friend: User) -> bool:
        rel = Query.find_relationship(user=user, friend=friend)
        if rel:
            rel.delete()
            return True
        return False
