"""
Integration tests for group.services.Service.

Tests verify the core creation, membership management, update and deletion
flows.  FCM and notification side-effects are mocked.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from exceptions.group import GroupNotFound, LeaveIsDenied, UserNotInGroup
from exceptions.users import UserNotFound
from group.models import Group, GroupMember, GroupMemberBalance
from group.services import Service
from tests.integration.conftest import make_user
from utils.exceptions import DeleteIsDenied


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service():
    return Service()


# Decorator / context manager used by most tests in this module
MOCK_EXTERNALS = (
    patch("utils.services.firebase_cm.fcm_service.FCMService.send_notification"),
    patch(
        "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
    ),
    patch("message.orm.notification_queries.NotificationORM.create_notification"),
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateGroup:
    def test_create_group_persists_in_db(
        self, user_a, user_b, user_c, mock_fcm, mock_notification
    ):
        service = _make_service()
        group = service.create_group(
            leader=user_a,
            name="Weekend Trip",
            list_user_uids=[user_b.uid, user_c.uid],
        )
        assert Group.objects.filter(uid=group.uid).exists()
        assert group.name == "Weekend Trip"
        assert group.leader == user_a

    def test_create_group_adds_all_members_including_leader(
        self, user_a, user_b, user_c, mock_fcm, mock_notification
    ):
        service = _make_service()
        group = service.create_group(
            leader=user_a,
            name="Trip",
            list_user_uids=[user_b.uid, user_c.uid],
        )
        member_uids = set(
            GroupMember.objects.filter(group=group).values_list("user_id", flat=True)
        )
        assert {user_a.uid, user_b.uid, user_c.uid} == member_uids

    def test_create_group_with_nonexistent_user_raises(
        self, user_a, mock_fcm, mock_notification
    ):
        import uuid

        service = _make_service()
        with pytest.raises(UserNotFound):
            service.create_group(
                leader=user_a,
                name="Ghost Group",
                list_user_uids=[uuid.uuid4()],
            )

    def test_create_group_with_empty_member_list_only_has_leader(
        self, user_a, mock_fcm, mock_notification
    ):
        service = _make_service()
        group = service.create_group(leader=user_a, name="Solo", list_user_uids=[])
        count = GroupMember.objects.filter(group=group).count()
        assert count == 1


@pytest.mark.django_db
class TestLeaveGroup:
    def test_leave_group_removes_member(
        self, group_with_members, user_b, mock_fcm, mock_notification
    ):
        group, _ = group_with_members
        service = _make_service()
        service.leave_group(user=user_b, group_uid=group.uid)
        assert not GroupMember.objects.filter(group=group, user=user_b).exists()

    def test_leave_group_nonexistent_group_raises(self, user_a):
        import uuid

        service = _make_service()
        with pytest.raises(GroupNotFound):
            service.leave_group(user=user_a, group_uid=uuid.uuid4())

    def test_leave_group_when_not_member_raises(
        self, group_with_members, mock_fcm, mock_notification
    ):
        group, _ = group_with_members
        outsider = make_user("outsider@example.com", phone_number="0999000001")
        service = _make_service()
        with pytest.raises(UserNotInGroup):
            service.leave_group(user=outsider, group_uid=group.uid)

    def test_leave_group_with_nonzero_balance_raises(
        self, group_with_members, user_b, mock_fcm, mock_notification
    ):
        group, _ = group_with_members
        # Give user_b a non-zero balance in the group
        GroupMemberBalance.objects.create(
            group=group, user=user_b, currency="VND", balance=Decimal("50.00")
        )
        service = _make_service()
        with pytest.raises(LeaveIsDenied):
            service.leave_group(user=user_b, group_uid=group.uid)


@pytest.mark.django_db
class TestDeleteGroup:
    def test_leader_can_delete_group(
        self, group_with_members, user_a, mock_fcm, mock_notification
    ):
        group, _ = group_with_members
        service = _make_service()
        result = service.delete_group(user=user_a, group_uid=group.uid)
        assert result is True
        assert not Group.objects.filter(uid=group.uid).exists()

    def test_non_leader_cannot_delete_group(
        self, group_with_members, user_b, mock_fcm, mock_notification
    ):
        group, _ = group_with_members
        service = _make_service()
        with pytest.raises(DeleteIsDenied):
            service.delete_group(user=user_b, group_uid=group.uid)

    def test_delete_nonexistent_group_raises(self, user_a):
        import uuid

        service = _make_service()
        with pytest.raises(GroupNotFound):
            service.delete_group(user=user_a, group_uid=uuid.uuid4())


@pytest.mark.django_db
class TestListGroupMembers:
    def test_returns_all_members(
        self, group_with_members, user_a, mock_fcm, mock_notification
    ):
        group, users = group_with_members
        service = _make_service()
        from utils.schemas.filter_and_order_by import (
            FilterFullNameSchema,
            OrderByFullNameAndUpdatedAtSchema,
        )

        members = service.list_group_members(
            user=user_a,
            group_uid=group.uid,
            filter=FilterFullNameSchema(),
            order_by=OrderByFullNameAndUpdatedAtSchema(),
        )
        assert len(list(members)) == 3

    def test_non_member_cannot_list_members(
        self, group_with_members, mock_fcm, mock_notification
    ):
        group, _ = group_with_members
        outsider = make_user("outsider2@example.com", phone_number="0999000002")
        service = _make_service()
        from utils.exceptions import GetIsDenied
        from utils.schemas.filter_and_order_by import (
            FilterFullNameSchema,
            OrderByFullNameAndUpdatedAtSchema,
        )

        with pytest.raises(GetIsDenied):
            service.list_group_members(
                user=outsider,
                group_uid=group.uid,
                filter=FilterFullNameSchema(),
                order_by=OrderByFullNameAndUpdatedAtSchema(),
            )
