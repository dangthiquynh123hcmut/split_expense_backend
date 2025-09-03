import secrets
import uuid
from datetime import timedelta
from typing import cast
from uuid import uuid4

import jwt
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from utils.functions.remove_accents import remove_accents


class UserManager(BaseUserManager["User"]):
    def create_user(
        self, email: str, password: str | None = None, **extra_fields
    ) -> "User":
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None  # type: ignore[assignment]
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    full_name = models.CharField(max_length=255, blank=False, null=False)
    full_name_no_accent = models.TextField(blank=True, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar_url = models.URLField(max_length=500, blank=True, null=True)
    uid = models.UUIDField(default=uuid4, unique=True, editable=False, primary_key=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects: "UserManager" = UserManager()  # type: ignore[misc,assignment]

    def get_full_name(self):
        return self.full_name or super().get_full_name()

    def save(self, *args, **kwargs):
        if self.full_name:
            self.full_name_no_accent = remove_accents(self.full_name)
        return super().save(*args, **kwargs)


class AuthenticateToken(models.Model):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="authenticate_token_fk_user",
        to_field="uid",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )

    access_token = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        null=False,
        blank=False,
        default=uuid.uuid4,
    )

    expires_at = models.DateTimeField(null=True, blank=True)
    blacklisted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False)

    @property
    def is_available(self) -> bool:
        return not self.blacklisted_at and (
            self.expires_at is not None and self.expires_at >= now()
        )

    @staticmethod
    def generate_access_token(user_uid: str) -> "AuthenticateToken":
        current_time = now()
        access_token_payload = {
            "user_uid": user_uid,
            "type": "access",
            "iat": current_time,
            "exp": current_time + timedelta(minutes=settings.ACCESS_TOKEN_LIFETIME),
        }

        return AuthenticateToken(
            user_id=user_uid,
            access_token=jwt.encode(
                access_token_payload, cast(str, settings.SECRET_KEY), algorithm="HS256"
            ),
            expires_at=str(access_token_payload["exp"]),
        )


def generate_token():
    return secrets.token_urlsafe(128)


class ResetPassword(models.Model):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="uid",
        db_column="user_uid",
        related_name="reset_password_fk_user",
        db_constraint=True,
        null=False,
        blank=False,
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        null=False,
        blank=False,
        default=generate_token,
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, auto_now=False)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False)

    def is_expired(self):
        expiration_minutes = settings.RESET_PASSWORD_EXPIRES_IN_MINUTES
        return now() > self.created_at + timedelta(minutes=expiration_minutes)


class RefreshToken(models.Model):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
        to_field="uid",
        db_column="user_uid",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )

    refresh_token = models.CharField(
        _("token"),
        max_length=255,
        unique=True,
        db_index=True,
        null=False,
        blank=False,
    )

    is_blacklisted = models.BooleanField(
        _("is blacklisted"),
        default=False,
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    expires_at = models.DateTimeField(_("expires at"), null=True, blank=True)

    class Meta:
        verbose_name = _("refresh token")
        verbose_name_plural = _("refresh tokens")
        ordering = ("-created_at",)

    @property
    def is_valid(self) -> bool:
        if self.is_blacklisted:
            return False

        if self.expires_at and self.expires_at <= now():
            return False

        return True

    @staticmethod
    def generate_refresh_token(user_uid: str) -> "RefreshToken":
        current_time = now()
        refresh_token_payload = {
            "user_uid": str(user_uid),
            "type": "refresh",
            "exp": (current_time + timedelta(minutes=settings.REFRESH_TOKEN_LIFETIME)),
            "iat": current_time,
        }

        refresh_token = jwt.encode(
            refresh_token_payload, cast(str, settings.SECRET_KEY), algorithm="HS256"
        )

        return RefreshToken(
            user_id=user_uid,
            refresh_token=refresh_token,
            expires_at=str(refresh_token_payload["exp"]),
        )
