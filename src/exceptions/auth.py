from http import HTTPStatus

from utils.router.exception import APIException


class InvalidOrExpiredToken(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "INVALID_OR_EXPIRED_TOKEN"
    message = "Invalid or expired token"


class InvalidOrExpiredOTP(APIException):
    error_code = HTTPStatus.FORBIDDEN
    message_code = "INVALID_OR_EXPIRED_OTP"
    message = "Invalid or expired OTP"
