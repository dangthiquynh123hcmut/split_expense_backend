from datetime import datetime, timedelta
from typing import Tuple
from uuid import uuid4

import jwt
from django.conf import settings
from django.contrib import auth as django_auth
from django.http import HttpRequest
from django.utils import timezone

from authenticate.schemas import (
    PasswordChangeRequest,
    PasswordNewRequest,
    PinNewRequest,
    RegisterSchema,
    ResetPasswordOTPRequest,
    UpdateMeSchema,
    UpdatePinRequest,
    WalletInfoResponse,
)
from exceptions.auth import InvalidOrExpiredOTP, InvalidOrExpiredToken
from exceptions.users import (
    EmailAlreadyExists,
    PasswordIncorrect,
    PhoneNumberAlreadyExists,
    UserNotFound,
)
from exceptions.wallet import PinAlreadyExists, PinIncorrect
from utils.exceptions import SecretKeyNotFound
from utils.services.base import BaseService
from utils.services.email.client import EmailClient
from utils.services.email.template import EmailTemplate
from utils.types import AuthenticatedRequest, TUser
from wallet.orm.deposit import DepositORM
from wallet.orm.transaction import TransactionORM
from wallet.orm.withdraw import WithdrawORM

from .queries import Query


class Service(BaseService):
    auth = django_auth

    def __init__(self):
        self.query = Query()
        self.email_template = EmailTemplate()
        self.email_client = EmailClient()
        self.deposit_orm = DepositORM()
        self.withdraw_orm = WithdrawORM()
        self.transaction_orm = TransactionORM()

    def register(
        self, request: HttpRequest, data: RegisterSchema
    ) -> Tuple[TUser, str, str]:
        user = self.query.get_user_by_email(email=data.email)
        if user:
            raise EmailAlreadyExists
        user = self.query.get_user_by_phone_number(phone_number=data.phone_number)
        if user:
            raise PhoneNumberAlreadyExists

        user = self.query.create_user(data=data)
        self.auth.login(request=request, user=user)
        return (
            user,
            self.query.generate_access_token(user_uid=str(user.uid)),
            self.query.generate_refresh_token(user_uid=str(user.uid)),
        )

    def login(
        self, request: HttpRequest, email: str, password: str
    ) -> Tuple[TUser, str, str]:
        user = self.query.get_user_by_email_and_password(
            email=email,
            password=password,
        )
        self.auth.login(request=request, user=user)
        return (
            user,
            self.query.generate_access_token(user_uid=str(user.uid)),
            self.query.generate_refresh_token(user_uid=str(user.uid)),
        )

    def refresh(self, request: HttpRequest, refresh_token: str) -> Tuple[str, str]:
        try:
            if not settings.SECRET_KEY:
                raise SecretKeyNotFound
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
            exp_time = datetime.fromtimestamp(
                payload.get("exp"), tz=timezone.get_current_timezone()
            )
            if exp_time < timezone.now():
                raise InvalidOrExpiredToken

            if payload.get("type") != "refresh":
                raise InvalidOrExpiredToken

            user_uid = payload.get("user_uid")
            if not user_uid:
                raise InvalidOrExpiredToken

            user = self.query.get_user_by_uid(uid=user_uid)
            if not user:
                raise InvalidOrExpiredToken
            try:
                stored_token = self.query.get_refresh_token(
                    user_uid=user_uid, refresh_token=refresh_token
                )
            except InvalidOrExpiredToken:
                raise InvalidOrExpiredToken

            new_access_token = self.query.generate_access_token(user_uid=user_uid)
            if exp_time < timezone.now() + timedelta(
                seconds=settings.REFRESH_TOKEN_REMAIN
            ):
                self.query.add_refresh_token_to_blacklist(refresh_token=stored_token)
                refresh_token = self.query.generate_refresh_token(user_uid=user_uid)

            return new_access_token, refresh_token

        except jwt.PyJWTError:
            raise InvalidOrExpiredToken

    def logout(self, request: AuthenticatedRequest) -> bool:
        self.query.logout(token=request.token)
        self.auth.logout(request=request)
        return True

    def get_me(self, user: TUser) -> TUser:
        return user

    def update_me(self, user: TUser, data: UpdateMeSchema) -> TUser:
        return self.query.update_me(user=user, data=data)

    def change_password(self, user: TUser, payload: PasswordChangeRequest):
        is_password_correct = self.query.check_password(
            user=user, password=payload.old_password
        )
        if not is_password_correct:
            raise PasswordIncorrect
        user = self.query.change_password(user=user, password=payload.new_password)

        template = self.email_template.change_password(user=user)
        self.email_client.send(messages=[template])

    def forget_password(self, email: str):
        user = self.query.get_user_by_email(email=email)
        if not user:
            raise UserNotFound

        # Inactive all old otp, create a new one
        self.query.inactive_otp(user=user)

        otp = self.query.create_otp(user=user)

        # Sending email to user
        template = self.email_template.reset_password(user=user, otp=otp)
        self.email_client.send(messages=[template])

    def creat_reset_password_token(self, payload: ResetPasswordOTPRequest):
        user = self.query.get_user_by_email(email=payload.email)
        if not user:
            raise UserNotFound
        otp = self.query.get_otp(user=user, otp=payload.otp)

        if not otp:
            raise InvalidOrExpiredOTP

        # Inactive all old token, create a new one
        self.query.inactive_reset_password_token(user=user)

        return self.query.create_reset_password_token(user=user, raw_token=str(uuid4()))

    def reset_password(self, payload: PasswordNewRequest):
        record = self.query.get_reset_password_token(token=payload.token)

        if not record or record.is_expired():
            raise InvalidOrExpiredToken

        return self.query.reset_password(record=record, payload=payload)

    def create_pin(self, user: TUser, payload: PinNewRequest):
        if user.pin not in [None, "", "None"]:
            raise PinAlreadyExists
        return self.query.create_or_update_pin(user=user, pin=payload.pin)

    def update_pin(self, user: TUser, payload: UpdatePinRequest):
        if not user.check_pin(raw_pin=payload.old_pin):
            raise PinIncorrect
        return self.query.create_or_update_pin(user=user, pin=payload.new_pin)

    def update_fcm_token(self, user: TUser, fcm_token: str):
        return self.query.update_fcm_token(user=user, fcm_token=fcm_token)

    def get_wallet_info(self, user: TUser):
        total_deposit = self.deposit_orm.get_total_deposit(user=user)
        total_withdraw = self.withdraw_orm.get_total_withdraw(user=user)
        total_transactions = self.transaction_orm.get_total_transactions(user=user)
        total_transactions = total_deposit + total_withdraw + total_transactions

        times = [
            self.deposit_orm.get_latest_deposits(user=user),
            self.withdraw_orm.get_latest_withdrawals(user=user),
            self.transaction_orm.get_latest_transactions(user=user),
        ]

        times = [t for t in times if t is not None]

        latest_time = max(times) if times else None

        return WalletInfoResponse(
            balance=user.balance,
            currency=user.currency,
            total_transactions=total_transactions,
            phone_number=user.phone_number,
            full_name=user.full_name,
            latest_time=latest_time,
        )
