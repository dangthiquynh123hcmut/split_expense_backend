"""
Unit tests for authenticate.schemas — specifically the field validators on
RegisterSchema.  No database access required.

The validators in RegisterSchema raise custom APIException subclasses
(InvalidEmailFormat, WeakPasswordError, InvalidPhoneNumberFormat) directly
rather than pydantic ValidationError, so tests assert on those types.
The only case where pydantic's own ValidationError fires is the Field
min_length constraint on passwords shorter than 8 characters.
"""

import pytest
from pydantic import ValidationError

from authenticate.schemas import RegisterSchema
from exceptions.users import (
    InvalidEmailFormat,
    InvalidPhoneNumberFormat,
    WeakPasswordError,
)


def _valid_payload(**overrides):
    """Return a dict for a valid RegisterSchema, with optional overrides."""
    base = {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "StrongPass1!",
        "phone_number": "0912345678",
    }
    base.update(overrides)
    return base


class TestRegisterSchemaEmail:
    def test_valid_email_accepted(self):
        schema = RegisterSchema(**_valid_payload())
        assert schema.email == "test@example.com"

    def test_email_is_lowercased(self):
        schema = RegisterSchema(**_valid_payload(email="USER@Example.COM"))
        assert schema.email == "user@example.com"

    def test_missing_at_sign_raises(self):
        with pytest.raises(InvalidEmailFormat):
            RegisterSchema(**_valid_payload(email="notanemail"))

    def test_missing_tld_raises(self):
        with pytest.raises(InvalidEmailFormat):
            RegisterSchema(**_valid_payload(email="user@domain"))

    def test_empty_local_part_raises(self):
        with pytest.raises(InvalidEmailFormat):
            RegisterSchema(**_valid_payload(email="@example.com"))


class TestRegisterSchemaPassword:
    def test_strong_password_accepted(self):
        schema = RegisterSchema(**_valid_payload(password="Abcdef1@"))
        assert schema.password == "Abcdef1@"

    def test_no_uppercase_raises(self):
        with pytest.raises(WeakPasswordError):
            RegisterSchema(**_valid_payload(password="abcdef1@"))

    def test_no_lowercase_raises(self):
        with pytest.raises(WeakPasswordError):
            RegisterSchema(**_valid_payload(password="ABCDEF1@"))

    def test_no_digit_raises(self):
        with pytest.raises(WeakPasswordError):
            RegisterSchema(**_valid_payload(password="Abcdefg!"))

    def test_no_special_char_raises(self):
        with pytest.raises(WeakPasswordError):
            RegisterSchema(**_valid_payload(password="Abcdef12"))

    def test_too_short_raises(self):
        """Password shorter than 8 chars is rejected by the Field min_length constraint."""
        with pytest.raises(ValidationError):
            RegisterSchema(**_valid_payload(password="Ab1!"))


class TestRegisterSchemaPhoneNumber:
    def test_valid_phone_accepted(self):
        schema = RegisterSchema(**_valid_payload(phone_number="0123456789"))
        assert schema.phone_number == "0123456789"

    def test_phone_not_starting_with_zero_raises(self):
        with pytest.raises(InvalidPhoneNumberFormat):
            RegisterSchema(**_valid_payload(phone_number="1234567890"))

    def test_phone_with_letters_raises(self):
        with pytest.raises(InvalidPhoneNumberFormat):
            RegisterSchema(**_valid_payload(phone_number="012345678a"))

    def test_phone_too_short_raises(self):
        with pytest.raises(InvalidPhoneNumberFormat):
            RegisterSchema(**_valid_payload(phone_number="012345678"))

    def test_phone_too_long_raises(self):
        with pytest.raises(InvalidPhoneNumberFormat):
            RegisterSchema(**_valid_payload(phone_number="01234567890"))

    def test_phone_with_spaces_raises(self):
        with pytest.raises(InvalidPhoneNumberFormat):
            RegisterSchema(**_valid_payload(phone_number="0123 45678"))
