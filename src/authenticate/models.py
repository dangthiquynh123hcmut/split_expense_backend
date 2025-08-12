import secrets
import uuid
from datetime import timedelta

import jwt
from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

class AuthenticateToken(models.Model):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="authenticate_token_fk_user",
        to_field="id",
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
        # Not being blacklisted and if it has an expiration date, it must be in the future
        return not self.blacklisted_at and (
            self.expires_at is not None and self.expires_at >= now()
        )

    @staticmethod
    def generate_access_token(user_id: int) -> "AuthenticateToken":
        current_time = now()
        access_token_payload = {
            "user_id": user_id,
            'type': 'access',
            "iat": current_time,
            "exp": current_time
            + timedelta(minutes=settings.ACCESS_TOKEN_LIFETIME),
        }

        return AuthenticateToken(
            user_id=user_id,
            access_token=jwt.encode(access_token_payload, settings.SECRET_KEY, algorithm="HS256"),
            expires_at=str(access_token_payload["exp"]),
        )

def generate_token():
    return secrets.token_urlsafe(128)

class ResetPassword(models.Model):
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        to_field="id",
        db_column="user_id",
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
        to_field="id",
        db_constraint=True,
        db_index=True,
        null=False,
        blank=False,
    )
    
    refresh_token = models.CharField(
        _('token'),
        max_length=255,
        unique=True,
        db_index=True,
        null=False,
        blank=False,
    )
    
    is_blacklisted = models.BooleanField(
        _('is blacklisted'),
        default=False,
    )
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    expires_at = models.DateTimeField(_('expires at'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('refresh token')
        verbose_name_plural = _('refresh tokens')
        ordering = ('-created_at',)
    
    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (not blacklisted and not expired)."""
        if self.is_blacklisted:
            return False
            
        if self.expires_at and self.expires_at <= now():
            return False
            
        return True
    
    @staticmethod
    def generate_refresh_token(user_id: int) -> "RefreshToken":
        current_time = now()
        # Refresh token expires in 7 days
        refresh_token_payload = {
            'user_id': str(user_id),
            'type': 'refresh',
            'exp': (current_time + timedelta(minutes=settings.REFRESH_TOKEN_LIFETIME)),
            'iat': current_time,
        }
        
        refresh_token = jwt.encode(
            refresh_token_payload,
            settings.SECRET_KEY,
            algorithm='HS256'
        )

        return RefreshToken(
            user_id=user_id,
            refresh_token=refresh_token,
            expires_at=str(refresh_token_payload["exp"]),
        )