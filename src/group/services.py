from decimal import Decimal
from typing import List
from uuid import UUID

from django.db import transaction

from authenticate.queries import Query as UserQuery
from event.queries import Query as EventQuery
from exceptions.group import GroupNotFound, LeaveIsDenied, UserNotInGroup
from exceptions.users import UserNotFound
from expense.queries import Query as ExpenseQuery
from expense.schemas.response import NameExpense
from message.orm.notification_queries import NotificationORM
from utils.enums import NotificationTypeEnum
from utils.exceptions import DeleteIsDenied, GetIsDenied, UpdatedIsDenied
from utils.schemas.filter_and_order_by import (
    FilterCurrencySchema,
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.services.firebase_cm.fcm_service import FCMService
from utils.types import TUser
from wallet.orm.transaction import TransactionORM

from .models import GroupMember
from .queries import Query
from .schemas.request import GroupUpdateRequest
from .schemas.response import DebtMember, DetailGroup, GroupReport, GroupResponse


class Service:
    def __init__(self):
        self.query = Query()
        self.user_query = UserQuery()
        self.expense_query = ExpenseQuery()
        self.event_query = EventQuery()
        self.transaction_orm = TransactionORM()
        self.fcm_service = FCMService()
        self.notification_orm = NotificationORM()

    @transaction.atomic
    def create_group(self, leader: TUser, name: str, list_user_uids: List[UUID]):
        group = self.query.create_group(leader=leader, name=name)
        members = self.user_query.get_user_by_uids(uids=list_user_uids)
        if len(members) != len(list_user_uids):
            raise UserNotFound
        group_members = [GroupMember(group=group, user=member) for member in members]
        group_members.append(GroupMember(group=group, user=leader))
        self.query.create_group_members(group_members=group_members)
        self.fcm_service.send_multicast_notification(
            tokens=[
                member.user.fcm_token
                for member in group_members
                if member.user.fcm_token
            ],
            title="Group created",
            body=f"{leader.full_name} have created a group {name}",
        )
        self.notification_orm.create_notification(
            from_user=leader,
            content=f"{leader.full_name} have created a group {name}",
            type=NotificationTypeEnum.GROUP_CREATED,
            related_uid=group.uid,
            to_users=[member.user for member in group_members],
        )
        return group

    def list_groups(
        self,
        user: TUser,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        return self.query.list_groups(user=user, filter=filter, order_by=order_by)

    def get_group(self, group_uid: UUID):
        return self.query.get_group_sync(group_uid=group_uid)

    @transaction.atomic
    def update_group(self, user: TUser, group_uid: UUID, data: GroupUpdateRequest):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise UpdatedIsDenied
        group = self.query.update_group(group=group, name=data.name)

        existing_members = self.query.get_members_by_uids(
            group=group, uids=data.list_add_uids
        )
        existing_uids = {m.user_id for m in existing_members}
        list_add_uids = data.list_add_uids or []
        add_member_uids = [u for u in list_add_uids if u not in existing_uids]
        add_members = self.user_query.get_user_by_uids(uids=add_member_uids)
        if len(list_add_uids) != len(add_member_uids) + len(existing_uids):
            raise UserNotFound
        group_members = [
            GroupMember(group=group, user=member) for member in add_members
        ]
        self.query.create_group_members(group_members=group_members)

        if data.list_delete_uids:
            deleted_members = self.query.get_members_by_uids(
                group=group, uids=data.list_delete_uids
            )
            if len(deleted_members) != len(data.list_delete_uids):
                raise UserNotInGroup
            for deleted_member in deleted_members:
                if deleted_member.total_amount != 0:
                    raise DeleteIsDenied
            self.query.delete_group_members(group_members=deleted_members)
        members = self.query.list_group_members_not_filter(group=group)
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have updated a group {group.name}",
            type=NotificationTypeEnum.GROUP_UPDATED,
            related_uid=group.uid,
            to_users=[member.user for member in members],
        )
        return group

    def leave_group(self, user: TUser, group_uid: UUID):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound

        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise UserNotInGroup
        if member.total_amount != 0:
            raise LeaveIsDenied
        query = self.query.leave_group(user=user, group=group)
        return query

    def delete_group(self, user: TUser, group_uid: UUID):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        if group.leader != user and not user.is_staff:
            raise DeleteIsDenied
        self.query.delete_group(group=group)
        return True

    def list_group_members(
        self,
        user: TUser,
        group_uid: UUID,
        filter: FilterFullNameSchema,
        order_by: OrderByFullNameAndUpdatedAtSchema,
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member and not user.is_staff:
            raise GetIsDenied
        return self.query.list_group_members(
            group=group, filter=filter, order_by=order_by
        )

    def get_group_detail(
        self, user: TUser, group_uid: UUID, filter: FilterCurrencySchema
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        event_attended = self.event_query.events_attended_in_group(
            user=user, group=group
        )
        event_total = self.event_query.total_events_in_group(group=group)
        agg = self.expense_query.total_expenses_in_group(group=group)
        total_amount = float(agg["total_amount"] or 0.0)
        expense_total = agg["expense_total"] or 0
        agg = self.expense_query.expense_attended_in_group(user=user, group=group)
        user_spent = float(agg["user_spent"] or 0.0)
        expense_attended = agg["expense_attended"] or 0
        restructured_debt = self.query.restructured_debt(
            user=user, group=group, filter=filter
        )

        return DetailGroup(
            group=GroupResponse.from_orm(group),
            event_attended=f"{event_attended}/{event_total}",
            shared_expenses=f"{expense_attended}/{expense_total}",
            total_amount=total_amount,
            user_spent=user_spent if user_spent > 0 else -user_spent,
            restructured_debt=[
                DebtMember(
                    debtor=rd.debtor,
                    creditor=rd.creditor,
                    value=float(rd.value),
                    currency=rd.currency,
                )
                for rd in restructured_debt
            ],
        )

    def list_events_in_a_group(
        self,
        user: TUser,
        group_uid: UUID,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member and not user.is_staff:
            raise GetIsDenied
        return self.query.list_events_in_a_group(
            group=group, filter=filter, order_by=order_by
        )

    def list_expenses_in_a_group(
        self,
        user: TUser,
        group_uid: UUID,
        status: str,
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        queryset = self.query.list_expenses_in_a_group(
            user=user,
            group=group,
            status=status,
        )
        transactions_query = self.transaction_orm.get_transactions_in_group(group=group)

        if status == "ACTIVE":
            transactions = [
                NameExpense(
                    uid=txn.uid,
                    category="Transfer",
                    currency=txn.currency,
                    amount=float(txn.amount),
                    created_at=txn.created_at,
                    from_user=txn.from_user.full_name,
                    to_user=txn.to_user.full_name,
                    name=f"From {txn.from_user.full_name} to {txn.to_user.full_name}",
                )
                for txn in transactions_query
            ]
        else:
            transactions = []

        combined = queryset + transactions

        combined_sorted = sorted(combined, key=lambda x: x.created_at, reverse=True)

        return combined_sorted

    def update_group_leader(self, user: TUser, group_uid: UUID, new_leader: UUID):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member or group.leader != user:
            raise UpdatedIsDenied
        leader = self.user_query.get_user_by_uid(uid=new_leader)
        self.query.update_group_leader(group=group, leader=leader)
        members = self.query.list_group_members_not_filter(group=group)
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{leader.full_name} is new leader of group {group.name}",
            type=NotificationTypeEnum.GROUP_UPDATED,
            related_uid=group.uid,
            to_users=[member.user for member in members],
        )
        return group

    def get_balances_by_group_and_member(
        self,
        user: TUser,
        currency: str,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        return self.query.get_balances_by_group_and_member(
            user=user, currency=currency, filter=filter, order_by=order_by
        )

    def group_report(self, user: TUser, group_uid: UUID):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        events = self.event_query.total_events_in_group(group=group)
        agg = self.expense_query.total_expenses_in_group(group=group)
        total_amount = float(agg["total_amount"] or 0.0)
        shared_expenses = agg["expense_total"] or 0
        members = self.query.get_member_count(group=group)

        return GroupReport(
            group=GroupResponse.from_orm(group),
            events=events,
            shared_expenses=shared_expenses,
            total_amount=total_amount,
            members=members,
        )

    def get_member_spending(self, user: TUser, group_uid: UUID, currency: str = "VND"):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        agg = self.expense_query.total_expenses_in_group(group=group, currency=currency)
        total_amount = Decimal(agg["total_amount"] or 0.0)
        return self.query.get_member_spending(
            group=group, total_amount=total_amount, currency=currency
        )

    def chart_expenses_in_group(self, user: TUser, group_uid: UUID, year: int):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        return self.expense_query.chart_expenses(user=user, group=group, year=year)
