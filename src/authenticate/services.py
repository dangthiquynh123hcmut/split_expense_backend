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
    RegisterSchema,
    UpdateMeSchema,
)
from exceptions.auth import InvalidOrExpiredToken
from exceptions.users import (
    EmailAlreadyExists,
    PasswordIncorrect,
    PhoneNumberAlreadyExists,
    UserNotFound,
)
from utils.exceptions import SecretKeyNotFound
from utils.services.base import BaseService
from utils.services.email.client import EmailClient
from utils.services.email.template import EmailTemplate
from utils.types import AuthenticatedRequest, TUser

from .queries import Query


class Service(BaseService):
    auth = django_auth

    def __init__(self):
        self.query = Query()
        self.email_template = EmailTemplate()
        self.email_client = EmailClient()

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

            if payload.get("type") != "refresh":
                raise InvalidOrExpiredToken

            user_uid = payload.get("user_uid")
            if not user_uid:
                raise InvalidOrExpiredToken

            try:
                stored_token = self.query.get_refresh_token(
                    user_uid=user_uid, refresh_token=refresh_token
                )
            except InvalidOrExpiredToken:
                raise InvalidOrExpiredToken

            new_access_token = self.query.generate_access_token(user_uid=user_uid)
            exp_time = datetime.fromtimestamp(
                payload.get("exp"), tz=timezone.get_current_timezone()
            )
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

    def update_me(self, user: TUser, data: UpdateMeSchema) -> TUser:
        is_user = self.query.get_user_by_email(email=data.email)
        if is_user and is_user.email != user.email:
            raise EmailAlreadyExists
        is_user = self.query.get_user_by_phone_number(phone_number=data.phone_number)
        if is_user and is_user.phone_number != user.phone_number:
            raise PhoneNumberAlreadyExists
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

        # Inactive all old tokens, create a new one
        self.query.inactive_reset_password_token(user=user)

        token = self.query.create_reset_password_token(
            user=user, raw_token=str(uuid4())
        )

        # Sending email to user
        template = self.email_template.reset_password(user=user, token=token.token)
        self.email_client.send(messages=[template])

    def reset_password(self, payload: PasswordNewRequest):
        record = self.query.get_reset_password_token(token=payload.token)

        if not record or record.is_expired():
            raise InvalidOrExpiredToken

        return self.query.reset_password(record=record, payload=payload)
