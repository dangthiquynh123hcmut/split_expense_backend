from typing import Optional
from uuid import UUID

from django.db.models import Case, CharField, F, Q, When

from attachment.schemas.responses import AttachmentResponse
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
            avatar_url=AttachmentResponse.from_orm(user.avatar_url)
            if user.avatar_url
            else None,
        )

    @staticmethod
    def list_friends(
        user: User,
        status: str,
        filter: Optional[FilterFriendSchema] = None,
        order_by: Optional[OrderByUserSchema] = None,
    ):
        query = Friend.objects.filter((Q(user=user) | Q(friend=user)), status=status)

        if filter and filter.search:
            query = query.filter(filter.filter_search(filter.search, user))

        query = query.annotate(
            full_name=Case(
                When(user=user, then=F("friend__full_name")),
                default=F("user__full_name"),
                output_field=CharField(),
            )
        )
        if order_by:
            query = query.order_by(order_by.get_order_by_expression())
        return query

    @staticmethod
    def find_relationship(user: User, friend: User) -> Optional[Friend]:
        return Friend.objects.filter(
            Q(user=user, friend=friend) | Q(user=friend, friend=user)
        ).first()

    @staticmethod
    def accept_request_friend(friendship_uid: UUID) -> Optional[Friend]:
        try:
            rel = Friend.objects.get(uid=friendship_uid)
        except Friend.DoesNotExist:
            return None
        if rel and rel.status == FriendStatusEnum.PENDING:
            rel.status = FriendStatusEnum.ACCEPTED
            rel.message_request = ""
            rel.save(update_fields=["status", "updated_at", "message_request"])
            return rel
        return None

    @staticmethod
    def remove_or_reject_friend(friendship_uid: UUID):
        try:
            rel = Friend.objects.get(uid=friendship_uid)
        except Friend.DoesNotExist:
            return None
        if rel:
            rel.delete()
            return True
        return False

    @staticmethod
    def get_friend_by_uid(uid: UUID) -> User | None:
        try:
            return User.objects.get(uid=uid)
        except User.DoesNotExist:
            return None

    @staticmethod
    def list_mutual_friends(user: TUser, friend_uid: UUID):
        def friend_q(uid):
            return Q(
                friend_fk_user__friend__uid=uid, friend_fk_user__status="ACCEPTED"
            ) | Q(friend_fk_friend__user__uid=uid, friend_fk_friend__status="ACCEPTED")

        return User.objects.filter(friend_q(user.uid) & friend_q(friend_uid)).distinct()

    # @staticmethod
    # def friends_profile(user: TUser, friend_uid: UUID):
    #     return
