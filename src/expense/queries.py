from datetime import timedelta
from typing import List, Literal, Optional
from uuid import UUID

from django.db.models import Count, Sum
from django.utils.timezone import now

from authenticate.models import User
from event.models import Event
from expense.models import Expense, ExpenseAttachment, UserSharesInExpense
from expense.schemas.request import UpdateExpenseRequest
from expense.schemas.response import NameExpense
from group.models import Group
from utils.schemas.filter_and_order_by import (
    FilterDateSchema,
    FilterEventSchema,
    FilterExpenseAdminSchema,
)
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
    def list_expenses_in_event(
        user: User, event: Event, status: Literal["DELETED", "ACTIVE"] = "ACTIVE"
    ):
        expenses = list(
            Expense.objects.filter(event=event, status=status)
            .select_related("event")
            .order_by("-created_at")
        )

        user_shares = UserSharesInExpense.objects.filter(
            expense__event=event,
            user=user,
            deleted=status,
        ).select_related("expense")

        user_share_map = {share.expense_id: share for share in user_shares}
        result = []

        for expense in expenses:
            share = user_share_map.get(expense.uid)
            if share:
                amount_value = (
                    share.receiver_amount
                    if (share.receiver_amount or 0) > 0
                    else share.amount
                )
                amount = float(amount_value or 0)
            else:
                amount = 0.0
            result.append(
                NameExpense(
                    uid=expense.uid,
                    name=expense.name,
                    currency=expense.currency,
                    amount=amount,
                    created_at=expense.created_at,
                    status=expense.status,
                    event=expense.event.name,
                    category=expense.category,
                )
            )
        return result

    @staticmethod
    def get_expense(expense_uid: UUID, status: Optional[str] = None):
        if status is None:
            return Expense.objects.filter(uid=expense_uid).first()
        return Expense.objects.filter(uid=expense_uid, status=status).first()

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

    @staticmethod
    def chart_expenses(
        user: TUser,
        year: int,
        group: Optional[Group] = None,
        event: Optional[Event] = None,
    ):
        queryset = UserSharesInExpense.objects.filter(user=user, created_at__year=year)

        if group:
            queryset = queryset.filter(expense__event__group=group)
        elif event:
            queryset = queryset.filter(expense__event=event, deleted="ACTIVE")

        return (
            queryset.values("created_at__month")
            .annotate(total_amount=Sum("amount"))
            .order_by("created_at__month")
        )

    @staticmethod
    def list_expenses_by_user(
        user: TUser,
        status: str,
        filter: FilterDateSchema,
        filter_name: FilterEventSchema,
    ):
        if filter_name.group is not None:
            queryset = UserSharesInExpense.objects.filter(
                user=user, deleted=status, expense__event__group__name=filter_name.group
            )
        else:
            queryset = UserSharesInExpense.objects.filter(user=user, deleted=status)
        if filter_name.name is not None:
            queryset = queryset.filter(filter_name.get_filter_expression())
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())
        return queryset

    @staticmethod
    def transaction_chart(user: TUser, year: int):
        return (
            UserSharesInExpense.objects.filter(
                user=user, created_at__year=year, deleted="ACTIVE"
            )
            .values("created_at__month")
            .annotate(total_amount=Sum("amount"))
            .order_by("created_at__month")
        )

    @staticmethod
    def expense_categories():
        return (
            Expense.objects.filter(status="ACTIVE")
            .values("category")
            .annotate(total_amount=Sum("total_amount"))
        )

    @staticmethod
    def get_expenses_in_event(event_uid: UUID):
        return Expense.objects.filter(event__uid=event_uid, status="ACTIVE")

    @staticmethod
    def count_expenses():
        yesterday = now().date() - timedelta(days=1)
        return Expense.objects.filter().count(), Expense.objects.filter(
            created_at__date__lte=yesterday
        ).count()

    @staticmethod
    def count_active_expenses():
        yesterday = now().date() - timedelta(days=1)
        return Expense.objects.filter(status="ACTIVE").count(), Expense.objects.filter(
            status="ACTIVE", created_at__date__lte=yesterday
        ).count()

    @staticmethod
    def count_expense_amount():
        yesterday = now().date() - timedelta(days=1)
        return Expense.objects.aggregate(total_amount=Sum("total_amount"))[
            "total_amount"
        ], Expense.objects.filter(created_at__date__lte=yesterday).aggregate(
            total_amount=Sum("total_amount")
        )["total_amount"]

    @staticmethod
    def total_expenses_members():
        return UserSharesInExpense.objects.count(), UserSharesInExpense.objects.filter(
            created_at__date__lte=now().date() - timedelta(days=1)
        ).count()

    @staticmethod
    def count_expired_expenses():
        yesterday = now().date() - timedelta(days=1)
        return Expense.objects.filter(
            end_date__lte=now().date()
        ).count(), Expense.objects.filter(
            end_date__lte=yesterday, created_at__date__lte=yesterday
        ).count()

    @staticmethod
    def count_expense_members():
        return UserSharesInExpense.objects.count(), UserSharesInExpense.objects.filter(
            created_at__date__lte=now().date() - timedelta(days=1)
        ).count()

    @staticmethod
    def get_all_expenses(filter: FilterExpenseAdminSchema):
        return Expense.objects.filter(filter.get_filter_expression())

    @staticmethod
    def deactivate_expense(expense_uid: UUID):
        Expense.objects.filter(uid=expense_uid).update(status="DELETED")
        return

    @staticmethod
    def active_expense(expense_uid: UUID):
        Expense.objects.filter(uid=expense_uid).update(status="ACTIVE")
        return

    @staticmethod
    def get_expense_by_uid(expense_uid: UUID):
        return Expense.objects.filter(uid=expense_uid).first()

    @staticmethod
    def get_user_shares_in_expense(expense: Expense):
        return UserSharesInExpense.objects.filter(expense=expense)

    @staticmethod
    def get_expense_attachments(expense: Expense):
        return ExpenseAttachment.objects.filter(expense=expense)
