import re

from ninja import Schema
from pydantic import Field, field_validator

from exceptions.users import (
    InvalidEmailFormat,
    InvalidPhoneNumberFormat,
    WeakPasswordError,
)
from utils.schemas.user import UserSchema


class RegisterSchema(Schema):
    full_name: str
    email: str
    password: str = Field(..., min_length=8)
    phone_number: str

    @field_validator("email")
    def validate_email(cls, v):
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, v):
            raise InvalidEmailFormat
        return v.lower()

    @field_validator("password")
    def validate_password(cls, v):
        if (
            not re.search(r"[A-Z]", v)
            or not re.search(r"[a-z]", v)
            or not re.search(r"[0-9]", v)
            or not re.search(r"[^A-Za-z0-9]", v)
        ):
            raise WeakPasswordError
        return v

    @field_validator("phone_number")
    def validate_phone_number(cls, v):
        if not v.isdigit() or len(v) != 10 or not v.startswith("0"):
            raise InvalidPhoneNumberFormat
        return v


class LoginSchema(Schema):
    email: str
    password: str


class UpdateMeSchema(Schema):
    full_name: str
    email: str
    phone_number: str
    currency: str


class LoginResponseSchema(Schema):
    access_token: str
    refresh_token: str
    user: UserSchema


class MeResponseSchema(UserSchema):
    currency: str


class RefreshResponse(Schema):
    access_token: str
    refresh_token: str


class RefreshRequest(Schema):
    refresh_token: str


class PasswordChangeRequest(Schema):
    old_password: str
    new_password: str = Field(..., min_length=8)


class PasswordForgetRequest(Schema):
    email: str


class ResetPasswordOTPRequest(Schema):
    otp: str
    email: str


class ResetPasswordToken(Schema):
    token: str


class PasswordNewRequest(Schema):
    token: str
    new_password: str = Field(..., min_length=8)
