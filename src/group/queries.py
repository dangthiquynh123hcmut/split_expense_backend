from typing import List
from uuid import UUID

from channels.db import database_sync_to_async
from django.db.models import F

from attachment.models import Attachment
from authenticate.models import User
from event.models import Event
from expense.models import Expense
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.types import TUser

from .models import Group, GroupMember


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
        return GroupMember.objects.filter(user=user, group=group).update(
            status="DELETED"
        )

    @staticmethod
    def delete_group(group: Group):
        return Group.objects.filter(uid=group.uid).update(status="DELETED")

    @staticmethod
    def list_members(group: Group):
        return GroupMember.objects.filter(group=group, status="ACTIVE")

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
    def get_group_detail(group_uid: UUID):
        return Group.objects.filter(uid=group_uid, status="ACTIVE").first()

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
