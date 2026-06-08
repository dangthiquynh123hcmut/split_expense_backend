from decimal import Decimal
from typing import List
from uuid import UUID

from django.db import transaction

from authenticate.queries import Query as AuthQuery
from authenticate.queries import Query as UserQuery
from event.queries import Query as EventQuery
from exceptions.group import GroupNotFound, LeaveIsDenied, UserNotInGroup
from exceptions.users import UserNotFound
from expense.queries import Query as ExpenseQuery
from expense.schemas.response import NameExpense
from message.orm.notification_queries import NotificationORM
from utils.enums import DebtOptimizationEnum, NotificationTypeEnum
from utils.exceptions import DeleteIsDenied, GetIsDenied, UpdatedIsDenied
from utils.functions.debt_simplification import settle_event_debts_by_group_payment
from utils.schemas.filter_and_order_by import (
    FilterCurrencySchema,
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.services.email.client import EmailClient
from utils.services.email.template import EmailTemplate
from utils.services.firebase_cm.fcm_service import FCMService
from utils.types import TUser
from wallet.orm.transaction import TransactionORM

from .models import GroupMember, GroupMemberBalance
from .queries import Query
from .schemas.request import ExternalTransferRequest, GroupUpdateRequest, RemindRequest
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
        self.auth_query = AuthQuery()
        self.transaction_orm = TransactionORM()
        self.email_client = EmailClient()
        self.email_template = EmailTemplate()

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
        if (
            GroupMemberBalance.objects.filter(group=group, user=user)
            .exclude(balance=0)
            .exists()
        ):
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

    def update_debt_optimization(
        self, user: TUser, group_uid: UUID, debt_optimization: str
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        if group.leader != user:
            raise UpdatedIsDenied
        return self.query.update_debt_optimization(
            group=group, debt_optimization=debt_optimization
        )

    @transaction.atomic
    def remind_group_members(
        self, user: TUser, group_uid: UUID, payload: RemindRequest
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        if payload.user_uid:
            remind_member = self.user_query.get_user_by_uid(uid=payload.user_uid)
            if not remind_member:
                raise UserNotFound
        else:
            remind_member = self.query.get_all_users_debt(user=user, group=group)

        self.notification_orm.create_notification(
            from_user=user,
            content=f"You owe money in group {group.name}. Click to see details.",
            type=NotificationTypeEnum.REMINDER,
            related_uid=group_uid,
            to_users=[member.user for member in remind_member]
            if isinstance(remind_member, list)
            else [remind_member],
        )

        if isinstance(remind_member, list):
            for member in remind_member:
                self.fcm_service.send_notification(
                    token=member.fcm_token,
                    title=f"Reminder from {group.name}",
                    body=f"You owe money in group {group.name}. Click to see details.",
                )
        else:
            self.fcm_service.send_notification(
                token=remind_member.fcm_token,
                title=f"Reminder from {group.name}",
                body=f"You owe money in group {group.name}. Click to see details.",
            )

    @transaction.atomic
    def group_external_transfer(
        self, user: TUser, group_uid: UUID, payload: ExternalTransferRequest
    ):
        to_user = self.auth_query.get_user_by_uid(uid=payload.user_uid)
        if not to_user:
            raise UserNotFound
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        confirm_token = self.query.create_transfer_confirm_token(
            amount=payload.amount, to_user=to_user, from_user=user, group=group
        )
        email = self.email_template.confirm_transfer(
            to_user=to_user,
            from_name=user.get_full_name(),
            amount=payload.amount,
            currency="VND",
            group_name=group.name,
            description="External transfer",
            confirm_token=confirm_token.uid,
        )
        self.email_client.send(messages=[email])
        return True

    @transaction.atomic
    def confirm_transfer_token(self, uid: str) -> bool:
        tranfer = self.query.token_transfer(uid=uid)
        if not tranfer:
            raise GetIsDenied

        if (
            tranfer.group.debt_optimization == DebtOptimizationEnum.EVENT
            and tranfer.event is None
        ):
            event_debts = self.event_query.get_event_restructure_debts_by_event(
                debtor=tranfer.from_user,
                creditor=tranfer.to_user,
                group=tranfer.group,
                currency="VND",
            )
            settlements = settle_event_debts_by_group_payment(
                event_debts, tranfer.amount
            )
            for debt, settled_amount in settlements:
                self.event_query.settle_event_restructure_debt(
                    debt=debt,
                    amount=settled_amount,
                    debtor=tranfer.from_user,
                    creditor=tranfer.to_user,
                    currency="VND",
                )
            self.query.update_balance_in_group(
                user=tranfer.from_user,
                group=tranfer.group,
                amount=-tranfer.amount,
                currency="VND",
            )
            self.query.update_balance_in_group(
                user=tranfer.to_user,
                group=tranfer.group,
                amount=tranfer.amount,
                currency="VND",
            )
            self.query.update_restructure_debt(
                debtor=tranfer.from_user,
                creditor=tranfer.to_user,
                group=tranfer.group,
                amount=tranfer.amount,
                currency="VND",
            )
        elif tranfer.group.debt_optimization == DebtOptimizationEnum.GROUP or (
            tranfer.group.debt_optimization == DebtOptimizationEnum.EVENT
            and tranfer.event is None
        ):
            self.query.update_balance_in_group(
                user=tranfer.from_user,
                group=tranfer.group,
                amount=-tranfer.amount,
                currency="VND",
            )
            self.query.update_balance_in_group(
                user=tranfer.to_user,
                group=tranfer.group,
                amount=tranfer.amount,
                currency="VND",
            )
            self.query.update_restructure_debt(
                debtor=tranfer.from_user,
                creditor=tranfer.to_user,
                group=tranfer.group,
                amount=tranfer.amount,
                currency="VND",
            )
        else:
            self.event_query.update_event_member_balance(
                debtor=tranfer.from_user,
                creditor=tranfer.to_user,
                event=tranfer.event,
                amount=tranfer.amount,
                currency="VND",
            )
            self.event_query.update_event_restructure_debt(
                debtor=tranfer.from_user,
                creditor=tranfer.to_user,
                event=tranfer.event,
                amount=tranfer.amount,
                currency="VND",
            )
            self.query.update_balance_in_group(
                user=tranfer.from_user,
                group=tranfer.group,
                amount=-tranfer.amount,
                currency="VND",
            )
            self.query.update_balance_in_group(
                user=tranfer.to_user,
                group=tranfer.group,
                amount=tranfer.amount,
                currency="VND",
            )

            self.query.update_restructure_debt(
                debtor=tranfer.from_user,
                creditor=tranfer.to_user,
                group=tranfer.group,
                amount=tranfer.amount,
                currency="VND",
            )

        self.transaction_orm.create_transaction(
            from_user=tranfer.from_user,
            to_user=tranfer.to_user,
            amount=tranfer.amount,
            description="External transfer",
            group=tranfer.group,
        )
        self.query.confirm_transfer_token(confirm_token=tranfer)
        return True
