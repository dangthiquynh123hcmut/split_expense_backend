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
from exceptions.users import EmailOrPasswordIncorrect, UserInactive
from my_admin.models import UserMonthlyActivity
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
            if not user.is_active:
                raise UserInactive
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
        return User.objects.filter(email=email, is_active=True).first()

    @staticmethod
    def get_user_by_phone_number(phone_number: str) -> TUser | None:
        return User.objects.filter(phone_number=phone_number, is_active=True).first()

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
    def delete_user(user_uid: UUID) -> None:
        User.objects.filter(uid=user_uid).delete()

    @staticmethod
    def add_attachment(user: TUser, attachment: Attachment):
        user.avatar_url = attachment
        user.save()
        return user

    @staticmethod
    def create_or_update_pin(user: TUser, pin: str):
        user.set_pin(pin)
        user.save(update_fields=["pin"])
        return True

    @staticmethod
    def update_fcm_token(user: TUser, fcm_token: str):
        user.fcm_token = fcm_token
        user.save(update_fields=["fcm_token"])
        return True

    @staticmethod
    def total_users_use_app():
        today = now().date()
        return User.objects.filter(
            is_active=True, role="USER", last_login__date=today
        ).count(), User.objects.filter(
            is_active=True, role="USER", last_login__date=today - timedelta(days=1)
        ).count()

    @staticmethod
    def count_new_users():
        today = now().date()
        return User.objects.filter(
            is_active=True, role="USER", date_joined__date=today
        ).count(), User.objects.filter(
            is_active=True, role="USER", date_joined__date=today - timedelta(days=1)
        ).count()

    @staticmethod
    def track_user_activity(user: User):
        today = now()
        activity, _ = UserMonthlyActivity.objects.get_or_create(
            user=user,
            year=today.year,
            month=today.month,
        )
        activity.login_count += 1
        activity.last_login_at = today
        user.count_use_app += 1
        user.save(update_fields=["count_use_app"])
        activity.save()

    @staticmethod
    def get_info_user(user_uid: UUID):
        return User.objects.filter(uid=user_uid).first()

    @staticmethod
    def activate_user(user: TUser):
        user.is_active = True
        user.save()
        return True

    @staticmethod
    def get_all_active_users():
        return User.objects.filter(is_active=True, is_staff=False)
