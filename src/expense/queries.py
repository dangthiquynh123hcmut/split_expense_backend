from typing import List
from uuid import UUID

from django.db.models import Count, Sum

from authenticate.models import User
from event.models import Event
from expense.models import Expense, ExpenseAttachment, UserSharesInExpense
from expense.schemas.request import ExpenseRequest
from expense.schemas.response import ListExpenseResponse, NameExpense
from group.models import Group
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
                status=share.status_paid,
                created_at=share.expense.created_at,
                deleted=share.deleted,
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
        return Expense.objects.filter(uid=expense_uid).first()

    @staticmethod
    def update_expense(expense: Expense, payload: ExpenseRequest, updated_by: User):
        for field, value in payload.dict(
            exclude={"list_expense_member", "paid_by", "event_uid"}
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
    def soft_delete_expense_members(expense_uid: UUID):
        UserSharesInExpense.objects.filter(expense=expense_uid).update(
            deleted="DELETED"
        )
        return

    @staticmethod
    def hard_delete_expense(expense_uid: UUID):
        Expense.objects.filter(uid=expense_uid).delete()
        return

    @staticmethod
    def hard_delete_expense_members(expense_uid: UUID):
        UserSharesInExpense.objects.filter(expense=expense_uid).delete()
        return

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

    @staticmethod
    def total_expenses_in_group(group: Group):
        return Expense.objects.filter(event__group=group, status="ACTIVE").aggregate(
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
