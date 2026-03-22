"""
Integration tests for authenticate.services.Service.

Tests cover the core login / registration / password / PIN flows.
External side-effects (email, FCM, session login, admin history) are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from authenticate.models import User
from authenticate.schemas import RegisterSchema
from authenticate.services import Service
from exceptions.users import (
    EmailAlreadyExists,
    EmailOrPasswordIncorrect,
    PasswordIncorrect,
    PhoneNumberAlreadyExists,
)
from tests.integration.conftest import make_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_register_schema(**overrides):
    payload = {
        "full_name": "New User",
        "email": "newuser@example.com",
        "password": "StrongPass1!",
        "phone_number": "0911000001",
    }
    payload.update(overrides)
    return RegisterSchema(**payload)


def _make_fake_request(factory):
    """Build a minimal fake request with the extras that Service.register reads."""
    request = factory.post("/api/auth/register/")
    request.session = {}
    return request


# ---------------------------------------------------------------------------
# Patches that every auth-service test needs
# ---------------------------------------------------------------------------


_PATCHES = [
    "authenticate.services.Service.auth",  # django.contrib.auth module
    "authenticate.services.AdminQuery.create_user_login_history",
    "utils.services.email.client.EmailClient.send",
]


@pytest.mark.django_db
class TestRegister:
    def _register(self, rf, **schema_overrides):
        service = Service()
        request = _make_fake_request(rf)
        with (
            patch("authenticate.services.Service.auth") as mock_auth,
            patch("my_admin.orm.admin_orm.Query.create_user_login_history"),
            patch("utils.services.email.client.EmailClient.send"),
        ):
            mock_auth.login = MagicMock()
            return service.register(request, _make_register_schema(**schema_overrides))

    def test_register_creates_user_in_db(self, rf):
        user, _, _ = self._register(rf)
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_returns_access_and_refresh_tokens(self, rf):
        user, access_token, refresh_token = self._register(rf)
        assert isinstance(access_token, str) and len(access_token) > 10
        assert isinstance(refresh_token, str) and len(refresh_token) > 10

    def test_register_stores_full_name(self, rf):
        user, _, _ = self._register(rf, full_name="Alice Wonder")
        assert user.full_name == "Alice Wonder"

    def test_register_stores_full_name_no_accent(self, rf):
        user, _, _ = self._register(rf, full_name="Nguyễn Văn An")
        assert user.full_name_no_accent == "nguyen van an"

    def test_duplicate_email_raises(self, rf, db):
        make_user("newuser@example.com")
        with pytest.raises(EmailAlreadyExists):
            self._register(rf)

    def test_duplicate_phone_raises(self, rf, db):
        make_user("other@example.com", phone_number="0911000001")
        with pytest.raises(PhoneNumberAlreadyExists):
            self._register(rf)


@pytest.mark.django_db
class TestLogin:
    def _login(self, rf, email, password):
        service = Service()
        request = _make_fake_request(rf)
        with (
            patch("authenticate.services.Service.auth") as mock_auth,
            patch("my_admin.orm.admin_orm.Query.create_user_login_history"),
        ):
            mock_auth.login = MagicMock()
            return service.login(request, email, password)

    def test_login_success_returns_tokens(self, rf, db):
        make_user("login@example.com", password="TestPass1!")
        user, access, refresh = self._login(rf, "login@example.com", "TestPass1!")
        assert user.email == "login@example.com"
        assert isinstance(access, str)
        assert isinstance(refresh, str)

    def test_wrong_password_raises(self, rf, db):
        make_user("login2@example.com", password="TestPass1!")
        with pytest.raises(EmailOrPasswordIncorrect):
            self._login(rf, "login2@example.com", "WrongPass1!")

    def test_nonexistent_email_raises(self, rf, db):
        with pytest.raises(EmailOrPasswordIncorrect):
            self._login(rf, "nobody@example.com", "AnyPass1!")

    def test_inactive_user_raises(self, rf, db):
        user = make_user("inactive@example.com", password="TestPass1!")
        user.is_active = False
        user.save(update_fields=["is_active"])
        from exceptions.users import UserInactive

        with pytest.raises(UserInactive):
            self._login(rf, "inactive@example.com", "TestPass1!")


@pytest.mark.django_db
class TestChangePassword:
    def test_change_password_success(self, db):
        user = make_user("changepw@example.com", password="OldPass1!")
        service = Service()
        from authenticate.schemas import PasswordChangeRequest

        payload = PasswordChangeRequest(
            old_password="OldPass1!", new_password="NewPass2@"
        )
        with patch("utils.services.email.client.EmailClient.send"):
            service.change_password(user=user, payload=payload)
        user.refresh_from_db()
        assert user.check_password("NewPass2@")

    def test_wrong_old_password_raises(self, db):
        user = make_user("changepw2@example.com", password="CorrectPass1!")
        service = Service()
        from authenticate.schemas import PasswordChangeRequest

        payload = PasswordChangeRequest(
            old_password="WrongPass1!", new_password="NewPass2@"
        )
        with pytest.raises(PasswordIncorrect):
            service.change_password(user=user, payload=payload)
