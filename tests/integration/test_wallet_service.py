"""
Integration tests for wallet.service.transactions.TransactionService.

Covers PIN verification, transfer-token generation, and wallet-to-wallet
transactions including balance enforcement.
Cache is backend by LocMemCache (configured in test_settings.py).
"""

from unittest.mock import patch

import pytest
from django.core.cache import cache

from exceptions.users import BalanceNotEnough
from exceptions.wallet import InvalidTokenOrAmountIncorrect, PinIncorrect, PinNotSet
from group.models import Group, GroupMember
from tests.integration.conftest import make_user
from utils.functions.transfer_token import generate_transfer_token
from wallet.schemas.request import TransferRequest, VerifyPinRequest
from wallet.service.transactions import TransactionService


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def _make_service():
    return TransactionService()


# ---------------------------------------------------------------------------
# verify_pin
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVerifyPin:
    def _user_with_pin(self, email, pin="123456"):
        user = make_user(email, phone_number="0901010101")
        user.set_pin(pin)
        user.currency = "VND"
        user.save(update_fields=["pin", "currency"])
        return user

    def test_correct_pin_returns_token_string(self, db):
        user = self._user_with_pin("pintest@example.com")
        service = _make_service()
        token = service.verify_pin(
            user=user, payload=VerifyPinRequest(pin="123456", amount=500.0)
        )
        assert isinstance(token, str) and len(token) > 0

    def test_wrong_pin_raises_pin_incorrect(self, db):
        user = self._user_with_pin("pintest2@example.com")
        service = _make_service()
        with pytest.raises(PinIncorrect):
            service.verify_pin(
                user=user, payload=VerifyPinRequest(pin="000000", amount=500.0)
            )

    def test_no_pin_set_raises_pin_not_set(self, db):
        user = make_user("nopintest@example.com", phone_number="0901010102")
        # user.pin is None by default
        service = _make_service()
        with pytest.raises(PinNotSet):
            service.verify_pin(
                user=user, payload=VerifyPinRequest(pin="123456", amount=500.0)
            )


# ---------------------------------------------------------------------------
# create_transaction
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateTransaction:
    def _setup_users(self, db, sender_balance=1000.0):
        sender = make_user(
            "sender@example.com", phone_number="0901020304", balance=sender_balance
        )
        receiver = make_user("receiver@example.com", phone_number="0905060708")
        # A shared group is required so the service can resolve the `group`
        # variable before creating the transaction record.
        group = Group.objects.create(name="Wallet Test Group", leader=sender)
        GroupMember.objects.bulk_create(
            [
                GroupMember(group=group, user=sender),
                GroupMember(group=group, user=receiver),
            ]
        )
        return sender, receiver, group

    def _make_payload(self, to_user, amount, token, currency="VND", group_uid=None):
        return TransferRequest(
            user_uid=to_user.uid,
            transfer_token=token,
            original_amount=amount,
            convert_amount=amount,
            currency=currency,
            description="Test transfer",
            group_uid=group_uid,
        )

    @patch("utils.services.firebase_cm.fcm_service.FCMService.send_notification")
    def test_successful_transaction_deducts_sender_balance(self, _mock_fcm, db):
        sender, receiver, group = self._setup_users(db, sender_balance=1000.0)
        transfer_amount = 200.0
        token = generate_transfer_token(user_uid=sender.uid, amount=transfer_amount)
        service = _make_service()
        service.create_transaction(
            user=sender,
            payload=self._make_payload(
                receiver, transfer_amount, token, group_uid=group.uid
            ),
        )
        sender.refresh_from_db()
        assert sender.balance == pytest.approx(800.0)

    @patch("utils.services.firebase_cm.fcm_service.FCMService.send_notification")
    def test_successful_transaction_adds_to_receiver_balance(self, _mock_fcm, db):
        sender, receiver, group = self._setup_users(db, sender_balance=1000.0)
        transfer_amount = 300.0
        token = generate_transfer_token(user_uid=sender.uid, amount=transfer_amount)
        service = _make_service()
        service.create_transaction(
            user=sender,
            payload=self._make_payload(
                receiver, transfer_amount, token, group_uid=group.uid
            ),
        )
        receiver.refresh_from_db()
        assert receiver.balance == pytest.approx(300.0)

    @patch("utils.services.firebase_cm.fcm_service.FCMService.send_notification")
    def test_insufficient_balance_raises(self, _mock_fcm, db):
        sender, receiver, _group = self._setup_users(db, sender_balance=50.0)
        transfer_amount = 500.0  # more than balance
        token = generate_transfer_token(user_uid=sender.uid, amount=transfer_amount)
        service = _make_service()
        with pytest.raises(BalanceNotEnough):
            service.create_transaction(
                user=sender,
                payload=self._make_payload(receiver, transfer_amount, token),
            )

    @patch("utils.services.firebase_cm.fcm_service.FCMService.send_notification")
    def test_invalid_transfer_token_raises(self, _mock_fcm, db):
        sender, receiver, _group = self._setup_users(db, sender_balance=1000.0)
        service = _make_service()
        with pytest.raises(InvalidTokenOrAmountIncorrect):
            service.create_transaction(
                user=sender,
                payload=self._make_payload(receiver, 100.0, "fake-token-xyz"),
            )

    @patch("utils.services.firebase_cm.fcm_service.FCMService.send_notification")
    def test_amount_mismatch_in_token_raises(self, _mock_fcm, db):
        sender, receiver, _group = self._setup_users(db, sender_balance=1000.0)
        # Generate token for 100 but send 200
        token = generate_transfer_token(user_uid=sender.uid, amount=100.0)
        service = _make_service()
        with pytest.raises(InvalidTokenOrAmountIncorrect):
            service.create_transaction(
                user=sender,
                payload=self._make_payload(receiver, 200.0, token),
            )

    @patch("utils.services.firebase_cm.fcm_service.FCMService.send_notification")
    def test_transaction_is_atomic_on_balance_error(self, _mock_fcm, db):
        """When balance is insufficient the combined DB change must be rolled back."""
        sender, receiver, _group = self._setup_users(db, sender_balance=10.0)
        transfer_amount = 500.0
        token = generate_transfer_token(user_uid=sender.uid, amount=transfer_amount)
        service = _make_service()
        with pytest.raises(BalanceNotEnough):
            service.create_transaction(
                user=sender,
                payload=self._make_payload(receiver, transfer_amount, token),
            )
        # Balances must remain unchanged
        sender.refresh_from_db()
        receiver.refresh_from_db()
        assert sender.balance == pytest.approx(10.0)
        assert receiver.balance == pytest.approx(0.0)
