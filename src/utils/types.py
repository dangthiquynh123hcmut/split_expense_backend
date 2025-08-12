from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest

from authenticate.models import AuthenticateToken


if TYPE_CHECKING:
    from django.contrib.auth.models import User as TUser
else:
    TUser = object  # Django's type checker doesn't support forward references


User = get_user_model()


class UnauthenticatedRequest(HttpRequest):
    user: AnonymousUser


class AuthenticatedRequest(HttpRequest):
    user: TUser
    token: AuthenticateToken


__all__ = ["AuthenticatedRequest", "UnauthenticatedRequest", "TUser", "User"]
