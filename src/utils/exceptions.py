from http import HTTPStatus

from utils.router.exception import APIException


class InvalidEmailOrPassword(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "INVALID_EMAIL_OR_PASSWORD"
    message = "Invalid email or password"


class InvalidOldPassword(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "INVALID_PASSWORD"
    message = "Password is mismatch"


class PasswordIsTooWeak(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "PASSWORD_TOO_WEAK"
    message = "Password is too weak"


class DeleteIsDenied(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "DELETE_IS_DENIED"
    message = "Delete is denied"


class UpdatedIsDenied(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "UPDATED_IS_DENIED"
    message = "Updated is denied"


class GetIsDenied(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "GET_IS_DENIED"
    message = "Get is denied"


class CreateIsDenied(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "CREATE_IS_DENIED"
    message = "Create is denied"


class SecretKeyNotFound(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "SECRET_KEY_NOT_FOUND"
    message = "Secret key not found"
