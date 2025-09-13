from typing import List
from uuid import UUID

from django.db.models import F

from attachment.models import Attachment
from authenticate.models import User
from event.models import Event
from expense.models import Expense, ExpenseAttachment, UserSharesInExpense
from expense.schemas.request import ExpenseUpdateRequest
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
    def list_expenses(user: TUser, event: Event):
        queryset = (
            UserSharesInExpense.objects.filter(
                expense__event=event,
                user=user,
            )
            .select_related("expense")
            .annotate(
                expense_name=F("expense__name"),
                expense_currency=F("expense__currency"),
            )
            .order_by("expense__created_at")
        )

        return queryset

    @staticmethod
    def get_expense(expense_uid: UUID):
        return Expense.objects.filter(uid=expense_uid, status="ACTIVE").first()

    @staticmethod
    def update_expense(expense_uid: UUID, payload: ExpenseUpdateRequest):
        return Expense.objects.filter(uid=expense_uid, status="ACTIVE").update(
            **payload.dict()
        )

    @staticmethod
    def delete_expense(expense_uid: UUID):
        return Expense.objects.filter(uid=expense_uid).update(status="DELETED")

    @staticmethod
    def add_attachment(expense: Expense, attachment: Attachment):
        return ExpenseAttachment.objects.create(expense=expense, attachment=attachment)
