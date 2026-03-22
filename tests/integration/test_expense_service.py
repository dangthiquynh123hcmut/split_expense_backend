"""
Integration tests for expense.service.Service.

Tests cover the full lifecycle of an expense: creation, soft-delete, hard-delete
and restoration.  FCM and notification side-effects are always mocked.

Fixture dependency chain:
  event_with_members ─► group_with_members ─► user_a, user_b, user_c
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from exceptions.expense import ExpenseNotFound, ListMemberNotMatch
from exceptions.users import UserNotFound
from expense.models import Expense, UserSharesInExpense
from expense.schemas.request import AmountExpenseMember, ExpenseRequest
from expense.service import Service
from tests.integration.conftest import make_user
from utils.enums import SplitTypeEnum


def _make_service():
    return Service()


def _now():
    return datetime.now(tz=timezone.utc)


def _expense_payload(event, paid_by, members):
    """
    Build an ExpenseRequest where:
      - paid_by covers the full amount (100)
      - each member (including paid_by) bears an equal share
    """
    per_person = Decimal("100.00") / len(members)
    return ExpenseRequest(
        name="Dinner",
        total_amount=Decimal("100.00"),
        currency="VND",
        split_type=SplitTypeEnum.EQUAL,
        event_uid=event.uid,
        paid_by=paid_by.uid,
        expense_date=_now(),
        list_expense_member=[
            AmountExpenseMember(user_uid=m.uid, amount=per_person) for m in members
        ],
    )


MOCK_SIDE_EFFECTS = (
    patch(
        "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
    ),
    patch("message.orm.notification_queries.NotificationORM.create_notification"),
)


@pytest.mark.django_db
class TestCreateExpense:
    def _create(self, event_with_members):
        event, group, users = event_with_members
        payload = _expense_payload(event, paid_by=users[0], members=users)
        service = _make_service()
        with (
            patch(
                "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
            ),
            patch(
                "message.orm.notification_queries.NotificationORM.create_notification"
            ),
        ):
            expense = service.create_expense(
                creator=users[0], payload=payload, event=event
            )
        return expense, users

    def test_expense_is_saved_in_db(self, event_with_members):
        expense, _ = self._create(event_with_members)
        assert Expense.objects.filter(uid=expense.uid).exists()

    def test_expense_has_correct_name(self, event_with_members):
        expense, _ = self._create(event_with_members)
        assert expense.name == "Dinner"

    def test_expense_creates_user_share_rows(self, event_with_members):
        expense, users = self._create(event_with_members)
        shares = UserSharesInExpense.objects.filter(expense=expense)
        assert shares.count() == len(users)

    def test_paid_by_receiver_amount_is_set(self, event_with_members):
        event, group, users = event_with_members
        paid_by = users[0]
        payload = _expense_payload(event, paid_by=paid_by, members=users)
        service = _make_service()
        with (
            patch(
                "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
            ),
            patch(
                "message.orm.notification_queries.NotificationORM.create_notification"
            ),
        ):
            expense = service.create_expense(
                creator=paid_by, payload=payload, event=event
            )
        share = UserSharesInExpense.objects.get(expense=expense, user=paid_by)
        # receiver_amount = total - own share
        assert share.receiver_amount > 0

    def test_member_count_mismatch_raises(self, event_with_members):
        event, group, users = event_with_members
        # Provide only 2 members for an event that has 3
        partial_payload = ExpenseRequest(
            name="Partial",
            total_amount=Decimal("60.00"),
            currency="VND",
            split_type=SplitTypeEnum.EQUAL,
            event_uid=event.uid,
            paid_by=users[0].uid,
            expense_date=_now(),
            list_expense_member=[
                AmountExpenseMember(user_uid=users[0].uid, amount=Decimal("30")),
                AmountExpenseMember(user_uid=users[1].uid, amount=Decimal("30")),
            ],
        )
        service = _make_service()
        with (
            patch(
                "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
            ),
            patch(
                "message.orm.notification_queries.NotificationORM.create_notification"
            ),
        ):
            with pytest.raises(ListMemberNotMatch):
                service.create_expense(
                    creator=users[0], payload=partial_payload, event=event
                )

    def test_nonexistent_paid_by_raises(self, event_with_members):
        import uuid

        event, group, users = event_with_members
        payload = ExpenseRequest(
            name="Ghost",
            total_amount=Decimal("90.00"),
            currency="VND",
            split_type=SplitTypeEnum.EQUAL,
            event_uid=event.uid,
            paid_by=uuid.uuid4(),  # does not exist
            expense_date=_now(),
            list_expense_member=[
                AmountExpenseMember(user_uid=u.uid, amount=Decimal("30")) for u in users
            ],
        )
        service = _make_service()
        with pytest.raises(UserNotFound):
            service.create_expense(creator=users[0], payload=payload, event=event)


@pytest.mark.django_db
class TestSoftDeleteExpense:
    def _setup_expense(self, event_with_members):
        event, group, users = event_with_members
        payload = _expense_payload(event, paid_by=users[0], members=users)
        service = _make_service()
        with (
            patch(
                "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
            ),
            patch(
                "message.orm.notification_queries.NotificationORM.create_notification"
            ),
        ):
            expense = service.create_expense(
                creator=users[0], payload=payload, event=event
            )
        return expense, users, service

    def test_soft_delete_marks_expense_as_deleted(self, event_with_members):
        expense, users, service = self._setup_expense(event_with_members)
        with patch(
            "message.orm.notification_queries.NotificationORM.create_notification"
        ):
            service.soft_delete_expense(user=users[0], expense_uid=expense.uid)
        expense.refresh_from_db()
        assert expense.status == "DELETED"

    def test_soft_delete_nonexistent_expense_raises(self, db):
        import uuid

        user = make_user("del@example.com", phone_number="0901010203")
        service = _make_service()
        with pytest.raises(ExpenseNotFound):
            service.soft_delete_expense(user=user, expense_uid=uuid.uuid4())


@pytest.mark.django_db
class TestRestoreExpense:
    def _setup_deleted_expense(self, event_with_members):
        event, group, users = event_with_members
        payload = _expense_payload(event, paid_by=users[0], members=users)
        service = _make_service()
        with (
            patch(
                "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
            ),
            patch(
                "message.orm.notification_queries.NotificationORM.create_notification"
            ),
        ):
            expense = service.create_expense(
                creator=users[0], payload=payload, event=event
            )
        with patch(
            "message.orm.notification_queries.NotificationORM.create_notification"
        ):
            service.soft_delete_expense(user=users[0], expense_uid=expense.uid)
        return expense, users, service

    def test_restore_sets_status_to_active(self, event_with_members):
        expense, users, service = self._setup_deleted_expense(event_with_members)
        with patch(
            "message.orm.notification_queries.NotificationORM.create_notification"
        ):
            service.restore_expense(user=users[0], expense_uid=expense.uid)
        expense.refresh_from_db()
        assert expense.status == "ACTIVE"

    def test_restore_nonexistent_expense_raises(self, db):
        import uuid

        user = make_user("restore@example.com", phone_number="0901010204")
        service = _make_service()
        with pytest.raises(ExpenseNotFound):
            service.restore_expense(user=user, expense_uid=uuid.uuid4())


@pytest.mark.django_db
class TestHardDeleteExpense:
    def _setup_deleted_expense(self, event_with_members):
        event, group, users = event_with_members
        payload = _expense_payload(event, paid_by=users[0], members=users)
        service = _make_service()
        with (
            patch(
                "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
            ),
            patch(
                "message.orm.notification_queries.NotificationORM.create_notification"
            ),
        ):
            expense = service.create_expense(
                creator=users[0], payload=payload, event=event
            )
        with patch(
            "message.orm.notification_queries.NotificationORM.create_notification"
        ):
            service.soft_delete_expense(user=users[0], expense_uid=expense.uid)
        return expense, users, service

    def test_hard_delete_removes_expense_from_db(self, event_with_members):
        expense, users, service = self._setup_deleted_expense(event_with_members)
        with patch(
            "message.orm.notification_queries.NotificationORM.create_notification"
        ):
            service.hard_delete_expense(user=users[0], expense_uid=expense.uid)
        assert not Expense.objects.filter(uid=expense.uid).exists()

    def test_hard_delete_on_active_expense_raises(self, event_with_members):
        """hard_delete requires status=DELETED; an ACTIVE expense raises ExpenseNotFound."""
        event, group, users = event_with_members
        payload = _expense_payload(event, paid_by=users[0], members=users)
        service = _make_service()
        with (
            patch(
                "utils.services.firebase_cm.fcm_service.FCMService.send_multicast_notification"
            ),
            patch(
                "message.orm.notification_queries.NotificationORM.create_notification"
            ),
        ):
            expense = service.create_expense(
                creator=users[0], payload=payload, event=event
            )
        # Attempt hard-delete without soft-deleting first
        with patch(
            "message.orm.notification_queries.NotificationORM.create_notification"
        ):
            with pytest.raises(ExpenseNotFound):
                service.hard_delete_expense(user=users[0], expense_uid=expense.uid)
