from uuid import UUID

from django.db import transaction

from attachment.schemas.responses import AttachmentResponse
from authenticate.queries import Query as UserQuery
from event.queries import Query as EventQuery
from exceptions.event import EventNotFound
from exceptions.expense import ExpenseNotFound
from exceptions.users import UserNotFound
from expense.models import UserSharesInExpense
from expense.queries import Query
from expense.schemas.request import ExpenseRequest, ExpenseUpdateRequest
from expense.schemas.response import UserExpense
from group.queries import Query as GroupQuery
from utils.exceptions import GetIsDenied
from utils.types import TUser


class Service:
    def __init__(self):
        self.query = Query()
        self.group_query = GroupQuery()
        self.event_query = EventQuery()
        self.user_query = UserQuery()

    @transaction.atomic
    def create_expense(self, creator: TUser, payload: ExpenseRequest):
        event = self.event_query.get_event(event_uid=payload.event_uid)
        if not event:
            raise EventNotFound
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
                amount=m.amount,
            )
            for m in payload.list_expense_member
        ]
        self.query.create_expense_members(expense_members=expense_members)
        self.group_query.update_total_amount(
            group=event.group, expense_members=expense_members
        )
        return expense

    def list_expenses(self, user: TUser, event_uid: UUID):
        event = self.event_query.get_event(event_uid=event_uid)
        if not event:
            raise EventNotFound
        is_member_event = self.event_query.get_event_has_user(user=user, event=event)
        if not is_member_event:
            raise GetIsDenied
        return self.query.list_expenses(user=user, event=event)

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
                amount=float(m[5]),
            )
            for m in raw_members
        ]

        expense.list_user = expense_members
        return expense

    def update_expense(
        self, user: TUser, expense_uid: UUID, payload: ExpenseUpdateRequest
    ):
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        return self.query.update_expense(expense_uid=expense_uid, payload=payload)

    def delete_expense(self, user: TUser, expense_uid: UUID):
        expense = self.query.get_expense(expense_uid=expense_uid)
        if not expense:
            raise ExpenseNotFound
        return self.query.delete_expense(expense_uid=expense_uid)
