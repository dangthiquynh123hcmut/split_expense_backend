from typing import List
from uuid import UUID

from django.db import transaction

from authenticate.queries import Query as UserQuery
from exceptions.group import GroupNotFound, LeaveIsDenied, UserNotInGroup
from exceptions.users import UserNotFound
from expense.queries import Query as ExpenseQuery
from utils.exceptions import DeleteIsDenied, GetIsDenied, UpdatedIsDenied
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
        self.expense_query = ExpenseQuery()

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

    @transaction.atomic
    def update_group(self, user: TUser, group_uid: UUID, data: GroupUpdateRequest):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise UpdatedIsDenied
        group = self.query.update_group(group=group, name=data.name)

        existing_members = self.query.get_members_by_uids(
            group=group, uids=data.list_add_uids
        )
        existing_uids = {m.user_id for m in existing_members}
        list_add_uids = data.list_add_uids or []
        add_member_uids = [u for u in list_add_uids if u not in existing_uids]
        add_members = self.user_query.get_user_by_uids(uids=add_member_uids)
        if len(list_add_uids) != len(add_member_uids) + len(existing_uids):
            raise UserNotFound
        group_members = [
            GroupMember(group=group, user=member) for member in add_members
        ]
        self.query.create_group_members(group_members=group_members)

        if data.list_delete_uids:
            deleted_members = self.query.get_members_by_uids(
                group=group, uids=data.list_delete_uids
            )
            if len(deleted_members) != len(data.list_delete_uids):
                raise UserNotInGroup
            for deleted_member in deleted_members:
                if deleted_member.total_amount != 0:
                    raise DeleteIsDenied
            self.query.delete_group_members(group_members=deleted_members)
        return group

    def leave_group(self, user: TUser, group_uid: UUID):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound

        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise UserNotInGroup
        if member.total_amount != 0:
            raise LeaveIsDenied
        return self.query.leave_group(user=user, group=group)

    def delete_group(self, user: TUser, group_uid: UUID):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        if group.leader != user:
            raise DeleteIsDenied
        self.query.delete_group(group=group)
        return True

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

    # def get_group_detail(self, group_uid: UUID):
    #     group = self.query.get_group_sync(group_uid=group_uid)
    #     if not group:
    #         raise GroupNotFound
    #     return self.query.get_group_detail(group_uid=group_uid)

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

    # def debt_simplification(self, user: TUser, group_uid: UUID):
    #     group = self.query.get_group_sync(group_uid=group_uid)
    #     if not group:
    #         raise GroupNotFound
    #     member = self.query.get_group_has_user(user=user, group=group)
    #     if not member:
    #         raise GetIsDenied
    #     list_user_uids = self.query.list_uids_members(group=group)
    #     list_expenses = self.query.get_expenses_in_group(group=group)
    #     list_debts = self.expense_query.get_debts(list_expenses=list_expenses)
    #     debt_members, balance_members = debt_simplification(list_user_uids, list_debts)
    #     return DebtSimplification(
    #         user=user,
    #         debt_members=debt_members,
    #         balance_members=balance_members,
    #     )

    def list_expenses_in_a_group(
        self,
        user: TUser,
        group_uid: UUID,
    ):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member:
            raise GetIsDenied
        return self.query.list_expenses_in_a_group(
            user=user,
            group=group,
        )

    def update_group_leader(self, user: TUser, group_uid: UUID, new_leader: UUID):
        group = self.query.get_group_sync(group_uid=group_uid)
        if not group:
            raise GroupNotFound
        member = self.query.get_group_has_user(user=user, group=group)
        if not member or group.leader != user:
            raise UpdatedIsDenied
        new_leader = self.user_query.get_user_by_uid(uid=new_leader)
        self.query.update_group_leader(group=group, new_leader=new_leader)

    def get_balances_by_group_and_member(self, user: TUser):
        return self.query.get_balances_by_group_and_member(user=user)
