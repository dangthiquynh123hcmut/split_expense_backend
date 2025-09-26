from typing import List
from uuid import UUID

from authenticate.models import User
from event.models import Event
from expense.models import Expense, ExpenseAttachment, UserSharesInExpense
from expense.schemas.request import ExpenseUpdateRequest
from expense.schemas.response import ListExpenseResponse, NameExpense
from group.schemas.response import GroupName
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
                status=share.status,
                created_at=share.expense.created_at,
            )
            for share in queryset
        ]
        return ListExpenseResponse(
            event=event.name,
            expense=expenses,
            group=GroupName.from_orm(event.group),
        )

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
    def add_attachment(expense_attachments: List[ExpenseAttachment]):
        return ExpenseAttachment.objects.bulk_create(expense_attachments)

    # @staticmethod
    # def get_debts(list_expenses: List[Expense]):
    #     list_debts = []
    #     for expense in list_expenses:
    #         list_debtor = UserSharesInExpense.objects.filter(
    #             expense=expense
    #         ).values_list("user__uid", "amount")
    #         list_debtor = [
    #             (
    #                 user,
    #                 expense.paid_by.uid,
    #                 amount,
    #             )
    #             for user, amount in list_debtor
    #         ]
    #         list_debts.extend(list_debtor)
    #     return list_debts
