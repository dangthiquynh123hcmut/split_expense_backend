
from typing import Tuple
from uuid import uuid4

from django.contrib import auth as django_auth
from django.http import HttpRequest

from authenticate.schemas import PasswordChangeRequest, PasswordNewRequest, RegisterSchema, UpdateMeSchema
from exceptions.auth import InvalidOrExpiredToken
from exceptions.users import PasswordIncorrect, UserNotFound, EmailAlreadyExists, PhoneNumberAlreadyExists
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
    
        user = self.query.create_user(
           data=data
        )
        return user, self.query.generate_access_token(user_id=user.id), self.query.generate_refresh_token(user_id=user.id)

    def login(
        self, request: HttpRequest, email: str, password: str
    ) -> Tuple[TUser, str, str]:
        user = self.query.get_user_by_email_and_password(
            email=email,
            password=password,
        )
        self.auth.login(request=request, user=user)
        return user, self.query.generate_access_token(user_id=user.id), self.query.generate_refresh_token(user_id=user.id)

    def get_me(self, user: TUser) -> TUser:
        return user

    def logout(self, request: AuthenticatedRequest) -> bool:
        self.query.logout(token=request.token)
        self.auth.logout(request=request)
        return True

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

        if record.is_expired():
            raise InvalidOrExpiredToken

        return self.query.reset_password(record=record, payload=payload)
