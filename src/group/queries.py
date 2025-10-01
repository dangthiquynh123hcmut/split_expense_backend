from collections import defaultdict
from typing import List
from uuid import UUID

from channels.db import database_sync_to_async
from django.db.models import Case, F, When

from attachment.models import Attachment
from authenticate.models import User
from event.models import Event
from expense.models import Expense, UserSharesInExpense
from expense.schemas.response import ExpenseEvent, NameExpense
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.types import TUser

from .models import Group, GroupMember, RestructureDebt


class Query:
    @staticmethod
    def create_group(leader: User, name: str):
        return Group.objects.create(leader=leader, name=name)

    @staticmethod
    def create_group_members(group_members: List[GroupMember]):
        GroupMember.objects.bulk_create(group_members)
        return

    @staticmethod
    def list_groups(
        user: TUser, filter: FilterNameSchema, order_by: OrderByNameAndUpdatedAtSchema
    ):
        queryset = Group.objects.filter(
            group_member_fk_group__user__uid=user.uid, status="ACTIVE"
        ).distinct()
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())

        if order_by:
            queryset = queryset.order_by(order_by.get_order_by_expression())

        return queryset

    @staticmethod
    @database_sync_to_async
    def get_group(group_uid: UUID):
        return Group.objects.filter(uid=group_uid, status="ACTIVE").first()

    @staticmethod
    def get_group_sync(group_uid: UUID):
        try:
            return Group.objects.get(uid=group_uid, status="ACTIVE")
        except Group.DoesNotExist:
            return None

    @staticmethod
    def get_group_has_user(user: TUser, group: Group):
        try:
            return GroupMember.objects.get(user=user, group=group)
        except GroupMember.DoesNotExist:
            return None

    @staticmethod
    def update_group(group: Group, name: str):
        if group:
            group.name = name
            group.save()
        return group

    @staticmethod
    def leave_group(user: TUser, group: Group):
        return GroupMember.objects.filter(user=user, group=group).delete()

    @staticmethod
    def delete_group(group: Group):
        return Group.objects.filter(uid=group.uid).delete()

    @staticmethod
    def get_members_by_uids(group: Group, uids: List[UUID]):
        return GroupMember.objects.filter(
            user_id__in=uids, status="ACTIVE", group=group
        )

    @staticmethod
    def list_uids_members(group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE").values_list(
            "user__uid", flat=True
        )

    @staticmethod
    def list_group_members(
        group: Group,
        filter: FilterFullNameSchema,
        order_by: OrderByFullNameAndUpdatedAtSchema,
    ):
        query = GroupMember.objects.filter(group=group, status="ACTIVE")
        if filter and filter.search:
            query = query.filter(filter.filter_search(filter.search))

        if order_by:
            query = query.annotate(full_name=F("user__full_name")).order_by(
                order_by.get_order_by_expression()
            )
        return query

    @staticmethod
    def list_group_members_not_filter(group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE")

    # @staticmethod
    # def get_group_detail(group_uid: UUID):
    #     return Group.objects.filter(uid=group_uid, status="ACTIVE").first()

    @staticmethod
    def list_events_in_a_group(
        group: Group,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        queryset = Event.objects.filter(group=group, status="ACTIVE").distinct()
        if filter:
            queryset = queryset.filter(filter.get_filter_expression())

        if order_by:
            queryset = queryset.order_by(order_by.get_order_by_expression())

        return queryset

    @staticmethod
    def add_attachment(group: Group, attachment: Attachment):
        group.avatar_url = attachment
        group.save()
        return group

    @staticmethod
    def get_expenses_in_group(group: Group):
        return Expense.objects.filter(event__group=group, status="ACTIVE").distinct()

    @staticmethod
    def update_total_amount(group: Group, expense_members: List[UserSharesInExpense]):
        whens = []
        users = []

        for em in expense_members:
            users.append(em.user)
            whens.append(When(user=em.user, then=F("total_amount") + em.amount))
        return GroupMember.objects.filter(group=group, user__in=users).update(
            total_amount=Case(*whens, default=F("total_amount"))
        )

    @staticmethod
    def list_expenses_in_a_group(
        user: User,
        group: Group,
    ):
        expense_members = (
            UserSharesInExpense.objects.filter(
                expense__event__group=group, expense__status="ACTIVE", user=user
            )
            .select_related("expense", "expense__event")
            .order_by("expense__event__name", "expense__created_at")
        )
        grouped: dict[str, list[NameExpense]] = defaultdict(list)

        for share in expense_members:
            grouped[share.expense.event.name].append(
                NameExpense(
                    uid=share.expense.uid,
                    name=share.expense.name,
                    currency=share.expense.currency,
                    amount=float(share.amount),
                    status=share.status_paid,
                    created_at=share.expense.created_at,
                )
            )
        result: list[ExpenseEvent] = [
            ExpenseEvent(event=event_name, expense=expenses)
            for event_name, expenses in grouped.items()
        ]
        return result

    @staticmethod
    def list_member_balances(group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE").values_list(
            "user__uid", "total_amount"
        )

    @staticmethod
    def delete_restructure_debt(group: Group):
        return RestructureDebt.objects.filter(group=group).delete()

    @staticmethod
    def create_restructure_debt(restructure_debt: List[RestructureDebt]):
        RestructureDebt.objects.bulk_create(restructure_debt)

    @staticmethod
    def delete_group_members(group_members: List[GroupMember]):
        return GroupMember.objects.filter(
            uid__in=[gm.uid for gm in group_members]
        ).delete()

    @staticmethod
    def update_group_leader(group: Group, new_leader: TUser):
        group.leader = new_leader
        group.save()
        return

    @staticmethod
    def list_members_for_balance(group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE").order_by(
            "user__full_name"
        )

    @staticmethod
    def get_groups_by_member(user: TUser):
        return Group.objects.filter(
            group_member_fk_group__user__uid=user.uid, status="ACTIVE"
        ).distinct()
