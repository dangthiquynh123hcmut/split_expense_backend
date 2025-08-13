from django.utils.timezone import now

from authenticate.models import RefreshToken, ResetPassword
from authenticate.schemas import PasswordNewRequest, RegisterSchema, UpdateMeSchema
from exceptions.auth import InvalidOrExpiredToken
from exceptions.users import EmailOrPasswordIncorrect
from utils.types import TUser, User

from .models import AuthenticateToken


class Query:
    @staticmethod
    def create_user(data: RegisterSchema) -> TUser:
        return User.objects.create_user(
            username=data.email,
            password=data.password,
            first_name=data.full_name,
            phone_number=data.phone_number,
        )

    @staticmethod
    def get_user_by_email_and_password(email: str, password: str) -> TUser:
        try:
            user = User.objects.get(username=email)
        except User.DoesNotExist:
            raise EmailOrPasswordIncorrect

        # Check if password is correct
        if not user.check_password(password):
            raise EmailOrPasswordIncorrect
        return user

    @staticmethod
    def generate_access_token(user_id: int) -> str:
        new_key = AuthenticateToken.generate_access_token(user_id=user_id)
        new_key.save()
        return new_key.access_token

    @staticmethod
    def generate_refresh_token(user_id: int) -> str:
        new_key = RefreshToken.generate_refresh_token(user_id=user_id)
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
        user.first_name = data.full_name
        user.avatar = data.avatar
        user.email = data.email
        user.phone_number = data.phone_number
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
        return User.objects.filter(username=email).first()

    @staticmethod
    def get_user_by_phone_number(phone_number: str) -> TUser | None:
        return User.objects.filter(phone_number=phone_number).first()

    @staticmethod
    def inactive_reset_password_token(user: TUser):
        return ResetPassword.objects.filter(user=user, active=True).update(active=False)

    @staticmethod
    def create_reset_password_token(user: TUser, raw_token: str):
        return ResetPassword.objects.create(user=user, token=raw_token)

    @staticmethod
    def get_reset_password_token(token: str):
        try:
            return ResetPassword.objects.get(token=token, active=True)
        except ResetPassword.DoesNotExist:
            raise InvalidOrExpiredToken

    @staticmethod
    def reset_password(record: ResetPassword, payload: PasswordNewRequest):
        record.user.set_password(raw_password=payload.new_password)
        record.user.save()
        record.active = False
        record.save()
        return True

    @staticmethod
    def store_refresh_token(user_id: int, token: str) -> None:
        """
        Store refresh token in the database for validation.

        Args:
            user_id: ID of the user
            token: Refresh token to store
        """
        # Invalidate any existing refresh tokens for this user
        RefreshToken.objects.filter(user_id=user_id).update(is_blacklisted=True)

        # Store the new refresh token
        RefreshToken.objects.create(user_id=user_id, token=token, is_blacklisted=False)
