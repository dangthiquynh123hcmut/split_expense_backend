"""
Unit tests for utils.functions.transfer_token.

Uses Django's LocMemCache (configured in test_settings.py) — no Redis needed.
These tests do NOT touch the database.
"""

import uuid

import pytest

from utils.functions.transfer_token import (
    generate_transfer_token,
    verify_transfer_token,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure each test starts with a clean cache."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


# class TestGenerateTransferToken:
#     def test_returns_string(self):
#         token = generate_transfer_token(user_uid=uuid.uuid4(), amount=100.0)
#         assert isinstance(token, str)
#         assert len(token) > 0

#     def test_returns_unique_tokens_each_call(self):
#         uid = uuid.uuid4()
#         token1 = generate_transfer_token(user_uid=uid, amount=100.0)
#         token2 = generate_transfer_token(user_uid=uid, amount=100.0)
#         assert token1 != token2

#     def test_token_stored_in_cache(self):
#         from django.core.cache import cache

#         uid = uuid.uuid4()
#         token = generate_transfer_token(user_uid=uid, amount=50.0)
#         key = f"transfer_token:{uid}:{token}"
#         data = cache.get(key)
#         assert data is not None
#         assert data["amount"] == 50.0
#         assert data["user_uid"] == str(uid)


class TestVerifyTransferToken:
    def test_valid_token_returns_true(self):
        uid = uuid.uuid4()
        token = generate_transfer_token(user_uid=uid, amount=200.0)
        assert verify_transfer_token(user_uid=uid, token=token, amount=200.0) is True

    def test_nonexistent_token_returns_false(self):
        uid = uuid.uuid4()
        assert (
            verify_transfer_token(user_uid=uid, token="fake-token", amount=100.0)
            is False
        )

    def test_wrong_amount_returns_false(self):
        uid = uuid.uuid4()
        token = generate_transfer_token(user_uid=uid, amount=100.0)
        assert verify_transfer_token(user_uid=uid, token=token, amount=999.0) is False

    def test_wrong_user_uid_returns_false(self):
        uid = uuid.uuid4()
        other_uid = uuid.uuid4()
        token = generate_transfer_token(user_uid=uid, amount=100.0)
        assert (
            verify_transfer_token(user_uid=other_uid, token=token, amount=100.0)
            is False
        )

    def test_token_is_consumed_after_successful_verification(self):
        """Verify that a token can only be used once (deleted from cache after use)."""
        uid = uuid.uuid4()
        token = generate_transfer_token(user_uid=uid, amount=150.0)
        # First verification succeeds
        assert verify_transfer_token(user_uid=uid, token=token, amount=150.0) is True
        # Second verification fails because token was deleted
        assert verify_transfer_token(user_uid=uid, token=token, amount=150.0) is False

    def test_token_not_consumed_on_failed_verification(self):
        """A failed verify (wrong amount) should NOT consume the token."""
        uid = uuid.uuid4()
        token = generate_transfer_token(user_uid=uid, amount=100.0)
        # Wrong amount — token is NOT deleted
        assert verify_transfer_token(user_uid=uid, token=token, amount=50.0) is False
        # Correct amount — should still succeed
        assert verify_transfer_token(user_uid=uid, token=token, amount=100.0) is True
