from uuid import UUID

from authenticate.models import User
from event.queries import Query as EventQuery
from exceptions.friends import FriendHasRelation, FriendshipNotFound
from exceptions.users import UserNotFound
from expense.queries import Query as ExpenseQuery
from friend.schemas.response import FriendResponse, RequestAddFriend
from group.queries import Query as GroupQuery
from utils.types import TUser

from .queries import Query
from .schemas.request import AddFriendRequest, FilterFriendSchema, OrderByUserSchema
from .schemas.response import FriendOverview


class FriendService:
    def __init__(self):
        self.query = Query()
        self.group_query = GroupQuery()
        self.event_query = EventQuery()
        self.expense_query = ExpenseQuery()

    def get_friend_by_uid(self, uid: UUID) -> User:
        friend = self.query.get_friend_by_uid(uid=uid)
        if not friend:
            raise UserNotFound
        return friend

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

    def accept_request_friend(self, friendship_uid: UUID):
        friendship = self.query.accept_request_friend(friendship_uid=friendship_uid)
        if not friendship:
            raise FriendshipNotFound

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
        return FriendOverview(
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
