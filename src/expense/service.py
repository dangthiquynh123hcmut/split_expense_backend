from decimal import Decimal
from typing import Optional
from uuid import UUID

from django.db import transaction

from attachment.schemas.responses import AttachmentResponse
from authenticate.queries import Query as UserQuery
from event.models import Event
from event.queries import Query as EventQuery
from exceptions.event import EventNotFound
from exceptions.expense import ExpenseNotFound, ListMemberNotMatch
from exceptions.users import UserNotFound
from expense.models import Expense, UserSharesInExpense
from expense.queries import Query
from expense.schemas.request import ExpenseRequest, UpdateExpenseRequest
from expense.schemas.response import ListExpenseUser, UserExpense
from group.models import GroupMemberBalance, RestructureDebt
from group.queries import Query as GroupQuery
from message.orm.notification_queries import NotificationORM
from utils.enums import NotificationTypeEnum
from utils.exceptions import GetIsDenied
from utils.functions.debt_simplification import simplify_minflow
from utils.schemas.filter_and_order_by import (
    FilterAmountSchema,
    FilterDateSchema,
    FilterEventSchema,
)
from utils.services.fcm_service import FCMService
from utils.types import TUser
from wallet.orm.transaction import TransactionORM


class Service:
    def __init__(self):
        self.query = Query()
        self.group_query = GroupQuery()
        self.event_query = EventQuery()
        self.user_query = UserQuery()
        self.transaction_orm = TransactionORM()
        self.fcm_service = FCMService()
        self.notification_orm = NotificationORM()

    @transaction.atomic
    def create_expense(self, creator: TUser, payload: ExpenseRequest, event: Event):
        paid_by = self.user_query.get_user_by_uid(uid=payload.paid_by)
        if not paid_by:
            raise UserNotFound
        list_uids = [m.user_uid for m in payload.list_expense_member]
        users = self.user_query.get_user_by_uids(uids=list_uids)
        if len(users) != len(payload.list_expense_member):
            raise UserNotFound
        event_members = self.event_query.total_event_members(event=event)
        if event_members != len(payload.list_expense_member):
            raise ListMemberNotMatch
        expense = self.query.create_expense(
            creator=creator,
            event=event,
            paid_by=paid_by,
            **payload.dict(
                exclude={
                    "list_expense_member",
                    "event_uid",
                    "paid_by",
                }
            ),
        )
        user_map = {u.uid: u for u in users}
        expense_members = [
            UserSharesInExpense(
                expense=expense,
                user=user_map.get(m.user_uid),
                amount=(Decimal(m.amount)),
                receiver_amount=(
                    Decimal(payload.total_amount) - Decimal(m.amount)
                    if m.user_uid == paid_by.uid
                    else Decimal("0.0")
                ),
            )
            for m in payload.list_expense_member
        ]
        self.query.create_expense_members(expense_members=expense_members)
        user_exits = self.group_query.get_users_in_group_member_balance(
            group=expense.event.group, currency=payload.currency
        )
        if len(user_exits) < len(expense_members):
            new_user_uids = list(
                set([m.user.uid for m in expense_members]) - set(user_exits)
            )
            new_user_balance = [
                GroupMemberBalance(
                    group=expense.event.group,
                    user=m.user,
                    currency=payload.currency,
                    balance=-m.amount
                    if m.user != paid_by
                    else (m.receiver_amount or Decimal("0.0")),
                )
                for m in expense_members
                if m.user.uid in new_user_uids
            ]
            self.group_query.create_group_member_balance(
                group_member_balance=new_user_balance
            )

        if len(user_exits) > 0:
            user_update = [m for m in expense_members if m.user.uid in user_exits]

            for m in user_update:
                if m.user != paid_by:
                    m.amount = -m.amount
                else:
                    m.amount = m.receiver_amount or Decimal("0.0")

            self.group_query.update_total_amount(
                group=expense.event.group,
                expense_members=user_update,
                currency=payload.currency,
            )

        self.notification_orm.create_notification(
            from_user=creator,
            content=f"{creator.full_name} have created an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_CREATED,
            related_uid=expense.uid,
            to_users=[member.user for member in expense_members],
        )
        self.fcm_service.send_multicast_notification(
            tokens=[m.user.fcm_token for m in expense_members],
            title="New Expense",
            body=f"{creator.full_name} have created an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_CREATED,
            related_uid=expense.uid,
        )
        return expense

    @transaction.atomic
    def calculate_debt(self, expense: Expense, old_currency: Optional[str] = None):
        balances = self.group_query.list_member_balances(
            group=expense.event.group, currency=expense.currency
        )
        balances = list(balances)
        transactions = simplify_minflow(balances)
        user_map = {
            group_member.user.uid: group_member.user
            for group_member in self.group_query.list_group_members_not_filter(
                group=expense.event.group
            )
        }
        restructure_debt = [
            RestructureDebt(
                group=expense.event.group,
                debtor=user_map.get(transactions[i][0]),
                creditor=user_map.get(transactions[i][1]),
                value=transactions[i][2],
                currency=expense.currency,
            )
            for i in range(len(transactions))
        ]
        if old_currency:
            delete_currency = old_currency
        else:
            delete_currency = expense.currency
        self.group_query.delete_restructure_debt(
            group=expense.event.group, currency=delete_currency
        )
        self.group_query.create_restructure_debt(restructure_debt=restructure_debt)
        return

    def list_expenses_in_event(self, user: TUser, event_uid: UUID, status: str):
        event = self.event_query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        is_member_event = self.event_query.get_event_has_user(user=user, event=event)
        if not is_member_event:
            raise GetIsDenied
        return self.query.list_expenses_in_event(user=user, event=event, status=status)

    def get_expense_detail(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        if not UserSharesInExpense.objects.filter(expense=expense, user=user).exists():
            raise GetIsDenied
        raw_members = list(
            UserSharesInExpense.objects.filter(expense=expense)
            .select_related("user__avatar_url")
            .values_list(
                "user__uid",
                "user__full_name",
                "user__avatar_url__uid",
                "user__avatar_url__original_name",
                "user__avatar_url__public_url",
                "amount",
            )
        )
        expense_members = [
            UserExpense(
                uid=m[0],
                full_name=m[1],
                avatar_url=AttachmentResponse(
                    uid=m[2], original_name=m[3], public_url=m[4]
                )
                if m[2]
                else None,
                amount=-m[5],
            )
            for m in raw_members
        ]

        expense.list_user = expense_members
        return expense

    @transaction.atomic
    def update_expense(
        self, user: TUser, expense_uid: UUID, payload: UpdateExpenseRequest
    ):
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        paid_by = self.user_query.get_user_by_uid(uid=payload.paid_by)
        if not paid_by:
            raise UserNotFound
        list_uids = [m.user_uid for m in payload.list_expense_member]
        users = self.user_query.get_user_by_uids(uids=list_uids)
        if len(users) != len(payload.list_expense_member):
            raise UserNotFound
        list_user_share_in_expense = self.query.list_user_share_in_expense(
            expense=expense
        )
        old_currency = expense.currency
        if len(list_user_share_in_expense) != len(payload.list_expense_member):
            raise ListMemberNotMatch
        self.query.update_expense(expense=expense, payload=payload, updated_by=user)
        user_share_in_expense_map = {m.user.uid: m for m in list_user_share_in_expense}
        self.query.hard_delete_expense_members(expense=expense)
        user_map = {u.uid: u for u in users}
        expense_members = [
            UserSharesInExpense(
                expense=expense,
                user=user_map.get(m.user_uid),
                amount=(Decimal(m.amount)),
                receiver_amount=(
                    Decimal(payload.total_amount) - Decimal(m.amount)
                    if m.user_uid == paid_by.uid
                    else Decimal("0.0")
                ),
            )
            for m in payload.list_expense_member
        ]
        if not user_map.get(paid_by.uid):
            expense_members.append(
                UserSharesInExpense(
                    expense=expense,
                    user=paid_by,
                    amount=Decimal("0.0"),
                    receiver_amount=payload.total_amount,
                )
            )
        self.query.create_expense_members(expense_members=expense_members)
        if old_currency != payload.currency:
            self.group_query.update_currency_in_group_member_balance(
                group=expense.event.group,
                old_currency=old_currency,
                new_currency=payload.currency,
            )

        user_exits = self.group_query.get_users_in_group_member_balance(
            group=expense.event.group, currency=payload.currency
        )
        if len(user_exits) < len(expense_members):
            new_user_uids = list(
                set([m.user.uid for m in expense_members]) - set(user_exits)
            )
            new_user_balance = [
                GroupMemberBalance(
                    group=expense.event.group,
                    user=m.user,
                    currency=payload.currency,
                    balance=m.amount,
                )
                for m in expense_members
                if m.user.uid in new_user_uids
            ]
            self.group_query.create_group_member_balance(
                group_member_balance=new_user_balance
            )

        if len(user_exits) > 0:
            user_update = [m for m in expense_members if m.user.uid in user_exits]

            for m in user_update:
                if m.user != paid_by:
                    m.amount = -m.amount
                else:
                    m.amount = m.receiver_amount or Decimal("0.0")
            for member in user_update:
                old = user_share_in_expense_map.get(member.user.uid)
                if old:
                    if old.user == member.user and old.user != expense.paid_by:
                        member.amount += old.amount
                    else:
                        member.amount -= old.receiver_amount or Decimal("0.0")
            self.group_query.update_total_amount(
                group=expense.event.group,
                expense_members=user_update,
                currency=payload.currency,
            )

        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have updated an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_UPDATED,
            related_uid=expense.uid,
            to_users=[member.user for member in expense_members],
        )
        self.fcm_service.send_multicast_notification(
            tokens=[m.user.fcm_token for m in expense_members],
            title="New Expense",
            body=f"{user.full_name} have updated an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_UPDATED,
            related_uid=expense.uid,
        )
        return expense

    @transaction.atomic
    def soft_delete_expense(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        expense_members = self.query.list_user_share_in_expense(expense=expense)
        for member in expense_members:
            if member.user == expense.paid_by:
                member.amount = -member.receiver_amount
        self.group_query.update_total_amount(
            group=expense.event.group,
            expense_members=expense_members,
            currency=expense.currency,
        )
        self.query.soft_delete_expense_members(expense=expense)
        self.query.soft_delete_expense(expense_uid=expense_uid)
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have deleted an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_SOFT_DELETED,
            related_uid=expense.uid,
            to_users=[member.user for member in expense_members],
        )
        return expense

    def hard_delete_expense(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense_deleted(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        self.query.hard_delete_expense_members(expense=expense)
        self.query.hard_delete_expense(expense_uid=expense_uid)
        expense_members = self.query.list_user_share_in_expense(expense=expense)
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have deleted an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_HARD_DELETED,
            related_uid=expense.uid,
            to_users=[member.user for member in expense_members],
        )
        return True

    def restore_expense(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense_deleted(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        self.query.restore_expense(expense_uid=expense_uid)
        self.query.restore_user_shares_in_expense(expense=expense)
        expense_members = self.query.list_user_share_in_expense(expense=expense)
        for member in expense_members:
            if member.user == expense.paid_by:
                member.amount = member.receiver_amount
            else:
                member.amount = -member.amount
        self.group_query.update_total_amount(
            group=expense.event.group,
            expense_members=expense_members,
            currency=expense.currency,
        )
        self.notification_orm.create_notification(
            from_user=user,
            content=f"{user.full_name} have restored an expense {expense.name}",
            type=NotificationTypeEnum.EXPENSE_RESTORED,
            related_uid=expense.uid,
            to_users=[member.user for member in expense_members],
        )
        return expense

    def list_expenses_by_user(
        self,
        user: TUser,
        status: str,
        filter: FilterDateSchema,
        filter_amount: FilterAmountSchema,
        filter_name: FilterEventSchema,
    ):
        query_set = self.query.list_expenses_by_user(
            user=user, status=status, filter=filter, filter_name=filter_name
        )
        expenses: list[ListExpenseUser] = [
            ListExpenseUser(
                uid=share.expense.uid,
                name=share.expense.name,
                currency=share.expense.currency,
                amount=-float(share.amount or 0)
                if share.expense.paid_by != share.user
                else float(share.receiver_amount or 0),
                created_at=share.expense.created_at,
                status=share.deleted,
                category=share.expense.category,
                event=share.expense.event.name,
            )
            for share in query_set
        ]
        if filter_amount.max_amount is not None:
            expenses = [e for e in expenses if e.amount <= filter_amount.max_amount]

        if filter_amount.min_amount is not None:
            expenses = [e for e in expenses if e.amount >= filter_amount.min_amount]
        if filter_name.group is not None:
            expenses = [e for e in expenses if e.event.group == filter_name.group]  # type: ignore
        if filter_name.event is not None:
            expenses = [e for e in expenses if e.event == filter_name.event]
        if filter_name.category is not None:
            expenses = [e for e in expenses if e.category == filter_name.category]

        return expenses

    def transaction_chart(self, user: TUser, year: int):
        return self.query.transaction_chart(user=user, year=year)
