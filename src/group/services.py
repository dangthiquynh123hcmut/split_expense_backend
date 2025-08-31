from uuid import UUID

from django.db import transaction

from exceptions.group import GroupNotFound
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.types import TUser

from .queries import Query
from .schemas.request import GroupRequest, GroupUpdateRequest


class Service:
    def __init__(self):
        self.query = Query()

    @transaction.atomic
    def create_group(self, leader: TUser, data: GroupRequest):
        group = self.query.create_group(
            leader=leader, name=data.name, avatar_url=data.avatar_url
        )
        self.query.create_group_members(group=group, members=data.list_user_uid)
        return group

    def list_groups(
        self,
        user: TUser,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        return self.query.list_groups(user=user, filter=filter, order_by=order_by)

    def get_group(self, group_uid: UUID):
        return self.query.get_group(group_uid=group_uid)

    def update_group(self, group_uid: UUID, data: GroupUpdateRequest):
        group = self.query.get_group(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        return self.query.update_group(group=group, data=data)

    def leave_group(self, user: TUser, group_uid: UUID):
        group = self.query.get_group(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        return self.query.leave_group(user=user, group=group)

    def delete_group(self, user: TUser, group_uid: UUID):
        group = self.query.get_group(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        return self.query.delete_group(user=user, group=group)

    def list_group_members(
        self,
        group_uid: UUID,
        filter: FilterFullNameSchema,
        order_by: OrderByFullNameAndUpdatedAtSchema,
    ):
        group = self.query.get_group(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        return self.query.list_group_members(
            group=group, filter=filter, order_by=order_by
        )

    def get_detail_group(self, group_uid: UUID):
        group = self.query.get_group(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        return self.query.get_detail_group(group_uid=group_uid)

    def list_events_in_a_group(
        self,
        group_uid: UUID,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        return self.query.list_events_in_a_group(
            group_uid=group_uid, filter=filter, order_by=order_by
        )
