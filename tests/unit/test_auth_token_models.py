"""
Unit tests for authenticate.models token/PIN helper methods.

These tests verify instance-level properties and methods without persisting
anything to the database — model instances are built in memory only.
"""

from datetime import timedelta

from django.utils.timezone import now

from authenticate.models import AuthenticateToken, RefreshToken


# ---------------------------------------------------------------------------
# AuthenticateToken.is_available
# ---------------------------------------------------------------------------


class TestAuthenticateTokenIsAvailable:
    def _make_token(self, blacklisted_at=None, expires_at=None):
        """Construct an unsaved AuthenticateToken instance."""
        token = AuthenticateToken.__new__(AuthenticateToken)
        token.blacklisted_at = blacklisted_at
        token.expires_at = expires_at
        return token

    def test_not_blacklisted_and_not_expired_is_available(self):
        token = self._make_token(
            blacklisted_at=None, expires_at=now() + timedelta(hours=1)
        )
        assert token.is_available is True

    def test_blacklisted_is_not_available(self):
        token = self._make_token(
            blacklisted_at=now() - timedelta(minutes=5),
            expires_at=now() + timedelta(hours=1),
        )
        assert token.is_available is False

    def test_expired_is_not_available(self):
        token = self._make_token(
            blacklisted_at=None,
            expires_at=now() - timedelta(seconds=1),
        )
        assert token.is_available is False

    def test_no_expires_at_is_not_available(self):
        token = self._make_token(blacklisted_at=None, expires_at=None)
        assert token.is_available is False

    def test_both_blacklisted_and_expired_is_not_available(self):
        token = self._make_token(
            blacklisted_at=now() - timedelta(hours=1),
            expires_at=now() - timedelta(hours=2),
        )
        assert token.is_available is False


# ---------------------------------------------------------------------------
# RefreshToken.is_valid
# ---------------------------------------------------------------------------


class TestRefreshTokenIsValid:
    def _make_token(self, is_blacklisted=False, expires_at=None):
        token = RefreshToken.__new__(RefreshToken)
        token.is_blacklisted = is_blacklisted
        token.expires_at = expires_at
        return token

    def test_not_blacklisted_and_not_expired_is_valid(self):
        token = self._make_token(
            is_blacklisted=False,
            expires_at=now() + timedelta(hours=1),
        )
        assert token.is_valid is True

    def test_blacklisted_is_not_valid(self):
        token = self._make_token(
            is_blacklisted=True,
            expires_at=now() + timedelta(hours=1),
        )
        assert token.is_valid is False

    def test_expired_is_not_valid(self):
        token = self._make_token(
            is_blacklisted=False,
            expires_at=now() - timedelta(seconds=1),
        )
        assert token.is_valid is False

    def test_no_expires_at_is_valid(self):
        """expires_at=None means the token never expires."""
        token = self._make_token(is_blacklisted=False, expires_at=None)
        assert token.is_valid is True

    def test_exactly_expired_is_not_valid(self):
        """A token that expired at exactly the current time is no longer valid."""
        token = self._make_token(
            is_blacklisted=False,
            expires_at=now() - timedelta(microseconds=1),
        )
        assert token.is_valid is False
