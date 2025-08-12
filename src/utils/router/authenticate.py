from http import HTTPStatus

from django.http import HttpRequest
from ninja.security import HttpBearer

from authenticate.queries import Query
from utils.router.exception import APIException


class InvalidOrExpiredToken(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "INVALID_OR_EXPIRED_TOKEN"
    message = "Invalid or expired token"


class AuthBear(HttpBearer):
    @classmethod
    def authenticate(cls, request: HttpRequest, token: str):
        authenticate_token = Query.get_access_token(token=token)

        if not authenticate_token.is_available:
            raise InvalidOrExpiredToken

        setattr(request, "user", authenticate_token.user)
        setattr(request, "token", authenticate_token)

        return request
