import secrets
from datetime import timedelta
from typing import List
from uuid import UUID

from django.conf import settings
from django.utils.timezone import now

from attachment.models import Attachment
from authenticate.models import (
    AuthenticateToken,
    Otp,
    RefreshToken,
    ResetPassword,
    User,
)
from authenticate.schemas import PasswordNewRequest, RegisterSchema, UpdateMeSchema
from exceptions.auth import InvalidOrExpiredToken
from exceptions.users import EmailOrPasswordIncorrect
from utils.types import TUser


class Query:
    @staticmethod
    def create_user(data: RegisterSchema) -> TUser:
        return User.objects.create_user(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            phone_number=data.phone_number,
        )

    @staticmethod
    def get_user_by_email_and_password(email: str, password: str) -> TUser:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise EmailOrPasswordIncorrect
        if not user.check_password(password):
            raise EmailOrPasswordIncorrect
        return user

    @staticmethod
    def generate_access_token(user_uid: str) -> str:
        new_key = AuthenticateToken.generate_access_token(user_uid=user_uid)
        new_key.save()
        return new_key.access_token

    @staticmethod
    def generate_refresh_token(user_uid: str) -> str:
        new_key = RefreshToken.generate_refresh_token(user_uid=user_uid)
        new_key.save()
        return new_key.refresh_token

    @staticmethod
    def logout(token: AuthenticateToken) -> bool:
        token.blacklisted_at = now()
        token.save()
        return True

    @staticmethod
    def get_access_token(token: str) -> AuthenticateToken:
        try:
            return AuthenticateToken.objects.get(access_token=token)
        except AuthenticateToken.DoesNotExist:
            raise InvalidOrExpiredToken

    @staticmethod
    def update_me(user: TUser, data: UpdateMeSchema) -> TUser:
        user.full_name = data.full_name
        user.email = data.email
        user.phone_number = data.phone_number
        user.currency = data.currency
        user.save()
        return user

    @staticmethod
    def check_password(user: TUser, password: str) -> bool:
        return user.check_password(raw_password=password)

    @staticmethod
    def change_password(user: TUser, password: str) -> TUser:
        user.set_password(raw_password=password)
        user.save()
        return user

    @staticmethod
    def get_user_by_email(email: str) -> TUser | None:
        return User.objects.filter(email=email).first()

    @staticmethod
    def get_user_by_phone_number(phone_number: str) -> TUser | None:
        return User.objects.filter(phone_number=phone_number).first()

    @staticmethod
    def get_user_by_uid(uid: UUID) -> TUser | None:
        try:
            return User.objects.get(
                uid=uid,
                is_active=True,
            )
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_uids(uids: List[UUID]):
        return User.objects.filter(uid__in=uids, is_active=True, is_staff=False)

    @staticmethod
    def inactive_otp(user: TUser):
        return Otp.objects.filter(
            user=user,
            created_at__lt=now() - timedelta(minutes=settings.OTP_LIFETIME),
        ).delete()

    @staticmethod
    def create_otp(user: TUser) -> Otp:
        otp = "".join(str(secrets.randbelow(10)) for _ in range(6))
        return Otp.objects.create(user=user, otp=otp)

    @staticmethod
    def get_otp(user: TUser, otp: str):
        try:
            return Otp.objects.get(
                user=user,
                otp=otp,
                created_at__gt=now() - timedelta(minutes=settings.OTP_LIFETIME),
            )
        except Otp.DoesNotExist:
            return None

    @staticmethod
    def inactive_reset_password_token(user: TUser):
        return ResetPassword.objects.filter(user=user, active=True).update(active=False)

    @staticmethod
    def create_reset_password_token(user: TUser, raw_token: str) -> ResetPassword:
        return ResetPassword.objects.create(user=user, token=raw_token)

    @staticmethod
    def get_reset_password_token(token: str):
        try:
            return ResetPassword.objects.get(token=token, active=True)
        except ResetPassword.DoesNotExist:
            return None

    @staticmethod
    def reset_password(record: ResetPassword, payload: PasswordNewRequest):
        record.user.set_password(raw_password=payload.new_password)
        record.user.save()
        record.active = False
        record.save()
        return True

    @staticmethod
    def store_refresh_token(user_uid: str, token: str) -> None:
        RefreshToken.objects.filter(user_id=user_uid).update(is_blacklisted=True)

        RefreshToken.objects.create(
            user_id=user_uid,
            refresh_token=token,
            is_blacklisted=False,
            expires_at=now() + timedelta(days=settings.REFRESH_TOKEN_LIFETIME),
        )

    @staticmethod
    def get_refresh_token(user_uid: str, refresh_token: str):
        return RefreshToken.objects.get(
            refresh_token=refresh_token,
            user_id=user_uid,
            is_blacklisted=False,
            expires_at__gt=now(),
        )

    @staticmethod
    def add_refresh_token_to_blacklist(refresh_token: RefreshToken) -> None:
        refresh_token.is_blacklisted = True
        refresh_token.save()

    @staticmethod
    def delete_user(user: TUser) -> None:
        user.is_active = False
        user.save()

    @staticmethod
    def add_attachment(user: TUser, attachment: Attachment):
        user.avatar_url = attachment
        user.save()
        return user
