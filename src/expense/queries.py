from typing import List
from uuid import UUID

from django.db.models import Count, Sum

from authenticate.models import User
from event.models import Event
from expense.models import Expense, ExpenseAttachment, UserSharesInExpense
from expense.schemas.request import UpdateExpenseRequest
from expense.schemas.response import NameExpense
from group.models import Group
from utils.types import TUser


class Query:
    @staticmethod
    def create_expense(creator: TUser, event: Event, paid_by: User, **kwargs):
        return Expense.objects.create(
            creator=creator, event=event, paid_by=paid_by, **kwargs
        )

    @staticmethod
    def create_expense_members(expense_members: List[UserSharesInExpense]):
        UserSharesInExpense.objects.bulk_create(expense_members)
        return

    @staticmethod
    def list_expenses_in_event(user: TUser, event: Event):
        queryset = (
            UserSharesInExpense.objects.filter(
                expense__event=event,
                user=user,
            )
            .select_related("expense")
            .order_by("expense__created_at")
        )
        expenses: list[NameExpense] = [
            NameExpense(
                uid=share.expense.uid,
                name=share.expense.name,
                currency=share.expense.currency,
                amount=float(share.amount),
                created_at=share.expense.created_at,
                deleted=share.deleted,
            )
            for share in queryset
        ]
        return expenses

    @staticmethod
    def get_expense(expense_uid: UUID):
        return Expense.objects.filter(uid=expense_uid, status="ACTIVE").first()

    @staticmethod
    def get_expense_deleted(expense_uid: UUID):
        return Expense.objects.filter(uid=expense_uid, status="DELETED").first()

    @staticmethod
    def update_expense(
        expense: Expense, payload: UpdateExpenseRequest, updated_by: User
    ):
        for field, value in payload.dict(
            exclude={"list_expense_member", "paid_by"}
        ).items():
            setattr(expense, field, value)
        expense.updated_by = updated_by
        expense.save()
        return expense

    @staticmethod
    def list_user_share_in_expense(expense: Expense):
        return UserSharesInExpense.objects.filter(expense=expense)

    @staticmethod
    def soft_delete_expense(expense_uid: UUID):
        Expense.objects.filter(uid=expense_uid).update(status="DELETED")
        return

    @staticmethod
    def soft_delete_expense_members(expense: Expense):
        UserSharesInExpense.objects.filter(expense=expense).update(deleted="DELETED")
        return

    @staticmethod
    def hard_delete_expense(expense_uid: UUID):
        Expense.objects.filter(uid=expense_uid).delete()
        return

    @staticmethod
    def hard_delete_expense_members(expense: Expense):
        UserSharesInExpense.objects.filter(expense=expense).delete()
        return

    @staticmethod
    def add_attachment(expense_attachments: List[ExpenseAttachment]):
        return ExpenseAttachment.objects.bulk_create(expense_attachments)

    @staticmethod
    def total_expenses_in_group(group: Group, currency: str = "VND"):
        return Expense.objects.filter(
            event__group=group, status="ACTIVE", currency=currency
        ).aggregate(
            total_amount=Sum("total_amount"),
            expense_total=Count("uid", distinct=True),
        )

    @staticmethod
    def total_expenses_in_event(event: Event, currency: str = "VND"):
        return Expense.objects.filter(
            event=event, status="ACTIVE", currency=currency
        ).aggregate(
            total_amount=Sum("total_amount"),
            expense_total=Count("uid", distinct=True),
        )

    @staticmethod
    def expense_attended_in_group(user: TUser, group: Group):
        return UserSharesInExpense.objects.filter(
            expense__event__group=group, user=user, deleted="ACTIVE"
        ).aggregate(
            user_spent=Sum("amount"),
            expense_attended=Count("uid", distinct=True),
        )

    @staticmethod
    def restore_expense(expense_uid: UUID):
        Expense.objects.filter(uid=expense_uid).update(status="ACTIVE")
        return

    @staticmethod
    def restore_user_shares_in_expense(expense: Expense):
        UserSharesInExpense.objects.filter(expense=expense).update(deleted="ACTIVE")
        return

    @staticmethod
    def total_mutual_expenses(user: TUser, friend: TUser):
        return UserSharesInExpense.objects.filter(
            user=user,
            expense__user_shares_in_expense_fk_expense__user=friend,
            expense__user_shares_in_expense_fk_expense__deleted="ACTIVE",
            deleted="ACTIVE",
        ).count()
