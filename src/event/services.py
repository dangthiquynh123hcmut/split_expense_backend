from decimal import Decimal
from uuid import UUID

from django.db import transaction

from authenticate.queries import Query as UseQuery
from exceptions.event import EventNotFound
from exceptions.group import GroupNotFound
from exceptions.users import UserNotFound
from expense.queries import Query as ExpenseQuery
from group.queries import Query as GroupQuery
from message.orm.notification_queries import NotificationORM
from utils.enums import NotificationTypeEnum
from utils.exceptions import (
    CreateIsDenied,
    DeleteIsDenied,
    GetIsDenied,
    UpdatedIsDenied,
)
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
)
from utils.services.firebase_cm.fcm_service import FCMService
from utils.types import TUser

from .models import EventMember
from .queries import Query
from .schemas.request import AddMember, EventRequest, EventUpdateRequest


class Service:
    def __init__(self):
        self.query = Query()
        self.group_query = GroupQuery()
        self.user_query = UseQuery()
        self.expense_query = ExpenseQuery()
        self.notification_orm = NotificationORM()
        self.fcm_service = FCMService()

    def create_event(self, user: TUser, data: EventRequest):
        group = self.group_query.get_group_sync(group_uid=data.group_id)
        if not group:
            raise GroupNotFound
        event = self.query.create_event(
            user=user, **data.dict(exclude={"list_user_uid"})
        )
        users = self.user_query.get_user_by_uids(uids=data.list_user_uid)
        if data.list_user_uid and len(users) != len(data.list_user_uid):
            raise UserNotFound
        is_member_in_group = self.group_query.get_group_has_user(user=user, group=group)
        if not is_member_in_group:
            raise CreateIsDenied
        event_members = [EventMember(event=event, user=user) for user in users]
        member = EventMember(event=event, user=user)
        event_members.append(member)
        self.query.create_event_members(event_members=event_members)
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have created an event {event.name}",
            type=NotificationTypeEnum.EVENT_CREATED,
            related_uid=event.uid,
            to_users=[member.user for member in event_members],
        )
        self.fcm_service.send_multicast_notification(
            tokens=[
                member.user.fcm_token
                for member in event_members
                if member.user.fcm_token
            ],
            title="Event created",
            body=f"{user.full_name} have created an event {event.name}",
        )
        return event

    def get_event(self, event_uid: UUID):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        return event

    @transaction.atomic
    def update_event(self, user: TUser, event_uid: UUID, data: EventUpdateRequest):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        is_member_in_event = self.query.get_event_has_user(user=user, event=event)
        if not is_member_in_event:
            raise UpdatedIsDenied
        self.query.update_event(event=event, data=data)
        event_members = self.query.get_event_members(event=event)
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have updated an event {event.name}",
            type=NotificationTypeEnum.EVENT_UPDATED,
            related_uid=event.uid,
            to_users=[member.user for member in event_members],
        )
        return event

    # def leave_event(self, user: TUser, event_uid: UUID):
    #     event = self.query.get_event(event_uid=event_uid)
    #     if not event:
    #         raise EventNotFound
    #     return self.query.leave_event(user=user, event=event)

    def delete_event(self, user: TUser, event_uid: UUID):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        if user != event.creator:
            raise DeleteIsDenied
        result = self.query.delete_event(event_uid=event_uid)
        event_members = self.query.get_event_members(event=event)
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have deleted an event {event.name}",
            type=NotificationTypeEnum.EVENT_DELETED,
            related_uid=event.uid,
            to_users=[member.user for member in event_members],
        )
        return result

    def list_event_members(
        self,
        user: TUser,
        event_uid: UUID,
        filter: FilterFullNameSchema,
        order_by: OrderByFullNameAndUpdatedAtSchema,
    ):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        is_member_in_event = self.query.get_event_has_user(user=user, event=event)
        if not is_member_in_event:
            raise GetIsDenied
        return self.query.list_event_members(
            event=event, filter=filter, order_by=order_by
        )

    def join_event(self, user: TUser, event_uid: UUID):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        return self.query.join_event(user=user, event=event)

    def list_events_groups(
        self,
        user: TUser,
        filter: FilterNameSchema,
    ):
        return self.query.list_events_groups(user=user, filter=filter)

    def add_member_to_event(self, event_uid: UUID, data: AddMember):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        users = self.user_query.get_user_by_uids(uids=data.user_uids)
        if data.user_uids and len(users) != len(data.user_uids):
            raise UserNotFound
        event_members = [EventMember(event=event, user=user) for user in users]
        self.query.create_event_members(event_members=event_members)
        return

    def get_event_spending(self, user: TUser, event_uid: UUID, currency: str = "VND"):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        is_member_in_event = self.query.get_event_has_user(user=user, event=event)
        if not is_member_in_event:
            raise GetIsDenied
        agg = self.expense_query.total_expenses_in_event(event=event, currency=currency)
        total_amount = Decimal(agg["total_amount"] or 0.0)
        return self.query.get_event_spending(
            event=event, total_amount=total_amount, currency=currency
        )

    def chart_expenses_in_event(self, user: TUser, event_uid: UUID, year: int):
        event = self.query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        is_member_in_event = self.query.get_event_has_user(user=user, event=event)
        if not is_member_in_event:
            raise GetIsDenied
        return self.expense_query.chart_expenses(user=user, event=event, year=year)
