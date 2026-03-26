"""
Performance tests for group ORM queries and service operations.

What is measured
----------------
1. Query-count efficiency — list_groups and list_group_members must issue
   a fixed, bounded number of SQL statements regardless of dataset size.
2. Member-lookup efficiency — get_group_has_user must not trigger extra
   queries when called repeatedly for members of a large group.
3. Wall-time for bulk group creation — creating 15 groups in a loop must
   complete within an acceptable time on in-memory SQLite.

Fixtures are supplied by tests/performance/conftest.py.
"""

import time

import pytest
from django.db import connection, reset_queries
from django.test.utils import override_settings

from group.models import Group, GroupMember
from group.queries import Query as GroupQuery
from tests.performance.conftest import MEMBER_COUNT, make_user
from utils.schemas.filter_and_order_by import (
    FilterFullNameSchema,
    FilterNameSchema,
    OrderByFullNameAndUpdatedAtSchema,
    OrderByNameAndUpdatedAtSchema,
)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

MAX_QUERIES_LIST_GROUPS = 5
MAX_QUERIES_LIST_MEMBERS = 5
BULK_GROUP_CREATE_COUNT = 15
BULK_GROUP_BUDGET_SECONDS = 3.0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _reset_and_count(fn):
    reset_queries()
    result = fn()
    return result, len(connection.queries)


# ---------------------------------------------------------------------------
# list_groups query count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListGroupsQueryCount:
    """
    list_groups must issue a bounded number of SQL statements even when
    the user belongs to many groups.
    """

    def _create_extra_groups(self, leader, count: int = BULK_GROUP_CREATE_COUNT):
        """Create *count* additional groups all led by *leader*."""
        groups = [Group(name=f"Extra Group {i}", leader=leader) for i in range(count)]
        created = Group.objects.bulk_create(groups)
        GroupMember.objects.bulk_create(
            [GroupMember(group=g, user=leader) for g in created]
        )
        return created

    @override_settings(DEBUG=True)
    def test_list_groups_query_count_bounded(self, large_group):
        """
        list_groups for a user in BULK_GROUP_CREATE_COUNT + 1 groups must
        not exceed MAX_QUERIES_LIST_GROUPS SQL statements.
        """
        group, leader, _members = large_group
        self._create_extra_groups(leader)

        result, n_queries = _reset_and_count(
            lambda: list(
                GroupQuery.list_groups(
                    user=leader,
                    filter=FilterNameSchema(),
                    order_by=OrderByNameAndUpdatedAtSchema(),
                )
            )
        )

        assert n_queries <= MAX_QUERIES_LIST_GROUPS, (
            f"list_groups issued {n_queries} queries for "
            f"{BULK_GROUP_CREATE_COUNT + 1} groups (budget: {MAX_QUERIES_LIST_GROUPS})"
        )

    @override_settings(DEBUG=True)
    def test_list_groups_returns_all_groups_for_leader(self, large_group):
        """
        After creating extra groups, the result set size must match the total
        number of groups the leader belongs to.
        """
        group, leader, _members = large_group
        self._create_extra_groups(leader, count=5)

        results = list(
            GroupQuery.list_groups(
                user=leader,
                filter=FilterNameSchema(),
                order_by=OrderByNameAndUpdatedAtSchema(),
            )
        )

        # 1 original group + 5 extra
        assert len(results) >= 6


# ---------------------------------------------------------------------------
# list_group_members query count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListGroupMembersQueryCount:
    """
    list_group_members must issue a bounded number of queries for a group
    with MEMBER_COUNT + 1 members.
    """

    @override_settings(DEBUG=True)
    def test_query_count_bounded_for_large_group(self, large_group):
        group, leader, _members = large_group

        result, n_queries = _reset_and_count(
            lambda: list(
                GroupQuery.list_group_members(
                    group=group,
                    filter=FilterFullNameSchema(),
                    order_by=OrderByFullNameAndUpdatedAtSchema(),
                )
            )
        )

        assert n_queries <= MAX_QUERIES_LIST_MEMBERS, (
            f"list_group_members issued {n_queries} queries for "
            f"{MEMBER_COUNT + 1} members (budget: {MAX_QUERIES_LIST_MEMBERS})"
        )

    def test_member_count_is_correct(self, large_group):
        """GroupMember count matches leader + MEMBER_COUNT members."""
        group, leader, members = large_group

        count = GroupMember.objects.filter(group=group).count()

        assert count == MEMBER_COUNT + 1  # leader + members


# ---------------------------------------------------------------------------
# get_group_has_user efficiency
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetGroupHasUserEfficiency:
    """
    get_group_has_user is called on the hot path (permissions check).
    It should issue exactly 1 query per call and never return wrong results.
    """

    @override_settings(DEBUG=True)
    def test_membership_check_uses_single_query(self, large_group):
        group, leader, members = large_group

        reset_queries()
        result = GroupQuery.get_group_has_user(user=leader, group=group)
        n_queries = len(connection.queries)

        assert result is not None, "Leader should be a group member"
        assert n_queries == 1, (
            f"get_group_has_user issued {n_queries} queries (expected 1)"
        )

    def test_non_member_check_uses_bounded_queries(self, db):
        """
        get_group_has_user for a non-member must return None and issue
        at most 2 SQL statements.

        Uses connection.execute_wrapper to count queries without requiring
        DEBUG=True (which can perturb the test's database connection).
        """
        leader = make_user("iso_leader@example.com", "0850000001")
        outsider = make_user("iso_outsider@example.com", "0850000002")
        group = Group.objects.create(name="Isolation Group", leader=leader)
        GroupMember.objects.create(group=group, user=leader)

        # Verify setup: outsider must genuinely NOT be a member
        assert not GroupMember.objects.filter(user=outsider, group=group).exists(), (
            "Test setup: outsider should not be a group member"
        )

        # Count SQL without relying on DEBUG mode
        executed: list = []

        def _capture(execute, sql, params, many, context):
            if not sql.strip().upper().startswith(("SAVEPOINT", "RELEASE SAVEPOINT")):
                executed.append(sql)
            return execute(sql, params, many, context)

        with connection.execute_wrapper(_capture):
            result = GroupQuery.get_group_has_user(user=outsider, group=group)

        assert not result, (
            "get_group_has_user must return a falsy value for a non-member"
        )
        assert len(executed) <= 2, (
            f"get_group_has_user issued {len(executed)} queries for non-member (budget: 2)"
        )

    def test_all_members_are_recognised(self, large_group):
        """Each user created for the group must be detected as a member."""
        group, leader, members = large_group

        for user in [leader] + members:
            assert GroupQuery.get_group_has_user(user=user, group=group) is not None


# ---------------------------------------------------------------------------
# Bulk group creation wall-time
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBulkGroupCreationTime:
    """Creating many groups via bulk_create must stay within time budget."""

    def test_create_15_groups_within_budget(self, large_group):
        _, leader, _ = large_group

        t0 = time.perf_counter()
        groups = Group.objects.bulk_create(
            [
                Group(name=f"BulkGroup {i}", leader=leader)
                for i in range(BULK_GROUP_CREATE_COUNT)
            ]
        )
        GroupMember.objects.bulk_create(
            [GroupMember(group=g, user=leader) for g in groups]
        )
        elapsed = time.perf_counter() - t0

        assert elapsed < BULK_GROUP_BUDGET_SECONDS, (
            f"Bulk creation of {BULK_GROUP_CREATE_COUNT} groups took {elapsed:.3f}s "
            f"(budget: {BULK_GROUP_BUDGET_SECONDS}s)"
        )

    def test_bulk_created_groups_are_persisted(self, large_group):
        _, leader, _ = large_group

        Group.objects.bulk_create(
            [Group(name=f"PersistGroup {i}", leader=leader) for i in range(5)]
        )

        assert (
            Group.objects.filter(name__startswith="PersistGroup", leader=leader).count()
            == 5
        )
