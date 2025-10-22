from decimal import Decimal
from uuid import UUID

from django.db import transaction

from attachment.schemas.responses import AttachmentResponse
from authenticate.queries import Query as UserQuery
from event.models import Event
from event.queries import Query as EventQuery
from exceptions.event import EventNotFound
from exceptions.expense import ExpenseNotFound
from exceptions.users import UserNotFound
from expense.models import Expense, UserSharesInExpense
from expense.queries import Query
from expense.schemas.request import ExpenseRequest, UpdateExpenseRequest
from expense.schemas.response import UserExpense
from group.models import GroupMemberBalance, RestructureDebt
from group.queries import Query as GroupQuery
from utils.exceptions import GetIsDenied
from utils.functions.debt_simplification import simplify_minflow
from utils.types import TUser


class Service:
    def __init__(self):
        self.query = Query()
        self.group_query = GroupQuery()
        self.event_query = EventQuery()
        self.user_query = UserQuery()

    @transaction.atomic
    def create_expense(self, creator: TUser, payload: ExpenseRequest, event: Event):
        paid_by = self.user_query.get_user_by_uid(uid=payload.paid_by)
        if not paid_by:
            raise UserNotFound
        list_uids = [m.user_uid for m in payload.list_expense_member]
        users = self.user_query.get_user_by_uids(uids=list_uids)
        if len(users) != len(payload.list_expense_member):
            raise UserNotFound
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
                amount=(
                    -Decimal(m.amount)
                    if m.user_uid != paid_by.uid
                    else Decimal(payload.total_amount) - Decimal(m.amount)
                ),
                payer_amount=(
                    -Decimal(m.amount) if m.user_uid == paid_by.uid else Decimal("0.0")
                ),
            )
            for m in payload.list_expense_member
        ]
        if not user_map.get(paid_by.uid):
            expense_members.append(
                UserSharesInExpense(
                    expense=expense,
                    user=paid_by,
                    amount=payload.total_amount,
                    payer_amount=Decimal("0.0"),
                )
            )
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
                    balance=m.amount,
                )
                for m in expense_members
                if m.user.uid in new_user_uids
            ]
            self.group_query.create_group_member_balance(
                group_member_balance=new_user_balance
            )

        self.group_query.update_total_amount(
            group=expense.event.group, expense_members=expense_members
        )
        return expense

    def calculate_debt(self, expense: Expense):
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
        self.group_query.delete_restructure_debt(
            group=expense.event.group, currency=expense.currency
        )
        self.group_query.create_restructure_debt(restructure_debt=restructure_debt)
        return

    def list_expenses_in_event(self, user: TUser, event_uid: UUID):
        event = self.event_query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        is_member_event = self.event_query.get_event_has_user(user=user, event=event)
        if not is_member_event:
            raise GetIsDenied
        return self.query.list_expenses_in_event(user=user, event=event)

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
                "payer_amount",
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
                amount=m[5] if expense.paid_by.uid != m[0] else (m[6] or Decimal(0)),
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
        self.query.update_expense(expense=expense, payload=payload, updated_by=user)
        list_user_share_in_expense = self.query.list_user_share_in_expense(
            expense=expense
        )
        user_share_in_expense_map = {m.user.uid: m for m in list_user_share_in_expense}
        self.query.hard_delete_expense_members(expense=expense)
        user_map = {u.uid: u for u in users}
        expense_members = [
            UserSharesInExpense(
                expense=expense,
                user=user_map.get(m.user_uid),
                amount=(
                    -Decimal(m.amount)
                    if m.user_uid != paid_by.uid
                    else Decimal(payload.total_amount) - Decimal(m.amount)
                ),
                payer_amount=(
                    Decimal(m.amount) if m.user_uid == paid_by.uid else Decimal("0.0")
                ),
            )
            for m in payload.list_expense_member
        ]
        if not user_map.get(paid_by.uid):
            expense_members.append(
                UserSharesInExpense(
                    expense=expense,
                    user=paid_by,
                    amount=payload.total_amount,
                    payer_amount=Decimal("0.0"),
                )
            )
        self.query.create_expense_members(expense_members=expense_members)

        for member in expense_members:
            old = user_share_in_expense_map.get(member.user.uid)
            if old:
                member.amount -= old.amount
        self.group_query.update_total_amount(
            group=expense.event.group, expense_members=expense_members
        )
        return expense

    def soft_delete_expense(self, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        expense_members = self.query.list_user_share_in_expense(expense=expense)
        for member in expense_members:
            member.amount = -member.amount
        self.group_query.update_total_amount(
            group=expense.event.group, expense_members=expense_members
        )
        self.query.soft_delete_expense_members(expense=expense)
        self.query.soft_delete_expense(expense_uid=expense_uid)
        return expense.event

    def hard_delete_expense(self, expense_uid: UUID):
        self.query.hard_delete_expense_members(expense_uid=expense_uid)
        self.query.hard_delete_expense(expense_uid=expense_uid)
        return True

    def restore_expense(self, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        self.query.restore_expense(expense_uid=expense_uid)
        self.query.restore_user_shares_in_expense(expense=expense)
        expense_members = self.query.list_user_share_in_expense(expense=expense)
        self.group_query.update_total_amount(
            group=expense.event.group, expense_members=expense_members
        )
        return expense
