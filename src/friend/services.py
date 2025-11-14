from uuid import UUID

from django.db import transaction

from attachment.schemas.responses import AttachmentResponse
from authenticate.models import User
from event.queries import Query as EventQuery
from exceptions.friends import FriendHasRelation, FriendshipNotFound
from exceptions.users import UserNotFound
from expense.queries import Query as ExpenseQuery
from friend.schemas.response import FriendResponse, RequestAddFriend
from group.queries import Query as GroupQuery
from message.orm.notification_queries import NotificationORM
from user.schemas.response import UserResponse
from utils.enums import NotificationTypeEnum
from utils.services.fcm_service import FCMService
from utils.types import TUser

from .queries import Query
from .schemas.request import AddFriendRequest, FilterFriendSchema, OrderByUserSchema
from .schemas.response import AddFriendResponse, FriendOverview


class FriendService:
    def __init__(self):
        self.query = Query()
        self.group_query = GroupQuery()
        self.event_query = EventQuery()
        self.expense_query = ExpenseQuery()
        self.fcm_service = FCMService()
        self.notification_orm = NotificationORM()

    def get_friend_by_uid(self, uid: UUID) -> User:
        friend = self.query.get_friend_by_uid(uid=uid)
        if not friend:
            raise UserNotFound
        return friend

    @transaction.atomic
    def send_friend_request(self, user: TUser, data: AddFriendRequest):
        friend = self.get_friend_by_uid(uid=data.receiver_uid)
        if self.query.find_relationship(user=user, friend=friend):
            raise FriendHasRelation
        if user.uid == friend.uid:
            raise FriendHasRelation
        friendship = self.query.send_friend_request(
            user=user, message=data.message, friend=friend
        )

        if friend.fcm_token:
            self.fcm_service.send_notification(
                token=friend.fcm_token,
                title="Friend request",
                body=f"You have received a friend request from {user.full_name}",
            )

        self.notification_orm.create_notification(
            from_user=user,
            related_uid=friendship.uid,
            content=f"{user.full_name} has sent you a friend request. message: {data.message}",
            type=NotificationTypeEnum.FRIEND_REQUEST,
            to_users=[friend],
        )
        return AddFriendResponse(
            requester_uid=user.uid,
            receiver_uid=friend.uid,
            message=data.message,
            full_name=user.full_name,
            avatar_url=AttachmentResponse.from_orm(user.avatar_url)
            if user.avatar_url
            else None,
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
                    start=f.updated_at,
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

    @transaction.atomic
    def accept_request_friend(self, friendship_uid: UUID):
        friendship = self.query.accept_request_friend(friendship_uid=friendship_uid)
        if not friendship:
            raise FriendshipNotFound
        self.fcm_service.send_notification(
            token=friendship.user.fcm_token,
            title="Friend request",
            body=f"{friendship.friend.full_name} accepted your friend request",
        )
        self.notification_orm.create_notification(
            from_user=friendship.friend,
            related_uid=friendship.uid,
            content=f"{friendship.friend.full_name} accepted your friend request",
            type=NotificationTypeEnum.FRIEND_ACCEPTED,
            to_users=[friendship.user],
        )
        return

    def remove_or_reject_friend(self, friendship_uid: UUID):
        friendship = self.query.remove_or_reject_friend(friendship_uid=friendship_uid)
        if not friendship:
            raise FriendshipNotFound
        return friendship

    def list_mutual_friends(self, user: TUser, friend_uid: UUID):
        friend = self.query.get_friend_by_uid(uid=friend_uid)
        if not friend:
            raise UserNotFound
        return self.query.list_mutual_friends(user=user, friend=friend)

    def friends_overview(self, user: TUser, friend_uid: UUID):
        friend = self.query.get_friend_by_uid(uid=friend_uid)
        if not friend:
            raise UserNotFound
        mutual_groups = self.group_query.total_mutual_groups(user=user, friend=friend)
        shared_events = self.event_query.total_mutual_events(user=user, friend=friend)
        shared_expenses = self.expense_query.total_mutual_expenses(
            user=user, friend=friend
        )
        total_debt = self.group_query.total_debt_between_two_people(
            user=user, friend=friend
        )
        friendship = self.query.find_relationship(user=user, friend=friend)
        if not friendship:
            status = "NOTYET"
            friendship_uid = None
            message_request = None
        else:
            if friendship.status == "PENDING" and friendship.user == user:
                status = "SENT"
            elif friendship.status == "PENDING" and friendship.friend == user:
                status = "RECEIVED"
            else:
                status = friendship.status
            friendship_uid = friendship.uid
            message_request = friendship.message_request
        return FriendOverview(
            friend=UserResponse.from_orm(friend),
            message=message_request,
            status=status,
            friendship_uid=friendship_uid,
            mutual_groups=mutual_groups,
            shared_events=shared_events,
            shared_expenses=shared_expenses,
            total_debt=total_debt,
        )

    def friend_debt(self, user: TUser, friend_uid: UUID):
        friend = self.query.get_friend_by_uid(uid=friend_uid)
        if not friend:
            raise UserNotFound
        return self.group_query.friend_debt(user=user, friend=friend)
