from typing import List
from uuid import UUID

from django.db import transaction

from authenticate.queries import Query as UserQuery
from exceptions.group import GroupNotFound
from exceptions.users import UserNotFound
from utils.exceptions import GetIsDenied, UpdatedIsDenied
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)
from utils.types import TUser

from .models import GroupMember
from .queries import Query
from .schemas.request import GroupUpdateRequest


class Service:
    def __init__(self):
        self.query = Query()
        self.user_query = UserQuery()

    @transaction.atomic
    def create_group(self, leader: TUser, name: str, list_user_uids: List[UUID]):
        group = self.query.create_group(leader=leader, name=name)
        members = self.user_query.get_user_by_uids(uids=list_user_uids)
        if len(members) != len(list_user_uids):
            raise UserNotFound
        group_members = [GroupMember(group=group, user=member) for member in members]
        group_members.append(GroupMember(group=group, user=leader))
        self.query.create_group_members(group_members=group_members)
        return group

    def list_groups(
        self,
        user: TUser,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        return self.query.list_groups(user=user, filter=filter, order_by=order_by)

    def get_group(self, group_uid: UUID):
        return self.query.get_group_sync(group_uid=group_uid)

    def update_group(self, user: TUser, group_uid: UUID, data: GroupUpdateRequest):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise UpdatedIsDenied
        group = self.query.update_group(group=group, name=data.name)
        members = self.user_query.get_user_by_uids(uids=data.list_user_uids)
        if len(members) != len(data.list_user_uids):
            raise UserNotFound
        group_members = [GroupMember(group=group, user=member) for member in members]
        group_members.append(GroupMember(group=group, user=group.leader))
        self.query.create_group_members(group_members=group_members)
        return group

    # def leave_group(self, user: TUser, group_uid: UUID):
    #     group = self.query.get_group_sync(group_uid=group_uid)
    #     if not group:
    #         raise GroupNotFound
    #     return self.query.leave_group(user=user, group=group)

    # def delete_group(self, user: TUser, group_uid: UUID):
    #     group = self.query.get_group_sync(group_uid=group_uid)
    #     if not group:
    #         raise GroupNotFound
    #     return self.query.delete_group(user=user, group=group)

    def list_group_members(
        self,
        user: TUser,
        group_uid: UUID,
        filter: FilterFullNameSchema,
        order_by: OrderByFullNameAndUpdatedAtSchema,
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        return self.query.list_group_members(
            group=group, filter=filter, order_by=order_by
        )

    # def get_group(self, group_uid: UUID):
    #     group = self.query.get_group_sync(group_uid=group_uid)
    #     if not group:
    #         raise GroupNotFound
    #     return self.query.get_group(group_uid=group_uid)

    def list_events_in_a_group(
        self,
        user: TUser,
        group_uid: UUID,
        filter: FilterNameSchema,
        order_by: OrderByNameAndUpdatedAtSchema,
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        return self.query.list_events_in_a_group(
            group=group, filter=filter, order_by=order_by
        )
